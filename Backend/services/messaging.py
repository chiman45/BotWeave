"""
services/messaging.py
---------------------
Builds auto-replies from a bot's configuration (keyword matching, welcome / fallback
messages) and wraps outbound Twilio sends.

No flow logic lives here — mandi and AI flows are handled in their own modules.
"""

import logging
from typing import Dict

from twilio.rest import Client

import config

log = logging.getLogger(__name__)

# Twilio client is instantiated once and reused across all requests.
twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Keywords that trigger the greeting branch before keyword matching is checked.
_GREETING_TOKENS = frozenset({'hi', 'hello', 'hey', 'start', 'hii', 'helo'})

# Maximum outbound WhatsApp message length (Twilio limit is 1600 chars).
_MAX_MESSAGE_LEN = 1600


def build_reply(bot: Dict, incoming_msg: str) -> str:
    """
    Generate an auto-reply for a normal (non-AI, non-mandi) bot.

    Priority order:
      1. Human-handoff trigger keywords
      2. Configured keyword responses (word-level match)
      3. Welcome message (greeted with hi/hello/start etc.)
      4. Bot fallback message
      5. Legacy autoReplyMessage field
      6. Generic default reply
    """
    if not bot.get('autoReply', False):
        return ''

    msg_lower = incoming_msg.lower().strip()

    # 1. Human handoff
    handoff_keywords = bot.get('humanHandoffKeywords', ['human', 'agent', 'support'])
    if bot.get('humanHandoff') and any(k in msg_lower for k in handoff_keywords):
        return (
            bot.get('humanHandoffMessage')
            or f"Connecting you to a human agent for {bot.get('businessName', 'our team')}. "
               "Please hold on."
        )

    # 2. Keyword responses
    keyword_responses: Dict = bot.get('keywordResponses', {})
    for keyword, response in keyword_responses.items():
        if keyword.lower() in msg_lower:
            return response

    # 3. Welcome message on greeting
    if any(
        msg_lower == g or msg_lower.startswith(g + ' ')
        for g in _GREETING_TOKENS
    ):
        welcome = bot.get('welcomeMessage')
        if welcome:
            return welcome

    # 4. Fallback
    if bot.get('fallbackMessage'):
        return bot['fallbackMessage']

    # 5. Legacy field
    if bot.get('autoReplyMessage'):
        return bot['autoReplyMessage']

    # 6. Generic default
    return (
        f"Hi! Thanks for reaching out to {bot.get('businessName', 'us')}. "
        "We received your message and will get back to you shortly."
    )


def send_whatsapp(to_number: str, body: str) -> str:
    """
    Send a WhatsApp message via Twilio.

    Parameters
    ----------
    to_number : E.164 number, with or without the 'whatsapp:' prefix.
    body      : Message text. Truncated to 1600 chars if longer.

    Returns the Twilio message SID on success.
    Raises on Twilio API errors — callers are responsible for catching.
    """
    if len(body) > _MAX_MESSAGE_LEN:
        body = body[:_MAX_MESSAGE_LEN - 3] + '...'

    to_wa = to_number if to_number.startswith('whatsapp:') else f'whatsapp:{to_number}'

    message = twilio_client.messages.create(
        from_=config.TWILIO_WHATSAPP_NUMBER,
        to=to_wa,
        body=body,
    )
    return message.sid
