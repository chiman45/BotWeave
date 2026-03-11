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
from datetime import datetime, timezone
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
bookings_col      = db['mandi-bookings']      # mandi slot bookings

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
    """Return the bot that owns this customer's session, or the most recently activated bot."""
    session = sessions_col.find_one({'customerPhone': customer_phone})
    if session:
        bot = bots_col.find_one({'businessId': session['businessId']})
        if bot:
            return bot
        # Session points to a deleted bot — clean it up and fall through
        sessions_col.delete_one({'customerPhone': customer_phone})

    # Fallback: most recently activated verified bot
    return bots_col.find_one(
        {'verificationStatus': 'verified'},
        sort=[('activatedAt', -1)]
    )


def _now():
    return datetime.now(timezone.utc)


def _upsert_session(customer_phone: str, business_id: str) -> None:
    """Stick a customer to a bot for the lifetime of the conversation."""
    sessions_col.update_one(
        {'customerPhone': customer_phone},
        {'$set': {'businessId': business_id, 'updatedAt': _now()}},
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
        'timestamp':     _now()
    })
    bots_col.update_one(
        {'businessId': business_id},
        {
            '$set': {'lastConversationAt': _now()},
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
# ── MANDI BOOKING FLOW ENGINE
# ═════════════════════════════════════════════════════════════

CROP_MAP: Dict[str, str] = {
    '1': 'Paddy', '2': 'Wheat', '3': 'Maize',
    '4': 'Soybean', '5': 'Cotton', '6': 'Other'
}

DEFAULT_SLOTS = [
    '9:00 AM – 10:00 AM',
    '10:00 AM – 11:00 AM',
    '11:00 AM – 12:00 PM',
    '12:00 PM – 1:00 PM',
    '2:00 PM – 3:00 PM',
    '3:00 PM – 4:00 PM',
]

DEFAULT_MANDIS = [
    {'name': 'Main Mandi', 'location': 'City Center', 'address': 'Central Market'},
]


def _handle_mandi_flow(bot: Dict, customer_phone: str, incoming_msg: str) -> str:
    """
    Stateful multi-step conversation flow for mandi slot booking.
    State is persisted per customer in bot-sessions.
    """
    session   = sessions_col.find_one({'customerPhone': customer_phone}) or {}
    step      = session.get('flowStep', 'greet')
    flow_data = session.get('flowData', {})

    mandis       = bot.get('mandis', DEFAULT_MANDIS)
    slots        = bot.get('slots', DEFAULT_SLOTS)
    max_per_slot = int(bot.get('maxBookingsPerSlot', 10))

    # If the conversation was already completed let the user restart
    if step == 'done':
        step = 'greet'
        flow_data = {}

    reply     = ''
    next_step = step

    # ── STEP: greet ──────────────────────────────────────────
    if step == 'greet':
        reply = (
            f"🌾 *Welcome to {bot.get('businessName', 'Mandi Booking')}!*\n\n"
            f"I'll help you book a mandi slot in a few quick steps.\n\n"
            f"Please enter your *Full Name*:"
        )
        next_step = 'ask_name'

    # ── STEP: ask_name ───────────────────────────────────────
    elif step == 'ask_name':
        flow_data['farmerName'] = incoming_msg.strip()
        reply = (
            f"Hello *{flow_data['farmerName']}*! 👋\n\n"
            f"Please enter your *Village Name*:"
        )
        next_step = 'ask_village'

    # ── STEP: ask_village ────────────────────────────────────
    elif step == 'ask_village':
        flow_data['village'] = incoming_msg.strip()
        reply = (
            "Select your *Crop Type*:\n\n"
            "1️⃣ Paddy\n2️⃣ Wheat\n3️⃣ Maize\n"
            "4️⃣ Soybean\n5️⃣ Cotton\n6️⃣ Other\n\n"
            "Reply with the *number* or crop name:"
        )
        next_step = 'ask_crop'

    # ── STEP: ask_crop ───────────────────────────────────────
    elif step == 'ask_crop':
        crop_input = incoming_msg.strip()
        flow_data['cropType'] = CROP_MAP.get(crop_input, crop_input.title())
        reply = (
            f"Crop: *{flow_data['cropType']}* ✅\n\n"
            f"Enter *Quantity* in quintals (or send *0* to skip):"
        )
        next_step = 'ask_quantity'

    # ── STEP: ask_quantity ───────────────────────────────────
    elif step == 'ask_quantity':
        qty = incoming_msg.strip()
        flow_data['quantity'] = qty if qty != '0' else 'Not specified'
        mandi_list = '\n'.join(
            [f"{i+1}️⃣ {m['name']} – {m.get('location','')}" for i, m in enumerate(mandis)]
        )
        reply = (
            f"Select your *nearest Mandi*:\n\n{mandi_list}\n\n"
            "Reply with the number:"
        )
        next_step = 'ask_mandi'

    # ── STEP: ask_mandi ──────────────────────────────────────
    elif step == 'ask_mandi':
        try:
            idx = int(incoming_msg.strip()) - 1
            if 0 <= idx < len(mandis):
                flow_data['mandiIndex']    = idx
                flow_data['mandiName']     = mandis[idx]['name']
                flow_data['mandiLocation'] = mandis[idx].get('address', mandis[idx].get('location', ''))

                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                available = [
                    s for s in slots
                    if bookings_col.count_documents({
                        'businessId': bot['businessId'],
                        'mandiName':  flow_data['mandiName'],
                        'timeSlot':   s,
                        'date':       today,
                    }) < max_per_slot
                ]

                if not available:
                    reply     = "❌ Sorry, all slots for *today* are fully booked. Please try again tomorrow!"
                    next_step = 'done'
                else:
                    flow_data['availableSlots'] = available
                    slot_list = '\n'.join([f"{i+1}️⃣ {s}" for i, s in enumerate(available)])
                    reply = (
                        f"Available slots at *{flow_data['mandiName']}*:\n\n"
                        f"{slot_list}\n\nReply with the *slot number*:"
                    )
                    next_step = 'ask_slot'
            else:
                reply = f"⚠️ Please enter a number between *1* and *{len(mandis)}*."
        except ValueError:
            reply = "⚠️ Please enter a *number* to select the mandi."

    # ── STEP: ask_slot ───────────────────────────────────────
    elif step == 'ask_slot':
        available = flow_data.get('availableSlots', slots)
        try:
            idx = int(incoming_msg.strip()) - 1
            if 0 <= idx < len(available):
                flow_data['timeSlot'] = available[idx]

                today       = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                token_count = bookings_col.count_documents({'businessId': bot['businessId'], 'date': today})
                token       = f"TK-{today.replace('-','')}-{str(token_count + 1).zfill(3)}"

                flow_data['tokenNumber'] = token
                flow_data['date']        = today

                bookings_col.insert_one({
                    'businessId':    bot['businessId'],
                    'tokenNumber':   token,
                    'farmerName':    flow_data.get('farmerName', ''),
                    'village':       flow_data.get('village', ''),
                    'cropType':      flow_data.get('cropType', ''),
                    'quantity':      flow_data.get('quantity', ''),
                    'mandiName':     flow_data.get('mandiName', ''),
                    'mandiLocation': flow_data.get('mandiLocation', ''),
                    'timeSlot':      flow_data['timeSlot'],
                    'date':          today,
                    'phoneNumber':   customer_phone,
                    'status':        'confirmed',
                    'createdAt':     _now(),
                })

                reply = (
                    f"✅ *Booking Confirmed!*\n\n"
                    f"🎫 Token: *{token}*\n"
                    f"👤 Name: {flow_data.get('farmerName')}\n"
                    f"🌿 Crop: {flow_data.get('cropType')} ({flow_data.get('quantity')} qtl)\n"
                    f"🏪 Mandi: {flow_data.get('mandiName')}\n"
                    f"📍 Location: {flow_data.get('mandiLocation')}\n"
                    f"⏰ Slot: {flow_data['timeSlot']}\n"
                    f"📅 Date: {today}\n\n"
                    f"Please arrive *on time* with your produce. Thank you! 🙏\n\n"
                    f"_Send any message to make a new booking._"
                )
                next_step = 'done'
            else:
                reply = f"⚠️ Please enter a number between *1* and *{len(available)}*."
        except ValueError:
            reply = "⚠️ Please enter a *number* to choose a slot."

    # Persist updated state
    sessions_col.update_one(
        {'customerPhone': customer_phone},
        {'$set': {
            'businessId': bot['businessId'],
            'flowStep':   next_step,
            'flowData':   flow_data,
            'updatedAt':  _now(),
        }},
        upsert=True
    )

    return reply


# ═════════════════════════════════════════════════════════════
# ── AI BOT ENGINE  (Ollama + optional RAG via ChromaDB)
# ═════════════════════════════════════════════════════════════

# Path where per-bot Chroma vector stores are persisted
_VECTOR_STORE_ROOT = os.path.join(os.path.dirname(__file__), 'vector_stores')


def _rag_query(business_id: str, query: str) -> str:
    """
    Return the top-k most relevant chunks from this bot's vector store.
    Returns '' when no store exists or Ollama / ChromaDB is unavailable.
    """
    store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
    if not os.path.exists(store_path):
        return ''
    try:
        from langchain_ollama import OllamaEmbeddings
        from langchain_community.vectorstores import Chroma
        embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url='http://localhost:11434')
        vector_db  = Chroma(persist_directory=store_path, embedding_function=embeddings)
        docs       = vector_db.similarity_search(query, k=4)
        return '\n\n'.join(d.page_content for d in docs)
    except Exception as exc:
        log.warning(f"[RAG] Query failed for {business_id}: {exc}")
        return ''


def _handle_ai_flow(bot: Dict, customer_phone: str, incoming_msg: str) -> str:
    """
    Handle a message using a local Ollama LLM.
    Automatically injects RAG context when ragEnabled = True.
    Falls back to _build_reply() if Ollama / LangChain are not installed.
    """
    try:
        from langchain_ollama import OllamaLLM
    except ImportError:
        log.warning("[AI] langchain-ollama not installed — falling back to keyword reply")
        return _build_reply(bot, incoming_msg)

    model_name    = bot.get('aiModel', 'llama3.2')
    system_prompt = bot.get('aiSystemPrompt') or (
        f"You are a helpful assistant for *{bot.get('businessName', 'this business')}*. "
        "Answer clearly and concisely. Reply in the same language the user writes in."
    )
    rag_enabled = bool(bot.get('aiRagEnabled', False))
    business_id = bot['businessId']

    # ── Conversation history (last 8 turns, oldest first) ──
    history_docs = list(
        conversations_col.find(
            {'businessId': business_id, 'phoneNumber': customer_phone},
            {'messageContent': 1, 'sender': 1, '_id': 0}
        ).sort('timestamp', DESCENDING).limit(8)
    )
    history_docs.reverse()
    history_str = ''.join(
        f"{'User' if m['sender'] == 'user' else 'Assistant'}: {m['messageContent']}\n"
        for m in history_docs
    )

    # ── RAG context ────────────────────────────────────────
    rag_context = ''
    if rag_enabled:
        chunk = _rag_query(business_id, incoming_msg)
        if chunk:
            rag_context = f"Relevant knowledge base context:\n{chunk}\n\n"

    # ── Full prompt ────────────────────────────────────────
    prompt = (
        f"{system_prompt}\n\n"
        f"{rag_context}"
        f"Conversation so far:\n{history_str}"
        f"User: {incoming_msg}\nAssistant:"
    )

    try:
        llm      = OllamaLLM(model=model_name, base_url='http://localhost:11434')
        response = llm.invoke(prompt)
        return str(response).strip()
    except Exception as exc:
        log.error(f"[AI] Ollama error (model={model_name!r}): {exc}")
        return (
            "⚠️ I'm having trouble thinking right now — the AI model may be loading. "
            "Please send your message again in a moment."
        )


# ── ROUTE: AI — List Ollama models ────────────────────────────
@app.route('/api/ai/models', methods=['GET'])
def list_ollama_models():
    """Return available model names from the local Ollama server."""
    try:
        import requests as _req
        resp = _req.get('http://localhost:11434/api/tags', timeout=5)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            return jsonify({'models': models, 'ollamaRunning': True})
    except Exception as exc:
        log.warning(f"[AI] Ollama not reachable: {exc}")
    return jsonify({'models': [], 'ollamaRunning': False,
                    'error': 'Ollama not running at localhost:11434'})


# ── ROUTE: AI — Knowledge Base (RAG) ─────────────────────────
@app.route('/api/ai/kb/<business_id>', methods=['POST'])
def upload_kb(business_id: str):
    """
    Ingest a knowledge base file (TXT, JSON, CSV, MD) into the bot's
    per-bot Chroma vector store.  Embeddings are generated via Ollama
    nomic-embed-text (must be pulled: ollama pull nomic-embed-text).
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided (field name: file)'}), 400

    file     = request.files['file']
    filename = file.filename or 'kb.txt'
    ext      = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'

    raw = file.read().decode('utf-8', errors='replace')

    # ── Parse file into text segments ─────────────────────
    texts: List[str] = []
    if ext == 'json':
        try:
            import json as _json
            data = _json.loads(raw)
            if isinstance(data, list):
                texts = [_json.dumps(item, ensure_ascii=False) for item in data]
            elif isinstance(data, dict):
                # Support {question: answer, ...} or [{q:.., a:..}, ...]
                texts = [f"{k}: {v}" for k, v in data.items()]
            else:
                texts = [raw]
        except Exception:
            texts = [raw]
    elif ext == 'csv':
        import csv as _csv, io as _io
        reader = _csv.DictReader(_io.StringIO(raw))
        texts  = [', '.join(f"{k}: {v}" for k, v in row.items()) for row in reader if row]
    else:
        # TXT / MD / anything else — split on blank lines to preserve paragraphs
        texts = [p.strip() for p in raw.split('\n\n') if p.strip()]
        if not texts:
            texts = [raw]

    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_ollama import OllamaEmbeddings
        from langchain_community.vectorstores import Chroma
        from langchain.schema import Document

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=60)
        docs = [
            Document(page_content=chunk, metadata={'source': filename})
            for text in texts
            for chunk in splitter.split_text(text)
            if chunk.strip()
        ]
        if not docs:
            return jsonify({'error': 'No usable content found in file'}), 400

        store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
        os.makedirs(store_path, exist_ok=True)

        embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url='http://localhost:11434')
        Chroma.from_documents(docs, embeddings, persist_directory=store_path)

        log.info(f"[RAG] Ingested {len(docs)} chunks for bot {business_id} from {filename!r}")
        return jsonify({'message': f'Ingested {len(docs)} chunks from {filename}', 'chunks': len(docs)})

    except ImportError:
        return jsonify({'error': 'langchain-ollama or chromadb not installed on server. '
                                 'Run: pip install langchain-ollama chromadb'}), 500
    except Exception as exc:
        log.error(f"[RAG] KB upload failed for {business_id}: {exc}")
        return jsonify({'error': str(exc)}), 500


@app.route('/api/ai/kb/<business_id>', methods=['GET'])
def get_kb_info(business_id: str):
    """Return metadata about this bot's vector store."""
    store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
    if not os.path.exists(store_path):
        return jsonify({'exists': False, 'chunks': 0})
    try:
        from langchain_ollama import OllamaEmbeddings
        from langchain_community.vectorstores import Chroma
        embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url='http://localhost:11434')
        db    = Chroma(persist_directory=store_path, embedding_function=embeddings)
        count = db._collection.count()
        return jsonify({'exists': True, 'chunks': count})
    except Exception:
        return jsonify({'exists': True, 'chunks': -1})


