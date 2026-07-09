"""
services/mandi.py
-----------------
Stateful multi-step mandi (agricultural market) slot-booking flow over WhatsApp.

All user-facing strings (translations, crop names, default slots) are loaded from
MongoDB at runtime via a TTL-based in-memory cache.  The seed_all.py script
populates the required collections on first setup.

Flow steps
----------
lang_select  -> lang_confirm -> ask_name -> ask_village -> ask_crop
-> ask_quantity -> ask_mandi -> ask_slot -> [done]

On every greeting the flow resets to lang_select so users can rebook.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from database import (
    sessions_col,
    bookings_col,
    mandi_i18n_col,
    mandi_crops_col,
    mandi_config_col,
)
from utils.helpers import now

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTL-based config cache
# Avoids a DB round-trip on every webhook call while allowing live updates.
# ---------------------------------------------------------------------------

_CACHE_TTL = 300  # 5 minutes

class _MandiConfigCache:
    def __init__(self):
        self._lock       = threading.Lock()
        self._loaded_at  = 0.0
        self._i18n:    Dict[str, Dict[str, str]] = {}   # lang -> {key: template}
        self._crops:   Dict[str, Dict[str, str]] = {}   # lang -> {number: crop_name}
        self._config:  Dict[str, object]         = {}   # key -> value

    def _is_stale(self) -> bool:
        return (time.monotonic() - self._loaded_at) > _CACHE_TTL

    def _reload(self) -> None:
        with self._lock:
            if not self._is_stale():
                return

            i18n = {
                doc['lang']: doc.get('strings', {})
                for doc in mandi_i18n_col.find({}, {'_id': 0})
                if 'lang' in doc
            }
            crops = {
                doc['lang']: doc.get('crops', {})
                for doc in mandi_crops_col.find({}, {'_id': 0})
                if 'lang' in doc
            }
            cfg = {
                doc['key']: doc['value']
                for doc in mandi_config_col.find({}, {'_id': 0})
                if 'key' in doc and 'value' in doc
            }

            if i18n:
                self._i18n   = i18n
            if crops:
                self._crops  = crops
            if cfg:
                self._config = cfg

            self._loaded_at = time.monotonic()
            log.debug("[Mandi] Config cache refreshed.")

    # -- Public accessors ------------------------------------------------

    def translate(self, lang: str, key: str, **kwargs) -> str:
        """Return a translated template string, falling back to English."""
        if self._is_stale():
            self._reload()
        strings = self._i18n.get(lang) or self._i18n.get('en', {})
        tmpl = strings.get(key) or (self._i18n.get('en') or {}).get(key, '')
        return tmpl.format(**kwargs) if kwargs else tmpl

    def crop_name(self, lang: str, choice: str, raw_input: str) -> str:
        """Map a user's crop number to the crop name in the selected language."""
        if self._is_stale():
            self._reload()
        lang_crops = self._crops.get(lang) or self._crops.get('en', {})
        return lang_crops.get(choice, raw_input.title())

    def lang_select_msg(self) -> str:
        if self._is_stale():
            self._reload()
        return self._config.get('lang_select_msg', (
            "Welcome\n\n"
            "Please choose your language:\n\n"
            "1 - English\n"
            "2 - Hindi\n"
            "3 - Punjabi\n"
            "4 - Gujarati\n"
            "5 - Marathi\n\n"
            "Reply with 1, 2, 3, 4, or 5:"
        ))

    def supported_langs(self) -> Dict[str, str]:
        if self._is_stale():
            self._reload()
        return self._config.get('supported_langs', {
            '1': 'en', '2': 'hi', '3': 'pa', '4': 'gu', '5': 'mr',
            'english': 'en', 'hindi': 'hi',
            'punjabi': 'pa', 'gujarati': 'gu', 'marathi': 'mr',
        })

    def reset_greetings(self) -> set:
        if self._is_stale():
            self._reload()
        return set(self._config.get('lang_reset_greetings',
                                    ['hi', 'hii', 'hello', 'hey', 'namaste']))

    def default_slots(self) -> List[str]:
        if self._is_stale():
            self._reload()
        return self._config.get('default_slots', [
            '9:00 AM - 10:00 AM',
            '10:00 AM - 11:00 AM',
            '11:00 AM - 12:00 PM',
            '2:00 PM - 3:00 PM',
        ])

    def default_mandis(self) -> List[Dict]:
        if self._is_stale():
            self._reload()
        return self._config.get('default_mandis', [
            {'name': 'Main Mandi', 'location': 'City Center', 'address': 'Central Market'},
        ])


_cache = _MandiConfigCache()


# ---------------------------------------------------------------------------
# Booking flow
# ---------------------------------------------------------------------------

def _build_slot_list(slots: List[str]) -> str:
    return '\n'.join(f"{i + 1}. {s}" for i, s in enumerate(slots))


def _build_mandi_list(mandis: List[Dict]) -> str:
    return '\n'.join(
        f"{i + 1}. {m['name']} - {m.get('location', '')}"
        for i, m in enumerate(mandis)
    )


