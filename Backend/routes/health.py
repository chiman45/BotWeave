"""
routes/health.py
----------------
Lightweight health-check and root info endpoints.

  GET /          -- service name and route index
  GET /health    -- liveness probe (Twilio number + webhook URL)
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
import config
from database import bots_col, sessions_col

log = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'])
def index():
    return jsonify({
        'name':    'BotSetu Backend',
        'version': '2.0.0',
        'routes': [
            'GET  /health',
            'POST /webhook/whatsapp',
            'GET|POST /webhook/voice',
            'POST /webhook/voice/gather/<businessId>/<nodeId>',
            'POST /api/bot/activate',
            'POST /api/bot/deactivate',
            'GET  /api/bot/ivr-number',
            'GET  /api/bot/sandbox-info',
            'POST /api/message/send',
            'GET  /api/conversations/<businessId>',
            'GET  /api/conversations/<businessId>/<phone>',
            'PATCH /api/conversations/<businessId>/<phone>/read',
            'DELETE /api/conversations/<businessId>/<phone>',
            'GET|POST /api/payments/<userId>',
            'PATCH|DELETE /api/payments/<paymentId>',
            'GET  /api/bookings/<businessId>',
            'GET  /api/ai/models',
            'POST /api/ai/kb/<businessId>',
            'GET  /api/ai/kb/<businessId>',
            'DELETE /api/ai/kb/<businessId>',
            'GET  /api/ai/kb/progress/<jobId>',
            'POST /api/ai/generate-template',
            'GET  /api/templates',
            'GET  /api/templates/<templateId>',
        ]
    })


@health_bp.route('/health', methods=['GET'])
def health():
    """Liveness probe — returns 200 when the server is up."""
    return jsonify({
        'status':        'ok',
        'twilioNumber':  config.TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', ''),
        'webhookUrl':    config.WEBHOOK_URL,
        'timestamp':     datetime.now(timezone.utc).isoformat(),
    })


@health_bp.route('/api/bot/active', methods=['GET'])
def active_bot():
    """
    Debug endpoint — shows which bot will handle the next incoming message.

    Optional query param:
      ?phone=+919876543210  -- also shows which bot that specific number is pinned to
    """
    phone = request.args.get('phone', '').strip()

    # All verified bots, newest first
    all_verified = list(
        bots_col.find(
            {'verificationStatus': 'verified'},
            {'_id': 0, 'businessId': 1, 'businessName': 1, 'botType': 1,
             'useCaseType': 1, 'activatedAt': 1, 'ownerUserId': 1},
        ).sort('activatedAt', -1)
    )

    for b in all_verified:
        if isinstance(b.get('activatedAt'), datetime):
            b['activatedAt'] = b['activatedAt'].isoformat()

    # The bot that would receive the NEXT new message (no session)
    default_bot = all_verified[0] if all_verified else None

    result = {
        'defaultBot':   default_bot,
        'allVerified':  all_verified,
        'verifiedCount': len(all_verified),
    }

    # If a phone number is supplied, show its pinned session
    if phone:
        clean = phone.replace('whatsapp:', '')
        session = sessions_col.find_one({'customerPhone': clean}, {'_id': 0})
        pinned_bot = None
        if session:
            pinned_bot = bots_col.find_one(
                {'businessId': session['businessId']},
                {'_id': 0, 'businessId': 1, 'businessName': 1,
                 'botType': 1, 'useCaseType': 1},
            )
        result['phone']     = clean
        result['session']   = session
        result['pinnedBot'] = pinned_bot

    return jsonify(result)


@health_bp.route('/api/bot/session/<path:phone>', methods=['DELETE'])
def clear_session(phone: str):
    """
    Clear the bot session for a customer phone number.
    Their next message will be routed to the default (most recently activated) bot.

    Usage:  DELETE /api/bot/session/+919876543210
    """
    clean  = phone.replace('whatsapp:', '')
    result = sessions_col.delete_one({'customerPhone': clean})
    if result.deleted_count:
        log.info("[SESSION] Cleared session for %s", clean)
        return jsonify({'cleared': True, 'phone': clean})
    return jsonify({'cleared': False, 'phone': clean, 'message': 'No session found'})
