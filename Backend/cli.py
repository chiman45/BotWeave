"""
BotSetu — A CLI tool for managing your WhatsApp bots and conversations without a server.
===========================================
Manage bots, send messages, view conversations, and handle payments
directly via Twilio + MongoDB — no Flask server needed.

Usage:
    python cli.py
"""

import os
import sys
import uuid
import textwrap
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID     = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN      = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')   # whatsapp:+14155238886
MONGODB_URI            = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

# ─────────────────────────────────────────────────────────────
# Colours
# ─────────────────────────────────────────────────────────────
R  = "\033[91m"   # red
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
B  = "\033[94m"   # blue
C  = "\033[96m"   # cyan
W  = "\033[97m"   # white
DIM= "\033[2m"
RST= "\033[0m"
BOLD="\033[1m"

def ok(s):   print(f"  {G}✔{RST}  {s}")
def err(s):  print(f"  {R}✘{RST}  {s}")
def info(s): print(f"  {B}ℹ{RST}  {s}")
def warn(s): print(f"  {Y}⚠{RST}  {s}")

def sep(title=""):
    width = 58
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{C}{'─'*pad} {BOLD}{title}{RST}{C} {'─'*pad}{RST}")
    else:
        print(f"{DIM}{'─'*width}{RST}")

def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {W}{prompt}{suffix}: {RST}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return val if val else default

def ask_int(prompt, default=1):
    raw = ask(prompt, str(default))
    try:
        return int(raw)
    except ValueError:
        return default

def confirm(prompt):
    return ask(prompt + " (y/N)", "n").lower() == "y"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for pymongo

# ─────────────────────────────────────────────────────────────
# Init clients
# ─────────────────────────────────────────────────────────────
try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from bson import ObjectId
    mongo_client      = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=4000)
    mongo_client.admin.command('ping')
    db                = mongo_client['BotSetu']
    bots_col          = db['User-data']
    conversations_col = db['conversations']
    sessions_col      = db['bot-sessions']
    payments_col      = db['payments']
    MONGO_OK = True
except Exception as e:
    MONGO_OK = False
    err(f"MongoDB unavailable: {e}")

try:
    from twilio.rest import Client as TwilioClient
    twilio = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    TWILIO_OK = True
except Exception as e:
    TWILIO_OK = False
    err(f"Twilio unavailable: {e}")

DISPLAY_NUMBER = TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')


# ═════════════════════════════════════════════════════════════
# ── HELPERS
# ═════════════════════════════════════════════════════════════

def _pick_bot(prompt="Select bot #"):
    """Print numbered list of bots and return chosen bot doc."""
    bots = list(bots_col.find({}).sort('createdAt', DESCENDING).limit(20))
    if not bots:
        warn("No bots found in DB. Create one first.")
        return None
    print()
    for i, b in enumerate(bots, 1):
        status = b.get('verificationStatus', 'pending')
        color  = G if status == 'verified' else Y
        print(f"  {W}{i:2}.{RST}  {b.get('businessName','(no name)'):<28} "
              f"{color}{status:<10}{RST}  {DIM}{b.get('businessId','')}{RST}")
    sep()
    idx = ask_int(prompt, 1)
    if 1 <= idx <= len(bots):
        return bots[idx - 1]
    err("Invalid selection.")
    return None


