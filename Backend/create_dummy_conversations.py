"""
Generate Dummy Conversations for Testing
Creates realistic conversation data for Tribal Museum business
"""

from conversation_logger import ConversationLogger
from datetime import datetime, timedelta
import random
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Find existing Tribal Museum bot
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['BotSetu']
user_data_collection = db['User-data']

# Search for Tribal Museum bot
museum_bot = user_data_collection.find_one({
    'botName': {'$regex': 'Tribal Museum', '$options': 'i'}
})

if not museum_bot:
    print("❌ Tribal Museum bot not found in database!")
    print("Searching for any museum-related bot...")
    museum_bot = user_data_collection.find_one({
        'category': {'$regex': 'museum', '$options': 'i'}
    })

if museum_bot:
    USER_ID = museum_bot.get('ownerUserId', 'unknown')
    BUSINESS_ID = museum_bot.get('businessId', 'unknown')
    print(f"✅ Found bot: {museum_bot.get('botName', 'Unknown')}")
    print(f"   User ID: {USER_ID}")
    print(f"   Business ID: {BUSINESS_ID}")
else:
    print("❌ No museum bot found. Please create one first.")
    exit(1)

# Sample phone numbers
PHONE_NUMBERS = [
    "+14155552001",
    "+14155552002",
    "+14155552003",
    "+14155552004",
    "+14155552005",
]

