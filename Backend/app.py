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
from twilio.twiml.voice_response import VoiceResponse, Gather
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, Dict, List
import os
import logging
import re
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
# Raw phone number for voice calls (strips "whatsapp:" prefix if present)
TWILIO_PHONE_NUMBER     = os.getenv('TWILIO_PHONE_NUMBER',
                                    (TWILIO_WHATSAPP_NUMBER or '').replace('whatsapp:', ''))
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
credits_col       = db['credits']             # per-user credit balance

# Indexes (idempotent — safe to run every start)
sessions_col.create_index([('customerPhone', ASCENDING)], unique=True)
conversations_col.create_index([('businessId', ASCENDING), ('phoneNumber', ASCENDING)])
conversations_col.create_index([('timestamp', DESCENDING)])

app = Flask(__name__)
CORS(app)


# ═════════════════════════════════════════════════════════════
# ── HELPERS
# ═════════════════════════════════════════════════════════════



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


INITIAL_CREDITS = 100


def _get_or_init_credits(user_id: str) -> int:
    """Return credit balance for user, creating with 100 free credits if new."""
    now = _now()
    doc = credits_col.find_one({'userId': user_id})
    if doc is None:
        credits_col.insert_one({
            'userId':      user_id,
            'credits':     INITIAL_CREDITS,
            'totalEarned': INITIAL_CREDITS,
            'totalUsed':   0,
            'createdAt':   now,
            'updatedAt':   now,
        })
        return INITIAL_CREDITS
    return int(doc.get('credits', 0))


def _deduct_credit(user_id: str) -> bool:
    """Deduct 1 credit from user. Returns True if deducted, False if insufficient."""
    result = credits_col.update_one(
        {'userId': user_id, 'credits': {'$gt': 0}},
        {
            '$inc': {'credits': -1, 'totalUsed': 1},
            '$set': {'updatedAt': _now()},
        }
    )
    return result.modified_count == 1


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

# ── Language selection prompt (shown before any other step) ──
LANG_SELECT_MSG = (
    "🌐 *Welcome / स्वागत / ਸੁਆਗਤ / આવકાર / স্বাগতম / స్వాగతం*\n\n"
    "Please choose your language / कृपया भाषा चुनें:\n\n"
    "1️⃣  English\n"
    "2️⃣  हिंदी (Hindi)\n"
    "3️⃣  ਪੰਜਾਬੀ (Punjabi)\n"
    "4️⃣  ગુજરાતી (Gujarati)\n"
    "5️⃣  मराठी (Marathi)\n\n"
    "Reply with 1, 2, 3, 4, or 5:"
)

SUPPORTED_LANGS: Dict[str, str] = {
    '1': 'en', '2': 'hi', '3': 'pa', '4': 'gu', '5': 'mr',
    'english': 'en', 'hindi': 'hi',
    'punjabi': 'pa', 'gujarati': 'gu', 'marathi': 'mr',
}

# Greetings that should always restart language selection.
LANG_RESET_GREETINGS = {
    'hi', 'hii', 'hiii', 'hello', 'hey', 'namaste', 'namaskar'
}

# ── Per-language crop maps ────────────────────────────────────
CROP_MAP: Dict[str, str] = {
    '1': 'Paddy', '2': 'Wheat', '3': 'Maize',
    '4': 'Soybean', '5': 'Cotton', '6': 'Other'
}

CROP_MAP_I18N: Dict[str, Dict[str, str]] = {
    'en': {'1': 'Paddy',   '2': 'Wheat',  '3': 'Maize',   '4': 'Soybean', '5': 'Cotton', '6': 'Other'},
    'hi': {'1': 'धान',     '2': 'गेहूँ',  '3': 'मक्का',   '4': 'सोयाबीन', '5': 'कपास',  '6': 'अन्य'},
    'pa': {'1': 'ਝੋਨਾ',    '2': 'ਕਣਕ',   '3': 'ਮੱਕੀ',    '4': 'ਸੋਇਆਬੀਨ','5': 'ਕਪਾਹ',  '6': 'ਹੋਰ'},
    'gu': {'1': 'ડાંગર',   '2': 'ઘઉં',   '3': 'મકાઈ',    '4': 'સોયાબીન', '5': 'કપાસ',  '6': 'અન્ય'},
    'mr': {'1': 'भात',     '2': 'गहू',   '3': 'मका',     '4': 'सोयाबीन', '5': 'कापूस', '6': 'इतर'},
}

