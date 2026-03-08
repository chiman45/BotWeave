"""
BotSetu — WhatsApp Bot Creator (Wizard)
========================================
Asks step-by-step WHAT the bot should do, then creates and activates it.

Usage:
    python create_bot.py
"""

import os
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID     = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN      = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
MONGODB_URI            = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

# ── colours ──────────────────────────────────────────────────
G   = "\033[92m"
R   = "\033[91m"
Y   = "\033[93m"
C   = "\033[96m"
W   = "\033[97m"
DIM = "\033[2m"
B   = "\033[1m"
RST = "\033[0m"

def ok(s):    print(f"\n  {G}✔{RST}  {s}")
def err(s):   print(f"\n  {R}✘{RST}  {s}")
def info(s):  print(f"  {DIM}ℹ  {s}{RST}")
def step(n, title): print(f"\n  {C}{B}━━  Step {n}  ━━  {title}{RST}\n")
def sep():    print(f"  {DIM}{'─'*56}{RST}")

def ask(prompt, default=""):
    suffix = f" {DIM}[{default}]{RST}" if default else ""
    try:
        val = input(f"  {W}▶  {prompt}{suffix}: {RST}").strip()
    except (EOFError, KeyboardInterrupt):
        print(); return default
    return val if val else default

def ask_yn(prompt, default=True):
    hint = "Y/n" if default else "y/N"
    raw  = ask(f"{prompt} ({hint})", "y" if default else "n")
    return raw.lower().startswith("y")

def ask_int(prompt, default=1, lo=1, hi=99):
    raw = ask(prompt, str(default))
    try:
        v = int(raw)
        return v if lo <= v <= hi else default
    except ValueError:
        return default

def menu(title, options, default=1):
    print(f"\n  {B}{title}{RST}")
    sep()
    for i, o in enumerate(options, 1):
        print(f"  {W}{i}.{RST}  {o}")
    sep()
    return ask_int("Choose", default, 1, len(options))

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────────
# DB / Twilio init
# ─────────────────────────────────────────────────────────────
try:
    from pymongo import MongoClient
    _mc = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=4000)
    _mc.admin.command('ping')
    db       = _mc['BotSetu']
    bots_col = db['User-data']
    MONGO_OK = True
except Exception as e:
    MONGO_OK = False
    db = bots_col = None
    err(f"MongoDB unavailable: {e}")

try:
    from twilio.rest import Client as TwilioClient
    twilio   = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    TWILIO_OK = True
except Exception as e:
    TWILIO_OK = False
    twilio    = None
    err(f"Twilio unavailable: {e}")

DISPLAY_NUMBER = TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')


# ─────────────────────────────────────────────────────────────
# Bot-type templates
# ─────────────────────────────────────────────────────────────
BOT_TYPES = {
    1: "Customer Support",
    2: "Sales & Lead Generation",
    3: "FAQ / Information",
    4: "Appointment Booking",
    5: "E-commerce Order Tracking",
    6: "Custom (blank slate)",
}

