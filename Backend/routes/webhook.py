"""
routes/webhook.py
-----------------
Twilio webhook endpoints.

  POST /webhook/whatsapp         -- inbound WhatsApp messages
  GET|POST /webhook/voice        -- inbound phone calls (IVR root)
  POST /webhook/voice/gather/<businessId>/<nodeId>  -- DTMF digit handler
"""

import logging
import threading

from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

import config
from database import bots_col
from utils.helpers import (
    find_bot_for_customer,
    upsert_session,
    log_message,
    get_or_init_credits,
    deduct_credit,
)
from services.messaging import build_reply, send_whatsapp
from services.mandi     import handle_mandi_flow
from services.ai_engine import handle_ai_flow
from services.ivr       import build_twiml, webhook_base_url

log = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)


# ---------------------------------------------------------------------------
# WhatsApp
# ---------------------------------------------------------------------------

@webhook_bp.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    Entry point for all inbound WhatsApp messages from Twilio.

    Returns 204 immediately and processes the reply in a daemon thread so
    Twilio does not time out waiting for a response.
    """
    incoming_msg   = request.values.get('Body', '').strip()
    from_number    = request.values.get('From', '')
    num_media      = int(request.values.get('NumMedia', 0))
    customer_phone = from_number.replace('whatsapp:', '')

    # Ignore Twilio status callbacks that arrive from our own number.
    own_number = config.TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')
    if from_number == config.TWILIO_WHATSAPP_NUMBER or customer_phone == own_number:
        log.debug("[WEBHOOK] Ignoring self-callback from %s", from_number)
        return '', 204

    log.info("[WEBHOOK] Inbound from %s: %r", customer_phone, incoming_msg)

    bot = find_bot_for_customer(customer_phone)
    if not bot:
        log.warning("[WEBHOOK] No active bot found")
        resp = MessagingResponse()
        resp.message("No active bot is configured right now. Please try again later.")
        return str(resp), 200, {'Content-Type': 'text/xml'}

    business_id = bot.get('businessId', '')
    user_id     = bot.get('ownerUserId', '')

    upsert_session(customer_phone, business_id)
    log_message(business_id, user_id, customer_phone, incoming_msg, 'user')

    if num_media > 0:
        log.info("[WEBHOOK] Media received: %s", request.values.get('MediaUrl0', ''))

    # Credit check — fast synchronous read before spawning the background thread.
    if user_id:
        credits = get_or_init_credits(user_id)
        if credits <= 0:
            log.warning("[CREDITS] User %s has no credits — bot %s blocked", user_id, business_id)

            def _send_low_credits():
                try:
                    send_whatsapp(
                        from_number,
                        "Your BotSetu message credits are exhausted. "
                        "Please top up at https://botsetu.com/payment to continue.",
                    )
                except Exception as exc:
                    log.error("[WEBHOOK] Failed to send low-credits notice: %s", exc)

            threading.Thread(target=_send_low_credits, daemon=True).start()
            return '', 204

    def _process_and_reply():
        bot_type = bot.get('botType', 'normal')
        try:
            if bot_type == 'ai':
                reply = handle_ai_flow(bot, customer_phone, incoming_msg)
            elif bot.get('useCaseType') == 'mandi_booking':
                reply = handle_mandi_flow(bot, customer_phone, incoming_msg)
            else:
                reply = build_reply(bot, incoming_msg)
        except Exception as exc:
            log.error("[WEBHOOK] Reply generation error: %s", exc)
            reply = ''

        if not reply:
            log.info("[WEBHOOK] No reply for bot %s (autoReply off or empty result)", business_id)
            return

        try:
            sid = send_whatsapp(from_number, reply)
            log_message(business_id, user_id, customer_phone, reply, 'bot')
            if user_id:
                deduct_credit(user_id)
            log.info("[WEBHOOK] Reply sent to %s  SID=%s", customer_phone, sid)
        except Exception as exc:
            log.error("[WEBHOOK] Twilio send failed: %s", exc)

    threading.Thread(target=_process_and_reply, daemon=True).start()
    return '', 204


# ---------------------------------------------------------------------------
# Voice / IVR
# ---------------------------------------------------------------------------

@webhook_bp.route('/webhook/voice', methods=['GET', 'POST'])
def voice_webhook():
    """
    Handle an incoming phone call and serve the IVR root menu.
    Set this as "A call comes in" in Twilio Console -> Phone Numbers.
    """
    from_number = request.values.get('From', 'unknown')
    log.info("[VOICE] Inbound call from %s", from_number)

    bot = bots_col.find_one(
        {'verificationStatus': 'verified', 'useCaseType': 'ivr'},
        sort=[('activatedAt', -1)],
    )

    if not bot:
        response = VoiceResponse()
        response.say("No IVR bot is currently active. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    ivr_nodes = bot.get('ivrNodes') or []
    root_node = next((n for n in ivr_nodes if n['id'] == 'node_root'), None)

    if not root_node or not (root_node.get('message') or '').strip():
        response = VoiceResponse()
        response.say("This bot has no IVR flow configured. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    log.info("[VOICE] Routing to IVR bot %s", bot['businessId'])
    return build_twiml(root_node, bot['businessId'])


@webhook_bp.route('/webhook/voice/gather/<business_id>/<node_id>', methods=['POST'])
def voice_gather(business_id: str, node_id: str):
    """
    Handle a DTMF digit input from a Twilio <Gather> and navigate the IVR tree.
    """
    digit = request.values.get('Digits', '').strip()
    log.info("[VOICE] Gather: bot=%s node=%s digit=%r", business_id, node_id, digit)

    bot = bots_col.find_one({'businessId': business_id})
    if not bot:
        response = VoiceResponse()
        response.say("Bot not found. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    ivr_nodes    = bot.get('ivrNodes') or []
    current_node = next((n for n in ivr_nodes if n['id'] == node_id), None)

    if not current_node:
        response = VoiceResponse()
        response.say("Invalid menu. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    options = current_node.get('options') or []
    try:
        opt_index = int(digit) - 1
        if 0 <= opt_index < len(options):
            next_node_id = options[opt_index].get('nextNodeId', '')
            next_node    = next((n for n in ivr_nodes if n['id'] == next_node_id), None)
            if next_node:
                return build_twiml(next_node, business_id)
    except (ValueError, IndexError):
        pass

    response = VoiceResponse()
    response.say("Invalid option. Please try again. Goodbye.", voice='alice')
    response.hangup()
    return str(response), 200, {'Content-Type': 'text/xml'}
