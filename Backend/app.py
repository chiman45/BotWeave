"""
BotSetu Backend — Single Entry Point
=====================================
Combines:
  • Twilio WhatsApp webhook (incoming/outgoing messages)
  • Bot activation (allocates the shared Twilio number)
  • Conversation logger
  • Payment manager

One Twilio account · One WhatsApp number · Multiple bots
Messages are routed to the correct bot via sticky customer sessions stored in MongoDB.

Run:
    python app.py

Twilio webhook URL (set in Twilio console):
    POST https://<your-domain>/webhook/whatsapp
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from datetime import datetime
from typing import Optional, Dict, List
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('botsetu.log', encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Config  (all values come from Backend/.env)
# ─────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID     = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN      = os.getenv('TWILIO_AUTH_TOKEN')
# Format: whatsapp:+14155238886  (the Twilio sandbox or approved number)
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
MONGODB_URI            = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
PORT                   = int(os.getenv('PORT', 5000))

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")

if not TWILIO_WHATSAPP_NUMBER:
    raise RuntimeError("TWILIO_WHATSAPP_NUMBER must be set in .env  (e.g. whatsapp:+14155238886)")

# ─────────────────────────────────────────────────────────────
# Clients
# ─────────────────────────────────────────────────────────────
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

mongo_client      = MongoClient(MONGODB_URI)
db                = mongo_client['BotSetu']
bots_col          = db['User-data']          # created by Next.js /api/bot
conversations_col = db['conversations']       # message history
sessions_col      = db['bot-sessions']        # customer phone → businessId mapping
payments_col      = db['payments']            # payment records

# Indexes (idempotent — safe to run every start)
sessions_col.create_index([('customerPhone', ASCENDING)], unique=True)
conversations_col.create_index([('businessId', ASCENDING), ('phoneNumber', ASCENDING)])
conversations_col.create_index([('timestamp', DESCENDING)])

app = Flask(__name__)
CORS(app)


# ═════════════════════════════════════════════════════════════
# ── HELPERS
# ═════════════════════════════════════════════════════════════

def _serialize(doc: dict) -> dict:
    """Convert MongoDB ObjectId fields to strings."""
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc


def _find_bot_for_customer(customer_phone: str) -> Optional[Dict]:
    """Return the bot that owns this customer's session, or the first active bot."""
    session = sessions_col.find_one({'customerPhone': customer_phone})
    if session:
        bot = bots_col.find_one({'businessId': session['businessId']})
        if bot:
            return bot
    # Fallback: first verified bot
    return bots_col.find_one({'verificationStatus': 'verified'})


def _upsert_session(customer_phone: str, business_id: str) -> None:
    """Stick a customer to a bot for the lifetime of the conversation."""
    sessions_col.update_one(
        {'customerPhone': customer_phone},
        {'$set': {'businessId': business_id, 'updatedAt': datetime.utcnow()}},
        upsert=True
    )


def _log_message(business_id: str, user_id: str, customer_phone: str,
                 content: str, sender: str) -> None:
    """Persist a message and increment bot message counter."""
    conversations_col.insert_one({
        'businessId':    business_id,
        'userId':        user_id,
        'phoneNumber':   customer_phone,
        'messageContent': content,
        'messageType':   'text',
        'sender':        sender,   # 'user' or 'bot'
        'read':          False,
        'timestamp':     datetime.utcnow()
    })
    bots_col.update_one(
        {'businessId': business_id},
        {
            '$set': {'lastConversationAt': datetime.utcnow()},
            '$inc': {'totalMessages': 1}
        }
    )