def handle_mandi_flow(bot: Dict, customer_phone: str, incoming_msg: str) -> str:
    """
    Process one turn of the mandi booking conversation.

    Reads and writes flow state to the bot-sessions collection so the
    conversation can span multiple webhook calls.
    """
    session   = sessions_col.find_one({'customerPhone': customer_phone}) or {}
    step      = session.get('flowStep', 'lang_select')
    flow_data = session.get('flowData', {})

    # Any greeting resets the flow so users can make a new booking.
    if incoming_msg.strip().lower() in _cache.reset_greetings():
        step      = 'lang_select'
        flow_data = {}

    # Completed conversations also restart cleanly.
    if step == 'done':
        step      = 'lang_select'
        flow_data = {}

    mandis       = bot.get('mandis')  or _cache.default_mandis()
    slots        = bot.get('slots')   or _cache.default_slots()
    max_per_slot = int(bot.get('maxBookingsPerSlot', 10))
    lang         = flow_data.get('language', 'en')
    t            = _cache.translate   # shorthand
    business_id  = bot['businessId']

    reply     = ''
    next_step = step

    # ------------------------------------------------------------------ #
    if step == 'lang_select':
        reply     = _cache.lang_select_msg()
        next_step = 'lang_confirm'

    # ------------------------------------------------------------------ #
    elif step == 'lang_confirm':
        choice = incoming_msg.strip().lower()
        lang   = _cache.supported_langs().get(choice)
        if not lang:
            reply = t('en', 'lang_invalid')
        else:
            flow_data['language'] = lang
            reply     = t(lang, 'lang_ok') + '\n\n' + t(lang, 'welcome',
                            bname=bot.get('businessName', 'Mandi Booking'))
            next_step = 'ask_name'

    # ------------------------------------------------------------------ #
    elif step == 'ask_name':
        flow_data['farmerName'] = incoming_msg.strip()
        reply     = t(lang, 'ask_village', name=flow_data['farmerName'])
        next_step = 'ask_village'

    # ------------------------------------------------------------------ #
    elif step == 'ask_village':
        flow_data['village'] = incoming_msg.strip()
        reply     = t(lang, 'ask_crop')
        next_step = 'ask_crop'

    # ------------------------------------------------------------------ #
    elif step == 'ask_crop':
        raw_input          = incoming_msg.strip()
        flow_data['cropType'] = _cache.crop_name(lang, raw_input, raw_input)
        reply     = t(lang, 'crop_ok', crop=flow_data['cropType'])
        next_step = 'ask_quantity'

    # ------------------------------------------------------------------ #
    elif step == 'ask_quantity':
        qty                  = incoming_msg.strip()
        flow_data['quantity'] = qty if qty != '0' else 'Not specified'
        reply     = t(lang, 'ask_mandi', mandi_list=_build_mandi_list(mandis))
        next_step = 'ask_mandi'

    # ------------------------------------------------------------------ #
    elif step == 'ask_mandi':
        try:
            idx = int(incoming_msg.strip()) - 1
            if 0 <= idx < len(mandis):
                selected_mandi = mandis[idx]
                flow_data['mandiIndex']    = idx
                flow_data['mandiName']     = selected_mandi['name']
                flow_data['mandiLocation'] = selected_mandi.get(
                    'address', selected_mandi.get('location', '')
                )
                today     = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                available = [
                    s for s in slots
                    if bookings_col.count_documents({
                        'businessId': business_id,
                        'mandiName':  flow_data['mandiName'],
                        'timeSlot':   s,
                        'date':       today,
                    }) < max_per_slot
                ]
                if not available:
                    reply     = t(lang, 'no_slots')
                    next_step = 'done'
                else:
                    flow_data['availableSlots'] = available
                    reply     = t(lang, 'slots_header',
                                  mandi=flow_data['mandiName'],
                                  slot_list=_build_slot_list(available))
                    next_step = 'ask_slot'
            else:
                reply = t(lang, 'bad_mandi', n=len(mandis))
        except ValueError:
            reply = t(lang, 'bad_mandi_type')

    # ------------------------------------------------------------------ #
    elif step == 'ask_slot':
        available = flow_data.get('availableSlots', slots)
        try:
            idx = int(incoming_msg.strip()) - 1
            if 0 <= idx < len(available):
                flow_data['timeSlot'] = available[idx]
                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                token_count          = bookings_col.count_documents(
                    {'businessId': business_id, 'date': today}
                )
                token                = f"TK-{today.replace('-', '')}-{str(token_count + 1).zfill(3)}"
                flow_data['tokenNumber'] = token
                flow_data['date']        = today

                bookings_col.insert_one({
                    'businessId':    business_id,
                    'tokenNumber':   token,
                    'farmerName':    flow_data.get('farmerName', ''),
                    'village':       flow_data.get('village', ''),
                    'cropType':      flow_data.get('cropType', ''),
                    'quantity':      flow_data.get('quantity', ''),
                    'mandiName':     flow_data.get('mandiName', ''),
                    'mandiLocation': flow_data.get('mandiLocation', ''),
                    'timeSlot':      flow_data['timeSlot'],
                    'date':          today,
                    'phoneNumber':   customer_phone,
                    'status':        'confirmed',
                    'language':      lang,
                    'createdAt':     now(),
                })

                reply = t(
                    lang, 'confirmed',
                    token=token,
                    name=flow_data.get('farmerName', ''),
                    crop=flow_data.get('cropType', ''),
                    qty=flow_data.get('quantity', ''),
                    mandi=flow_data.get('mandiName', ''),
                    loc=flow_data.get('mandiLocation', ''),
                    slot=flow_data['timeSlot'],
                    date=today,
                )
                next_step = 'done'
            else:
                reply = t(lang, 'bad_slot', n=len(available))
        except ValueError:
            reply = t(lang, 'bad_slot_type')

    # Persist updated state into the session document.
    sessions_col.update_one(
        {'customerPhone': customer_phone},
        {'$set': {
            'businessId': business_id,
            'flowStep':   next_step,
            'flowData':   flow_data,
            'updatedAt':  now(),
        }},
        upsert=True,
    )

    return reply
