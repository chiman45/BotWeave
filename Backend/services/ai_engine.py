"""
services/ai_engine.py
---------------------
Handles AI-powered bot replies using a local Ollama LLM.

Responsibilities
----------------
- Language detection (Unicode script ranges + Hinglish heuristics + langdetect)
- RAG context injection when aiRagEnabled = True
- Multilingual greeting and fallback messages (loaded from MongoDB)
- Institution-specific quick-reference link matching (loaded from MongoDB)
- Deterministic faculty-list answer path (avoids hallucinated names)

All user-facing strings are fetched from the ai-i18n and knowledge-links
collections; no translatable text is hardcoded here.
"""

import re
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple

import requests

import config
from database import ai_i18n_col, knowledge_links_col, conversations_col
from pymongo import DESCENDING

from services.rag import rag_query

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTL-based i18n cache
# ---------------------------------------------------------------------------

_CACHE_TTL = 300  # 5 minutes


class _AiI18nCache:
    def __init__(self):
        self._lock      = threading.Lock()
        self._loaded_at = 0.0
        self._greetings:    Dict[str, str] = {}
        self._fallbacks:    Dict[str, str] = {}
        self._links_header: Dict[str, str] = {}
        self._links:        List[Dict]     = []  # [{keywords, label, url}]

    def _is_stale(self) -> bool:
        return (time.monotonic() - self._loaded_at) > _CACHE_TTL

    def _reload(self) -> None:
        with self._lock:
            if not self._is_stale():
                return
            greetings    = {}
            fallbacks    = {}
            links_header = {}
            for doc in ai_i18n_col.find({}, {'_id': 0}):
                lang = doc.get('lang')
                if lang:
                    if doc.get('greeting'):
                        greetings[lang]    = doc['greeting']
                    if doc.get('fallback'):
                        fallbacks[lang]    = doc['fallback']
                    if doc.get('linksHeader'):
                        links_header[lang] = doc['linksHeader']
            links = list(knowledge_links_col.find({}, {'_id': 0}))

            if greetings:
                self._greetings    = greetings
            if fallbacks:
                self._fallbacks    = fallbacks
            if links_header:
                self._links_header = links_header
            if links:
                self._links = links

            self._loaded_at = time.monotonic()
            log.debug("[AI] i18n cache refreshed.")

    def greeting(self, lang: str) -> str:
        if self._is_stale():
            self._reload()
        return (
            self._greetings.get(lang)
            or self._greetings.get('en')
            or "Hi! I am here to help you. Just ask!"
        )

    def fallback(self, lang: str) -> str:
        if self._is_stale():
            self._reload()
        return (
            self._fallbacks.get(lang)
            or self._fallbacks.get('en')
            or "Sorry, I don't have that information right now."
        )

    def links_header(self, lang: str) -> str:
        if self._is_stale():
            self._reload()
        return self._links_header.get(lang) or self._links_header.get('en') or 'Relevant Links:'

    def relevant_links(self, query: str) -> List[str]:
        if self._is_stale():
            self._reload()
        q = query.lower()
        matched = []
        for entry in self._links:
            keywords = entry.get('keywords', [])
            if any(kw in q for kw in keywords):
                matched.append(f"- {entry.get('label', '')}: {entry.get('url', '')}")
        return matched


_i18n = _AiI18nCache()


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

# Unicode script ranges mapped to (lang_code, lang_name)
_SCRIPT_RANGES: List[Tuple[int, int, str, str]] = [
    (0x0900, 0x097F, 'hi',  'Hindi'),
    (0x0980, 0x09FF, 'bn',  'Bengali'),
    (0x0A00, 0x0A7F, 'pa',  'Punjabi'),
    (0x0A80, 0x0AFF, 'gu',  'Gujarati'),
    (0x0B00, 0x0B7F, 'or',  'Odia'),
    (0x0B80, 0x0BFF, 'ta',  'Tamil'),
    (0x0C00, 0x0C7F, 'te',  'Telugu'),
    (0x0C80, 0x0CFF, 'kn',  'Kannada'),
    (0x0D00, 0x0D7F, 'ml',  'Malayalam'),
    (0x0600, 0x06FF, 'ur',  'Urdu'),
]

# Common Hinglish (Roman-script Hindi) words that signal the user is writing Hindi
# in the Latin alphabet.
_HINGLISH_WORDS = frozenset({
    'kya', 'hai', 'hain', 'mujhe', 'mera', 'meri', 'mere', 'aap', 'tum',
    'kaise', 'kaisa', 'kahan', 'kitne', 'kitna', 'chahiye', 'batao',
    'bata', 'samjhao', 'accha', 'theek', 'sahi', 'nahi', 'nahin',
    'kyun', 'kyunki', 'lekin', 'aur', 'yeh', 'woh',
})

