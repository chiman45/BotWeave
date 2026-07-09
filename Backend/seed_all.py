"""
seed_all.py
-----------
One-shot database seeder for all BotSetu collections.

Run once after setting up a new environment:
    python seed_all.py

Safe to re-run — all operations are upserts (insert or update, never duplicate).

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

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME     = os.getenv('DB_NAME', 'BotSetu')

client = MongoClient(MONGODB_URI)
db     = client[DB_NAME]


def upsert(col_name: str, key_field: str, docs: list) -> None:
    """Upsert a list of documents into a collection, keyed by key_field."""
    col         = db[col_name]
    inserted    = 0
    updated     = 0
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


# ===========================================================================
# mandi-i18n
# ===========================================================================

MANDI_I18N = [
    {
        'lang': 'en',
        'strings': {
            'lang_ok':        "You selected: *English*\n\nLet's begin the booking.",
            'welcome':        "*Welcome to {bname}!*\n\nI'll help you book a mandi slot in a few quick steps.\n\nPlease enter your *Full Name*:",
            'ask_village':    "Hello *{name}*!\n\nPlease enter your *Village Name*:",
            'ask_crop':       "Select your *Crop Type*:\n\n1. Paddy\n2. Wheat\n3. Maize\n4. Soybean\n5. Cotton\n6. Other\n\nReply with the *number* or crop name:",
            'crop_ok':        "Crop: *{crop}*\n\nEnter *Quantity* in quintals (or send *0* to skip):",
            'ask_mandi':      "Select your *nearest Mandi*:\n\n{mandi_list}\n\nReply with the number:",
            'slots_header':   "Available slots at *{mandi}*:\n\n{slot_list}\n\nReply with the *slot number*:",
            'no_slots':       "Sorry, all slots for *today* are fully booked. Please try again tomorrow!",
            'confirmed':      "*Booking Confirmed!*\n\nToken: *{token}*\nName: {name}\nCrop: {crop} ({qty} qtl)\nMandi: {mandi}\nLocation: {loc}\nSlot: {slot}\nDate: {date}\n\nPlease arrive *on time* with your produce. Thank you!\n\n_Send any message to make a new booking._",
            'bad_mandi':      "Please enter a number between *1* and *{n}*.",
            'bad_mandi_type': "Please enter a *number* to select the mandi.",
            'bad_slot':       "Please enter a number between *1* and *{n}*.",
            'bad_slot_type':  "Please enter a *number* to choose a slot.",
            'lang_invalid':   "Please choose a language by replying with:\n1 = English\n2 = Hindi\n3 = Punjabi\n4 = Gujarati\n5 = Marathi",
        },
    },
    {
        'lang': 'hi',
        'strings': {
            'lang_ok':        "आपने चुना: *हिंदी*\n\nआइए बुकिंग शुरू करते हैं।",
            'welcome':        "*{bname} में आपका स्वागत है!*\n\nमैं आपको मंडी स्लॉट बुक करने में मदद करूंगा।\n\nकृपया अपना *पूरा नाम* दर्ज करें:",
            'ask_village':    "नमस्ते *{name}*!\n\nकृपया अपने *गाँव का नाम* दर्ज करें:",
            'ask_crop':       "अपनी *फसल का प्रकार* चुनें:\n\n1. धान\n2. गेहूँ\n3. मक्का\n4. सोयाबीन\n5. कपास\n6. अन्य\n\n*नंबर* या फसल का नाम भेजें:",
            'crop_ok':        "फसल: *{crop}*\n\n*मात्रा* क्विंटल में दर्ज करें (छोड़ने के लिए *0* भेजें):",
            'ask_mandi':      "अपनी *नजदीकी मंडी* चुनें:\n\n{mandi_list}\n\nनंबर से जवाब दें:",
            'slots_header':   "*{mandi}* में उपलब्ध स्लॉट:\n\n{slot_list}\n\n*स्लॉट नंबर* से जवाब दें:",
            'no_slots':       "खेद है, *आज* के सभी स्लॉट भर गए हैं। कृपया कल पुनः प्रयास करें!",
            'confirmed':      "*बुकिंग की पुष्टि हो गई!*\n\nटोकन: *{token}*\nनाम: {name}\nफसल: {crop} ({qty} क्विंटल)\nमंडी: {mandi}\nस्थान: {loc}\nस्लॉट: {slot}\nतारीख: {date}\n\nकृपया अपनी उपज के साथ *समय पर* पहुँचें। धन्यवाद!\n\n_नई बुकिंग के लिए कोई भी संदेश भेजें।_",
            'bad_mandi':      "कृपया *1* और *{n}* के बीच संख्या दर्ज करें।",
            'bad_mandi_type': "मंडी चुनने के लिए कृपया एक *नंबर* दर्ज करें।",
            'bad_slot':       "कृपया *1* और *{n}* के बीच संख्या दर्ज करें।",
            'bad_slot_type':  "स्लॉट चुनने के लिए कृपया एक *नंबर* दर्ज करें।",
            'lang_invalid':   "कृपया भाषा चुनने के लिए 1, 2, 3, 4 या 5 से जवाब दें।",
        },
    },
    {
        'lang': 'pa',
        'strings': {
            'lang_ok':        "ਤੁਸੀਂ ਚੁਣਿਆ: *ਪੰਜਾਬੀ*\n\nਆਓ ਬੁਕਿੰਗ ਸ਼ੁਰੂ ਕਰੀਏ।",
            'welcome':        "*{bname} ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ!*\n\nਮੈਂ ਤੁਹਾਨੂੰ ਮੰਡੀ ਸਲਾਟ ਬੁੱਕ ਕਰਨ ਵਿੱਚ ਮਦਦ ਕਰਾਂਗਾ।\n\nਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ *ਪੂਰਾ ਨਾਮ* ਦਰਜ ਕਰੋ:",
            'ask_village':    "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ *{name}*!\n\nਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ *ਪਿੰਡ ਦਾ ਨਾਮ* ਦਰਜ ਕਰੋ:",
            'ask_crop':       "ਆਪਣੀ *ਫ਼ਸਲ ਦੀ ਕਿਸਮ* ਚੁਣੋ:\n\n1. ਝੋਨਾ\n2. ਕਣਕ\n3. ਮੱਕੀ\n4. ਸੋਇਆਬੀਨ\n5. ਕਪਾਹ\n6. ਹੋਰ\n\n*ਨੰਬਰ* ਜਾਂ ਫ਼ਸਲ ਦਾ ਨਾਮ ਭੇਜੋ:",
            'crop_ok':        "ਫ਼ਸਲ: *{crop}*\n\n*ਮਾਤਰਾ* ਕੁਇੰਟਲ ਵਿੱਚ ਦਰਜ ਕਰੋ (ਛੱਡਣ ਲਈ *0* ਭੇਜੋ):",
            'ask_mandi':      "ਆਪਣੀ *ਨੇੜੇ ਦੀ ਮੰਡੀ* ਚੁਣੋ:\n\n{mandi_list}\n\nਨੰਬਰ ਨਾਲ ਜਵਾਬ ਦਿਓ:",
            'slots_header':   "*{mandi}* ਵਿੱਚ ਉਪਲਬਧ ਸਲਾਟ:\n\n{slot_list}\n\n*ਸਲਾਟ ਨੰਬਰ* ਨਾਲ ਜਵਾਬ ਦਿਓ:",
            'no_slots':       "ਮਾਫ਼ ਕਰਨਾ, *ਅੱਜ* ਦੇ ਸਾਰੇ ਸਲਾਟ ਭਰੇ ਹੋਏ ਹਨ। ਕੱਲ੍ਹ ਫਿਰ ਕੋਸ਼ਿਸ਼ ਕਰੋ!",
            'confirmed':      "*ਬੁਕਿੰਗ ਪੱਕੀ ਹੋ ਗਈ!*\n\nਟੋਕਨ: *{token}*\nਨਾਮ: {name}\nਫ਼ਸਲ: {crop} ({qty} ਕੁਇੰਟਲ)\nਮੰਡੀ: {mandi}\nਟਿਕਾਣਾ: {loc}\nਸਲਾਟ: {slot}\nਮਿਤੀ: {date}\n\nਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਉਪਜ ਨਾਲ *ਸਮੇਂ ਸਿਰ* ਆਓ। ਧੰਨਵਾਦ!\n\n_ਨਵੀਂ ਬੁਕਿੰਗ ਲਈ ਕੋਈ ਵੀ ਸੁਨੇਹਾ ਭੇਜੋ।_",
            'bad_mandi':      "ਕਿਰਪਾ ਕਰਕੇ *1* ਅਤੇ *{n}* ਦੇ ਵਿਚਕਾਰ ਨੰਬਰ ਦਰਜ ਕਰੋ।",
            'bad_mandi_type': "ਮੰਡੀ ਚੁਣਨ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਇੱਕ *ਨੰਬਰ* ਦਰਜ ਕਰੋ।",
            'bad_slot':       "ਕਿਰਪਾ ਕਰਕੇ *1* ਅਤੇ *{n}* ਦੇ ਵਿਚਕਾਰ ਨੰਬਰ ਦਰਜ ਕਰੋ।",
            'bad_slot_type':  "ਸਲਾਟ ਚੁਣਨ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਇੱਕ *ਨੰਬਰ* ਦਰਜ ਕਰੋ।",
            'lang_invalid':   "ਕਿਰਪਾ ਕਰਕੇ ਭਾਸ਼ਾ ਚੁਣਨ ਲਈ 1, 2, 3, 4 ਜਾਂ 5 ਨਾਲ ਜਵਾਬ ਦਿਓ।",
        },
    },
    {
        'lang': 'gu',
        'strings': {
            'lang_ok':        "તમે પસંદ કર્યું: *ગુજરાતી*\n\nચાલો બુકિંગ શરૂ કરીએ.",
            'welcome':        "*{bname} માં આપનું સ્વાગત છે!*\n\nહું મંડી સ્લોટ બુક કરવામાં મદદ કરીશ.\n\nકૃપા કરી તમારું *પૂરું નામ* દાખલ કરો:",
            'ask_village':    "નમસ્તે *{name}*!\n\nકૃપા કરી તમારા *ગામનું નામ* દાખલ કરો:",
            'ask_crop':       "તમારી *પાકનો પ્રકાર* પસંદ કરો:\n\n1. ડાંગર\n2. ઘઉં\n3. મકાઈ\n4. સોયાબીન\n5. કપાસ\n6. અન્ય\n\n*નંબર* અથવા પાકનું નામ મોકલો:",
            'crop_ok':        "પાક: *{crop}*\n\n*જથ્થો* ક્વિન્ટલમાં દાખલ કરો (છોડવા *0* મોકલો):",
            'ask_mandi':      "તમારી *નજીકની મંડી* પસંદ કરો:\n\n{mandi_list}\n\nનંબર સાથે જવાબ આપો:",
            'slots_header':   "*{mandi}* માં ઉપલબ્ધ સ્લોટ:\n\n{slot_list}\n\n*સ્લોટ નંબર* સાથે જવાબ આપો:",
            'no_slots':       "માફ કરશો, *આજ*ના તમામ સ્લોટ ભરાઇ ગયા છે. કૃપા કરી કાલે ફરી પ્રયાસ કરો!",
            'confirmed':      "*બુકિંગ પ્રમાણિત!*\n\nટોકન: *{token}*\nનામ: {name}\nપાક: {crop} ({qty} ક્વિ.)\nમંડી: {mandi}\nસ્થળ: {loc}\nસ્લોટ: {slot}\nતારીખ: {date}\n\nકૃપા કરી *સમયસર* ઉત્પાદન સાથે આવો. આભાર!\n\n_નવી બુકિંગ માટે કોઇ પણ સંદેશ મોકલો._",
            'bad_mandi':      "કૃપા કરી *1* અને *{n}* ની વચ્ચે નંબર દાખલ કરો.",
            'bad_mandi_type': "મંડી પસંદ કરવા *નંબર* દાખલ કરો.",
            'bad_slot':       "કૃપા કરી *1* અને *{n}* ની વચ્ચે નંબર દાખલ કરો.",
            'bad_slot_type':  "સ્લોટ પસંદ કરવા *નંબર* દાખલ કરો.",
            'lang_invalid':   "ભાષા પસંદ કરવા 1, 2, 3, 4 અથવા 5 સાથે જવાબ આપો.",
        },
    },
    {
        'lang': 'mr',
        'strings': {
            'lang_ok':        "तुम्ही निवडले: *मराठी*\n\nचला बुकिंग सुरू करूया.",
            'welcome':        "*{bname} मध्ये आपले स्वागत आहे!*\n\nमी मंडी स्लॉट बुक करण्यात मदत करेन.\n\nकृपया आपले *पूर्ण नाव* प्रविष्ट करा:",
            'ask_village':    "नमस्कार *{name}*!\n\nकृपया आपल्या *गावाचे नाव* प्रविष्ट करा:",
            'ask_crop':       "आपला *पिकाचा प्रकार* निवडा:\n\n1. भात\n2. गहू\n3. मका\n4. सोयाबीन\n5. कापूस\n6. इतर\n\n*क्रमांक* किंवा पिकाचे नाव पाठवा:",
            'crop_ok':        "पीक: *{crop}*\n\n*प्रमाण* क्विंटलमध्ये प्रविष्ट करा (वगळण्यासाठी *0* पाठवा):",
            'ask_mandi':      "आपली *जवळची मंडी* निवडा:\n\n{mandi_list}\n\nक्रमांकाने उत्तर द्या:",
            'slots_header':   "*{mandi}* मध्ये उपलब्ध स्लॉट:\n\n{slot_list}\n\n*स्लॉट क्रमांक* पाठवा:",
            'no_slots':       "दिलगिरी, *आज*चे सर्व स्लॉट भरले आहेत. उद्या पुन्हा प्रयत्न करा!",
            'confirmed':      "*बुकिंग निश्चित झाली!*\n\nटोकन: *{token}*\nनाव: {name}\nपीक: {crop} ({qty} क्विं.)\nमंडी: {mandi}\nपत्ता: {loc}\nस्लॉट: {slot}\nतारीख: {date}\n\nकृपया आपल्या उत्पादनासह *वेळेवर* या. धन्यवाद!\n\n_नवीन बुकिंगसाठी कोणताही संदेश पाठवा._",
            'bad_mandi':      "कृपया *1* आणि *{n}* दरम्यान क्रमांक प्रविष्ट करा.",
            'bad_mandi_type': "मंडी निवडण्यासाठी *क्रमांक* प्रविष्ट करा.",
            'bad_slot':       "कृपया *1* आणि *{n}* दरम्यान क्रमांक प्रविष्ट करा.",
            'bad_slot_type':  "स्लॉट निवडण्यासाठी *क्रमांक* प्रविष्ट करा.",
            'lang_invalid':   "भाषा निवडण्यासाठी 1, 2, 3, 4 किंवा 5 ने उत्तर द्या.",
        },
    },
]

# ===========================================================================
# mandi-crops
# ===========================================================================

MANDI_CROPS = [
    {'lang': 'en', 'crops': {'1': 'Paddy',    '2': 'Wheat',  '3': 'Maize',  '4': 'Soybean', '5': 'Cotton',  '6': 'Other'}},
    {'lang': 'hi', 'crops': {'1': 'धान',      '2': 'गेहूँ', '3': 'मक्का',  '4': 'सोयाबीन', '5': 'कपास',   '6': 'अन्य'}},
    {'lang': 'pa', 'crops': {'1': 'ਝੋਨਾ',     '2': 'ਕਣਕ',  '3': 'ਮੱਕੀ',   '4': 'ਸੋਇਆਬੀਨ','5': 'ਕਪਾਹ',   '6': 'ਹੋਰ'}},
    {'lang': 'gu', 'crops': {'1': 'ડાંગર',    '2': 'ઘઉં',  '3': 'મકાઈ',   '4': 'સોયાબીન', '5': 'કપાસ',   '6': 'અન્ય'}},
    {'lang': 'mr', 'crops': {'1': 'भात',      '2': 'गहू',   '3': 'मका',    '4': 'सोयाबीन', '5': 'कापूस',  '6': 'इतर'}},
]

# ===========================================================================
# mandi-config
# ===========================================================================

MANDI_CONFIG = [
    {
        'key': 'lang_select_msg',
        'value': (
            "Welcome / Swagat / Suagat / Swagat\n\n"
            "Please choose your language / Kripaya bhasha chunein:\n\n"
            "1 - English\n"
            "2 - Hindi\n"
            "3 - Punjabi\n"
            "4 - Gujarati\n"
            "5 - Marathi\n\n"
            "Reply with 1, 2, 3, 4, or 5:"
        ),
    },
    {
        'key': 'supported_langs',
        'value': {
            '1': 'en', '2': 'hi', '3': 'pa', '4': 'gu', '5': 'mr',
            'english': 'en', 'hindi': 'hi',
            'punjabi': 'pa', 'gujarati': 'gu', 'marathi': 'mr',
        },
    },
    {
        'key': 'lang_reset_greetings',
        'value': ['hi', 'hii', 'hiii', 'hello', 'hey', 'namaste', 'namaskar'],
    },
    {
        'key': 'default_slots',
        'value': [
            '9:00 AM - 10:00 AM',
            '10:00 AM - 11:00 AM',
            '11:00 AM - 12:00 PM',
            '12:00 PM - 1:00 PM',
            '2:00 PM - 3:00 PM',
            '3:00 PM - 4:00 PM',
        ],
    },
    {
        'key': 'default_mandis',
        'value': [
            {'name': 'Main Mandi', 'location': 'City Center', 'address': 'Central Market'},
        ],
    },
]

# ===========================================================================
# ai-i18n
# ===========================================================================

AI_I18N = [
    {
        'lang': 'hi',
        'greeting':    "Namaste! Main aapke kisi bhi sawaal mein madad karne ke liye yahan hoon. Bas poochiye!",
        'fallback':    "Maaf kijiye, abhi mere paas is baare mein jaankari nahi hai. Seedha sampark karein.",
        'linksHeader': "*Sambandhit Link:*",
    },
    {
        'lang': 'hi_roman',
        'greeting':    "Namaste! Main aapke kisi bhi sawaal mein madad karne ke liye yahan hoon. Bas poochiye!",
        'fallback':    "Sorry, abhi mere paas is baare mein jaankari nahi hai. Sahi jaankari ke liye seedha sampark karein.",
        'linksHeader': "*Relevant Links:*",
    },
    {
        'lang': 'mr',
        'greeting':    "Namaskar! Mi tumchya konyatyahi prashnansathi yethe aahe. Vicharaa!",
        'fallback':    "Maaf kara, saadhya mazhy akaade tya babat mahiti naahi. Thets sampark saadhaa.",
        'linksHeader': "*Sambandhit Link:*",
    },
    {
        'lang': 'bn',
        'greeting':    "Hello! Ami apnar jekono proshner jonno ekhane achi. Jiggesh korun!",
        'fallback':    "Duhkhit, ekhon amar kache e bishoy tottho nei. Shothik tottho pore seedha sampark korun.",
        'linksHeader': "*Sambondhit Links:*",
    },
    {
        'lang': 'ta',
        'greeting':    "Vanakkam! Naan ungal kelvilukku udava inga irukiren. Kelunga!",
        'fallback':    "Mannikkavum, ippo ennidham adhaRkana vivaragal illai. Neradiyaga thodarbu kollunga.",
        'linksHeader': "*Thodarpudaiya Inaipugal:*",
    },
    {
        'lang': 'te',
        'greeting':    "Namaskaram! Nenu mee emaina prashnalaku sahayam cheyyadaniki ikkade unnanu. Adagandi!",
        'fallback':    "Kshamincandi, ippudu naa dagara aa vishayam gurinchi vivaragalu levu. Nerudunga samprdinchandi.",
        'linksHeader': "*Sambandhita Linkulu:*",
    },
    {
        'lang': 'kn',
        'greeting':    "Namaskara! Nanu nimage sahaya maadalu illi iddene. Keli!",
        'fallback':    "Kshamisi, idara bagge iga nanna bali mahiti illa. Neravagi samparki.",
        'linksHeader': "*Sambandhita Linkgalu:*",
    },
    {
        'lang': 'ml',
        'greeting':    "Namaskaram! Ninglkku sahaychavan ippol inge und. Chodyichu!",
        'fallback':    "Kshamikkuka, ippol ente pakkl adathe kurich vivaragal illa. Neriyai baandhapeduka.",
        'linksHeader': "*Bandhapetta Linkukal:*",
    },
    {
        'lang': 'gu',
        'greeting':    "Namaste! Hu tamara koi pan sawal mate ahiya chhu. Pucho!",
        'fallback':    "Maaf karsho, haju mara pase aa vishe mahiti nathi. Sachu janava IIIT ne seedho sampark karo.",
        'linksHeader': "*Sambandhit Links:*",
    },
    {
        'lang': 'pa',
        'greeting':    "Sat Sri Akal! Main tumhade kise vi sawal vich madad karan layi ithey haan. Puchho!",
        'fallback':    "Maaf karna, hun mere kol is baare jankari nahi hai. Sahi jankari layi seedha sampark karo.",
        'linksHeader': "*Sambandhit Link:*",
    },
    {
        'lang': 'ur',
        'greeting':    "Assalam Alaikum! Main aapke kisi bhi sawal mein madad ke liye yahan hoon. Poochiye!",
        'fallback':    "Maaf kijiye, abhi mere paas is baare mein maloomat nahi hai. Seedha sampark karein.",
        'linksHeader': "*Mutalliqah Link:*",
    },
    {
        'lang': 'en',
        'greeting':    "Hi! I'm here to help you with any questions. Just ask!",
        'fallback':    "Sorry, I don't have details on that right now. Please contact us directly for accurate information.",
        'linksHeader': "*Relevant Links:*",
    },
]

# ===========================================================================
# knowledge-links  (IIIT-NR quick-reference catalogue)
# ===========================================================================

KNOWLEDGE_LINKS = [
    {'keywords': ['dean', 'academic', 'dean academic'],                                'label': 'Dean Academics',                              'url': 'https://www.iiitnr.ac.in/node/3003'},
    {'keywords': ['dean research', 'research', 'innovation', 'dean innovation'],       'label': 'Dean Research & Innovation',                  'url': 'https://www.iiitnr.ac.in/node/1246'},
    {'keywords': ['board', 'board member', 'governing body'],                          'label': 'Board Members',                               'url': 'https://www.iiitnr.ac.in/content/board'},
    {'keywords': ['annual report', 'yearly report', 'annual'],                         'label': 'Yearly Reports',                              'url': 'https://www.iiitnr.ac.in/content/yearly-reports'},
    {'keywords': ['btech curriculum', 'b.tech curriculum', 'ug curriculum'],           'label': 'B.Tech Curriculum',                           'url': 'https://www.iiitnr.ac.in/content/btech-curriculum'},
    {'keywords': ['mtech curriculum', 'm.tech curriculum', 'pg curriculum'],           'label': 'M.Tech Curriculum',                           'url': 'https://www.iiitnr.ac.in/content/mtech-0'},
    {'keywords': ['phd', 'ph.d', 'doctorate', 'doctoral'],                             'label': 'PhD Program',                                 'url': 'https://www.iiitnr.ac.in/content/phd'},
    {'keywords': ['syllabus', 'subject', 'course content'],                            'label': 'Syllabus',                                    'url': 'https://www.iiitnr.ac.in/content/syllabus'},
    {'keywords': ['academic calendar', 'calendar', 'schedule', 'semester date'],       'label': 'Academic Calendar',                           'url': 'https://www.iiitnr.ac.in/content/academic-calendar-archive'},
    {'keywords': ['faculty', 'professor', 'teacher', 'staff', 'lecturer'],             'label': 'Faculty Details',                             'url': 'https://www.iiitnr.ac.in/faculty'},
    {'keywords': ['past faculty', 'former faculty', 'previous faculty'],               'label': 'Past Faculty',                                'url': 'https://www.iiitnr.ac.in/past-faculty'},
    {'keywords': ['adjunct faculty', 'visiting faculty', 'adjunct'],                   'label': 'Adjunct Faculty',                             'url': 'https://www.iiitnr.ac.in/content/adjunct-faculty'},
    {'keywords': ['emeritus', 'emeritus visit'],                                       'label': 'Emeritus Visits',                             'url': 'https://www.iiitnr.ac.in/content/emeritus-visits'},
    {'keywords': ['coe', 'next generation network', 'center of excellence'],           'label': 'CoE Next Generation Network',                 'url': 'https://www.iiitnr.ac.in/content/coe-next-generation-network'},
    {'keywords': ['tbie', 'incubation', 'entrepreneurship', 'startup', 'ecell'],       'label': 'IIIT-NR TBIE / Incubation',                  'url': 'https://sites.google.com/iiitnr.edu.in/iiit-nrtbie'},
    {'keywords': ['patent', 'intellectual property'],                                  'label': 'Patents',                                     'url': 'https://www.iiitnr.ac.in/content/patents'},
    {'keywords': ['lab', 'laboratory', 'lab detail'],                                  'label': 'Lab Details',                                 'url': 'https://www.iiitnr.ac.in/content/lab-details'},
    {'keywords': ['workshop', 'iwatm'],                                                'label': 'Workshops',                                   'url': 'https://www.iiitnr.ac.in/content/iwatm21'},
    {'keywords': ['conference', 'ssnm'],                                               'label': 'Conference',                                  'url': 'https://ims.iiitnr.edu.in/SSNM/'},
    {'keywords': ['ombudsperson', 'complaint', 'grievance'],                           'label': 'Ombudsperson',                                'url': 'https://www.iiitnr.ac.in/content/ombudsperson-contact-details'},
    {'keywords': ['sac', 'student activity', 'student club', 'activity center'],       'label': 'Student Activity Center (SAC)',               'url': 'https://sac.iiitnr.ac.in/'},
    {'keywords': ['ieee', 'ieee student'],                                             'label': 'IEEE Student Branch',                         'url': 'https://ieeesb.iiitnr.ac.in/'},
    {'keywords': ['ecell', 'e-cell', 'entrepreneurship cell'],                         'label': 'E-Cell',                                      'url': 'https://ecell.iiitnr.ac.in/'},
    {'keywords': ['facilit', 'infrastructure', 'campus facilit'],                      'label': 'Facilities',                                  'url': 'https://www.iiitnr.ac.in/content/facilities'},
    {'keywords': ['it facilit', 'it infrastructure', 'internet', 'wifi'],              'label': 'IT Infrastructure',                           'url': 'https://www.iiitnr.ac.in/content/it-infrastructure'},
    {'keywords': ['library', 'book', 'journal', 'reading'],                            'label': 'Library',                                     'url': 'https://www.iiitnr.ac.in/content/library-glance'},
    {'keywords': ['student achievement', 'achievement', 'award'],                      'label': 'Student Achievements',                        'url': 'https://www.iiitnr.ac.in/content/archive-2019'},
    {'keywords': ['anti ragging', 'ragging', 'anti-ragging'],                          'label': 'Anti-Ragging Committee',                      'url': 'https://www.iiitnr.ac.in/content/anti-ragging-committee'},
    {'keywords': ['internship', 'outreach', 'training program', 'summer intern'],      'label': 'Internship / Outreach Program',               'url': 'https://www.iiitnr.ac.in/content/outreach-2025'},
    {'keywords': ['vocational', 'vocational training'],                                'label': 'Vocational Training Programme',               'url': 'https://www.iiitnr.ac.in/content/vocational-training-programme'},
    {'keywords': ['placement statistic', 'placement stat', 'placement data'],          'label': 'Placement Statistics 2021-25',                'url': 'https://www.iiitnr.ac.in/content/placement-statistics-2021-25'},
    {'keywords': ['companies', 'recruiter', 'company visited', 'hiring company'],      'label': 'Companies Visited for Placement',             'url': 'https://www.iiitnr.ac.in/content/companies-visited-2021-25'},
    {'keywords': ['remuneration', 'salary', 'package', 'ctc'],                        'label': 'Remuneration Offered 2021-25',                'url': 'https://www.iiitnr.ac.in/content/remuneration-offered-2021-25'},
    {'keywords': ['industry academia', 'advisory committee'],                          'label': 'Industry-Academia Advisory Committee',        'url': 'https://www.iiitnr.ac.in/content/industry-academia-collaboration-cum-advisory-committee'},
    {'keywords': ['placement', 'training and placement', 'tpo', 'placement cell'],    'label': 'Training & Placement',                        'url': 'https://www.iiitnr.ac.in/content/training-and-placement'},
    {'keywords': ['tender', 'procurement', 'bid'],                                     'label': 'Tenders',                                     'url': 'https://www.iiitnr.ac.in/tenders'},
    {'keywords': ['guest house', 'accommodation', 'stay', 'hostel guest'],             'label': 'Guest House',                                 'url': 'https://www.iiitnr.ac.in/content/guest-house-accommodation'},
    {'keywords': ['btech admission', 'b.tech admission', 'ug admission', 'jee'],       'label': 'B.Tech Admission 2025',                       'url': 'https://www.iiitnr.ac.in/content/b-tech-admission-2025'},
    {'keywords': ['mtech cmit', 'cmit fellowship', 'dsai'],                            'label': 'M.Tech CMIT Fellowship',                      'url': 'https://www.iiitnr.ac.in/content/mtech-dsai-cmit-fellowship'},
    {'keywords': ['mtech admission', 'm.tech admission', 'pg admission', 'gate'],      'label': 'M.Tech Admission 2025',                       'url': 'https://www.iiitnr.ac.in/content/mtech-admission-2025'},
    {'keywords': ['phd admission', 'ph.d admission', 'doctoral admission'],            'label': 'PhD Admission Spring 2026',                   'url': 'https://www.iiitnr.ac.in/content/phd-admission-spring-semester-2026'},
]

# ===========================================================================
# system-config
# ===========================================================================

SYSTEM_CONFIG = [
    {'key': 'initial_credits', 'value': 100},
    {'key': 'plan_prices',     'value': {'starter': 99, 'pro': 499, 'enterprise': 1999}},
]

# ===========================================================================
# templates
# ===========================================================================

TEMPLATES = [
    {
        'id':             'ai-assistant',
        'name':           'AI Assistant',
        'icon':           '🤖',
        'category':       'General',
        'useCases':       ['General Q&A', 'Support', 'Information'],
        'intelligenceMode': 'ai',
        'useCaseType':    'faq',
        'aiModel':        'llama3',
        'aiSystemPrompt': 'You are a helpful and friendly AI assistant. Answer questions clearly and concisely.',
        'aiRagEnabled':   False,
        'welcomeMessage': 'Hello! I am your AI assistant. How can I help you today?',
        'fallbackMessage': 'I am not sure about that. Could you rephrase or provide more details?',
        'keywords':       [],
        'flow': [
            {'label': 'User Message', 'type': 'trigger'},
            {'label': 'AI Processing', 'type': 'ai'},
            {'label': 'Send Reply',    'type': 'action'},
        ],
    },
    {
        'id':             'customer-support',
        'name':           'Customer Support',
        'icon':           '🎧',
        'category':       'Business',
        'useCases':       ['Order Issues', 'Returns', 'FAQ', 'Complaints'],
        'intelligenceMode': 'workflow',
        'useCaseType':    'faq',
        'aiModel':        '',
        'aiSystemPrompt': '',
        'aiRagEnabled':   False,
        'welcomeMessage': 'Welcome to Customer Support! How can we help you today?\n\nType:\n- *order* for order help\n- *return* for returns\n- *complaint* to file a complaint\n- *human* to speak to an agent',
        'fallbackMessage': 'I did not understand that. Please type *order*, *return*, *complaint*, or *human* to continue.',
        'keywords':       [
            {'keyword': 'order',     'response': 'For order issues, please share your order ID and we will look into it right away.'},
            {'keyword': 'return',    'response': 'To initiate a return, share your order ID and reason. Our team will process it within 2-3 business days.'},
            {'keyword': 'complaint', 'response': 'We are sorry to hear that! Please describe your issue and we will escalate it to our team.'},
            {'keyword': 'refund',    'response': 'Refunds are processed within 5-7 business days after approval. Share your order ID to check status.'},
        ],
        'flow': [
            {'label': 'Welcome',          'type': 'message'},
            {'label': 'Customer Input',   'type': 'input'},
            {'label': 'Keyword Match',    'type': 'condition', 'branches': [
                {'label': 'Order',     'next': 'Order Help'},
                {'label': 'Return',    'next': 'Return Process'},
                {'label': 'Human',     'next': 'Human Handoff'},
            ]},
            {'label': 'Send Response',    'type': 'action'},
        ],
    },
    {
        'id':             'lead-generation',
        'name':           'Lead Generation',
        'icon':           '🎯',
        'category':       'Marketing',
        'useCases':       ['Capture Leads', 'Qualify Prospects', 'Schedule Demos'],
        'intelligenceMode': 'workflow',
        'useCaseType':    'leads',
        'aiModel':        '',
        'aiSystemPrompt': '',
        'aiRagEnabled':   False,
        'welcomeMessage': 'Hi! Welcome. I would love to learn more about your needs.\n\nWhat is your name?',
        'fallbackMessage': 'Could you please provide more details so I can assist you better?',
        'keywords':       [
            {'keyword': 'pricing',   'response': 'Our plans start at just Rs 99/month. Want to schedule a free demo?'},
            {'keyword': 'demo',      'response': 'Great! Our team will reach out to schedule a personalised demo. Please share your email.'},
            {'keyword': 'features',  'response': 'We offer WhatsApp automation, AI chatbots, CRM integration and more. Want to see a demo?'},
            {'keyword': 'contact',   'response': 'You can reach our sales team at sales@company.com or call +91-XXXXXXXXXX.'},
        ],
        'flow': [
            {'label': 'Greeting',         'type': 'message'},
            {'label': 'Collect Name',     'type': 'input'},
            {'label': 'Collect Phone',    'type': 'input'},
            {'label': 'Collect Interest', 'type': 'input'},
            {'label': 'Save Lead',        'type': 'action'},
            {'label': 'Thank You',        'type': 'message'},
        ],
    },
    {
        'id':             'appointment-booking',
        'name':           'Appointment Booking',
        'icon':           '📅',
        'category':       'Services',
        'useCases':       ['Doctor Appointments', 'Salon Booking', 'Consultations'],
        'intelligenceMode': 'workflow',
        'useCaseType':    'booking',
        'aiModel':        '',
        'aiSystemPrompt': '',
        'aiRagEnabled':   False,
        'welcomeMessage': 'Welcome! I can help you book an appointment.\n\nWhat service are you looking for?',
        'fallbackMessage': 'Please select a valid option from the menu to continue.',
        'keywords':       [
            {'keyword': 'book',      'response': 'To book an appointment, please tell me your preferred date and time.'},
            {'keyword': 'cancel',    'response': 'To cancel your appointment, please share your booking ID.'},
            {'keyword': 'reschedule','response': 'To reschedule, share your booking ID and preferred new slot.'},
            {'keyword': 'confirm',   'response': 'Your appointment has been noted. You will receive a confirmation shortly.'},
        ],
        'flow': [
            {'label': 'Welcome',          'type': 'message'},
            {'label': 'Select Service',   'type': 'input'},
            {'label': 'Choose Date/Time', 'type': 'input'},
            {'label': 'Collect Contact',  'type': 'input'},
            {'label': 'Confirm Booking',  'type': 'action'},
            {'label': 'Send Confirmation','type': 'message'},
        ],
    },
    {
        'id':             'document-qa',
        'name':           'Document Q&A (RAG)',
        'icon':           '📄',
        'category':       'Knowledge',
        'useCases':       ['Policy Queries', 'Manual Search', 'Research Assistant'],
        'intelligenceMode': 'kb',
        'useCaseType':    'faq',
        'aiModel':        'llama3',
        'aiSystemPrompt': 'You are a document assistant. Answer questions ONLY from the provided documents. Do not use your general knowledge. If the answer is not in the documents, say so clearly.',
        'aiRagEnabled':   True,
        'welcomeMessage': 'Hello! I can answer questions based on your uploaded documents. What would you like to know?',
        'fallbackMessage': 'I could not find relevant information in the documents. Please try rephrasing your question.',
        'keywords':       [],
        'flow': [
            {'label': 'User Query',         'type': 'trigger'},
            {'label': 'Document Retrieval', 'type': 'ai'},
            {'label': 'Generate Answer',    'type': 'ai'},
            {'label': 'Send Response',      'type': 'action'},
        ],
    },
    {
        'id':             'government-helpdesk',
        'name':           'Government Helpdesk',
        'icon':           '🏛️',
        'category':       'Government',
        'useCases':       ['Citizen Services', 'Scheme Information', 'Document Guidance'],
        'intelligenceMode': 'workflow',
        'useCaseType':    'faq',
        'aiModel':        '',
        'aiSystemPrompt': '',
        'aiRagEnabled':   False,
        'welcomeMessage': 'Namaste! Welcome to the Government Helpdesk.\n\nHow can I assist you today?\n\n1. Scheme Information\n2. Document Requirements\n3. Application Status\n4. Contact Office\n\nReply with a number or describe your query.',
        'fallbackMessage': 'I did not understand. Please type your query or choose from the menu options.',
        'keywords':       [
            {'keyword': 'scheme',      'response': 'We have various government schemes. Which scheme are you looking for? (e.g., PM Awas, Jan Dhan, Ayushman Bharat)'},
            {'keyword': 'document',    'response': 'Required documents vary by service. Please specify which service you need documents for.'},
            {'keyword': 'status',      'response': 'To check application status, please provide your application reference number.'},
            {'keyword': 'contact',     'response': 'You can visit the nearest government office or call the helpline at 1800-XXX-XXXX (toll free).'},
        ],
        'flow': [
            {'label': 'Welcome Menu',    'type': 'message'},
            {'label': 'User Selection',  'type': 'input'},
            {'label': 'Route Query',     'type': 'condition'},
            {'label': 'Provide Info',    'type': 'message'},
            {'label': 'Follow-up',       'type': 'input'},
        ],
    },
    {
        'id':             'ecommerce',
        'name':           'E-commerce',
        'icon':           '🛒',
        'category':       'E-commerce',
        'useCases':       ['Product Catalog', 'Order Tracking', 'Cart & Checkout'],
        'intelligenceMode': 'workflow',
        'useCaseType':    'orders',
        'aiModel':        '',
        'aiSystemPrompt': '',
        'aiRagEnabled':   False,
        'welcomeMessage': 'Welcome to our store! How can I help you today?\n\n- *catalog* — browse products\n- *order* — track your order\n- *offer* — latest deals\n- *support* — get help',
        'fallbackMessage': 'I did not catch that. Type *catalog*, *order*, *offer*, or *support* to continue.',
        'keywords':       [
            {'keyword': 'catalog',  'response': 'Here are our top categories: Electronics, Clothing, Home & Kitchen, Beauty. Which one interests you?'},
            {'keyword': 'order',    'response': 'Please share your order ID (e.g., ORD-12345) to track your order.'},
            {'keyword': 'offer',    'response': 'Today\'s deals: Flat 20% off on Electronics, Buy 2 Get 1 on Clothing! Shop now.'},
            {'keyword': 'cart',     'response': 'To view or manage your cart, please visit our app or website.'},
            {'keyword': 'payment',  'response': 'We accept UPI, credit/debit cards, net banking, and cash on delivery.'},
            {'keyword': 'delivery', 'response': 'Standard delivery: 3-5 business days. Express delivery: 1-2 business days (extra charge).'},
        ],
        'flow': [
            {'label': 'Welcome',         'type': 'message'},
            {'label': 'Menu Selection',  'type': 'input'},
            {'label': 'Route Action',    'type': 'condition', 'branches': [
                {'label': 'Browse',  'next': 'Show Catalog'},
                {'label': 'Order',   'next': 'Track Order'},
                {'label': 'Support', 'next': 'Support Flow'},
            ]},
            {'label': 'Respond',         'type': 'action'},
        ],
    },
]


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    print("Seeding BotSetu database...")
    upsert('mandi-i18n',       'lang',  MANDI_I18N)
    upsert('mandi-crops',      'lang',  MANDI_CROPS)
    upsert('mandi-config',     'key',   MANDI_CONFIG)
    upsert('ai-i18n',          'lang',  AI_I18N)
    upsert('knowledge-links',  'label', KNOWLEDGE_LINKS)
    upsert('system-config',    'key',   SYSTEM_CONFIG)
    upsert('templates',        'id',    TEMPLATES)
    print("[OK] Seeding complete.")


if __name__ == '__main__':
    main()
