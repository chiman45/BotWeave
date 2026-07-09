"""
routes/health.py
----------------
Lightweight health-check and root info endpoints.

  GET /          -- service name and route index
  GET /health    -- liveness probe (Twilio number + webhook URL)
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify
import config

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