_LANGDETECT_MAP: Dict[str, Tuple[str, str]] = {
    'hi': ('hi', 'Hindi'), 'bn': ('bn', 'Bengali'),
    'ta': ('ta', 'Tamil'), 'te': ('te', 'Telugu'),
    'kn': ('kn', 'Kannada'), 'ml': ('ml', 'Malayalam'),
    'gu': ('gu', 'Gujarati'), 'mr': ('mr', 'Marathi'),
    'pa': ('pa', 'Punjabi'), 'ur': ('ur', 'Urdu'),
    'or': ('or', 'Odia'),
}


def detect_language(text: str) -> Tuple[str, str]:
    """
    Return (lang_code, lang_name).

    Priority:
      1. Unicode script-based detection (instantaneous, reliable for typed scripts)
      2. Hinglish heuristic (Roman-alphabet Hindi)
      3. langdetect library (optional; falls back silently)
      4. English as the final default
    """
    # 1. Script
    for ch in text:
        cp = ord(ch)
        for lo, hi, code, name in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                return code, name

    # 2. Hinglish
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    if words & _HINGLISH_WORDS:
        return 'hi_roman', 'Hindi (Roman)'

    # 3. langdetect (optional dependency — graceful fallback)
    try:
        from langdetect import detect
        code = detect(text)
        if code in _LANGDETECT_MAP:
            return _LANGDETECT_MAP[code]
    except Exception:
        pass

    return 'en', 'English'


# ---------------------------------------------------------------------------
# Greeting detection
# ---------------------------------------------------------------------------

_GREETING_TOKENS = frozenset({
    'hi', 'hello', 'hey', 'hii', 'helo', 'heya', 'howdy', 'hola',
    'good morning', 'good afternoon', 'good evening', 'good night',
    'namaste', 'namaskar', 'jai hind', 'hello there', 'hi there',
    'start', 'help', 'menu',
    # Devanagari
    'नमस्ते',  # namaste
    'नमस्कार',  # namaskar
    'हेलो',  # hello
    'हाय',  # hi
    # Southern / Eastern scripts
    'வணக்கம்',  # Tamil
    'నమస్కారం',  # Telugu
    'ನಮಸ್ಕಾರ',  # Kannada
    'നമസ്കാരം',  # Malayalam
    'ਨਮਸਕਾਰ',  # Punjabi
    'પમવતન',  # Gujarati SAT SRI AKAL placeholder
})


def is_greeting(text: str) -> bool:
    t = text.strip().lower().rstrip('!.,?')
    return t in _GREETING_TOKENS or (len(t) <= 10 and any(g in t for g in ('hi', 'hello', 'hey')))


# ---------------------------------------------------------------------------
# Faculty-list deterministic path (IIIT-NR specific heuristic)
# ---------------------------------------------------------------------------

def _is_faculty_list_query(text: str) -> bool:
    q = text.lower()
    return 'faculty' in q and any(k in q for k in ('list', 'members', 'member', 'names', 'name'))


def _extract_faculty_names(context: str, max_names: int = 25) -> List[str]:
    pattern = re.compile(
        r"\b(?:Prof(?:essor)?\.?|Dr\.?)\s+[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3}"
    )
    seen:  set  = set()
    names: List[str] = []
    for match in pattern.findall(context or ''):
        clean = re.sub(r'\s+', ' ', match).strip()
        if clean.lower() not in seen:
            seen.add(clean.lower())
            names.append(clean)
            if len(names) >= max_names:
                break
    return names


# ---------------------------------------------------------------------------
# Main AI flow handler
# ---------------------------------------------------------------------------

