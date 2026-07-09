"""
utils/helpers.py
----------------
Low-level utility functions shared across services and routes.
Each function has exactly one responsibility and no side-effects beyond DB writes.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from database import (
    bots_col,
    conversations_col,
    sessions_col,
    credits_col,
    get_system_config,
)

log = logging.getLogger(__name__)

# Loaded once from DB; falls back to 100 if collection not seeded.
_INITIAL_CREDITS: Optional[int] = None


def now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def get_initial_credits() -> int:
    """Return the configured initial credit grant for new users."""
    global _INITIAL_CREDITS
    if _INITIAL_CREDITS is None:
        _INITIAL_CREDITS = int(get_system_config('initial_credits', 100))
    return _INITIAL_CREDITS


def find_bot_for_customer(customer_phone: str) -> Optional[Dict]:
    """
    Return the bot that owns this customer's active session.
    Falls back to the most recently activated verified bot if no session exists.
    Cleans up dangling sessions pointing to deleted bots.
    """
    session = sessions_col.find_one({'customerPhone': customer_phone})
    if session:
        bot = bots_col.find_one({'businessId': session['businessId']})
        if bot:
            return bot
        # Session points to a deleted bot; clean up and fall through to default.
        sessions_col.delete_one({'customerPhone': customer_phone})

    return bots_col.find_one(
        {'verificationStatus': 'verified'},
        sort=[('activatedAt', -1)],
    )


def upsert_session(customer_phone: str, business_id: str) -> None:
    """Associate a customer phone with a bot for the duration of the conversation."""
    sessions_col.update_one(
        {'customerPhone': customer_phone},
        {'$set': {'businessId': business_id, 'updatedAt': now()}},
        upsert=True,
    )


def log_message(
    business_id: str,
    user_id: str,
    customer_phone: str,
    content: str,
    sender: str,   # 'user' or 'bot'
) -> None:
    """
    Persist a single message to conversations and increment the bot's message counter.
    This is called for both inbound (user) and outbound (bot) messages.
    """
    conversations_col.insert_one({
        'businessId':     business_id,
        'userId':         user_id,
        'phoneNumber':    customer_phone,
        'messageContent': content,
        'messageType':    'text',
        'sender':         sender,
        'read':           False,
        'timestamp':      now(),
    })
    bots_col.update_one(
        {'businessId': business_id},
        {
            '$set': {'lastConversationAt': now()},
            '$inc': {'totalMessages': 1},
        },
    )


def get_or_init_credits(user_id: str) -> int:
    """
    Return the current credit balance for a user.
    Initialises the record with the configured initial grant if the user is new.
    """
    initial = get_initial_credits()
    ts = now()
    doc = credits_col.find_one({'userId': user_id})
    if doc is None:
        credits_col.insert_one({
            'userId':      user_id,
            'credits':     initial,
            'totalEarned': initial,
            'totalUsed':   0,
            'createdAt':   ts,
            'updatedAt':   ts,
        })
        return initial
    return int(doc.get('credits', 0))


def deduct_credit(user_id: str) -> bool:
    """
    Atomically deduct one credit from the user's balance.
    Returns True if the deduction succeeded, False if the balance was zero.
    """
    result = credits_col.update_one(
        {'userId': user_id, 'credits': {'$gt': 0}},
        {
            '$inc': {'credits': -1, 'totalUsed': 1},
            '$set': {'updatedAt': now()},
        },
    )
    return result.modified_count == 1