TEMPLATES = {
    1: {
        'welcomeMessage':  "Hello! 👋 Welcome to {name} support. How can I help you today?",
        'fallbackMessage': "I didn't understand that. Type 'help' to see options, or 'agent' to speak with a human.",
        'humanHandoff':    True,
        'humanHandoffKeywords': ['agent', 'human', 'support', 'help me', 'talk to someone'],
        'suggestedKeywords': [
            ('order',   "To track your order, share your order ID and we'll update you shortly."),
            ('refund',  "For refunds, email support@{domain} with your order details."),
            ('hours',   "Our support team is available Monday–Friday, 9 AM – 6 PM."),
            ('contact', "Reach us at support@{domain} or call +91-XXXXXXXXXX."),
        ],
    },
    2: {
        'welcomeMessage':  "Hi there! 👋 Thanks for reaching out to {name}. Interested in our products/services?",
        'fallbackMessage': "Type 'products' to browse, 'pricing' for plans, or 'demo' to request a demo.",
        'humanHandoff':    True,
        'humanHandoffKeywords': ['buy', 'purchase', 'price', 'demo', 'quote', 'sales'],
        'suggestedKeywords': [
            ('pricing',  "Our plans start at ₹999/month. Reply 'plans' for details or 'demo' to talk to sales."),
            ('products', "We offer [Product A], [Product B], and [Product C]. Which interests you?"),
            ('demo',     "Great! Our team will contact you. Please share your name and email."),
            ('discount', "Type 'subscribe' to get notified of deals and promotions."),
        ],
    },
    3: {
        'welcomeMessage':  "Hello! 👋 I'm the {name} info bot. Ask me anything or type 'menu' to see topics.",
        'fallbackMessage': "I don't have an answer for that. Type 'menu' to see available topics.",
        'humanHandoff':    False,
        'humanHandoffKeywords': [],
        'suggestedKeywords': [
            ('menu',     "Available topics: hours, location, contact, services. Just type any topic."),
            ('hours',    "We are open Monday–Saturday, 10 AM – 8 PM."),
            ('location', "We are located at [Your Address Here]."),
            ('contact',  "Reach us at info@{domain} or +91-XXXXXXXXXX."),
        ],
    },
    4: {
        'welcomeMessage':  "Hello! 👋 Welcome to {name}. Type 'book' to schedule an appointment.",
        'fallbackMessage': "Type 'book' to book, 'status' to check, or 'cancel' to cancel an appointment.",
        'humanHandoff':    True,
        'humanHandoffKeywords': ['book', 'appointment', 'schedule', 'cancel', 'reschedule'],
        'suggestedKeywords': [
            ('book',   "To book, share your name, preferred date & time, and service needed."),
            ('cancel', "To cancel, share your appointment ID or the date of your booking."),
            ('status', "Share your appointment ID to check its status."),
            ('hours',  "Appointments available: Mon–Sat, 9 AM – 5 PM."),
        ],
    },
    5: {
        'welcomeMessage':  "Hi! 👋 Welcome to {name}. Type your order ID to track your package.",
        'fallbackMessage': "Type your order ID (e.g. ORD-12345) for an update, or 'help' for assistance.",
        'humanHandoff':    True,
        'humanHandoffKeywords': ['help', 'return', 'refund', 'damage', 'wrong item', 'agent'],
        'suggestedKeywords': [
            ('return',   "To return, reply with your order ID and reason. Returns accepted within 7 days."),
            ('refund',   "Refunds are processed within 5–7 business days after we receive the item."),
            ('shipping', "Standard: 3–5 days. Express: 1–2 days. Free shipping over ₹499."),
            ('help',     "Type 'return', 'refund', 'shipping', or your Order ID for help."),
        ],
    },
    6: {
        'welcomeMessage':  "Hello! 👋 Welcome to {name}.",
        'fallbackMessage': "I didn't understand that. Please try again.",
        'humanHandoff':    False,
        'humanHandoffKeywords': [],
        'suggestedKeywords': [],
    },
}