def handle_ai_flow(bot: Dict, customer_phone: str, incoming_msg: str) -> str:
    """
    Generate an AI reply for a single inbound message.

    Steps
    -----
    1. Detect language.
    2. Short-circuit on greetings (no LLM call needed).
    3. Fetch conversation history for multi-turn context.
    4. Optionally retrieve RAG context.
    5. Deterministic faculty-list path if applicable.
    6. Build system prompt with language instruction.
    7. Call Ollama and append matched quick-reference links.
    """
    lang_code, lang_name = detect_language(incoming_msg)
    log.info("[AI] Language detected: %s (%s)", lang_name, lang_code)

    if is_greeting(incoming_msg):
        return _i18n.greeting(lang_code)

    business_id = bot['businessId']
    rag_enabled = bool(bot.get('aiRagEnabled', False))

    # Conversation history — last 8 turns in chronological order.
    history_docs = list(
        conversations_col.find(
            {'businessId': business_id, 'phoneNumber': customer_phone},
            {'messageContent': 1, 'sender': 1, '_id': 0},
        ).sort('timestamp', DESCENDING).limit(8)
    )
    history_docs.reverse()
    history_str = ''.join(
        f"{'User' if m['sender'] == 'user' else 'Assistant'}: {m['messageContent']}\n"
        for m in history_docs
    )

    # RAG retrieval
    rag_context = ''
    if rag_enabled:
        rag_context = rag_query(business_id, incoming_msg)
        log.info("[AI] RAG context: %d chars", len(rag_context))

    # Deterministic faculty-list answer — avoids hallucinated names.
    if rag_enabled and rag_context and _is_faculty_list_query(incoming_msg):
        chunks = rag_context.split('\n\n')
        main_chunks = [
            c for c in chunks
            if 'iiitnr.ac.in/faculty' in c
            and 'adjunct-faculty' not in c
            and 'past-faculty' not in c
            and 'emeritus' not in c.lower()
        ]
        names = _extract_faculty_names('\n\n'.join(main_chunks) if main_chunks else rag_context)
        source = 'https://www.iiitnr.ac.in/faculty'
        if names:
            lines = '\n'.join(f"- {n}" for n in names[:20])
            return f"Faculty members at IIIT Naya Raipur:\n\n{lines}\n\nFull list: {source}"
        return f"Full faculty list: {source}"

    # Language instruction — explicit is more reliable than "reply in same language"
    # for locally-run models.
    if lang_code == 'hi_roman':
        lang_instruction = (
            "IMPORTANT: The user is writing in Hinglish (Roman-script Hindi). "
            "Reply in the same Roman Hindi style. "
        )
    elif lang_code != 'en':
        lang_instruction = f"IMPORTANT: You MUST reply in {lang_name}. "
    else:
        lang_instruction = "Reply in English. "

    business_name = bot.get('businessName', 'this business')

    if bot.get('aiSystemPrompt'):
        system_prompt = bot['aiSystemPrompt']
        if rag_enabled:
            system_prompt += (
                f"\n\n{lang_instruction}"
                "Answer ONLY from the reference information provided below. "
                "Do not use your general training knowledge. "
                "Do not invent facts, links, numbers, or names not in the reference. "
                "If the answer is not there, say so and suggest contacting the organisation directly."
            )
        else:
            system_prompt += f"\n\n{lang_instruction}"
    elif rag_enabled:
        system_prompt = (
            f"You are a helpful assistant for {business_name}. "
            f"{lang_instruction}"
            "Answer ONLY from the reference information below. "
            "Do not use general knowledge. "
            "Do not invent facts, prices, links, or names not in the reference. "
            "If the answer is not present, say you do not have that information."
        )
    else:
        system_prompt = (
            f"You are a helpful assistant for {business_name}. "
            f"{lang_instruction}"
            "Answer clearly and concisely."
        )

    # No RAG context found — return pre-translated fallback immediately.
    if rag_enabled and not rag_context:
        matched_links = _i18n.relevant_links(incoming_msg)
        fallback = bot.get('fallbackMessage') or _i18n.fallback(lang_code)
        if matched_links:
            header = _i18n.links_header(lang_code)
            fallback += f"\n\n{header}\n" + '\n'.join(matched_links)
        log.warning("[AI] No RAG context for query: %r", incoming_msg[:80])
        return fallback

    context_block = (
        f"--- REFERENCE INFORMATION ---\n{rag_context}\n--- END ---\n\n"
        if rag_enabled and rag_context
        else ''
    )

    # Call Ollama
    try:
        resp = requests.post(
            f'{config.OLLAMA_BASE_URL}/api/chat',
            json={
                'model': config.OLLAMA_CHAT_MODEL,
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
        log.info("[AI] Ollama reply (first 200 chars): %r", reply[:200])

        if not reply:
            return _i18n.fallback(lang_code)

        # Append quick-reference links when relevant.
        matched_links = _i18n.relevant_links(incoming_msg)
        if matched_links:
            header = _i18n.links_header(lang_code)
            reply += f"\n\n{header}\n" + '\n'.join(matched_links)

        return reply

    except Exception as exc:
        log.error("[AI] Ollama error: %s", exc)
        return "I am having trouble connecting right now. Please try again in a moment."