def _build_reply(bot: Dict, incoming_msg: str) -> str:
    """
    Generate an auto-reply based on the bot's configuration.
    Priority: human handoff → keyword match → custom auto-reply → default.
    """
    if not bot.get('autoReply', False):
        return ''

    msg_lower = incoming_msg.lower().strip()

    # 1. Human handoff
    handoff_keywords = bot.get('humanHandoffKeywords', ['human', 'agent', 'support', 'help me'])
    if bot.get('humanHandoff') and any(k in msg_lower for k in handoff_keywords):
        return (
            bot.get('humanHandoffMessage')
            or f"Connecting you to a human agent for {bot.get('businessName', 'our team')}. "
               "Please hold on."
        )

    # 2. Keyword responses (exact word match)
    keyword_responses: Dict = bot.get('keywordResponses', {})
    for keyword, response in keyword_responses.items():
        if keyword.lower() in msg_lower:
            return response

    # 3. Welcome message for first/greeting messages
    greetings = ['hi', 'hello', 'hey', 'start', 'hii', 'helo']
    if any(g == msg_lower or msg_lower.startswith(g + ' ') for g in greetings):
        welcome = bot.get('welcomeMessage')
        if welcome:
            return welcome

    # 4. Fallback
    fallback = bot.get('fallbackMessage')
    if fallback:
        return fallback

    # 5. Legacy autoReplyMessage
    return (
        bot.get('autoReplyMessage')
        or f"Hi! Thanks for reaching out to {bot.get('businessName', 'us')}. "
           "We received your message and will get back to you shortly."
    )


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Twilio WhatsApp Webhook
# ═════════════════════════════════════════════════════════════

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    Twilio calls this endpoint for every incoming WhatsApp message.
    Set this URL in your Twilio console under:
      Messaging → Try it Out → Send a WhatsApp message → Sandbox Settings
      OR on your approved number's Webhook URL field.
    """
    incoming_msg   = request.values.get('Body', '').strip()
    from_number    = request.values.get('From', '')   # e.g. whatsapp:+919876543210
    num_media      = int(request.values.get('NumMedia', 0))

    customer_phone = from_number.replace('whatsapp:', '')

    log.info(f"[WEBHOOK] Incoming from {customer_phone}: {incoming_msg!r}")

    resp = MessagingResponse()
    msg  = resp.message()

    bot = _find_bot_for_customer(customer_phone)
    if not bot:
        log.warning("[WEBHOOK] No active bot found to handle message")
        msg.body("Sorry, no active bot is configured right now. Please try again later.")
        return str(resp), 200, {'Content-Type': 'text/xml'}

    business_id = bot.get('businessId', '')
    user_id     = bot.get('ownerUserId', '')

    # Stick this customer to the bot
    _upsert_session(customer_phone, business_id)

    # Log the incoming message
    _log_message(business_id, user_id, customer_phone, incoming_msg, 'user')

    # Log media info if present
    if num_media > 0:
        media_url = request.values.get('MediaUrl0', '')
        log.info(f"[WEBHOOK] Media received: {media_url}")

    # Build and send reply
    reply = _build_reply(bot, incoming_msg)
    if reply:
        msg.body(reply)
        _log_message(business_id, user_id, customer_phone, reply, 'bot')
        log.info(f"[WEBHOOK] Auto-reply sent to {customer_phone}: {reply!r}")
    else:
        log.info(f"[WEBHOOK] autoReply disabled for bot {business_id} — no reply sent")

    return str(resp), 200, {'Content-Type': 'text/xml'}


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Bot Activation
# ═════════════════════════════════════════════════════════════

@app.route('/api/bot/activate', methods=['POST'])
def activate_bot():
    """
    Activate a bot and return the shared Twilio WhatsApp number.
    Called by the Next.js dashboard Activate button.

    Body:
        { "businessId": "...", "userId": "..." }

    Response:
        { "allocatedNumber": "+14155238886", "businessId": "...", "activatedAt": "..." }
    """
    data        = request.get_json(force=True) or {}
    business_id = data.get('businessId')
    user_id     = data.get('userId')

    if not business_id or not user_id:
        return jsonify({'error': 'businessId and userId are required'}), 400

    bot = bots_col.find_one({'businessId': business_id, 'ownerUserId': user_id})
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404

    # Already activated — just return the number
    if bot.get('allocatedNumber'):
        return jsonify({
            'message':         'Bot already active',
            'allocatedNumber': bot['allocatedNumber'],
            'businessId':      business_id
        })

    # The "allocated" number is always the single shared Twilio number
    display_number = TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')
    now = datetime.utcnow()

    bots_col.update_one(
        {'businessId': business_id, 'ownerUserId': user_id},
        {
            '$set': {
                'allocatedNumber':    display_number,
                'verificationStatus': 'verified',
                'activatedAt':        now,
                'updatedAt':          now
            }
        }
    )

    log.info(f"[ACTIVATE] Bot {business_id} activated → {display_number}")

    return jsonify({
        'message':         'Bot activated successfully',
        'allocatedNumber': display_number,
        'businessId':      business_id,
        'activatedAt':     now.isoformat()
    })


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Send Outbound Message
# ═════════════════════════════════════════════════════════════

@app.route('/api/message/send', methods=['POST'])
def send_message():
    """
    Manually send a WhatsApp message to a customer from a bot.

    Body:
        { "to": "+919876543210", "body": "Hello!", "businessId": "..." }
    """
    data        = request.get_json(force=True) or {}
    to          = data.get('to', '').strip()
    body        = data.get('body', '').strip()
    business_id = data.get('businessId', '')

    if not to or not body:
        return jsonify({'error': 'to and body are required'}), 400

    to_wa = to if to.startswith('whatsapp:') else f'whatsapp:{to}'

    try:
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_wa,
            body=body
        )
        log.info(f"[SEND] Sent to {to}: {body!r}  SID={message.sid}")

        if business_id:
            bot = bots_col.find_one({'businessId': business_id})
            if bot:
                _log_message(business_id, bot.get('ownerUserId', ''), to, body, 'bot')

        return jsonify({'success': True, 'messageSid': message.sid})
    except Exception as e:
        log.error(f"[SEND] Failed: {e}")
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Conversations
# ═════════════════════════════════════════════════════════════

@app.route('/api/conversations/<business_id>', methods=['GET'])
def get_conversations(business_id):
    """
    Return all unique conversations (grouped by customer phone) for a bot.
    Query params: limit (default 50)
    """
    limit = int(request.args.get('limit', 50))

    pipeline = [
        {'$match': {'businessId': business_id}},
        {'$sort':  {'timestamp': -1}},
        {
            '$group': {
                '_id':             '$phoneNumber',
                'lastMessage':     {'$first': '$messageContent'},
                'lastMessageTime': {'$first': '$timestamp'},
                'lastSender':      {'$first': '$sender'},
                'messageCount':    {'$sum': 1},
                'unreadCount': {
                    '$sum': {'$cond': [{'$eq': ['$read', False]}, 1, 0]}
                }
            }
        },
        {'$sort':  {'lastMessageTime': -1}},
        {'$limit': limit}
    ]

    result = [
        {
            'phoneNumber':     c['_id'],
            'lastMessage':     c['lastMessage'],
            'lastMessageTime': c['lastMessageTime'].isoformat() if c.get('lastMessageTime') else None,
            'lastSender':      c['lastSender'],
            'messageCount':    c['messageCount'],
            'unreadCount':     c['unreadCount']
        }
        for c in conversations_col.aggregate(pipeline)
    ]

    return jsonify({'conversations': result, 'count': len(result)})


@app.route('/api/conversations/<business_id>/<path:phone_number>', methods=['GET'])
def get_chat_history(business_id, phone_number):
    """Return the full message thread between a bot and one customer."""
    limit = int(request.args.get('limit', 100))

    messages = list(
        conversations_col.find(
            {'businessId': business_id, 'phoneNumber': phone_number},
            {'_id': 0}
        ).sort('timestamp', ASCENDING).limit(limit)
    )

    for m in messages:
        if isinstance(m.get('timestamp'), datetime):
            m['timestamp'] = m['timestamp'].isoformat()

    return jsonify({'messages': messages, 'count': len(messages)})


@app.route('/api/conversations/<business_id>/<path:phone_number>/read', methods=['PATCH'])
def mark_read(business_id, phone_number):
    """Mark all messages from a customer as read."""
    result = conversations_col.update_many(
        {'businessId': business_id, 'phoneNumber': phone_number, 'read': False},
        {'$set': {'read': True}}
    )
    return jsonify({'success': True, 'marked': result.modified_count})


@app.route('/api/conversations/<business_id>/<path:phone_number>', methods=['DELETE'])
def delete_conversation(business_id, phone_number):
    """Delete a full conversation thread."""
    result = conversations_col.delete_many(
        {'businessId': business_id, 'phoneNumber': phone_number}
    )
    # Also clear their session
    sessions_col.delete_one({'customerPhone': phone_number})
    return jsonify({'success': True, 'deleted': result.deleted_count})


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Payments
# ═════════════════════════════════════════════════════════════

PLAN_PRICES: Dict[str, int] = {'starter': 99, 'pro': 499, 'enterprise': 1999}


@app.route('/api/payments/<user_id>', methods=['GET'])
def get_payments(user_id):
    """Return all payment records for a user with totals."""
    docs = list(payments_col.find({'userId': user_id}, {'_id': 0}))

    for d in docs:
        if isinstance(d.get('dueDate'), datetime):
            d['dueDate'] = d['dueDate'].isoformat()
        if isinstance(d.get('paidAt'), datetime):
            d['paidAt'] = d['paidAt'].isoformat()

    total_due       = sum(d['amount'] for d in docs if d.get('status') in ('due', 'pending'))
    total_completed = sum(d['amount'] for d in docs if d.get('status') in ('completed', 'paid'))

    return jsonify({
        'payments':        docs,
        'totalDue':        total_due,
        'totalCompleted':  total_completed,
        'count':           len(docs)
    })


@app.route('/api/payments', methods=['POST'])
def create_payment():
    """Create a new payment record."""
    data = request.get_json(force=True) or {}

    for field in ('userId', 'businessId', 'amount'):
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    plan_type = data.get('planType', 'starter')
    payment = {
        'userId':      data['userId'],
        'businessId':  data['businessId'],
        'amount':      float(data['amount']),
        'planType':    plan_type,
        'description': data.get('description', f"{plan_type.capitalize()} plan subscription"),
        'status':      data.get('status', 'due'),
        'dueDate':     datetime.utcnow(),
        'createdAt':   datetime.utcnow(),
        'updatedAt':   datetime.utcnow()
    }

    result = payments_col.insert_one(payment)
    return jsonify({'success': True, 'paymentId': str(result.inserted_id)}), 201


@app.route('/api/payments/<payment_id>', methods=['PATCH'])
def update_payment(payment_id):
    """Update the status (and optional transactionId) of a payment."""
    data   = request.get_json(force=True) or {}
    status = data.get('status')

    if not status:
        return jsonify({'error': 'status is required'}), 400

    update: Dict = {'status': status, 'updatedAt': datetime.utcnow()}
    if status in ('completed', 'paid'):
        update['paidAt'] = datetime.utcnow()
    if data.get('transactionId'):
        update['transactionId'] = data['transactionId']
    if data.get('paymentMethod'):
        update['paymentMethod'] = data['paymentMethod']

    try:
        result = payments_col.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': update}
        )
        if result.matched_count == 0:
            return jsonify({'error': 'Payment not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/payments/<payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    """Delete a payment record."""
    try:
        result = payments_col.delete_one({'_id': ObjectId(payment_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Payment not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Health Check
# ═════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    """Simple health check — also shows the configured Twilio number."""
    return jsonify({
        'status':         'ok',
        'twilioNumber':   TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', ''),
        'timestamp':      datetime.utcnow().isoformat()
    })


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'name':    'BotSetu Backend',
        'version': '1.0.0',
        'routes': [
            'POST /webhook/whatsapp',
            'POST /api/bot/activate',
            'POST /api/message/send',
            'GET  /api/conversations/<businessId>',
            'GET  /api/conversations/<businessId>/<phone>',
            'PATCH /api/conversations/<businessId>/<phone>/read',
            'DELETE /api/conversations/<businessId>/<phone>',
            'GET  /api/payments/<userId>',
            'POST /api/payments',
            'PATCH /api/payments/<paymentId>',
            'DELETE /api/payments/<paymentId>',
            'GET  /health'
        ]
    })


# ═════════════════════════════════════════════════════════════
# ── ENTRY POINT
# ═════════════════════════════════════════════════════════════

if __name__ == '__main__':
    log.info(f"🚀  BotSetu backend starting on port {PORT}")
    log.info(f"📱  Twilio WhatsApp number : {TWILIO_WHATSAPP_NUMBER}")
    log.info(f"🗄️   MongoDB               : {MONGODB_URI}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