# Conversation templates for Tribal Museum business
CONVERSATIONS = [
    # Conversation 1: Museum Visit Booking
    [
        ("user", "text", "Hello! I'd like to visit the Tribal Museum. What are your timings?"),
        ("bot", "text", "Welcome to Tribal Museum! 🏛️\n\nOur timings:\n🕐 Tuesday-Sunday: 9 AM - 6 PM\n🚫 Closed: Mondays\n\nLast entry at 5:30 PM\n\nWould you like to book tickets?"),
        ("user", "text", "Yes, how much are the tickets?"),
        ("bot", "text", "Our ticket prices:\n\n👨 Adults: $15\n👦 Children (5-12): $8\n👴 Seniors (60+): $10\n🎓 Students (with ID): $10\n👨‍👩‍👧‍👦 Family Pack (2A+2C): $40\n\nHow many tickets do you need?"),
        ("user", "text", "2 adult tickets for this Saturday"),
        ("bot", "text", "Perfect! 2 Adult tickets for Saturday.\n\n📅 Date: This Saturday\n👥 Guests: 2 Adults\n💰 Total: $30\n\nVisit includes:\n✅ Main Exhibition Hall\n✅ Tribal Art Gallery\n✅ Audio Guide\n✅ Photography allowed\n\nShall I confirm your booking?"),
        ("user", "text", "Yes, please confirm"),
        ("bot", "text", "✅ Booking Confirmed!\n\n🎫 Booking ID: TM-2026-1234\n📅 Date: Saturday\n⏰ Entry: 9 AM - 5:30 PM\n👥 2 Adults\n💰 Amount: $30\n\nPlease show this message at the entrance. See you soon! 🏛️"),
    ],
    
    # Conversation 2: Exhibition Inquiry
    [
        ("user", "text", "Do you have any special exhibitions right now?"),
        ("bot", "text", "Yes! Currently featuring:\n\n🎨 \"Indigenous Art & Crafts\"\nRunning until March 15, 2026\n\nShowcasing:\n- Traditional pottery\n- Handwoven textiles\n- Ancient tribal jewelry\n- Ceremonial masks\n\nFree with regular admission! Would you like to visit?"),
        ("user", "text", "Sounds amazing! Can I take photos?"),
        ("bot", "text", "Yes! 📸 Photography is allowed, but:\n\n✅ Allowed: Personal photos\n❌ No Flash\n❌ No Tripods\n❌ No Commercial use\n\nPerfect for your memories! Ready to book tickets?"),
        ("user", "text", "I'll book online later. Thanks!"),
        ("bot", "text", "You're welcome! Book anytime at www.tribalmuseum.com\n\nHave a great day! 🏛️"),
    ],
    
    # Conversation 3: Group Tour Booking
    [
        ("user", "text", "We're a school group of 45 students. Do you offer group tours?"),
        ("bot", "text", "Absolutely! 🎓 We love hosting school groups!\n\nGroup Tour Benefits:\n👨‍🏫 Dedicated guide\n📚 Educational worksheets\n🎯 Interactive sessions\n💰 Special rates: $6/student\n\nFor 45 students: $270\n(Teachers/Chaperones: Free)\n\nInterested?"),
        ("user", "text", "Yes! What dates are available in March?"),
        ("bot", "text", "March availability:\n📅 Any weekday (Mon-Fri)\n\nPreferred dates:\n- March 5, 12, 19, 26\n- Time slots: 10 AM or 2 PM\n\nWhich date works for you?"),
        ("user", "text", "March 12, 10 AM would be perfect"),
        ("bot", "text", "Excellent! To confirm, I need:\n1. School name\n2. Contact person's name\n3. Email & phone\n4. Student age group\n\nPlease share these details."),
        ("user", "text", "Lincoln High School, Ms. Sarah Johnson, sarah.j@lincolnhs.edu, +1-555-0123, ages 14-16"),
        ("bot", "text", "✅ Group Tour Confirmed!\n\n🏫 School: Lincoln High School\n📅 Date: March 12, 2026\n⏰ Time: 10:00 AM\n👥 45 Students\n👨‍🏫 Guide: Included\n💰 Total: $270\n\nConfirmation sent to sarah.j@lincolnhs.edu\n\nLooking forward to your visit! 🎓"),
    ],
    
    # Conversation 4: Artifacts Order Inquiry
    [
        ("user", "text", "Can I purchase tribal artifacts from the museum?"),
        ("bot", "text", "Yes! Our Gift Shop offers:\n\n🛍️ Authentic Items:\n- Handmade crafts\n- Replica artifacts\n- Books & catalogs\n- Tribal jewelry\n- Traditional clothing\n\n📦 We ship worldwide!\n\nWhat interests you?"),
        ("user", "text", "I'm interested in tribal jewelry"),
        ("bot", "text", "Beautiful choice! 💎\n\nOur jewelry collection:\n1. Beaded necklaces: $45-$120\n2. Silver bracelets: $80-$200\n3. Earrings: $30-$75\n4. Anklets: $40-$90\n\nAll handcrafted by local artisans!\n\nWould you like photos of current stock?"),
        ("user", "text", "Yes please!"),
        ("bot", "image", "https://example.com/museum/necklace_collection.jpg"),
        ("bot", "image", "https://example.com/museum/bracelet_collection.jpg"),
        ("user", "text", "I love the silver bracelet in the second photo!"),
        ("bot", "text", "Excellent taste! That's our:\n\n🌟 \"Tribal Heritage\" Silver Bracelet\n💰 Price: $150\n📏 Adjustable size\n✨ Handcrafted by skilled artisan\n📜 Certificate of authenticity included\n\nReady to order?"),
        ("user", "text", "Yes! How do I pay?"),
        ("bot", "text", "Payment options:\n💳 Credit/Debit card\n📱 PayPal\n🏦 Bank transfer\n\nShipping: $10 (3-5 business days)\n\nTotal: $160\n\nPlease provide:\n1. Name\n2. Shipping address\n3. Email\n\nI'll send payment link!"),
    ],
    
    # Conversation 5: Membership Inquiry
    [
        ("user", "text", "Do you have annual memberships?"),
        ("bot", "text", "Yes! 🎫 Museum Membership Benefits:\n\n🌟 Individual: $50/year\n- Unlimited visits\n- 10% gift shop discount\n- Members-only events\n\n👨‍👩‍👧 Family: $100/year\n- All individual benefits\n- Covers 2 adults + 3 children\n- Free guest passes (2/year)\n\nInterested?"),
        ("user", "text", "Family membership sounds great!"),
        ("bot", "text", "Perfect choice! 👨‍👩‍👧\n\nFamily Membership:\n💰 $100/year\n✅ Unlimited visits for family\n✅ 10% shop discount\n✅ Exclusive events\n✅ 2 guest passes\n✅ Newsletter access\n\nValid for 12 months from signup.\n\nReady to join?"),
        ("user", "text", "Yes, sign me up!"),
        ("bot", "text", "Wonderful! To complete membership:\n1. Primary member name\n2. Email address\n3. Phone number\n4. Number of family members\n\nPlease share these details."),
    ],
    
    # Conversation 6: Cancellation
    [
        ("user", "text", "I need to cancel my booking for tomorrow"),
        ("bot", "text", "I'm sorry to hear that! Could you please share your booking ID or name?"),
        ("user", "text", "Booking ID: TM-2026-5678"),
        ("bot", "text", "Found your booking:\n🎫 ID: TM-2026-5678\n📅 Tomorrow\n👥 3 Adult tickets\n💰 $45\n\nCancellation Policy:\n✅ 24+ hours: Full refund\n⚠️ <24 hours: No refund\n\nYou'll get full refund. Proceed with cancellation?"),
        ("user", "text", "Actually, can I reschedule instead?"),
        ("bot", "text", "Of course! When would you like to visit?\n\nAvailable dates:\n- This weekend\n- Next week (any day)\n- Choose your preferred date"),
        ("user", "text", "Next Sunday please"),
        ("bot", "text", "✅ Rescheduled!\n\n🎫 ID: TM-2026-5678\n📅 New Date: Next Sunday\n👥 3 Adult tickets\n💰 $45 (no extra charge)\n\nConfirmation email sent. See you then! 🏛️"),
    ],
]