# ── All UI strings translated per language ────────────────────
LANG: Dict[str, Dict[str, str]] = {
    'en': {
        'lang_ok':            "✅ You selected: *English*\n\nLet's begin the booking.",
        'welcome':            "🌾 *Welcome to {bname}!*\n\nI'll help you book a mandi slot in a few quick steps.\n\nPlease enter your *Full Name*:",
        'ask_village':        "Hello *{name}*! 👋\n\nPlease enter your *Village Name*:",
        'ask_crop':           "Select your *Crop Type*:\n\n1️⃣ Paddy\n2️⃣ Wheat\n3️⃣ Maize\n4️⃣ Soybean\n5️⃣ Cotton\n6️⃣ Other\n\nReply with the *number* or crop name:",
        'crop_ok':            "Crop: *{crop}* ✅\n\nEnter *Quantity* in quintals (or send *0* to skip):",
        'ask_mandi':          "Select your *nearest Mandi*:\n\n{mandi_list}\n\nReply with the number:",
        'slots_header':       "Available slots at *{mandi}*:\n\n{slot_list}\n\nReply with the *slot number*:",
        'no_slots':           "❌ Sorry, all slots for *today* are fully booked. Please try again tomorrow!",
        'confirmed':          "✅ *Booking Confirmed!*\n\n🎫 Token: *{token}*\n👤 Name: {name}\n🌿 Crop: {crop} ({qty} qtl)\n🏪 Mandi: {mandi}\n📍 Location: {loc}\n⏰ Slot: {slot}\n📅 Date: {date}\n\nPlease arrive *on time* with your produce. Thank you! 🙏\n\n_Send any message to make a new booking._",
        'bad_mandi':          "⚠️ Please enter a number between *1* and *{n}*.",
        'bad_mandi_type':     "⚠️ Please enter a *number* to select the mandi.",
        'bad_slot':           "⚠️ Please enter a number between *1* and *{n}*.",
        'bad_slot_type':      "⚠️ Please enter a *number* to choose a slot.",
        'lang_invalid':       "⚠️ Please choose a language by replying with:\n1 = English\n2 = Hindi\n3 = Punjabi\n4 = Gujarati\n5 = Marathi",
    },
    'hi': {
        'lang_ok':            "✅ आपने चुना: *हिंदी*\n\nआइए बुकिंग शुरू करते हैं।",
        'welcome':            "🌾 *{bname} में आपका स्वागत है!*\n\nमैं आपको कुछ आसान चरणों में मंडी स्लॉट बुक करने में मदद करूंगा।\n\nकृपया अपना *पूरा नाम* दर्ज करें:",
        'ask_village':        "नमस्ते *{name}*! 👋\n\nकृपया अपने *गाँव का नाम* दर्ज करें:",
        'ask_crop':           "अपनी *फसल का प्रकार* चुनें:\n\n1️⃣ धान\n2️⃣ गेहूँ\n3️⃣ मक्का\n4️⃣ सोयाबीन\n5️⃣ कपास\n6️⃣ अन्य\n\n*नंबर* या फसल का नाम भेजें:",
        'crop_ok':            "फसल: *{crop}* ✅\n\n*मात्रा* क्विंटल में दर्ज करें (छोड़ने के लिए *0* भेजें):",
        'ask_mandi':          "अपनी *नजदीकी मंडी* चुनें:\n\n{mandi_list}\n\nनंबर से जवाब दें:",
        'slots_header':       "*{mandi}* में उपलब्ध स्लॉट:\n\n{slot_list}\n\n*स्लॉट नंबर* से जवाब दें:",
        'no_slots':           "❌ खेद है, *आज* के सभी स्लॉट भर गए हैं। कृपया कल पुनः प्रयास करें!",
        'confirmed':          "✅ *बुकिंग की पुष्टि हो गई!*\n\n🎫 टोकन: *{token}*\n👤 नाम: {name}\n🌿 फसल: {crop} ({qty} क्विंटल)\n🏪 मंडी: {mandi}\n📍 स्थान: {loc}\n⏰ स्लॉट: {slot}\n📅 तारीख: {date}\n\nकृपया अपनी उपज के साथ *समय पर* पहुँचें। धन्यवाद! 🙏\n\n_नई बुकिंग के लिए कोई भी संदेश भेजें।_",
        'bad_mandi':          "⚠️ कृपया *1* और *{n}* के बीच संख्या दर्ज करें।",
        'bad_mandi_type':     "⚠️ मंडी चुनने के लिए कृपया एक *नंबर* दर्ज करें।",
        'bad_slot':           "⚠️ कृपया *1* और *{n}* के बीच संख्या दर्ज करें।",
        'bad_slot_type':      "⚠️ स्लॉट चुनने के लिए कृपया एक *नंबर* दर्ज करें।",
        'lang_invalid':       "⚠️ कृपया भाषा चुनने के लिए 1, 2, 3, 4 या 5 से जवाब दें।",
    },
    'pa': {
        'lang_ok':            "✅ ਤੁਸੀਂ ਚੁਣਿਆ: *ਪੰਜਾਬੀ*\n\nਆਓ ਬੁਕਿੰਗ ਸ਼ੁਰੂ ਕਰੀਏ।",
        'welcome':            "🌾 *{bname} ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ!*\n\nਮੈਂ ਤੁਹਾਨੂੰ ਕੁਝ ਆਸਾਨ ਕਦਮਾਂ ਵਿੱਚ ਮੰਡੀ ਸਲਾਟ ਬੁੱਕ ਕਰਨ ਵਿੱਚ ਮਦਦ ਕਰਾਂਗਾ।\n\nਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ *ਪੂਰਾ ਨਾਮ* ਦਰਜ ਕਰੋ:",
        'ask_village':        "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ *{name}*! 👋\n\nਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ *ਪਿੰਡ ਦਾ ਨਾਮ* ਦਰਜ ਕਰੋ:",
        'ask_crop':           "ਆਪਣੀ *ਫ਼ਸਲ ਦੀ ਕਿਸਮ* ਚੁਣੋ:\n\n1️⃣ ਝੋਨਾ\n2️⃣ ਕਣਕ\n3️⃣ ਮੱਕੀ\n4️⃣ ਸੋਇਆਬੀਨ\n5️⃣ ਕਪਾਹ\n6️⃣ ਹੋਰ\n\n*ਨੰਬਰ* ਜਾਂ ਫ਼ਸਲ ਦਾ ਨਾਮ ਭੇਜੋ:",
        'crop_ok':            "ਫ਼ਸਲ: *{crop}* ✅\n\n*ਮਾਤਰਾ* ਕੁਇੰਟਲ ਵਿੱਚ ਦਰਜ ਕਰੋ (ਛੱਡਣ ਲਈ *0* ਭੇਜੋ):",
        'ask_mandi':          "ਆਪਣੀ *ਨੇੜੇ ਦੀ ਮੰਡੀ* ਚੁਣੋ:\n\n{mandi_list}\n\nਨੰਬਰ ਨਾਲ ਜਵਾਬ ਦਿਓ:",
        'slots_header':       "*{mandi}* ਵਿੱਚ ਉਪਲਬਧ ਸਲਾਟ:\n\n{slot_list}\n\n*ਸਲਾਟ ਨੰਬਰ* ਨਾਲ ਜਵਾਬ ਦਿਓ:",
        'no_slots':           "❌ ਮਾਫ਼ ਕਰਨਾ, *ਅੱਜ* ਦੇ ਸਾਰੇ ਸਲਾਟ ਭਰੇ ਹੋਏ ਹਨ। ਕੱਲ੍ਹ ਫਿਰ ਕੋਸ਼ਿਸ਼ ਕਰੋ!",
        'confirmed':          "✅ *ਬੁਕਿੰਗ ਪੱਕੀ ਹੋ ਗਈ!*\n\n🎫 ਟੋਕਨ: *{token}*\n👤 ਨਾਮ: {name}\n🌿 ਫ਼ਸਲ: {crop} ({qty} ਕੁਇੰਟਲ)\n🏪 ਮੰਡੀ: {mandi}\n📍 ਟਿਕਾਣਾ: {loc}\n⏰ ਸਲਾਟ: {slot}\n📅 ਮਿਤੀ: {date}\n\nਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਉਪਜ ਨਾਲ *ਸਮੇਂ ਸਿਰ* ਆਓ। ਧੰਨਵਾਦ! 🙏\n\n_ਨਵੀਂ ਬੁਕਿੰਗ ਲਈ ਕੋਈ ਵੀ ਸੁਨੇਹਾ ਭੇਜੋ।_",
        'bad_mandi':          "⚠️ ਕਿਰਪਾ ਕਰਕੇ *1* ਅਤੇ *{n}* ਦੇ ਵਿਚਕਾਰ ਨੰਬਰ ਦਰਜ ਕਰੋ।",
        'bad_mandi_type':     "⚠️ ਮੰਡੀ ਚੁਣਨ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਇੱਕ *ਨੰਬਰ* ਦਰਜ ਕਰੋ।",
        'bad_slot':           "⚠️ ਕਿਰਪਾ ਕਰਕੇ *1* ਅਤੇ *{n}* ਦੇ ਵਿਚਕਾਰ ਨੰਬਰ ਦਰਜ ਕਰੋ।",
        'bad_slot_type':      "⚠️ ਸਲਾਟ ਚੁਣਨ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਇੱਕ *ਨੰਬਰ* ਦਰਜ ਕਰੋ।",
        'lang_invalid':       "⚠️ ਕਿਰਪਾ ਕਰਕੇ ਭਾਸ਼ਾ ਚੁਣਨ ਲਈ 1, 2, 3, 4 ਜਾਂ 5 ਨਾਲ ਜਵਾਬ ਦਿਓ।",
    },
    'gu': {
        'lang_ok':            "✅ તમે પસંદ કર્યું: *ગુજરાતી*\n\nચાલો બુકિંગ શરૂ કરીએ.",
        'welcome':            "🌾 *{bname} માં આપનું સ્વાગત છે!*\n\nહું થોડા સરળ પગલાઓમાં મંડી સ્લોટ બુક કરવામાં મદદ કરીશ.\n\nકૃપા કરી તમારું *પૂરું નામ* દાખલ કરો:",
        'ask_village':        "નમસ્તે *{name}*! 👋\n\nકૃપા કરી તમારા *ગામનું નામ* દાખલ કરો:",
        'ask_crop':           "તમારી *પાકનો પ્રકાર* પસંદ કરો:\n\n1️⃣ ડાંગર\n2️⃣ ઘઉં\n3️⃣ મકાઈ\n4️⃣ સોયાબીન\n5️⃣ કપાસ\n6️⃣ અન્ય\n\n*નંબર* અથવા પાકનું નામ મોકલો:",
        'crop_ok':            "પાક: *{crop}* ✅\n\n*જથ્થો* ક્વિન્ટલમાં દાખલ કરો (છોડવા *0* મોકલો):",
        'ask_mandi':          "તમારી *નજીકની મંડી* પસંદ કરો:\n\n{mandi_list}\n\nનંબર સાથે જવાબ આપો:",
        'slots_header':       "*{mandi}* માં ઉપલબ્ધ સ્લોટ:\n\n{slot_list}\n\n*સ્લોટ નંબર* સાથે જવાબ આપો:",
        'no_slots':           "❌ માફ કરશો, *આજ*ના તમામ સ્લોટ ભરાઇ ગયા છે. કૃપા કરી કાલે ફરી પ્રયાસ કરો!",
        'confirmed':          "✅ *બુકિંગ પ્રમાણિત!*\n\n🎫 ટોકન: *{token}*\n👤 નામ: {name}\n🌿 પાક: {crop} ({qty} ક્વિ.)\n🏪 મંડી: {mandi}\n📍 સ્થળ: {loc}\n⏰ સ્લોટ: {slot}\n📅 તારીખ: {date}\n\nકૃપા કરી *સમયસર* ઉત્પાદન સાથે આવો. આભાર! 🙏\n\n_નવી બુકિંગ માટે કોઇ પણ સંદેશ મોકલો._",
        'bad_mandi':          "⚠️ કૃપા કરી *1* અને *{n}* ની વચ્ચે નંબર દાખલ કરો.",
        'bad_mandi_type':     "⚠️ મંડી પસંદ કરવા *નંબર* દાખલ કરો.",
        'bad_slot':           "⚠️ કૃપા કરી *1* અને *{n}* ની વચ્ચે નંબર દાખલ કરો.",
        'bad_slot_type':      "⚠️ સ્લોટ પસંદ કરવા *નંબર* દાખલ કરો.",
        'lang_invalid':       "⚠️ ભાષા પસંદ કરવા 1, 2, 3, 4 અથવા 5 સાથે જવાબ આપો.",
    },
    'mr': {
        'lang_ok':            "✅ तुम्ही निवडले: *मराठी*\n\nचला बुकिंग सुरू करूया.",
        'welcome':            "🌾 *{bname} मध्ये आपले स्वागत आहे!*\n\nमी काही सोप्या पायऱ्यांमध्ये मंडी स्लॉट बुक करण्यात मदत करेन.\n\nकृपया आपले *पूर्ण नाव* प्रविष्ट करा:",
        'ask_village':        "नमस्कार *{name}*! 👋\n\nकृपया आपल्या *गावाचे नाव* प्रविष्ट करा:",
        'ask_crop':           "आपला *पिकाचा प्रकार* निवडा:\n\n1️⃣ भात\n2️⃣ गहू\n3️⃣ मका\n4️⃣ सोयाबीन\n5️⃣ कापूस\n6️⃣ इतर\n\n*क्रमांक* किंवा पिकाचे नाव पाठवा:",
        'crop_ok':            "पीक: *{crop}* ✅\n\n*प्रमाण* क्विंटलमध्ये प्रविष्ट करा (वगळण्यासाठी *0* पाठवा):",
        'ask_mandi':          "आपली *जवळची मंडी* निवडा:\n\n{mandi_list}\n\nक्रमांकाने उत्तर द्या:",
        'slots_header':       "*{mandi}* मध्ये उपलब्ध स्लॉट:\n\n{slot_list}\n\n*स्लॉट क्रमांक* पाठवा:",
        'no_slots':           "❌ दिलगिरी, *आज*चे सर्व स्लॉट भरले आहेत. उद्या पुन्हा प्रयत्न करा!",
        'confirmed':          "✅ *बुकिंग निश्चित झाली!*\n\n🎫 टोकन: *{token}*\n👤 नाव: {name}\n🌿 पीक: {crop} ({qty} क्विं.)\n🏪 मंडी: {mandi}\n📍 पत्ता: {loc}\n⏰ स्लॉट: {slot}\n📅 तारीख: {date}\n\nकृपया आपल्या उत्पादनासह *वेळेवर* या. धन्यवाद! 🙏\n\n_नवीन बुकिंगसाठी कोणताही संदेश पाठवा._",
        'bad_mandi':          "⚠️ कृपया *1* आणि *{n}* दरम्यान क्रमांक प्रविष्ट करा.",
        'bad_mandi_type':     "⚠️ मंडी निवडण्यासाठी *क्रमांक* प्रविष्ट करा.",
        'bad_slot':           "⚠️ कृपया *1* आणि *{n}* दरम्यान क्रमांक प्रविष्ट करा.",
        'bad_slot_type':      "⚠️ स्लॉट निवडण्यासाठी *क्रमांक* प्रविष्ट करा.",
        'lang_invalid':       "⚠️ भाषा निवडण्यासाठी 1, 2, 3, 4 किंवा 5 ने उत्तर द्या.",
    },
}