def _fmt_time(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%d %b %Y  %H:%M UTC')
    return str(dt) if dt else '—'


def _wrap(text, width=54, indent="       "):
    return ("\n" + indent).join(textwrap.wrap(str(text), width))


# ═════════════════════════════════════════════════════════════
# ── MENU SECTIONS
# ═════════════════════════════════════════════════════════════

# ── 1. BOT MANAGEMENT ────────────────────────────────────────

def menu_bots():
    while True:
        sep("BOT MANAGEMENT")
        print(f"  {W}1.{RST}  List all bots")
        print(f"  {W}2.{RST}  Create new bot")
        print(f"  {W}3.{RST}  Activate bot  (assign Twilio number)")
        print(f"  {W}4.{RST}  Update bot settings")
        print(f"  {W}5.{RST}  Delete bot")
        print(f"  {W}0.{RST}  ← Back")
        sep()
        choice = ask("Choice", "0")
        if choice == "1":   _bot_list()
        elif choice == "2": _bot_create()
        elif choice == "3": _bot_activate()
        elif choice == "4": _bot_update()
        elif choice == "5": _bot_delete()
        elif choice == "0": break


def _bot_list():
    sep("ALL BOTS")
    bots = list(bots_col.find({}).sort('createdAt', DESCENDING))
    if not bots:
        warn("No bots found.")
        return
    print(f"  {BOLD}{'#':<3} {'Business Name':<28} {'Status':<12} {'Number':<18} {'Messages'}{RST}")
    sep()
    for i, b in enumerate(bots, 1):
        status = b.get('verificationStatus', 'pending')
        color  = G if status == 'verified' else Y
        num    = b.get('allocatedNumber', '—')
        msgs   = b.get('totalMessages', 0)
        print(f"  {i:<3} {b.get('businessName','(unnamed)'):<28} "
              f"{color}{status:<12}{RST} {num:<18} {msgs}")
    info(f"{len(bots)} bot(s) total")


def _bot_create():
    sep("CREATE BOT")
    name        = ask("Business name")
    description = ask("Description", "")
    auto_reply  = confirm("Enable auto-reply?")
    auto_msg    = ""
    if auto_reply:
        auto_msg = ask("Auto-reply message (leave blank for default)", "")

    business_id = f"business_{int(datetime.utcnow().timestamp()*1000)}_{uuid.uuid4().hex[:9]}"
    owner_id    = ask("Owner user ID (any string, e.g. your Clerk userId)", "cli-user")

    doc = {
        'businessId':        business_id,
        'ownerUserId':       owner_id,
        'businessName':      name,
        'description':       description,
        'autoReply':         auto_reply,
        'autoReplyMessage':  auto_msg,
        'humanHandoff':      False,
        'verificationStatus':'pending',
        'allocatedNumber':   None,
        'totalMessages':     0,
        'createdAt':         utcnow(),
        'updatedAt':         utcnow(),
    }
    bots_col.insert_one(doc)
    ok(f"Bot created!  businessId = {C}{business_id}{RST}")


def _bot_activate():
    sep("ACTIVATE BOT")
    if not TWILIO_OK:
        err("Twilio not available — check credentials in .env")
        return
    bot = _pick_bot("Activate bot #")
    if not bot:
        return
    bid = bot['businessId']
    if bot.get('allocatedNumber'):
        info(f"Already activated → {bot['allocatedNumber']}")
        return

    now = utcnow()
    bots_col.update_one(
        {'businessId': bid},
        {'$set': {
            'allocatedNumber':    DISPLAY_NUMBER,
            'verificationStatus': 'verified',
            'activatedAt':        now,
            'updatedAt':          now,
        }}
    )
    ok(f"Bot {C}{bid}{RST} activated")
    ok(f"Shared WhatsApp number: {G}{DISPLAY_NUMBER}{RST}")
    info("Customers message this number; BotSetu routes to the correct bot.")


def _bot_update():
    sep("UPDATE BOT SETTINGS")
    bot = _pick_bot()
    if not bot:
        return
    print()
    print(f"  Current name      : {bot.get('businessName')}")
    print(f"  Auto-reply        : {bot.get('autoReply')}")
    print(f"  Auto-reply message: {bot.get('autoReplyMessage','(default)')}")
    print(f"  Human handoff     : {bot.get('humanHandoff')}")
    sep()
    updates = {}
    new_name = ask("New business name (Enter to keep)", bot.get('businessName',''))
    if new_name != bot.get('businessName'):
        updates['businessName'] = new_name

    ar = ask("Auto-reply? (y/n, Enter to keep)", 'y' if bot.get('autoReply') else 'n')
    updates['autoReply'] = ar.lower() == 'y'

    if updates['autoReply']:
        msg = ask("Auto-reply message (Enter to keep)", bot.get('autoReplyMessage',''))
        updates['autoReplyMessage'] = msg

    hh = ask("Human handoff? (y/n, Enter to keep)", 'y' if bot.get('humanHandoff') else 'n')
    updates['humanHandoff'] = hh.lower() == 'y'
    updates['updatedAt']    = utcnow()

    bots_col.update_one({'businessId': bot['businessId']}, {'$set': updates})
    ok("Bot updated.")


def _bot_delete():
    sep("DELETE BOT")
    bot = _pick_bot()
    if not bot:
        return
    if not confirm(f"Delete bot '{bot.get('businessName')}'? This is permanent"):
        info("Cancelled.")
        return
    bots_col.delete_one({'businessId': bot['businessId']})
    # Clean up sessions and conversations
    conversations_col.delete_many({'businessId': bot['businessId']})
    ok("Bot and all its conversations deleted.")


# ── 2. SEND MESSAGE ──────────────────────────────────────────

def menu_send():
    sep("SEND WHATSAPP MESSAGE")
    if not TWILIO_OK:
        err("Twilio unavailable — check .env credentials")
        return
    if not TWILIO_WHATSAPP_NUMBER:
        err("TWILIO_WHATSAPP_NUMBER not set in .env")
        return

    to = ask("Recipient phone (+91XXXXXXXXXX)")
    if not to:
        err("Phone number required.")
        return
    to_wa = f"whatsapp:{to}" if not to.startswith('whatsapp:') else to

    print()
    body = ask("Message text")
    if not body:
        err("Message cannot be empty.")
        return

    # Optionally attach to a bot for conversation logging
    bot = None
    if MONGO_OK and confirm("Log this message to a bot's conversation?"):
        bot = _pick_bot()

    try:
        msg = twilio.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_wa,
            body=body
        )
        ok(f"Message sent!  SID = {C}{msg.sid}{RST}  Status = {msg.status}")
        if bot and MONGO_OK:
            conversations_col.insert_one({
                'businessId':    bot['businessId'],
                'userId':        bot.get('ownerUserId', ''),
                'phoneNumber':   to,
                'messageContent': body,
                'messageType':   'text',
                'sender':        'bot',
                'read':          True,
                'timestamp':     utcnow()
            })
            bots_col.update_one(
                {'businessId': bot['businessId']},
                {'$inc': {'totalMessages': 1}, '$set': {'updatedAt': utcnow()}}
            )
            ok("Message logged to conversation.")
    except Exception as e:
        err(f"Send failed: {e}")