# ─────────────────────────────────────────────────────────────
# Wizard
# ─────────────────────────────────────────────────────────────
def create_bot():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\n{C}{B}  ╔════════════════════════════════════════════╗")
    print(f"  ║    BotSetu — WhatsApp Bot Creator          ║")
    print(f"  ╚════════════════════════════════════════════╝{RST}\n")

    if not MONGO_OK:
        err("MongoDB is not running. Start MongoDB and try again.")
        return
    if not TWILIO_OK:
        err("Twilio credentials invalid. Check .env")
        return

    # ══ Step 1: What kind of bot? ════════════════════════════
    step(1, "What kind of bot do you want to create?")
    bot_type_idx = menu("Bot Type", list(BOT_TYPES.values()))
    bot_type     = BOT_TYPES[bot_type_idx]
    template     = TEMPLATES[bot_type_idx]
    info(f"Template loaded: {bot_type}")

    # ══ Step 2: Business details ═════════════════════════════
    step(2, "Business Details")
    sep()
    name = ask("Business / Bot name")
    if not name:
        err("Business name is required.")
        return
    domain      = ask("Domain or email domain  (e.g. myshop.com)", "example.com")
    description = ask("Short description", f"{bot_type} bot for {name}")
    owner_id    = ask("Owner ID  (your user ID, any string)", "owner-1")

    def fill(s):
        return s.replace('{name}', name).replace('{domain}', domain)

    # ══ Step 3: Messages ════════════════════════════════════
    step(3, "Bot Messages")
    sep()
    print(f"  {DIM}Welcome message — sent when someone first messages your bot.{RST}\n")
    welcome  = ask("Welcome message", fill(template['welcomeMessage']))
    print()
    print(f"  {DIM}Fallback message — sent when the bot doesn't recognise an input.{RST}\n")
    fallback = ask("Fallback message", fill(template['fallbackMessage']))

    # ══ Step 4: Keyword Responses ════════════════════════════
    step(4, "Keyword Responses")
    sep()
    info("Define what the bot replies when a customer types a specific word.")
    info("Template keywords are pre-loaded — keep, edit, or skip each one.\n")

    keyword_responses = {}

    for kw, reply in template['suggestedKeywords']:
        print(f"\n  {Y}Keyword:{RST}  {B}{kw}{RST}")
        print(f"  {DIM}Default reply: {fill(reply)}{RST}")
        keep = ask_yn("  Keep this keyword?", True)
        if keep:
            custom_reply = ask(f"  Reply for '{kw}'", fill(reply))
            keyword_responses[kw] = custom_reply

    print()
    while ask_yn("Add a custom keyword?", False):
        kw    = ask("  Keyword  (e.g. 'price', 'hello', 'track')")
        reply = ask(f"  Reply when user types '{kw}'")
        if kw and reply:
            keyword_responses[kw] = reply
            print(f"  {G}✔{RST}  Added '{kw}'")

    # ══ Step 5: Auto-Reply & Human Handoff ══════════════════
    step(5, "Auto-Reply & Human Handoff")
    sep()
    auto_reply = ask_yn("Enable auto-reply  (bot responds to every message)?", True)

    human_handoff    = False
    handoff_keywords = list(template['humanHandoffKeywords'])
    handoff_msg      = ""

    if auto_reply and template['humanHandoff']:
        print()
        human_handoff = ask_yn(
            f"Enable human handoff?  (triggers on: {', '.join(handoff_keywords[:3])}…)",
            template['humanHandoff']
        )
        if human_handoff:
            extra = ask("Add more handoff keywords  (comma-separated, Enter to skip)", "")
            if extra:
                handoff_keywords += [k.strip() for k in extra.split(',') if k.strip()]
            handoff_msg = ask(
                "Message shown on handoff",
                f"Connecting you to a human agent from {name}. Please hold on."
            )

    # ══ Step 6: Business Hours ═══════════════════════════════
    step(6, "Business Hours  (optional)")
    sep()
    hours_msg = ""
    if ask_yn("Configure business hours?", False):
        days      = ask("Working days", "Monday–Saturday")
        times     = ask("Working hours", "9 AM – 6 PM")
        hours_msg = f"{days}, {times}"
        keyword_responses.setdefault('hours', f"Our business hours are {hours_msg}.")

    # ══ Step 7: Review ═══════════════════════════════════════
    step(7, "Review — Your Bot Configuration")
    sep()
    print(f"  Bot type       : {C}{bot_type}{RST}")
    print(f"  Business name  : {B}{name}{RST}")
    print(f"  Description    : {description}")
    print(f"  Owner ID       : {owner_id}")
    print(f"  WhatsApp no.   : {G}{DISPLAY_NUMBER}{RST}")
    print()
    ws = welcome[:68]+'…' if len(welcome) > 68 else welcome
    fb = fallback[:68]+'…' if len(fallback) > 68 else fallback
    print(f"  Welcome msg    : {DIM}{ws}{RST}")
    print(f"  Fallback msg   : {DIM}{fb}{RST}")
    print(f"  Auto-reply     : {G+'ON'+RST if auto_reply else R+'OFF'+RST}")
    print(f"  Human handoff  : {G+'ON'+RST if human_handoff else 'OFF'}")
    if hours_msg:
        print(f"  Business hours : {hours_msg}")
    print(f"\n  Keywords ({len(keyword_responses)}):")
    for kw, rep in keyword_responses.items():
        snippet = rep[:52]+'…' if len(rep) > 52 else rep
        print(f"    {Y}{kw:<16}{RST} → {DIM}{snippet}{RST}")
    sep()

    if not ask_yn("Create this bot?", True):
        info("Cancelled.")
        return

    # ══ Step 8: Save ══════════════════════════════════════════
    step(8, "Creating Bot")
    sep()

    business_id = f"business_{int(utcnow().timestamp()*1000)}_{uuid.uuid4().hex[:9]}"
    now = utcnow()

    doc = {
        'businessId':           business_id,
        'ownerUserId':          owner_id,
        'businessName':         name,
        'description':          description,
        'botType':              bot_type,
        'domain':               domain,
        'welcomeMessage':       welcome,
        'fallbackMessage':      fallback,
        'autoReplyMessage':     welcome,
        'autoReply':            auto_reply,
        'humanHandoff':         human_handoff,
        'humanHandoffKeywords': handoff_keywords,
        'humanHandoffMessage':  handoff_msg,
        'keywordResponses':     keyword_responses,
        'businessHours':        hours_msg,
        'verificationStatus':   'verified',
        'allocatedNumber':      DISPLAY_NUMBER,
        'totalMessages':        0,
        'activatedAt':          now,
        'createdAt':            now,
        'updatedAt':            now,
    }

    bots_col.insert_one(doc)
    ok(f"Bot saved to MongoDB  (businessId: {C}{business_id}{RST})")

    # ══ Step 9: Test send ═════════════════════════════════════
    step(9, "Send a Test Message  (optional)")
    sep()
    if ask_yn("Send the welcome message to your phone now?", False):
        test_phone = ask("Your WhatsApp number (+91XXXXXXXXXX)")
        if test_phone and TWILIO_OK:
            to_wa = f"whatsapp:{test_phone}" if not test_phone.startswith('whatsapp:') else test_phone
            try:
                msg = twilio.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER, to=to_wa, body=welcome
                )
                ok(f"Test message sent!  SID = {C}{msg.sid}{RST}")
            except Exception as e:
                err(f"Send failed: {e}")
        elif not test_phone:
            info("Skipped.")

    # ══ Done ══════════════════════════════════════════════════
    print(f"\n  {G}{B}{'═'*56}{RST}")
    print(f"\n  {G}{B}  ✔  Bot is live!{RST}\n")
    print(f"  Type       : {C}{bot_type}{RST}")
    print(f"  Business   : {B}{name}{RST}")
    print(f"  ID         : {C}{business_id}{RST}")
    print(f"  WhatsApp   : {G}{DISPLAY_NUMBER}{RST}")
    print(f"  Keywords   : {len(keyword_responses)} configured")
    print()
    info("Run  python setup_webhook.py  to expose your server to Twilio.")
    info("Run  python app.py  to start handling incoming messages.")
    print(f"\n  {DIM}{'═'*56}{RST}\n")

    if ask_yn("Export bot config to JSON file?", False):
        filename = f"bot_{business_id[:20]}.json"
        export   = {k: v for k, v in doc.items() if k != '_id'}
        export['createdAt'] = export['activatedAt'] = export['updatedAt'] = now.isoformat()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        ok(f"Saved to {filename}")


# ─────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    while True:
        create_bot()
        print()
        again = input(f"  {W}▶  Create another bot? (y/N): {RST}").strip().lower()
        if again != 'y':
            print(f"\n  {G}Done!{RST}\n")
            break
        print()