def _t(lang: str, key: str, **kwargs) -> str:
    """Return translated string, falling back to English."""
    strings = LANG.get(lang) or LANG['en']
    tmpl = strings.get(key) or LANG['en'].get(key, '')
    return tmpl.format(**kwargs) if kwargs else tmpl


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
    Starts with a language-selection step so each farmer can interact in
    their preferred language (English / Hindi / Punjabi / Gujarati / Marathi).
    State is persisted per customer in bot-sessions.
    """
    session   = sessions_col.find_one({'customerPhone': customer_phone}) or {}
    step      = session.get('flowStep', 'lang_select')
    flow_data = session.get('flowData', {})

    # If user greets (e.g., "hi"/"hii"), restart from language selection.
    if incoming_msg.strip().lower() in LANG_RESET_GREETINGS:
        step = 'lang_select'
        flow_data = {}

    mandis       = bot.get('mandis', DEFAULT_MANDIS)
    slots        = bot.get('slots', DEFAULT_SLOTS)
    max_per_slot = int(bot.get('maxBookingsPerSlot', 10))

    # If the conversation was already completed, restart from lang_select
    if step == 'done':
        step = 'lang_select'
        flow_data = {}

    lang      = flow_data.get('language', 'en')
    reply     = ''
    next_step = step

    # ── STEP: lang_select ────────────────────────────────────
    if step == 'lang_select':
        reply     = LANG_SELECT_MSG
        next_step = 'lang_confirm'

    # ── STEP: lang_confirm ───────────────────────────────────
    elif step == 'lang_confirm':
        choice = incoming_msg.strip().lower()
        lang   = SUPPORTED_LANGS.get(choice)
        if not lang:
            # Try matching by number directly
            reply = _t('en', 'lang_invalid')
            # Stay on lang_confirm
        else:
            flow_data['language'] = lang
            lang_ack = _t(lang, 'lang_ok')
            welcome  = _t(lang, 'welcome', bname=bot.get('businessName', 'Mandi Booking'))
            reply     = f"{lang_ack}\n\n{welcome}"
            next_step = 'ask_name'

    # ── STEP: ask_name ───────────────────────────────────────
    elif step == 'ask_name':
        flow_data['farmerName'] = incoming_msg.strip()
        reply     = _t(lang, 'ask_village', name=flow_data['farmerName'])
        next_step = 'ask_village'

    # ── STEP: ask_village ────────────────────────────────────
    elif step == 'ask_village':
        flow_data['village'] = incoming_msg.strip()
        reply     = _t(lang, 'ask_crop')
        next_step = 'ask_crop'

    # ── STEP: ask_crop ───────────────────────────────────────
    elif step == 'ask_crop':
        crop_input = incoming_msg.strip()
        lang_crops = CROP_MAP_I18N.get(lang, CROP_MAP_I18N['en'])
        flow_data['cropType'] = lang_crops.get(crop_input, crop_input.title())
        reply     = _t(lang, 'crop_ok', crop=flow_data['cropType'])
        next_step = 'ask_quantity'

    # ── STEP: ask_quantity ───────────────────────────────────
    elif step == 'ask_quantity':
        qty = incoming_msg.strip()
        flow_data['quantity'] = qty if qty != '0' else 'Not specified'
        mandi_list = '\n'.join(
            [f"{i+1}️⃣ {m['name']} – {m.get('location','')}" for i, m in enumerate(mandis)]
        )
        reply     = _t(lang, 'ask_mandi', mandi_list=mandi_list)
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
                    reply     = _t(lang, 'no_slots')
                    next_step = 'done'
                else:
                    flow_data['availableSlots'] = available
                    slot_list = '\n'.join([f"{i+1}️⃣ {s}" for i, s in enumerate(available)])
                    reply     = _t(lang, 'slots_header',
                                   mandi=flow_data['mandiName'], slot_list=slot_list)
                    next_step = 'ask_slot'
            else:
                reply = _t(lang, 'bad_mandi', n=len(mandis))
        except ValueError:
            reply = _t(lang, 'bad_mandi_type')

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
                    'language':      lang,
                    'createdAt':     _now(),
                })

                reply = _t(lang, 'confirmed',
                           token=token,
                           name=flow_data.get('farmerName', ''),
                           crop=flow_data.get('cropType', ''),
                           qty=flow_data.get('quantity', ''),
                           mandi=flow_data.get('mandiName', ''),
                           loc=flow_data.get('mandiLocation', ''),
                           slot=flow_data['timeSlot'],
                           date=today)
                next_step = 'done'
            else:
                reply = _t(lang, 'bad_slot', n=len(available))
        except ValueError:
            reply = _t(lang, 'bad_slot_type')

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
_KB_COLLECTION = 'knowledge_base'

# ── IIIT-NR Quick-reference links ────────────────────────────
_IIIT_LINKS = [
    (['dean', 'academic', 'dean academic'],                             'Dean Academics',                       'https://www.iiitnr.ac.in/node/3003'),
    (['dean research', 'research', 'innovation', 'dean innovation'],    'Dean Research & Innovation',           'https://www.iiitnr.ac.in/node/1246'),
    (['board', 'board member', 'governing body'],                       'Board Members',                        'https://www.iiitnr.ac.in/content/board'),
    (['annual report', 'yearly report', 'annual'],                      'Yearly Reports',                       'https://www.iiitnr.ac.in/content/yearly-reports'),
    (['btech curriculum', 'b.tech curriculum', 'ug curriculum'],        'B.Tech Curriculum',                    'https://www.iiitnr.ac.in/content/btech-curriculum'),
    (['mtech curriculum', 'm.tech curriculum', 'pg curriculum'],        'M.Tech Curriculum',                    'https://www.iiitnr.ac.in/content/mtech-0'),
    (['phd', 'ph.d', 'doctorate', 'doctoral'],                          'PhD Program',                          'https://www.iiitnr.ac.in/content/phd'),
    (['syllabus', 'subject', 'course content'],                         'Syllabus',                             'https://www.iiitnr.ac.in/content/syllabus'),
    (['academic calendar', 'calendar', 'schedule', 'semester date'],    'Academic Calendar',                    'https://www.iiitnr.ac.in/content/academic-calendar-archive'),
    (['faculty', 'professor', 'teacher', 'staff', 'lecturer'],          'Faculty Details',                      'https://www.iiitnr.ac.in/faculty'),
    (['past faculty', 'former faculty', 'previous faculty'],            'Past Faculty',                         'https://www.iiitnr.ac.in/past-faculty'),
    (['adjunct faculty', 'visiting faculty', 'adjunct'],                'Adjunct Faculty',                      'https://www.iiitnr.ac.in/content/adjunct-faculty'),
    (['emeritus', 'emeritus visit'],                                    'Emeritus Visits',                      'https://www.iiitnr.ac.in/content/emeritus-visits'),
    (['coe', 'next generation network', 'center of excellence'],        'CoE Next Generation Network',          'https://www.iiitnr.ac.in/content/coe-next-generation-network'),
    (['tbie', 'incubation', 'entrepreneurship', 'startup', 'ecell'],   'IIIT-NR TBIE / Incubation',            'https://sites.google.com/iiitnr.edu.in/iiit-nrtbie'),
    (['patent', 'intellectual property'],                               'Patents',                              'https://www.iiitnr.ac.in/content/patents'),
    (['lab', 'laboratory', 'lab detail'],                               'Lab Details',                          'https://www.iiitnr.ac.in/content/lab-details'),
    (['workshop', 'iwatm'],                                             'Workshops',                            'https://www.iiitnr.ac.in/content/iwatm21'),
    (['conference', 'ssnm'],                                            'Conference',                           'https://ims.iiitnr.edu.in/SSNM/'),
    (['ombudsperson', 'complaint', 'grievance'],                        'Ombudsperson',                         'https://www.iiitnr.ac.in/content/ombudsperson-contact-details'),
    (['sac', 'student activity', 'student club', 'activity center'],   'Student Activity Center (SAC)',         'https://sac.iiitnr.ac.in/'),
    (['ieee', 'ieee student'],                                          'IEEE Student Branch',                  'https://ieeesb.iiitnr.ac.in/'),
    (['ecell', 'e-cell', 'entrepreneurship cell'],                      'E-Cell',                               'https://ecell.iiitnr.ac.in/'),
    (['facilit', 'infrastructure', 'campus facilit'],                   'Facilities',                           'https://www.iiitnr.ac.in/content/facilities'),
    (['it facilit', 'it infrastructure', 'internet', 'wifi', 'network infrastructure'], 'IT Infrastructure',   'https://www.iiitnr.ac.in/content/it-infrastructure'),
    (['library', 'book', 'journal', 'reading'],                        'Library',                              'https://www.iiitnr.ac.in/content/library-glance'),
    (['student achievement', 'achievement', 'award', 'result'],        'Student Achievements',                 'https://www.iiitnr.ac.in/content/archive-2019'),
    (['anti ragging', 'ragging', 'anti-ragging'],                      'Anti-Ragging Committee',               'https://www.iiitnr.ac.in/content/anti-ragging-committee'),
    (['internship', 'outreach', 'training program', 'summer intern'],  'Internship / Outreach Program',        'https://www.iiitnr.ac.in/content/outreach-2025'),
    (['vocational', 'vocational training'],                             'Vocational Training Programme',        'https://www.iiitnr.ac.in/content/vocational-training-programme'),
    (['placement statistic', 'placement stat', 'placement data'],      'Placement Statistics 2021-25',         'https://www.iiitnr.ac.in/content/placement-statistics-2021-25'),
    (['companies', 'recruiter', 'company visited', 'hiring company'],  'Companies Visited for Placement',      'https://www.iiitnr.ac.in/content/companies-visited-2021-25'),
    (['remuneration', 'salary', 'package', 'ctc'],                     'Remuneration Offered 2021-25',         'https://www.iiitnr.ac.in/content/remuneration-offered-2021-25'),
    (['industry academia', 'advisory committee', 'industry collaboration'], 'Industry-Academia Advisory Committee', 'https://www.iiitnr.ac.in/content/industry-academia-collaboration-cum-advisory-committee'),
    (['placement', 'training and placement', 'tpo', 'placement cell'], 'Training & Placement',                 'https://www.iiitnr.ac.in/content/training-and-placement'),
    (['tender', 'procurement', 'bid'],                                  'Tenders',                              'https://www.iiitnr.ac.in/tenders'),
    (['guest house', 'accommodation', 'stay', 'hostel guest'],         'Guest House',                          'https://www.iiitnr.ac.in/content/guest-house-accommodation'),
    (['btech admission', 'b.tech admission', 'ug admission', 'jee'],   'B.Tech Admission 2025',                'https://www.iiitnr.ac.in/content/b-tech-admission-2025'),
    (['mtech cmit', 'cmit fellowship', 'dsai'],                        'M.Tech CMIT Fellowship',               'https://www.iiitnr.ac.in/content/mtech-dsai-cmit-fellowship'),
    (['mtech admission', 'm.tech admission', 'pg admission', 'gate'],  'M.Tech Admission 2025',                'https://www.iiitnr.ac.in/content/mtech-admission-2025'),
    (['phd admission', 'ph.d admission', 'doctoral admission'],        'PhD Admission Spring 2026',            'https://www.iiitnr.ac.in/content/phd-admission-spring-semester-2026'),
]

def _get_relevant_links(query: str) -> str:
    """Return a formatted list of relevant IIIT-NR links for the given query."""
    q = query.lower()
    matched = []
    for keywords, label, url in _IIIT_LINKS:
        if any(kw in q for kw in keywords):
            matched.append(f"- {label}: {url}")
    if not matched:
        return ''
    return "--- RELEVANT LINKS ---\n" + '\n'.join(matched) + "\n--- END LINKS ---\n\n"


def _get_ollama_embedding(text: str) -> list:
    """Get a single embedding vector from a local Ollama embedding model."""
    import requests as _req
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    model    = os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
    resp = _req.post(
        f'{base_url}/api/embeddings',
        json={'model': model, 'prompt': text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()['embedding']


# ── BM25 helpers ─────────────────────────────────────────────────────────────

# In-memory cache: bot_id → (file_mtime, BM25Okapi, chunks_list)
_BM25_CACHE: Dict[str, tuple] = {}

def _tokenize_bm25(text: str) -> List[str]:
    """
    Unicode-aware tokenizer for BM25.
    Splits on non-word characters, lowercases — works for English and Indian scripts.
    """
    return re.findall(r'\w+', text.lower())


def _load_bm25(business_id: str):
    """
    Load BM25Okapi + chunk list from disk with mtime-based cache invalidation.
    Returns (bm25_obj, chunks) or (None, None) if index doesn't exist.
    """
    import pickle
    index_path = os.path.join(_VECTOR_STORE_ROOT, business_id, 'bm25_index.pkl')
    if not os.path.exists(index_path):
        return None, None
    try:
        mtime = os.path.getmtime(index_path)
        cached = _BM25_CACHE.get(business_id)
        if cached and cached[0] == mtime:
            return cached[1], cached[2]          # cache hit
        with open(index_path, 'rb') as f:
            data = pickle.load(f)
        bm25_obj = data['bm25']
        chunks   = data['chunks']
        _BM25_CACHE[business_id] = (mtime, bm25_obj, chunks)
        log.info(f"[BM25] Loaded index for {business_id} ({len(chunks)} chunks)")
        return bm25_obj, chunks
    except Exception as exc:
        log.warning(f"[BM25] Failed to load index for {business_id}: {exc}")
        return None, None


def _bm25_search(business_id: str, query: str, top_k: int) -> List[tuple]:
    """
    Run BM25 keyword search.
    Returns list of (chunk_text, bm25_score) sorted by score desc, length = top_k.
    Returns [] if BM25 index not available.
    """
    bm25_obj, chunks = _load_bm25(business_id)
    if bm25_obj is None:
        return []
    tokens = _tokenize_bm25(query)
    if not tokens:
        return []
    scores = bm25_obj.get_scores(tokens)
    # Get top_k indices sorted by score descending
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = [(chunks[i], float(scores[i])) for i in top_indices if scores[i] > 0]
    log.info(f"[BM25] Top scores: {[round(s, 3) for _, s in results[:4]]}")
    return results


def _rrf_merge(
    vector_results: List[tuple],   # [(text, distance), ...]  distance lower = better
    bm25_results:   List[tuple],   # [(text, score), ...]     score higher = better
    top_k: int,
    k: int = 60,
) -> List[str]:
    """
    Reciprocal Rank Fusion.
    Returns top_k chunk texts ranked by combined RRF score.
    Formula: rrf(d) = Σ  1 / (k + rank_i(d))  across all ranked lists.
    """
    rrf: Dict[str, float] = {}

    for rank, (text, _) in enumerate(vector_results):
        rrf[text] = rrf.get(text, 0.0) + 1.0 / (k + rank + 1)

    for rank, (text, _) in enumerate(bm25_results):
        rrf[text] = rrf.get(text, 0.0) + 1.0 / (k + rank + 1)

    merged = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
    log.info(
        f"[RRF] vector={len(vector_results)} bm25={len(bm25_results)} "
        f"merged={len(merged)} → top {top_k}"
    )
    return [text for text, _ in merged[:top_k]]




def _chunk_text(text: str, size: int = 500, overlap: int = 60) -> List[str]:
    """Simple sliding-window text chunker — no external dependencies."""
    chunks: List[str] = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += size - overlap
    return chunks


def _rag_query(business_id: str, query: str) -> str:
    """
    Hybrid RAG: ChromaDB vector search + BM25 keyword search, fused via RRF.

    Pipeline:
      1. Vector search  — semantic similarity via nomic-embed-text + ChromaDB
      2. BM25 search    — exact keyword recall via rank_bm25 (graceful fallback if index missing)
      3. RRF fusion     — Reciprocal Rank Fusion (k=60) to merge & rerank both lists
      4. Returns top-5 chunks as a single string for the LLM prompt

    Kill switch: set RAG_BM25_ENABLED=false in .env to revert to pure vector search.
    """
    store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
    if not os.path.exists(store_path):
        log.warning(f"[RAG] No vector store found for bot {business_id}")
        return ''

    TOP_K      = 5    # final chunks sent to the LLM
    CANDIDATES = 10   # candidates fetched from each source before merging

    try:
        import chromadb

        # ── 1. Vector search ──────────────────────────────────
        query_embedding = _get_ollama_embedding(query)
        client     = chromadb.PersistentClient(path=store_path)
        collection = client.get_collection(_KB_COLLECTION)
        total      = collection.count()
        log.info(f"[RAG] Vector search over {total} chunks for bot {business_id}")

        results   = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(CANDIDATES, total),
            include=['documents', 'distances'],
        )
        docs      = results.get('documents', [[]])[0] or []
        distances = results.get('distances',  [[]])[0] or []

        # Distance threshold — auto-detect cosine vs L2 metric
        env_threshold = float(os.getenv('RAG_MAX_DISTANCE', '0.0'))
        if env_threshold > 0:
            max_dist = env_threshold
        elif distances and max(distances) > 10:
            median_d = sorted(distances)[len(distances) // 2]
            max_dist = median_d * 1.2
            log.info(f"[RAG] L2 metric detected; auto-threshold={max_dist:.1f}")
        else:
            max_dist = 0.55   # cosine: keep ≥45% similar chunks

        paired   = list(zip(docs, distances)) if distances else [(d, 0.0) for d in docs]
        filtered = [(doc, dist) for doc, dist in paired if dist <= max_dist]

        if not filtered and docs:
            # All chunks were filtered out — fall back to top candidates
            filtered = paired[:max(1, int(os.getenv('RAG_FALLBACK_TOP_K', '5')))]
            log.warning(f"[RAG] Distance filter removed all — using top fallback chunks")

        log.info(
            f"[RAG] Vector: retrieved {len(docs)}, kept {len(filtered)} "
            f"(max_dist={max_dist:.2f}) | top distances: {[round(d,3) for _,d in filtered[:4]]}"
        )
        vector_results = [(doc, dist) for doc, dist in filtered]  # (text, distance)

        # ── 2. BM25 keyword search ────────────────────────────
        bm25_enabled = os.getenv('RAG_BM25_ENABLED', 'true').lower() != 'false'
        if bm25_enabled:
            bm25_results = _bm25_search(business_id, query, top_k=CANDIDATES)
            if not bm25_results:
                log.info("[RAG] BM25 index missing or no matches — using pure vector results")
        else:
            bm25_results = []
            log.info("[RAG] BM25 disabled via RAG_BM25_ENABLED=false")

        # ── 3. RRF fusion ─────────────────────────────────────
        if bm25_results:
            final_chunks = _rrf_merge(vector_results, bm25_results, top_k=TOP_K)
            log.info(f"[RAG] Hybrid RRF final chunks: {len(final_chunks)}")
        else:
            # Pure vector fallback (BM25 disabled or index missing)
            final_chunks = [doc for doc, _ in vector_results[:TOP_K]]
            log.info(f"[RAG] Pure vector final chunks: {len(final_chunks)}")

        if final_chunks:
            log.debug(f"[RAG] First chunk preview: {final_chunks[0][:200]!r}")

        return '\n\n'.join(final_chunks)

    except Exception as exc:
        log.error(f"[RAG] Query failed for {business_id}: {exc}")
        return ''


def _is_faculty_list_query(text: str) -> bool:
    """Heuristic intent check for faculty-list style questions."""
    q = (text or '').lower()
    return (
        'faculty' in q and
        any(k in q for k in ('list', 'members', 'member', 'names', 'name'))
    )



def _extract_faculty_names(context: str, max_names: int = 25) -> List[str]:
    """Extract likely faculty names from RAG context using title-based patterns."""
    # Keep extraction conservative to avoid returning random entities.
    patt = re.compile(
        r"\b(?:Prof(?:essor)?\.?|Dr\.?)\s+[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3}"
    )
    seen = set()
    names: List[str] = []
    for match in patt.findall(context or ''):
        clean = re.sub(r"\s+", ' ', match).strip()
        if clean.lower() in seen:
            continue
        seen.add(clean.lower())
        names.append(clean)
        if len(names) >= max_names:
            break
    return names




# ── Multilingual support ─────────────────────────────────────────────────────

# Unicode script ranges → (lang_code, lang_name)
_INDIAN_SCRIPT_RANGES = [
    (0x0900, 0x097F, 'hi',  'Hindi'),        # Devanagari  (Hindi / Marathi / Sanskrit)
    (0x0980, 0x09FF, 'bn',  'Bengali'),
    (0x0A00, 0x0A7F, 'pa',  'Punjabi'),
    (0x0A80, 0x0AFF, 'gu',  'Gujarati'),
    (0x0B00, 0x0B7F, 'or',  'Odia'),
    (0x0B80, 0x0BFF, 'ta',  'Tamil'),
    (0x0C00, 0x0C7F, 'te',  'Telugu'),
    (0x0C80, 0x0CFF, 'kn',  'Kannada'),
    (0x0D00, 0x0D7F, 'ml',  'Malayalam'),
    (0x0600, 0x06FF, 'ur',  'Urdu'),         # Arabic script (Urdu)
]

# Romanised-Hindi / Hinglish keywords that identify the language
_HINGLISH_TRIGGERS = {
    'kya', 'hai', 'hain', 'mujhe', 'mera', 'meri', 'mere', 'aap', 'tum',
    'kaise', 'kaisa', 'kahan', 'kitne', 'kitna', 'chahiye', 'batao',
    'bata', 'samjhao', 'karo', 'karo', 'accha', 'theek', 'sahi',
    'nahi', 'nahin', 'kyun', 'kyunki', 'lekin', 'aur', 'yeh', 'woh',
}

def _detect_language(text: str) -> tuple:
    """
    Returns (lang_code, lang_name).
    Priority: Indian Unicode script → Hinglish heuristic → langdetect → English.
    """
    # 1. Script-based detection — instant and accurate for typed Indian scripts
    for ch in text:
        cp = ord(ch)
        for lo, hi, code, name in _INDIAN_SCRIPT_RANGES:
            if lo <= cp <= hi:
                return code, name

    # 2. Hinglish heuristic
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    if len(words & _HINGLISH_TRIGGERS) >= 1:
        return 'hi_roman', 'Hindi (Roman)'

    # 3. langdetect as optional fallback for other romanised languages
    try:
        from langdetect import detect
        _LANGDETECT_MAP = {
            'hi': ('hi', 'Hindi'), 'bn': ('bn', 'Bengali'),
            'ta': ('ta', 'Tamil'), 'te': ('te', 'Telugu'),
            'kn': ('kn', 'Kannada'), 'ml': ('ml', 'Malayalam'),
            'gu': ('gu', 'Gujarati'), 'mr': ('mr', 'Marathi'),
            'pa': ('pa', 'Punjabi'), 'ur': ('ur', 'Urdu'),
            'or': ('or', 'Odia'),
        }
        code = detect(text)
        if code in _LANGDETECT_MAP:
            return _LANGDETECT_MAP[code]
    except Exception:
        pass

    return 'en', 'English'


# Pre-translated greeting messages (instant, no LLM needed)
_GREETING_MSGS = {
    'hi':       "नमस्ते! 👋 मैं IIIT नया रायपुर के बारे में आपके किसी भी सवाल में मदद करने के लिए यहाँ हूँ। बस पूछिए!",
    'hi_roman': "Namaste! 👋 Main IIIT Naya Raipur ke baare mein aapke kisi bhi sawaal mein madad karne ke liye yahan hoon. Bas poochiye!",
    'mr':       "नमस्कार! 👋 मी IIIT नया रायपूर बद्दल तुमच्या कोणत्याही प्रश्नांसाठी येथे आहे. विचारा!",
    'bn':       "হ্যালো! 👋 আমি IIIT নয়া রায়পুর সম্পর্কে আপনার যেকোনো প্রশ্নে সাহায্য করতে এখানে আছি। জিজ্ঞেস করুন!",
    'ta':       "வணக்கம்! 👋 நான் IIIT நயா ரைபூர் பற்றிய உங்கள் கேள்விகளுக்கு உதவ இங்கே இருக்கிறேன். கேளுங்கள்!",
    'te':       "నమస్కారం! 👋 నేను IIIT నయా రైపూర్ గురించి మీ ఏ ప్రశ్నలకైనా సహాయం చేయడానికి ఇక్కడ ఉన్నాను. అడగండి!",
    'kn':       "ನಮಸ್ಕಾರ! 👋 ನಾನು IIIT ನಯಾ ರಾಯಪುರ್ ಬಗ್ಗೆ ನಿಮ್ಮ ಯಾವುದೇ ಪ್ರಶ್ನೆಗಳಿಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿದ್ದೇನೆ. ಕೇಳಿ!",
    'ml':       "നമസ്കാരം! 👋 IIIT നയാ റായ്‌പൂർ സംബന്ധിച്ച നിങ്ങളുടെ ഏത് ചോദ്യങ്ങൾക്കും ഞാൻ ഇവിടെ ഉണ്ട്. ചോദിക്കൂ!",
    'gu':       "નમસ્તે! 👋 હું IIIT નયા રાયપુર વિશે તમારા કોઈ પણ સવાલ માટે અહીં છું. પૂછો!",
    'pa':       "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! 👋 ਮੈਂ IIIT ਨਯਾ ਰਾਏਪੁਰ ਬਾਰੇ ਤੁਹਾਡੇ ਕਿਸੇ ਵੀ ਸਵਾਲ ਵਿੱਚ ਮਦਦ ਕਰਨ ਲਈ ਇੱਥੇ ਹਾਂ। ਪੁੱਛੋ!",
    'ur':       "السلام علیکم! 👋 میں IIIT نیا رائے پور کے بارے میں آپ کے کسی بھی سوال میں مدد کے لیے یہاں ہوں۔ پوچھیں!",
    'or':       "ନମସ୍କାର! 👋 ମୁଁ IIIT ନୟା ରାୟପୁର ବିଷୟରେ ଆପଣଙ୍କ ଯେକୌଣସି ପ୍ରଶ୍ନରେ ସାହାଯ୍ୟ କରିବାକୁ ଏଠାରେ ଅଛି। ପଚାରନ୍ତୁ!",
    'en':       "Hi 👋 I'm here to help you with any questions about IIIT Naya Raipur. Just ask!",
}

# Pre-translated fallback messages (no context found)
_FALLBACK_MSGS = {
    'hi':       "माफ़ कीजिए, मेरे पास अभी इस बारे में जानकारी नहीं है। सटीक जानकारी के लिए सीधे IIIT नया रायपुर से संपर्क करें।",
    'hi_roman': "Sorry, abhi mere paas is baare mein jaankari nahi hai. Sahi jaankari ke liye seedha IIIT Naya Raipur se sampark karein.",
    'mr':       "माफ करा, सध्या माझ्याकडे त्याबद्दल माहिती नाही. अचूक माहितीसाठी थेट IIIT नया रायपूरशी संपर्क साधा.",
    'bn':       "দুঃখিত, এখন আমার কাছে এ বিষয়ে তথ্য নেই। সঠিক তথ্যের জন্য সরাসরি IIIT নয়া রায়পুরে যোগাযোগ করুন।",
    'ta':       "மன்னிக்கவும், இப்போது அதற்கான விவரங்கள் என்னிடம் இல்லை। சரியான தகவலுக்கு IIIT நயா ரைபூரை நேரடியாக தொடர்பு கொள்ளுங்கள்.",
    'te':       "క్షమించండి, ఇప్పుడు నా దగ్గర దాని గురించి వివరాలు లేవు. సరైన సమాచారం కోసం నేరుగా IIIT నయా రైపూర్‌ను సంప్రదించండి.",
    'kn':       "ಕ್ಷಮಿಸಿ, ಇದರ ಬಗ್ಗೆ ಈಗ ನನ್ನ ಬಳಿ ಮಾಹಿತಿ ಇಲ್ಲ. ನಿಖರ ಮಾಹಿತಿಗಾಗಿ ನೇರವಾಗಿ IIIT ನಯಾ ರಾಯಪುರ್ ಅನ್ನು ಸಂಪರ್ಕಿಸಿ.",
    'ml':       "ക്ഷമിക്കണം, ഇപ്പോൾ എന്റെ കൈയ്യിൽ അതിനെ കുറിച്ചുള്ള വിവരങ്ങൾ ഇല്ല. കൃത്യമായ വിവരത്തിന് IIIT നയാ റായ്‌പൂരുമായി നേരിട്ട് ബന്ധപ്പെടുക.",
    'gu':       "માફ કરો, અત્યારે મારી પાસે આ વિશે માહિતી નથી. સચોટ માહિતી માટે IIIT નયા રાયપુરને સીધો સંપર્ક કરો.",
    'pa':       "ਮਾਫ਼ ਕਰਨਾ, ਹੁਣ ਮੇਰੇ ਕੋਲ ਇਸ ਬਾਰੇ ਜਾਣਕਾਰੀ ਨਹੀਂ ਹੈ। ਸਹੀ ਜਾਣਕਾਰੀ ਲਈ ਸਿੱਧੇ IIIT ਨਯਾ ਰਾਏਪੁਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
    'ur':       "معاف کیجیے، ابھی میرے پاس اس بارے میں معلومات نہیں ہے۔ درست معلومات کے لیے براہ راست IIIT نیا رائے پور سے رابطہ کریں۔",
    'en':       "Sorry, I don't have details on that right now. Please contact IIIT Naya Raipur directly for accurate information.",
}

# "Relevant Links" header in each language
_LINKS_HEADER = {
    'hi': '*संबंधित लिंक:*', 'hi_roman': '*Relevant Links:*',
    'mr': '*संबंधित लिंक:*', 'bn': '*সম্পর্কিত লিংক:*',
    'ta': '*தொடர்புடைய இணைப்புகள்:*', 'te': '*సంబంధిత లింకులు:*',
    'kn': '*ಸಂಬಂಧಿತ ಲಿಂಕ್‌ಗಳು:*', 'ml': '*ബന്ധപ്പെട്ട ലിങ്കുകൾ:*',
    'gu': '*સંબંધિત લિંક્સ:*', 'pa': '*ਸੰਬੰਧਿਤ ਲਿੰਕ:*',
    'ur': '*متعلقہ لنک:*', 'or': '*ସଂପ୍ରକ୍ତ ଲିଙ୍କ:*',
    'en': '*Relevant Links:*',
}

_GREETING_TRIGGERS = {
    'hi', 'hello', 'hey', 'hii', 'helo', 'heya', 'howdy', 'sup', 'hola',
    'good morning', 'good afternoon', 'good evening', 'good night',
    'namaste', 'namaskar', 'jai hind', 'hello there', 'hi there',
    'start', 'help', 'menu',
    # Hindi greetings typed in Devanagari
    'नमस्ते', 'नमस्कार', 'हेलो', 'हाय',
    # Other Indian language greetings
    'வணக்கம்', 'నమస్కారం', 'ನಮಸ್ಕಾರ', 'നമസ്കാരം',
    'নমস্কার', 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ', 'નમસ્તે', 'ନମସ୍କାର',
}

def _is_greeting(text: str) -> bool:
    t = text.strip().lower().rstrip('!.,?')
    return t in _GREETING_TRIGGERS or (len(t) <= 10 and any(g in t for g in ('hi', 'hello', 'hey')))


def _handle_ai_flow(bot: Dict, customer_phone: str, incoming_msg: str) -> str:
    """
    Handle a message using local Ollama LLM with full multilingual support.
    Automatically injects RAG context when aiRagEnabled = True.
    """
    import requests as _req

    # ── Detect language first (used throughout) ───────────────
    lang_code, lang_name = _detect_language(incoming_msg)
    log.info(f"[AI] Detected language: {lang_name} ({lang_code})")

    # ── Greet warmly without involving LLM or RAG ─────────────
    if _is_greeting(incoming_msg):
        return _GREETING_MSGS.get(lang_code, _GREETING_MSGS['en'])

    business_id = bot['businessId']
    rag_enabled = bool(bot.get('aiRagEnabled', False))

    # ── Conversation history (last 8 turns, oldest first) ──────
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

    # ── RAG context ────────────────────────────────────────────
    rag_context = ''
    if rag_enabled:
        rag_context = _rag_query(business_id, incoming_msg)
        log.info(f"[AI] RAG context length: {len(rag_context)} chars")

    # ── Deterministic faculty-list path ───────────────────────
    if rag_enabled and rag_context and _is_faculty_list_query(incoming_msg):
        chunks = rag_context.split('\n\n')
        main_chunks = [
            c for c in chunks
            if 'iiitnr.ac.in/faculty' in c
            and 'adjunct-faculty' not in c
            and 'past-faculty' not in c
            and 'emeritus' not in c.lower()
        ]
        context_for_names = '\n\n'.join(main_chunks) if main_chunks else rag_context
        names = _extract_faculty_names(context_for_names)
        source_url = 'https://www.iiitnr.ac.in/faculty'
        if names:
            lines = '\n'.join(f"- {n}" for n in names[:20])
            return (
                "Here are the faculty members at IIIT Naya Raipur:\n\n"
                f"{lines}\n\n"
                f"For the full list, visit: {source_url}"
            )
        return f"You can find the complete faculty list on the official page:\n{source_url}"

    # ── Build language-aware system prompt ────────────────────
    # Explicit language instruction beats "reply in same language" for local LLMs
    lang_instruction = (
        f"IMPORTANT: You MUST reply in {lang_name}. "
        if lang_code != 'en'
        else "Reply in English. "
    )
    if lang_code == 'hi_roman':
        lang_instruction = "IMPORTANT: The user is writing in Hinglish (Roman Hindi). Reply in the same Roman Hindi style. "

    business_name = bot.get('businessName', 'this business')
    if bot.get('aiSystemPrompt'):
        system_prompt = bot['aiSystemPrompt']
        if rag_enabled:
            system_prompt += (
                f"\n\n{lang_instruction}"
                "IMPORTANT: You have been provided reference information below. "
                "Answer ONLY from that information. Do NOT use your general training knowledge. "
                "Do NOT invent facts, links, numbers, or names not in the provided information. "
                "If the answer is not there, say you don't have that information and suggest contacting IIIT Naya Raipur directly."
            )
        else:
            system_prompt += f"\n\n{lang_instruction}"
    elif rag_enabled:
        system_prompt = (
            f"You are a friendly and helpful assistant for {business_name}. "
            f"{lang_instruction}"
            "Answer ONLY using the reference information provided below. "
            "Do NOT use your general training knowledge. "
            "Do NOT invent facts, prices, links, phone numbers, or names not in the provided information. "
            "Keep your tone warm and conversational. "
            "If the answer is not in the provided information, say you don't have that information "
            "and suggest contacting IIIT Naya Raipur directly."
        )
    else:
        system_prompt = (
            f"You are a helpful assistant for *{business_name}*. "
            f"{lang_instruction}"
            "Answer clearly and concisely."
        )

    # ── Full prompt ────────────────────────────────────────────
    links_header = _LINKS_HEADER.get(lang_code, _LINKS_HEADER['en'])

    if rag_enabled and rag_context:
        context_block = f"--- REFERENCE INFORMATION ---\n{rag_context}\n--- END ---\n\n"
    elif rag_enabled and not rag_context:
        # No context found — return pre-translated fallback + relevant links
        matched_links = _get_relevant_links(incoming_msg)
        link_lines = [l for l in matched_links.splitlines() if l.startswith('- ')] if matched_links else []
        fallback = bot.get('fallbackMessage') or _FALLBACK_MSGS.get(lang_code, _FALLBACK_MSGS['en'])
        if link_lines:
            fallback += f"\n\n{links_header}\n" + '\n'.join(link_lines)
        log.warning(f"[AI] No RAG context for query: {incoming_msg[:80]!r}")
        return fallback
    else:
        context_block = ''

    # ── Call Ollama ────────────────────────────────────────────
    base_url   = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    chat_model = os.getenv('OLLAMA_CHAT_MODEL', 'llama3')
    log.info(f"[AI] Ollama ({chat_model}) | lang={lang_name} | rag={rag_enabled}")
    try:
        resp = _req.post(
            f'{base_url}/api/chat',
            json={
                'model': chat_model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user',   'content': f"{context_block}{history_str}User: {incoming_msg}"},
                ],
                'stream': False,
                'options': {'temperature': 0.4, 'num_predict': 1024},
            },
            timeout=120,
        )
        resp.raise_for_status()
        reply = resp.json().get('message', {}).get('content', '').strip()
        log.info(f"[AI] Ollama reply: {reply[:200]!r}")
        if not reply:
            return _FALLBACK_MSGS.get(lang_code, _FALLBACK_MSGS['en'])
        # Append relevant links with language-appropriate header
        matched_links = _get_relevant_links(incoming_msg)
        if matched_links:
            link_lines = [l for l in matched_links.splitlines() if l.startswith('- ')]
            if link_lines:
                reply += f"\n\n{links_header}\n" + '\n'.join(link_lines)
        return reply
    except Exception as exc:
        log.error(f"[AI] Ollama error: {exc}")
        return "⚠️ I'm having trouble connecting right now. Please try again in a moment."


# ── ROUTE: AI — List available models ────────────────────────
@app.route('/api/ai/models', methods=['GET'])
def list_ai_models():
    """Return available local Ollama model names."""
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    try:
        import requests as _req
        r = _req.get(f'{base_url}/api/tags', timeout=5)
        r.raise_for_status()
        models = [m['name'] for m in r.json().get('models', [])]
    except Exception:
        models = [os.getenv('OLLAMA_CHAT_MODEL', 'llama3')]
    return jsonify({'models': models, 'provider': 'ollama'})


# ── In-memory KB job progress store ──────────────────────────
_kb_jobs: Dict[str, Dict] = {}  # job_id -> {status, progress, total, done, error}


def _parse_kb_texts(raw: str, ext: str) -> List[str]:
    """Parse raw file content into text segments based on file type."""
    texts: List[str] = []
    if ext == 'json':
        try:
            import json as _json
            data = _json.loads(raw)
            if isinstance(data, list) and data and isinstance(data[0], dict):
                if 'content' in data[0]:
                    for item in data:
                        content   = item.get('content', '')
                        title     = item.get('title', '')
                        url       = item.get('url', '')
                        section   = item.get('section', '')
                        key_links = item.get('key_links', [])

                        home_idx = content.find('Home >')
                        if home_idx != -1:
                            content = content[home_idx + len('Home >'):]

                        for footer_marker in ('Contact IIIT', 'Sitemap Terms', 'Back to Top',
                                              'Plot No. 7, Sector 24'):
                            idx = content.find(footer_marker)
                            if idx != -1:
                                content = content[:idx]
                                break

                        content = content.strip()
                        if not content:
                            continue

                        parts = [f"Source URL: {url}"]
                        if title:   parts.append(f"Page Title: {title}")
                        if section: parts.append(f"Section: {section}")
                        parts.append('')
                        parts.append(content)
                        if key_links:
                            parts.append('')
                            parts.append('Related links on this page:')
                            for lnk in key_links[:15]:
                                lnk_text = lnk.get('text', '')
                                lnk_url  = lnk.get('url', '')
                                if lnk_text and lnk_url:
                                    parts.append(f"  - {lnk_text}: {lnk_url}")
                        texts.append('\n'.join(parts))
                else:
                    texts = [_json.dumps(item, ensure_ascii=False) for item in data]
            elif isinstance(data, list):
                texts = [str(item) for item in data]
            elif isinstance(data, dict):
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
        texts = [p.strip() for p in raw.split('\n\n') if p.strip()] or [raw]
    return texts


def _run_kb_embed_job(job_id: str, business_id: str, filename: str, all_chunks: List[str]):
    """
    Background thread: embed all chunks via local Ollama embedding model,
    then persist to ChromaDB.
    """
    import requests as _req
    import chromadb, uuid as _uuid
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    job = _kb_jobs[job_id]
    total = len(all_chunks)
    base_url    = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    embed_model = os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
    all_embeddings: List[list] = [None] * total
    completed = [0]
    lock = threading.Lock()

    def _embed_one(idx: int, text: str) -> tuple:
        resp = _req.post(
            f'{base_url}/api/embeddings',
            json={'model': embed_model, 'prompt': text},
            timeout=60,
        )
        resp.raise_for_status()
        return idx, resp.json()['embedding']

    try:
        # Parallel workers — no rate limit since Ollama is local
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_embed_one, i, chunk): i for i, chunk in enumerate(all_chunks)}
            for future in as_completed(futures):
                idx, vec = future.result()
                all_embeddings[idx] = vec
                with lock:
                    completed[0] += 1
                    done = completed[0]
                job['progress'] = min(round((done / total) * 95), 95)
                if done % 200 == 0 or done == total:
                    log.info(f"[RAG] Job {job_id}: {done}/{total} chunks embedded")
        log.info(f"[RAG] Job {job_id}: embedding complete, writing to ChromaDB…")

        # Write to ChromaDB
        store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
        os.makedirs(store_path, exist_ok=True)
        client = chromadb.PersistentClient(path=store_path)
        try:
            client.delete_collection(_KB_COLLECTION)
        except Exception:
            pass
        collection = client.create_collection(_KB_COLLECTION, metadata={'hnsw:space': 'cosine'})
        ids       = [str(_uuid.uuid4()) for _ in all_chunks]
        metadatas = [{'source': filename} for _ in all_chunks]
        collection.add(documents=all_chunks, embeddings=all_embeddings, ids=ids, metadatas=metadatas)

        job['progress'] = 100
        job['status']   = 'done'
        job['chunks']   = total
        log.info(f"[RAG] Job {job_id}: done — {total} chunks ingested for bot {business_id}")
    except Exception as exc:
        log.error(f"[RAG] Job {job_id} failed: {exc}")
        job['status'] = 'error'
        job['error']  = str(exc)


# ── ROUTE: AI — Knowledge Base (RAG) ─────────────────────────
@app.route('/api/ai/kb/<business_id>', methods=['POST'])
def upload_kb(business_id: str):
    """
    Ingest a KB file (TXT, JSON, CSV, MD) into the bot's Chroma vector store.
    Returns a job_id immediately; embeddings run in a background thread.
    Poll GET /api/ai/kb/progress/<job_id> for live progress.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided (field name: file)'}), 400

    file     = request.files['file']
    filename = file.filename or 'kb.txt'
    ext      = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'
    raw      = file.read().decode('utf-8', errors='replace')

    texts = _parse_kb_texts(raw, ext)
    all_chunks = [c for text in texts for c in _chunk_text(text) if c.strip()]
    if not all_chunks:
        return jsonify({'error': 'No usable content found in file'}), 400

    import uuid as _uuid, threading
    job_id = str(_uuid.uuid4())
    _kb_jobs[job_id] = {'status': 'processing', 'progress': 0, 'total': len(all_chunks), 'chunks': 0, 'error': None}

    t = threading.Thread(target=_run_kb_embed_job, args=(job_id, business_id, filename, all_chunks), daemon=True)
    t.start()

    log.info(f"[RAG] Started KB embed job {job_id} for bot {business_id} ({len(all_chunks)} chunks)")
    return jsonify({'jobId': job_id, 'totalChunks': len(all_chunks), 'message': 'Embedding started'})