# ── 3. CONVERSATIONS ─────────────────────────────────────────

def menu_conversations():
    while True:
        sep("CONVERSATIONS")
        print(f"  {W}1.{RST}  List conversations for a bot")
        print(f"  {W}2.{RST}  View full chat with a customer")
        print(f"  {W}3.{RST}  Simulate incoming message  (test routing)")
        print(f"  {W}4.{RST}  Delete a conversation")
        print(f"  {W}0.{RST}  ← Back")
        sep()
        choice = ask("Choice", "0")
        if choice == "1":   _conv_list()
        elif choice == "2": _conv_view()
        elif choice == "3": _conv_simulate()
        elif choice == "4": _conv_delete()
        elif choice == "0": break


def _conv_list():
    sep("CONVERSATIONS — SELECT BOT")
    bot = _pick_bot()
    if not bot:
        return
    bid = bot['businessId']

    pipeline = [
        {'$match': {'businessId': bid}},
        {'$sort':  {'timestamp': -1}},
        {'$group': {
            '_id':             '$phoneNumber',
            'lastMessage':     {'$first': '$messageContent'},
            'lastTime':        {'$first': '$timestamp'},
            'lastSender':      {'$first': '$sender'},
            'total':           {'$sum': 1},
            'unread':          {'$sum': {'$cond': [{'$eq': ['$read', False]}, 1, 0]}}
        }},
        {'$sort': {'lastTime': -1}}
    ]
    rows = list(conversations_col.aggregate(pipeline))
    if not rows:
        warn("No conversations yet for this bot.")
        return

    sep(f"Conversations — {bot.get('businessName')}")
    print(f"  {BOLD}{'#':<3} {'Phone':<18} {'Last message':<30} {'Time':<20} {'Msgs':>4} {'Unread':>6}{RST}")
    sep()
    for i, r in enumerate(rows, 1):
        snippet = str(r.get('lastMessage', ''))[:28]
        sender  = '→' if r.get('lastSender') == 'bot' else '←'
        unread  = r.get('unread', 0)
        uc      = R if unread else DIM
        print(f"  {i:<3} {r['_id']:<18} {sender} {snippet:<28} {DIM}{_fmt_time(r.get('lastTime')):<20}{RST} "
              f"{r.get('total',0):>4} {uc}{unread:>6}{RST}")
    info(f"{len(rows)} conversation(s)")


