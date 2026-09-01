"""
BotSetu Backend
===============
Entry point for the refactored Flask application.

Start the server:
    python app_new.py

Directory layout
----------------
config.py           -- all environment variables
database.py         -- MongoDB client + all collection handles + index setup
utils/
    helpers.py      -- shared helper functions (now, credits, sessions, logging)
services/
    messaging.py    -- WhatsApp reply logic + Twilio send wrapper
    ivr.py          -- TwiML builder for IVR voice flows
    rag.py          -- hybrid RAG pipeline (ChromaDB + BM25 + RRF)
    mandi.py        -- stateful mandi booking flow
    ai_engine.py    -- Ollama LLM chat + multilingual support
routes/
    health.py       -- GET / and GET /health
    bots.py         -- bot activate / deactivate / ivr-number / sandbox-info
    conversations.py-- conversation history CRUD
    payments.py     -- payment record CRUD
    bookings.py     -- mandi booking reads
    ai.py           -- Ollama models, KB upload / progress / delete, generate-template
    templates.py    -- template catalogue
    webhook.py      -- Twilio WhatsApp and Voice webhooks
"""

import logging

from flask import Flask
from flask_cors import CORS

import config
from database import ensure_indexes

from routes.health        import health_bp
from routes.bots          import bots_bp
from routes.conversations import conversations_bp
from routes.payments      import payments_bp
from routes.bookings      import bookings_bp
from routes.ai            import ai_bp
from routes.templates     import templates_bp
from routes.webhook       import webhook_bp

# ---------------------------------------------------------------------------
# Logging — writes to stdout and to botsetu.log in the same directory.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('botsetu.log', encoding='utf-8'),
    ],
)
log = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory — build and configure the Flask app."""
    config.validate()

    app = Flask(__name__)
    CORS(app, origins=config.ALLOWED_ORIGINS)

    ensure_indexes()

    blueprints = [
        health_bp,
        bots_bp,
        conversations_bp,
        payments_bp,
        bookings_bp,
        ai_bp,
        templates_bp,
        webhook_bp,
    ]
    for bp in blueprints:
        app.register_blueprint(bp)

    log.info("BotSetu backend ready — %d blueprints registered", len(blueprints))
    return app


if __name__ == '__main__':
    application = create_app()
    log.info("Starting BotSetu backend on port %d", config.PORT)
    application.run(host='0.0.0.0', port=config.PORT, debug=False)