@app.route('/api/ai/kb/progress/<job_id>', methods=['GET'])
def kb_job_progress(job_id: str):
    """Poll this endpoint to get live embedding progress for a KB upload job."""
    job = _kb_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@app.route('/api/ai/kb/<business_id>', methods=['GET'])
def get_kb_info(business_id: str):
    """Return metadata about this bot's vector store."""
    store_path = os.path.join(_VECTOR_STORE_ROOT, business_id)
    if not os.path.exists(store_path):
        return jsonify({'exists': False, 'chunks': 0})
    try:
        import chromadb
        client     = chromadb.PersistentClient(path=store_path)
        collection = client.get_collection(_KB_COLLECTION)
        count      = collection.count()
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

    # Ignore Twilio status callbacks / self-pings (From == our own number)
    if from_number == TWILIO_WHATSAPP_NUMBER or customer_phone == TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', ''):
        log.debug(f"[WEBHOOK] Ignoring self-callback from {from_number}")
        return '', 204

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

    # ── Credit check (sync, fast) ────────────────────────────────
    if user_id:
        credits = _get_or_init_credits(user_id)
        if credits <= 0:
            log.warning(f"[CREDITS] User {user_id} has no credits — blocking reply for bot {business_id}")
            def _send_no_credit():
                try:
                    twilio_client.messages.create(
                        from_=TWILIO_WHATSAPP_NUMBER,
                        to=from_number,
                        body=(
                            "⚠️ Your BotSetu message credits are exhausted. "
                            "Please top up at https://botsetu.com/payment to continue."
                        ),
                    )
                except Exception as e:
                    log.error(f"[WEBHOOK] Failed to send no-credit msg: {e}")
            import threading
            threading.Thread(target=_send_no_credit, daemon=True).start()
            return '', 204

    # ── Ack Twilio immediately, process in background ────────────
    def _process_and_send():
        bot_type = bot.get('botType', 'normal')
        if bot_type == 'ai':
            reply = _handle_ai_flow(bot, customer_phone, incoming_msg)
        elif bot.get('useCaseType') == 'mandi_booking':
            reply = _handle_mandi_flow(bot, customer_phone, incoming_msg)
        else:
            reply = _build_reply(bot, incoming_msg)

        if reply:
            try:
                if len(reply) > 1600:
                    reply = reply[:1597] + '…'
                msg = twilio_client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    to=from_number,
                    body=reply,
                )
                log.info(f"[WEBHOOK] Outbound message SID={msg.sid} status={msg.status} to={customer_phone}")
                if msg.status in ('failed', 'undelivered'):
                    log.error(f"[WEBHOOK] Twilio rejected outbound message: error_code={msg.error_code} error_message={msg.error_message}")
                else:
                    _log_message(business_id, user_id, customer_phone, reply, 'bot')
                    if user_id:
                        _deduct_credit(user_id)
                    log.info(f"[WEBHOOK] Auto-reply sent to {customer_phone}: {reply!r}")
            except Exception as e:
                log.error(f"[WEBHOOK] Failed to send reply via Twilio: {e}")
        else:
            log.info(f"[WEBHOOK] autoReply disabled for bot {business_id} — no reply sent")

    import threading
    threading.Thread(target=_process_and_send, daemon=True).start()
    return '', 204


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
# ── ROUTE: Bot Deactivation
# ═════════════════════════════════════════════════════════════

