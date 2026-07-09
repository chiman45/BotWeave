"""
database.py
-----------
Single MongoDB connection shared across the application.
All collection handles are exported from here — no module creates its own connection.
"""

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from config import MONGODB_URI, DB_NAME

log = logging.getLogger(__name__)

# One client, one database — MongoDB driver handles connection pooling internally.
_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = _client[DB_NAME]

# ---------------------------------------------------------------------------
# Collection handles
# Keep names in one place; never scatter string literals across modules.
# ---------------------------------------------------------------------------
bots_col          = db['User-data']       # bot documents created by Next.js /api/bot
conversations_col = db['conversations']   # per-customer message history
sessions_col      = db['bot-sessions']    # customer-phone → businessId sticky sessions
payments_col      = db['payments']
bookings_col      = db['mandi-bookings']  # mandi slot bookings
credits_col       = db['credits']         # per-user message credit balance
templates_col     = db['templates']       # prebuilt bot templates

# Config collections — populated by seed_all.py; read at runtime with TTL caching.
mandi_i18n_col    = db['mandi-i18n']      # per-language UI strings for the mandi flow
mandi_crops_col   = db['mandi-crops']     # per-language crop name maps
mandi_config_col  = db['mandi-config']    # lang-select message, supported langs, defaults
ai_i18n_col       = db['ai-i18n']         # greeting / fallback / links-header per language
knowledge_links_col = db['knowledge-links']  # institution quick-reference links
system_config_col = db['system-config']   # global settings (initial credits, plan prices)


def ensure_indexes():
    """
    Create all required indexes.
    safe to call every time the process starts (idempotent).
    """
    sessions_col.create_index([('customerPhone', ASCENDING)], unique=True)
    conversations_col.create_index(
        [('businessId', ASCENDING), ('phoneNumber', ASCENDING)]
    )
    conversations_col.create_index([('timestamp', DESCENDING)])
    bots_col.create_index([('businessId', ASCENDING)])
    bots_col.create_index([('ownerUserId', ASCENDING)])
    credits_col.create_index([('userId', ASCENDING)], unique=True)
    bookings_col.create_index(
        [('businessId', ASCENDING), ('date', ASCENDING), ('timeSlot', ASCENDING)]
    )
    templates_col.create_index([('id', ASCENDING)], unique=True)
    system_config_col.create_index([('key', ASCENDING)], unique=True)
    mandi_i18n_col.create_index([('lang', ASCENDING)], unique=True)
    mandi_crops_col.create_index([('lang', ASCENDING)], unique=True)
    mandi_config_col.create_index([('key', ASCENDING)], unique=True)
    ai_i18n_col.create_index([('lang', ASCENDING)], unique=True)
    log.info("Database indexes verified.")


def get_system_config(key: str, default=None):
    """Fetch a single value from system-config by key."""
    doc = system_config_col.find_one({'key': key}, {'_id': 0, 'value': 1})
    return doc['value'] if doc else default
