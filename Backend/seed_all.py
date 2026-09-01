"""
seed_all.py
-----------
One-shot database seeder for all BotSetu collections.

Run once after setting up a new environment:
    python seed_all.py

Safe to re-run — all operations are upserts (insert or update, never duplicate).

Seed data lives in Backend/templates/*.json — edit those files, not this one.

Collections seeded
------------------
  mandi-i18n       -- per-language UI strings for the mandi booking flow
  mandi-crops      -- per-language crop name maps
  mandi-config     -- language-selection prompt, supported langs, slots, mandis
  ai-i18n          -- greeting, fallback, and links-header strings for AI bots
  knowledge-links  -- IIIT-NR quick-reference link catalogue
  system-config    -- initial_credits, plan_prices
  templates        -- 7 built-in bot templates
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI    = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME        = os.getenv('DB_NAME', 'BotSetu')
TEMPLATES_DIR  = Path(__file__).parent / 'templates'

client = MongoClient(MONGODB_URI)
db     = client[DB_NAME]


def load(filename: str):
    path = TEMPLATES_DIR / filename
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def upsert(col_name: str, key_field: str, docs: list) -> None:
    col      = db[col_name]
    inserted = 0
    updated  = 0
    for doc in docs:
        result = col.update_one(
            {key_field: doc[key_field]},
            {'$set': doc},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1
    print(f"[{col_name}] {inserted} inserted, {updated} updated (total {len(docs)})")


def seed_mandi_i18n():
    docs = load('mandi_i18n.json')
    upsert('mandi-i18n', 'lang', docs)


def seed_mandi_crops():
    raw  = load('mandi_crops.json')
    # JSON stores as { "en": {...}, "hi": {...} } — convert to list of {lang, crops}
    docs = [{'lang': lang, 'crops': crops} for lang, crops in raw.items()]
    upsert('mandi-crops', 'lang', docs)


def seed_mandi_config():
    raw = load('mandi_config.json')
    # Convert flat object to list of {key, value} documents
    docs = [{'key': k, 'value': v} for k, v in raw.items()]
    upsert('mandi-config', 'key', docs)


def seed_ai_i18n():
    docs = load('ai_i18n.json')
    upsert('ai-i18n', 'lang_code', docs)


def seed_knowledge_links():
    docs = load('knowledge_links.json')
    upsert('knowledge-links', 'url', docs)


def seed_system_config():
    raw  = load('system_config.json')
    docs = [{'key': k, 'value': v} for k, v in raw.items()]
    upsert('system-config', 'key', docs)


def seed_templates():
    docs = load('bot_templates.json')
    upsert('templates', 'id', docs)


def main():
    print(f"Seeding BotSetu database from {TEMPLATES_DIR}/ ...")
    seed_mandi_i18n()
    seed_mandi_crops()
    seed_mandi_config()
    seed_ai_i18n()
    seed_knowledge_links()
    seed_system_config()
    seed_templates()
    print("[OK] Seeding complete.")


if __name__ == '__main__':
    main()