def _conv_view():
    sep("VIEW CHAT")
    bot = _pick_bot()
    if not bot:
        return
    phone = ask("Customer phone number")
    if not phone:
        return

    msgs = list(
        conversations_col.find(
            {'businessId': bot['businessId'], 'phoneNumber': phone},
            {'_id': 0}
        ).sort('timestamp', ASCENDING).limit(100)
    )
    if not msgs:
        warn("No messages found for this number.")
        return

    sep(f"Chat: {bot.get('businessName')} ↔ {phone}")
    for m in msgs:
        ts     = _fmt_time(m.get('timestamp'))
        sender = m.get('sender', 'user')
        color  = B if sender == 'bot' else W
        label  = f"{color}{'[BOT]' if sender=='bot' else '[USER]'}{RST}"
        body   = _wrap(m.get('messageContent', ''))
        print(f"  {DIM}{ts}{RST}  {label}  {body}")

    # Mark as read
    conversations_col.update_many(
        {'businessId': bot['businessId'], 'phoneNumber': phone, 'read': False},
        {'$set': {'read': True}}
    )
    info(f"{len(msgs)} message(s)  — marked as read")


def _conv_simulate():
    """
    Simulate an incoming WhatsApp message — exercises the full
    routing + auto-reply + conversation-logging logic without Twilio.
    """
    sep("SIMULATE INCOMING MESSAGE")
    phone = ask("Simulated sender phone (+91XXXXXXXXXX)")
    if not phone:
        return
    body = ask("Message body")
    if not body:
        return

    # Find bot via sticky session or first verified bot
    session = sessions_col.find_one({'customerPhone': phone})
    bot = None
    if session:
        bot = bots_col.find_one({'businessId': session['businessId']})
    if not bot:
        bot = bots_col.find_one({'verificationStatus': 'verified'})

    if not bot:
        err("No verified bot found. Activate a bot first.")
        return

    bid = bot['businessId']
    uid = bot.get('ownerUserId', '')

    # Upsert session
    sessions_col.update_one(
        {'customerPhone': phone},
        {'$set': {'businessId': bid, 'updatedAt': utcnow()}},
        upsert=True
    )

    # Log incoming
    conversations_col.insert_one({
        'businessId':    bid,
        'userId':        uid,
        'phoneNumber':   phone,
        'messageContent': body,
        'messageType':   'text',
        'sender':        'user',
        'read':          False,
        'timestamp':     utcnow()
    })
    bots_col.update_one({'businessId': bid}, {'$inc': {'totalMessages': 1}})

    ok(f"Message logged → bot: {G}{bot.get('businessName')}{RST}  ({bid})")

    # Build auto-reply
    reply = ""
    if bot.get('autoReply'):
        handoff_kw = ['human', 'agent', 'support', 'help me', 'talk to someone']
        if bot.get('humanHandoff') and any(k in body.lower() for k in handoff_kw):
            reply = (f"Connecting you to a human agent for "
                     f"{bot.get('businessName','our team')}. Please hold on.")
        else:
            reply = (bot.get('autoReplyMessage')
                     or f"Hi! Thanks for reaching out to {bot.get('businessName','us')}. "
                        "We will get back to you shortly.")

    if reply:
        # Log the bot reply
        conversations_col.insert_one({
            'businessId':    bid,
            'userId':        uid,
            'phoneNumber':   phone,
            'messageContent': reply,
            'messageType':   'text',
            'sender':        'bot',
            'read':          True,
            'timestamp':     utcnow()
        })
        bots_col.update_one({'businessId': bid}, {'$inc': {'totalMessages': 1}})
        ok(f"Auto-reply generated:")
        print(f"\n  {B}[BOT]{RST}  {_wrap(reply)}\n")

        if TWILIO_OK and TWILIO_WHATSAPP_NUMBER and confirm("Send this reply via Twilio?"):
            to_wa = f"whatsapp:{phone}" if not phone.startswith('whatsapp:') else phone
            try:
                msg = twilio.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    to=to_wa,
                    body=reply
                )
                ok(f"Sent!  SID = {C}{msg.sid}{RST}")
            except Exception as e:
                err(f"Twilio send failed: {e}")
    else:
        info("Auto-reply is disabled for this bot — no reply sent.")