def create_dummy_conversations():
    """Generate and insert dummy conversations for testing"""
    
    print("🏛️ Tribal Museum - Dummy Conversation Generator")
    print("=" * 60)
    print(f"User ID: {USER_ID}")
    print(f"Business ID: {BUSINESS_ID}")
    print(f"Generating conversations for {len(PHONE_NUMBERS)} customers...")
    print()
    
    # Initialize conversation logger
    logger = ConversationLogger(USER_ID, BUSINESS_ID)
    
    total_messages = 0
    
    # Create conversations for each phone number
    for idx, (phone, conversation) in enumerate(zip(PHONE_NUMBERS, CONVERSATIONS), 1):
        print(f"\n📱 Customer {idx}: {phone}")
        print("-" * 60)
        
        # Calculate timestamps (conversations spread over last 7 days)
        base_time = datetime.utcnow() - timedelta(days=random.randint(0, 7))
        
        for msg_idx, (sender, msg_type, content) in enumerate(conversation):
            # Add realistic time gaps between messages (1-5 minutes)
            timestamp_offset = timedelta(minutes=msg_idx * random.randint(1, 5))
            message_time = base_time + timestamp_offset
            
            # Create metadata based on message type
            metadata = {
                "messageId": f"SM{random.randint(100000, 999999)}",
                "accountSid": f"AC{random.randint(100000, 999999)}",
            }
            
            if msg_type in ['image', 'video', 'audio', 'document']:
                metadata['mediaContentType'] = f"{msg_type}/jpeg" if msg_type == 'image' else f"{msg_type}/mp4"
            
            # Override timestamp for realistic conversation flow
            from pymongo import MongoClient
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            mongo_client = MongoClient(MONGODB_URI)
            db = mongo_client['BotSetu']
            conversations_collection = db['conversations']
            
            message_doc = {
                'userId': USER_ID,
                'businessId': BUSINESS_ID,
                'phoneNumber': phone,
                'messageType': msg_type,
                'messageContent': content,
                'sender': sender,
                'metadata': metadata,
                'timestamp': message_time,
                'read': random.choice([True, True, False])  # Most messages read
            }
            
            conversations_collection.insert_one(message_doc)
            
            # Print progress
            sender_icon = "🤖" if sender == "bot" else "👤"
            print(f"  {sender_icon} [{sender.upper()}] {content[:60]}{'...' if len(content) > 60 else ''}")
            
            total_messages += 1
        
        print(f"✅ Added {len(conversation)} messages for {phone}")
    
    # Update user data with conversation stats
    from pymongo import MongoClient
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client['BotSetu']
    user_data_collection = db['User-data']
    
    user_data_collection.update_one(
        {
            'ownerUserId': USER_ID,
            'businessId': BUSINESS_ID
        },
        {
            '$set': {
                'lastConversationAt': datetime.utcnow(),
                'totalMessages': total_messages,
                'updatedAt': datetime.utcnow()
            }
        }
    )
    
    print()
    print("=" * 60)
    print(f"✅ Successfully created {total_messages} messages")
    print(f"✅ Across {len(PHONE_NUMBERS)} conversations")
    print(f"✅ For business: Tribal Museum")
    print()
    print("🎯 You can now view these conversations at:")
    print(f"   /chats/{BUSINESS_ID}")
    print()
    print("📊 Stats:")
    stats = logger.get_conversation_stats()
    print(f"   Total Messages: {stats.get('totalMessages', 0)}")
    print(f"   Total Customers: {stats.get('totalCustomers', 0)}")
    print(f"   Bot Messages: {stats.get('botMessages', 0)}")
    print(f"   User Messages: {stats.get('userMessages', 0)}")
    print(f"   Unread Messages: {stats.get('unreadMessages', 0)}")
    print()


if __name__ == "__main__":
    try:
        create_dummy_conversations()
        print("🎉 Done! Check your database and visit the chat logs page.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
