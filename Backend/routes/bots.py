"""
routes/bots.py
--------------
Bot lifecycle endpoints.

  POST /api/bot/activate      -- allocate Twilio number to a bot
  POST /api/bot/deactivate    -- remove allocation and clear sessions
  GET  /api/bot/ivr-number    -- return Twilio phone + voice webhook URL
  GET  /api/bot/sandbox-info  -- return WhatsApp sandbox number + join keyword
  POST /api/message/send      -- manually send an outbound WhatsApp message
"""

import logging
import os

from flask import Blueprint, request, jsonify

import config
from database import bots_col, sessions_col
from utils.helpers import now, log_message
from services.messaging import send_whatsapp
from services.ivr import webhook_base_url

log = logging.getLogger(__name__)

bots_bp = Blueprint('bots', __name__)


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------

@bots_bp.route('/api/bot/activate', methods=['POST'])
def activate_bot():
    """
    Activate a bot and return the shared Twilio WhatsApp number.

    Body:
        { "businessId": "...", "userId": "..." }
    """
    data        = request.get_json(force=True) or {}
    business_id = data.get('businessId')
    user_id     = data.get('userId')

    if not business_id or not user_id:
        return jsonify({'error': 'businessId and userId are required'}), 400

    bot = bots_col.find_one({'businessId': business_id, 'ownerUserId': user_id})
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404

    if bot.get('allocatedNumber'):
        return jsonify({
            'message':         'Bot already active',
            'allocatedNumber': bot['allocatedNumber'],
            'businessId':      business_id,
        })

    display_number = config.TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')
    ts = now()

    bots_col.update_one(
        {'businessId': business_id, 'ownerUserId': user_id},
        {'$set': {
            'allocatedNumber':    display_number,
            'verificationStatus': 'verified',
            'activatedAt':        ts,
            'updatedAt':          ts,
        }},
    )

    log.info("[ACTIVATE] Bot %s activated -> %s", business_id, display_number)

    webhook_url = os.getenv('WEBHOOK_URL', '')
    return jsonify({
        'message':         'Bot activated successfully',
        'allocatedNumber': display_number,
        'businessId':      business_id,
        'activatedAt':     ts.isoformat(),
        'webhookUrl':      webhook_url,
    })


@bots_bp.route('/api/bot/deactivate', methods=['POST'])
def deactivate_bot():
    """
    Deactivate a bot — clear the allocated number and drop all customer sessions.

    Body:
        { "businessId": "...", "userId": "..." }
    """
    data        = request.get_json(force=True) or {}
    business_id = data.get('businessId')
    user_id     = data.get('userId')

    if not business_id or not user_id:
        return jsonify({'error': 'businessId and userId are required'}), 400

    bot = bots_col.find_one({'businessId': business_id, 'ownerUserId': user_id})
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404

    ts = now()
    bots_col.update_one(
        {'businessId': business_id, 'ownerUserId': user_id},
        {
            '$set':   {'verificationStatus': 'inactive', 'updatedAt': ts},
            '$unset': {'allocatedNumber': '', 'activatedAt': ''},
        },
    )

    sessions_col.delete_many({'businessId': business_id})

    log.info("[DEACTIVATE] Bot %s deactivated", business_id)
    return jsonify({'message': 'Bot deactivated successfully', 'businessId': business_id})


# ---------------------------------------------------------------------------
# IVR / sandbox info
# ---------------------------------------------------------------------------

@bots_bp.route('/api/bot/ivr-number', methods=['GET'])
def get_ivr_number():
    """Return the Twilio phone number and voice webhook URL for IVR bots."""
    base  = webhook_base_url()
    return jsonify({
        'phoneNumber':     config.TWILIO_PHONE_NUMBER,
        'voiceWebhookUrl': f'{base}/webhook/voice',
    })


@bots_bp.route('/api/bot/sandbox-info', methods=['GET'])
def get_sandbox_info():
    """Return WhatsApp sandbox number and join keyword for QR / link generation."""
    raw_number = config.TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '').lstrip('+')
    join_text  = os.getenv('TWILIO_SANDBOX_KEYWORD', '').strip().strip('"')
    return jsonify({
        'whatsappNumber': raw_number,
        'joinText':       join_text,
    })


# ---------------------------------------------------------------------------
# Manual outbound message
# ---------------------------------------------------------------------------

@bots_bp.route('/api/message/send', methods=['POST'])
def send_message():
    """
    Manually send a WhatsApp message from the dashboard.

    Body:
        { "to": "+919876543210", "body": "Hello!", "businessId": "..." }
    """
    data        = request.get_json(force=True) or {}
    to          = (data.get('to') or '').strip()
    body        = (data.get('body') or '').strip()
    business_id = (data.get('businessId') or '').strip()

    if not to or not body:
        return jsonify({'error': 'to and body are required'}), 400

    to_wa = to if to.startswith('whatsapp:') else f'whatsapp:{to}'

    try:
        sid = send_whatsapp(to_wa, body)
        log.info("[SEND] Manual message to %s  SID=%s", to, sid)

        if business_id:
            bot = bots_col.find_one({'businessId': business_id})
            if bot:
                log_message(business_id, bot.get('ownerUserId', ''), to, body, 'bot')

        return jsonify({'success': True, 'messageSid': sid})
    except Exception as exc:
        log.error("[SEND] Failed: %s", exc)
        return jsonify({'error': str(exc)}), 500