@app.route('/api/bot/deactivate', methods=['POST'])
def deactivate_bot():
    """
    Deactivate a bot — removes its allocated number and sets status to inactive.
    After this, the Twilio number will route to whichever other bot is activated next.

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

    now = _now()
    bots_col.update_one(
        {'businessId': business_id, 'ownerUserId': user_id},
        {
            '$set': {
                'verificationStatus': 'inactive',
                'updatedAt':          now,
            },
            '$unset': {
                'allocatedNumber': '',
                'activatedAt':     '',
            }
        }
    )

    # Drop all active sessions tied to this bot so customers aren't stuck
    sessions_col.delete_many({'businessId': business_id})

    log.info(f"[DEACTIVATE] Bot {business_id} deactivated")
    return jsonify({'message': 'Bot deactivated successfully', 'businessId': business_id})


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
# ── IVR VOICE HELPERS + ROUTES  (Twilio Voice / DTMF)
# ═════════════════════════════════════════════════════════════

def _ivr_webhook_base() -> str:
    """Return the base URL for IVR gather callbacks (strips WhatsApp webhook path)."""
    base = os.getenv('WEBHOOK_URL', '')
    if base.endswith('/webhook/whatsapp'):
        base = base[: -len('/webhook/whatsapp')]
    return base.rstrip('/')


def _build_ivr_twiml(node: Dict, business_id: str, webhook_base: str):
    """
    Recursively build a TwiML VoiceResponse for the given IVR node.
    - End nodes: say the message and hang up.
    - Branch nodes: build a <Gather> menu, then hang up if no input.
    Returns a Flask (response_str, status, headers) tuple.
    """
    response = VoiceResponse()
    message  = (node.get('message') or '').strip()
    options  = node.get('options') or []

    if not message:
        response.say("This menu has no message configured. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    if node.get('isEndNode') or not options:
        response.say(message, voice='alice', language='en-IN')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    # Build DTMF menu text
    menu_text = message + ' '
    for i, opt in enumerate(options, 1):
        label = (opt.get('label') or '').strip()
        if label:
            menu_text += f"Press {i} for {label}. "

    gather = Gather(
        num_digits=1,
        action=f"{webhook_base}/webhook/voice/gather/{business_id}/{node['id']}",
        method='POST',
        timeout=10,
    )
    gather.say(menu_text, voice='alice', language='en-IN')
    response.append(gather)

    # No input fallback
    response.say("We did not receive any input. Goodbye.", voice='alice')
    response.hangup()
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route('/webhook/voice', methods=['GET', 'POST'])
def voice_webhook():
    """
    Twilio Voice webhook — handles incoming phone calls and presents the IVR menu.
    Set this as the "A call comes in" webhook URL in Twilio Console → Phone Numbers.
    """
    from_number = request.values.get('From', 'unknown')
    log.info(f"[VOICE] Incoming call from {from_number}")

    # Find the most-recently-activated IVR bot
    bot = bots_col.find_one(
        {'verificationStatus': 'verified', 'useCaseType': 'ivr'},
        sort=[('activatedAt', -1)]
    )

    if not bot:
        response = VoiceResponse()
        response.say("No IVR bot is currently active. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    business_id = bot['businessId']
    ivr_nodes   = bot.get('ivrNodes') or []
    root_node   = next((n for n in ivr_nodes if n['id'] == 'node_root'), None)

    if not root_node or not (root_node.get('message') or '').strip():
        response = VoiceResponse()
        response.say("This bot has no IVR flow configured. Goodbye.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    log.info(f"[VOICE] Routing to IVR bot {business_id}")
    return _build_ivr_twiml(root_node, business_id, _ivr_webhook_base())


@app.route('/webhook/voice/gather/<business_id>/<node_id>', methods=['POST'])
def voice_gather(business_id: str, node_id: str):
    """
    Handle DTMF digit input from a Twilio <Gather>.
    Navigates the IVR tree and returns the next TwiML node.
    """
    digit = request.values.get('Digits', '').strip()
    log.info(f"[VOICE] Gather: bot={business_id} node={node_id} digit={digit!r}")

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
                return _build_ivr_twiml(next_node, business_id, _ivr_webhook_base())
    except (ValueError, IndexError):
        pass

    response = VoiceResponse()
    response.say("Invalid option. Please try again. Goodbye.", voice='alice')
    response.hangup()
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route('/api/bot/ivr-number', methods=['GET'])
def get_ivr_number():
    """Return the Twilio phone number and voice webhook URL for IVR bots."""
    voice_webhook = _ivr_webhook_base() + '/webhook/voice'
    return jsonify({
        'phoneNumber':    TWILIO_PHONE_NUMBER,
        'voiceWebhookUrl': voice_webhook,
    })


@app.route('/api/bot/sandbox-info', methods=['GET'])
def get_sandbox_info():
    """Return WhatsApp sandbox number and join keyword for QR/link generation."""
    raw_number = TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '').lstrip('+')
    join_text  = os.getenv('TWILIO_SANDBOX_KEYWORD', '').strip().strip('"')
    return jsonify({
        'whatsappNumber': raw_number,
        'joinText':       join_text,
    })


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