@app.route('/api/ai/kb/<business_id>', methods=['DELETE'])
def delete_kb(business_id: str):
    """Delete the entire vector store for this bot."""
    import shutil as _shutil
    store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
    if os.path.exists(store_path):
        _shutil.rmtree(store_path)
        log.info(f"[RAG] Deleted knowledge base for bot {business_id}")
    return jsonify({'message': 'Knowledge base deleted'})


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

    bot = _find_bot_for_customer(customer_phone)
    if not bot:
        log.warning("[WEBHOOK] No active bot found to handle message")
        resp = MessagingResponse()
        resp.message("Sorry, no active bot is configured right now. Please try again later.")
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

    # Build and send reply – route based on botType and useCaseType
    bot_type = bot.get('botType', 'normal')
    if bot_type == 'ai':
        reply = _handle_ai_flow(bot, customer_phone, incoming_msg)
    elif bot.get('useCaseType') == 'mandi_booking':
        reply = _handle_mandi_flow(bot, customer_phone, incoming_msg)
    else:
        reply = _build_reply(bot, incoming_msg)
    resp = MessagingResponse()
    if reply:
        resp.message(reply)
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
    now = _now()

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

    webhook_url = os.getenv('WEBHOOK_URL', '')
    return jsonify({
        'message':         'Bot activated successfully',
        'allocatedNumber': display_number,
        'businessId':      business_id,
        'activatedAt':     now.isoformat(),
        'webhookUrl':      webhook_url
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
        'dueDate':     _now(),
        'createdAt':   _now(),
        'updatedAt':   _now()
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

    update: Dict = {'status': status, 'updatedAt': _now()}
    if status in ('completed', 'paid'):
        update['paidAt'] = _now()
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
# ── ROUTE: Mandi Bookings
# ═════════════════════════════════════════════════════════════

@app.route('/api/bookings/<business_id>', methods=['GET'])
def get_bookings(business_id: str):
    """Return all mandi bookings for a given businessId (Flask backup endpoint)."""
    date_filter = request.args.get('date')
    query: Dict = {'businessId': business_id}
    if date_filter:
        query['date'] = date_filter

    docs = list(
        bookings_col.find(query, {'_id': 0})
                    .sort('createdAt', DESCENDING)
                    .limit(200)
    )
    for d in docs:
        if isinstance(d.get('createdAt'), datetime):
            d['createdAt'] = d['createdAt'].isoformat()

    return jsonify({'bookings': docs, 'count': len(docs)})


# ═════════════════════════════════════════════════════════════
# ── ROUTE: Health Check
# ═════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    """Simple health check — also shows the configured Twilio number and webhook URL."""
    return jsonify({
        'status':         'ok',
        'twilioNumber':   TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', ''),
        'webhookUrl':     os.getenv('WEBHOOK_URL', ''),
        'timestamp':      _now().isoformat()
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
