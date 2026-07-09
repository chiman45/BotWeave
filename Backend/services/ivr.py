"""
services/ivr.py
---------------
Builds Twilio TwiML responses for IVR (Interactive Voice Response) phone flows.
The IVR tree is stored per-bot in the 'ivrNodes' field of the bot document.
"""

import os
import logging
from typing import Dict, Optional, Tuple

from twilio.twiml.voice_response import VoiceResponse, Gather

log = logging.getLogger(__name__)

# Voice and language used for all synthesised speech.
_TTS_VOICE    = 'alice'
_TTS_LANGUAGE = 'en-IN'


def webhook_base_url() -> str:
    """
    Derive the base URL for IVR gather callbacks from WEBHOOK_URL.
    The WhatsApp webhook path is stripped so we get the root server URL.
    """
    base = os.getenv('WEBHOOK_URL', '').rstrip('/')
    if base.endswith('/webhook/whatsapp'):
        base = base[: -len('/webhook/whatsapp')]
    return base


def build_twiml(
    node: Dict,
    business_id: str,
    base_url: Optional[str] = None,
) -> Tuple[str, int, Dict]:
    """
    Build a TwiML VoiceResponse for the given IVR node.

    End nodes (isEndNode=True or no options): say the message and hang up.
    Branch nodes: build a <Gather> DTMF menu, then hang up if no input arrives.

    Returns a (twiml_str, status_code, headers) tuple for direct use as a
    Flask response.
    """
    if base_url is None:
        base_url = webhook_base_url()

    response = VoiceResponse()
    message  = (node.get('message') or '').strip()
    options  = node.get('options') or []

    if not message:
        response.say("This menu has no message configured. Goodbye.", voice=_TTS_VOICE)
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    if node.get('isEndNode') or not options:
        response.say(message, voice=_TTS_VOICE, language=_TTS_LANGUAGE)
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

    # Build the spoken menu prompt: message + "Press N for <option>."
    menu_text = message + ' '
    for idx, opt in enumerate(options, start=1):
        label = (opt.get('label') or '').strip()
        if label:
            menu_text += f"Press {idx} for {label}. "

    gather_url = f"{base_url}/webhook/voice/gather/{business_id}/{node['id']}"
    gather = Gather(
        num_digits=1,
        action=gather_url,
        method='POST',
        timeout=10,
    )
    gather.say(menu_text, voice=_TTS_VOICE, language=_TTS_LANGUAGE)
    response.append(gather)

    # Fallback when the caller does not press anything within the timeout.
    response.say("We did not receive any input. Goodbye.", voice=_TTS_VOICE)
    response.hangup()

    return str(response), 200, {'Content-Type': 'text/xml'}
