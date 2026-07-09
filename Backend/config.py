"""
config.py
---------
Loads all environment variables, validates required ones at startup,
and exports typed constants used across the application.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — configured once here; every module uses logging.getLogger(__name__)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('botsetu.log', encoding='utf-8'),
    ],
)

# ---------------------------------------------------------------------------
# Twilio
# ---------------------------------------------------------------------------
TWILIO_ACCOUNT_SID: str = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN: str  = os.getenv('TWILIO_AUTH_TOKEN', '')

# Format: whatsapp:+14155238886
TWILIO_WHATSAPP_NUMBER: str = os.getenv('TWILIO_WHATSAPP_NUMBER', '')

# Raw E.164 phone number used for Voice calls (strips "whatsapp:" prefix if present)
TWILIO_PHONE_NUMBER: str = os.getenv(
    'TWILIO_PHONE_NUMBER',
    TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', ''),
)

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGODB_URI: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME: str     = 'BotSetu'

# ---------------------------------------------------------------------------
# Ollama (local LLM)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str    = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_EMBED_MODEL: str = os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
OLLAMA_CHAT_MODEL: str  = os.getenv('OLLAMA_CHAT_MODEL', 'llama3')

# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------
RAG_BM25_ENABLED: bool = os.getenv('RAG_BM25_ENABLED', 'true').lower() != 'false'
RAG_MAX_DISTANCE: float = float(os.getenv('RAG_MAX_DISTANCE', '0.0'))
RAG_FALLBACK_TOP_K: int = int(os.getenv('RAG_FALLBACK_TOP_K', '5'))

# Root path for per-bot ChromaDB + BM25 index files
VECTOR_STORE_ROOT: str = os.path.join(os.path.dirname(__file__), 'vector_stores')

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------
PORT: int = int(os.getenv('PORT', '5000'))

# Public-facing webhook base URL — set by setup_webhook.py / ngrok at runtime.
# Example: https://abc123.ngrok-free.dev
WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')

# ---------------------------------------------------------------------------
# Startup validation — fail fast rather than producing confusing runtime errors
# ---------------------------------------------------------------------------
def validate():
    missing = []
    if not TWILIO_ACCOUNT_SID:
        missing.append('TWILIO_ACCOUNT_SID')
    if not TWILIO_AUTH_TOKEN:
        missing.append('TWILIO_AUTH_TOKEN')
    if not TWILIO_WHATSAPP_NUMBER:
        missing.append('TWILIO_WHATSAPP_NUMBER')
    if missing:
        raise RuntimeError(
            f"Required environment variables are not set: {', '.join(missing)}. "
            "Check Backend/.env."
        )