def _conv_delete():
    sep("DELETE CONVERSATION")
    bot = _pick_bot()
    if not bot:
        return
    phone = ask("Customer phone to delete")
    if not phone:
        return
    if not confirm(f"Delete all messages with {phone}?"):
        info("Cancelled.")
        return
    r = conversations_col.delete_many({'businessId': bot['businessId'], 'phoneNumber': phone})
    sessions_col.delete_one({'customerPhone': phone})
    ok(f"Deleted {r.deleted_count} message(s) and cleared session.")


# ── 4. PAYMENTS ──────────────────────────────────────────────

PLAN_PRICES = {'starter': 99, 'pro': 499, 'enterprise': 1999}

def menu_payments():
    while True:
        sep("PAYMENTS")
        print(f"  {W}1.{RST}  List payments for a user")
        print(f"  {W}2.{RST}  Create payment record")
        print(f"  {W}3.{RST}  Mark payment as paid / update status")
        print(f"  {W}4.{RST}  Delete payment record")
        print(f"  {W}0.{RST}  ← Back")
        sep()
        choice = ask("Choice", "0")
        if choice == "1":   _pay_list()
        elif choice == "2": _pay_create()
        elif choice == "3": _pay_update()
        elif choice == "4": _pay_delete()
        elif choice == "0": break


def _pay_list():
    uid = ask("User ID")
    if not uid:
        return
    docs = list(payments_col.find({'userId': uid}))
    if not docs:
        warn(f"No payments for user '{uid}'.")
        return

    sep(f"Payments — {uid}")
    total_due  = sum(d['amount'] for d in docs if d.get('status') in ('due','pending'))
    total_paid = sum(d['amount'] for d in docs if d.get('status') in ('completed','paid'))

    print(f"  {BOLD}{'#':<3} {'Plan':<12} {'Amount':>8}  {'Status':<12} {'Date':<20} {'ID'}{RST}")
    sep()
    for i, d in enumerate(docs, 1):
        st    = d.get('status','—')
        color = G if st in ('completed','paid') else (R if st == 'failed' else Y)
        dt    = d.get('paidAt') or d.get('dueDate')
        print(f"  {i:<3} {d.get('planType','—'):<12} ₹{d.get('amount',0):>7.0f}  "
              f"{color}{st:<12}{RST} {DIM}{_fmt_time(dt):<20}{RST} {DIM}{str(d['_id'])}{RST}")
    sep()
    print(f"  Due: {R}₹{total_due:.0f}{RST}    Paid: {G}₹{total_paid:.0f}{RST}")


def _pay_create():
    sep("CREATE PAYMENT RECORD")
    uid = ask("User ID")
    bot = _pick_bot("Link to bot #")
    if not bot:
        bid = ask("Business ID (manual)")
    else:
        bid = bot['businessId']

    print(f"\n  Plans:  {', '.join(f'{k} (₹{v})' for k,v in PLAN_PRICES.items())}")
    plan   = ask("Plan type", "starter")
    amount = ask("Amount", str(PLAN_PRICES.get(plan, 99)))
    status = ask("Status (due/pending/paid)", "due")
    desc   = ask("Description", f"{plan.capitalize()} plan subscription")

    payments_col.insert_one({
        'userId':      uid,
        'businessId':  bid,
        'amount':      float(amount),
        'planType':    plan,
        'description': desc,
        'status':      status,
        'dueDate':     utcnow(),
        'createdAt':   utcnow(),
        'updatedAt':   utcnow()
    })
    ok("Payment record created.")


def _select_payment(uid=None):
    if not uid:
        uid = ask("User ID")
    if not uid:
        return None, None
    docs = list(payments_col.find({'userId': uid}))
    if not docs:
        warn("No payments found.")
        return None, None
    print()
    for i, d in enumerate(docs, 1):
        print(f"  {i}. {d.get('planType','—'):12} ₹{d.get('amount',0):.0f}  "
              f"{d.get('status','—'):12} {DIM}{str(d['_id'])}{RST}")
    idx = ask_int("Select payment #", 1)
    if 1 <= idx <= len(docs):
        return docs[idx-1], uid
    err("Invalid selection.")
    return None, None


