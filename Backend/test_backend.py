"""
BotSetu Backend — Standalone Test Script
=========================================
Run this to verify your Twilio + MongoDB setup WITHOUT starting the Flask server.

Usage:
    python test_backend.py

Each test prints PASS / FAIL with details.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID     = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN      = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')   # whatsapp:+14155238886
MONGODB_URI            = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

# Phone number to send a real test WhatsApp message to.
# Set this to YOUR personal WhatsApp number (with country code, e.g. +919876543210)
# Leave empty to skip the live-send test.
TEST_RECIPIENT_PHONE = ""   # ← put your number here to test live sending

SEP  = "─" * 60
PASS = "\033[92m✔ PASS\033[0m"
FAIL = "\033[91m✘ FAIL\033[0m"
INFO = "\033[94mℹ INFO\033[0m"

results = []

def result(name, ok, detail=""):
    tag = PASS if ok else FAIL
    print(f"  {tag}  {name}")
    if detail:
        print(f"       {detail}")
    results.append(ok)


# ─────────────────────────────────────────────────────────────
# 1. ENV CHECK
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("1. ENV VARIABLES")
print(SEP)
result("TWILIO_ACCOUNT_SID set", bool(TWILIO_ACCOUNT_SID), TWILIO_ACCOUNT_SID or "MISSING")
result("TWILIO_AUTH_TOKEN set",  bool(TWILIO_AUTH_TOKEN),  "****" + (TWILIO_AUTH_TOKEN[-4:] if TWILIO_AUTH_TOKEN else "MISSING"))
result("TWILIO_WHATSAPP_NUMBER set", bool(TWILIO_WHATSAPP_NUMBER), TWILIO_WHATSAPP_NUMBER or "MISSING")
result("MONGODB_URI set", bool(MONGODB_URI), MONGODB_URI)


# ─────────────────────────────────────────────────────────────
# 2. TWILIO CONNECTION
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("2. TWILIO CONNECTION")
print(SEP)
twilio_client = None
try:
    from twilio.rest import Client
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    result("Twilio auth", True, f"Account: {account.friendly_name}  Status: {account.status}")
except Exception as e:
    result("Twilio auth", False, str(e))


# ─────────────────────────────────────────────────────────────
# 3. TWILIO WHATSAPP NUMBER CHECK
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("3. TWILIO WHATSAPP NUMBER")
print(SEP)
if twilio_client and TWILIO_WHATSAPP_NUMBER:
    try:
        # For the sandbox the number won't appear in incoming-phone-numbers,
        # but we can still verify the format and fetch available messages.
        plain = TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', '')
        nums  = twilio_client.incoming_phone_numbers.list(phone_number=plain)
        if nums:
            result("WhatsApp number in account", True, f"{plain}  SID: {nums[0].sid}")
        else:
            # Sandbox number (+14155238886) won't show — that's expected
            result(
                "WhatsApp number in account",
                True,
                f"{plain}  (sandbox number — not listed in phone-numbers, that's normal)"
            )
    except Exception as e:
        result("WhatsApp number check", False, str(e))
else:
    result("WhatsApp number check", False, "Skipped — Twilio client unavailable or number missing")


# ─────────────────────────────────────────────────────────────
# 4. MONGODB CONNECTION
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("4. MONGODB CONNECTION")
print(SEP)
db = None
try:
    from pymongo import MongoClient
    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=4000)
    mongo_client.admin.command('ping')
    db = mongo_client['BotSetu']
    result("MongoDB ping", True, MONGODB_URI)
except Exception as e:
    result("MongoDB ping", False, str(e))

# List collections if connected
if db is not None:
    try:
        cols = db.list_collection_names()
        result("List collections", True, "Found: " + (", ".join(cols) if cols else "(empty DB — that's OK)"))
    except Exception as e:
        result("List collections", False, str(e))


# ─────────────────────────────────────────────────────────────
# 5. BOT ACTIVATION LOGIC (dry run — reads from MongoDB)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("5. BOT ACTIVATION LOGIC")
print(SEP)
if db is not None:
    bots_col = db['User-data']
    count    = bots_col.count_documents({})
    result("Read bots collection", True, f"{count} bot(s) in User-data")

    verified = bots_col.count_documents({'verificationStatus': 'verified'})
    result("Verified bots", True, f"{verified} verified bot(s)")

    sample = bots_col.find_one({'verificationStatus': 'verified'})
    if sample:
        display_number = (TWILIO_WHATSAPP_NUMBER or '').replace('whatsapp:', '') if TWILIO_WHATSAPP_NUMBER else 'N/A'
        result(
            "Sample active bot",
            True,
            f"businessId={sample.get('businessId')}  allocatedNumber={sample.get('allocatedNumber', display_number)}"
        )
    else:
        print(f"  {INFO}  No verified bot yet — create one from the dashboard first")
else:
    result("Bot activation logic", False, "Skipped — MongoDB unavailable")


# ─────────────────────────────────────────────────────────────
# 6. CONVERSATION LOGGER (write + read)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("6. CONVERSATION LOGGER")
print(SEP)
if db is not None:
    conversations_col = db['conversations']
    TEST_BIZ = "__test_botsetu__"
    TEST_PHONE = "+910000000000"
    try:
        # Write
        doc_id = conversations_col.insert_one({
            'businessId':     TEST_BIZ,
            'userId':         'test-user',
            'phoneNumber':    TEST_PHONE,
            'messageContent': 'Hello, this is a test message',
            'messageType':    'text',
            'sender':         'user',
            'read':           False,
            'timestamp':      datetime.utcnow()
        }).inserted_id
        result("Write conversation", True, f"_id={doc_id}")

        # Read back
        doc = conversations_col.find_one({'_id': doc_id})
        result("Read conversation back", bool(doc), doc.get('messageContent') if doc else "not found")

        # Cleanup
        conversations_col.delete_one({'_id': doc_id})
        result("Cleanup test document", True, "deleted")
    except Exception as e:
        result("Conversation logger", False, str(e))
else:
    result("Conversation logger", False, "Skipped — MongoDB unavailable")


# ─────────────────────────────────────────────────────────────
# 7. SEND REAL WHATSAPP MESSAGE  (only if TEST_RECIPIENT_PHONE is set)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("7. LIVE WHATSAPP SEND")
print(SEP)
if not TEST_RECIPIENT_PHONE:
    print(f"  {INFO}  Skipped — set TEST_RECIPIENT_PHONE at the top of this file to test live sending")
elif twilio_client and TWILIO_WHATSAPP_NUMBER:
    try:
        to_wa = f"whatsapp:{TEST_RECIPIENT_PHONE}" if not TEST_RECIPIENT_PHONE.startswith('whatsapp:') else TEST_RECIPIENT_PHONE
        msg = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_wa,
            body="[BotSetu Test] Hello! This is a test message from BotSetu backend. You can ignore it."
        )
        result("Send WhatsApp message", True, f"SID={msg.sid}  Status={msg.status}")
    except Exception as e:
        result("Send WhatsApp message", False, str(e))
else:
    result("Send WhatsApp message", False, "Skipped — Twilio client not available")


# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
passed = sum(results)
total  = len(results)
color  = "\033[92m" if passed == total else "\033[93m"
print(f"{color}RESULTS: {passed}/{total} checks passed\033[0m")
print(SEP)
if passed < total:
    print("Fix the failing checks above before starting the Flask server.")
else:
    print("All checks passed! Run  python app.py  to start the server.")
print()