def _pay_update():
    sep("UPDATE PAYMENT STATUS")
    doc, uid = _select_payment()
    if not doc:
        return
    new_status = ask("New status (pending/due/paid/completed/failed)", "paid")
    txn        = ask("Transaction ID (optional)", "")
    update = {'status': new_status, 'updatedAt': utcnow()}
    if new_status in ('paid', 'completed'):
        update['paidAt'] = utcnow()
    if txn:
        update['transactionId'] = txn
    payments_col.update_one({'_id': doc['_id']}, {'$set': update})
    ok("Payment updated.")


def _pay_delete():
    sep("DELETE PAYMENT RECORD")
    doc, uid = _select_payment()
    if not doc:
        return
    if not confirm("Delete this record?"):
        info("Cancelled.")
        return
    payments_col.delete_one({'_id': doc['_id']})
    ok("Deleted.")


# ── 5. TWILIO STATUS ─────────────────────────────────────────

def menu_status():
    sep("TWILIO & SYSTEM STATUS")

    # Twilio
    if TWILIO_OK:
        try:
            acct = twilio.api.accounts(TWILIO_ACCOUNT_SID).fetch()
            ok(f"Twilio account : {C}{acct.friendly_name}{RST}  status={acct.status}")
        except Exception as e:
            err(f"Twilio fetch: {e}")
    else:
        err("Twilio client not initialised")

    ok(f"WhatsApp number: {G}{DISPLAY_NUMBER}{RST}")

    # Recent messages from Twilio
    if TWILIO_OK and confirm("\nFetch last 5 messages from Twilio?"):
        try:
            msgs = twilio.messages.list(limit=5)
            sep("Recent Twilio Messages")
            for m in msgs:
                direction = "→" if m.direction.startswith('outbound') else "←"
                print(f"  {direction}  {m.from_:<20} → {m.to:<20}  "
                      f"{DIM}{str(m.date_sent)[:19]}{RST}  {m.status}")
        except Exception as e:
            err(str(e))

    # Mongo
    if MONGO_OK:
        ok(f"MongoDB         : {C}{MONGODB_URI}{RST}")
        ok(f"Collections     : {', '.join(db.list_collection_names())}")
        ok(f"Bots            : {bots_col.count_documents({})}")
        ok(f"Verified bots   : {bots_col.count_documents({'verificationStatus':'verified'})}")
        ok(f"Conversations   : {conversations_col.count_documents({})}")
        ok(f"Payments        : {payments_col.count_documents({})}")
    else:
        err("MongoDB not connected")


# ═════════════════════════════════════════════════════════════
# ── MAIN MENU
# ═════════════════════════════════════════════════════════════

def main():
    if not MONGO_OK:
        print(f"\n{R}MongoDB is required. Ensure it is running and MONGODB_URI is set.{RST}\n")
        sys.exit(1)

    while True:
        clear()
        print(f"\n{BOLD}{C}  ╔══════════════════════════════════════════╗")
        print(f"  ║        BotSetu — WhatsApp Bot CLI        ║")
        print(f"  ║   No server needed · Direct DB & Twilio  ║")
        print(f"  ╚══════════════════════════════════════════╝{RST}")
        twilio_label = f"{G}connected{RST}" if TWILIO_OK else f"{R}unavailable{RST}"
        mongo_label  = f"{G}connected{RST}" if MONGO_OK  else f"{R}unavailable{RST}"
        print(f"\n  Twilio: {twilio_label}   MongoDB: {mongo_label}   "
              f"Number: {C}{DISPLAY_NUMBER or '(not set)'}{RST}\n")

        print(f"  {W}1.{RST}  Bot Management      — create / activate / update bots")
        print(f"  {W}2.{RST}  Send WhatsApp Message")
        print(f"  {W}3.{RST}  Conversations       — view / simulate / delete")
        print(f"  {W}4.{RST}  Payments            — list / create / update")
        print(f"  {W}5.{RST}  System & Twilio Status")
        print(f"\n  {W}0.{RST}  Exit")
        sep()
        choice = ask("Choice", "0")

        if   choice == "1": menu_bots()
        elif choice == "2": menu_send()
        elif choice == "3": menu_conversations()
        elif choice == "4": menu_payments()
        elif choice == "5": menu_status()
        elif choice == "0":
            print(f"\n{G}Bye!{RST}\n")
            break
        else:
            warn("Unknown option.")

        if choice != "0":
            input(f"\n  {DIM}Press Enter to continue…{RST}")


if __name__ == '__main__':
    main()
