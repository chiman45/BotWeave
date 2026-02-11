"""
Generate Dummy Conversations for Specific Bot
Fetches bot details and creates relevant conversations
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['BotSetu']
user_data_collection = db['User-data']
conversations_collection = db['conversations']

# Target bot ObjectId
BOT_OBJECT_ID = "6980ff1300473ab63f2d661b"

# Sample phone numbers
PHONE_NUMBERS = [
    "+14155552001",
    "+14155552002",
    "+14155552003",
    "+14155552004",
    "+14155552005",
]

# Museum conversation templates
MUSEUM_CONVERSATIONS = [
    # Conversation 1: Ticket Booking
    [
        ("user", "text", "Hi! Are you open today?"),
        ("bot", "text", "Hello! Welcome to Tribal Museum 🏛️\n\nYes, we're open today!\n\nHours:\n🕐 Monday-Friday: 9 AM - 6 PM\n🕐 Saturday-Sunday: 10 AM - 7 PM\n\nWould you like to book tickets?"),
        ("user", "text", "Yes! How much are the tickets?"),
        ("bot", "text", "Our ticket prices:\n\n👨 Adults: $15\n👦 Children (5-12): $8\n👴 Seniors (60+): $10\n👨‍👩‍👧‍👦 Family Pack (2A+2C): $35\n\nHow many tickets do you need?"),
        ("user", "text", "2 adult tickets please"),
        ("bot", "text", "Perfect! 2 Adult tickets = $30\n\nYour visit includes:\n✅ Full museum access\n✅ Guided audio tour\n✅ Tribal artifacts exhibition\n✅ Cultural performance (3 PM daily)\n\nWhich date would you like to visit?"),
        ("user", "text", "This Saturday"),
        ("bot", "text", "Great choice! Saturday visits also include our special pottery demonstration at 2 PM.\n\nTo confirm booking:\n📅 Date: This Saturday\n🎫 2 Adult tickets\n💰 Total: $30\n\nPlease provide your name and email."),
        ("user", "text", "Emily Chen, emily.chen@email.com"),
        ("bot", "text", "✅ Booking Confirmed!\n\n📧 Confirmation sent to emily.chen@email.com\n🎫 E-tickets attached\n\n📍 Address: 123 Heritage Lane\n🅿️ Free parking available\n\nLooking forward to your visit! 🏛️"),
    ],
    
    # Conversation 2: Exhibition Inquiry
    [
        ("user", "text", "What exhibitions do you have right now?"),
        ("bot", "text", "We currently have 3 special exhibitions:\n\n1️⃣ \"Ancient Tribal Arts\" - Traditional crafts & textiles\n2️⃣ \"Warriors & Weapons\" - Historical tribal warfare\n3️⃣ \"Sacred Rituals\" - Spiritual practices & ceremonies\n\nPlus our permanent collection of 500+ artifacts!\n\nWhich interests you most?"),
        ("user", "text", "The Sacred Rituals sounds fascinating!"),
        ("bot", "text", "Excellent choice! 🙏\n\nThe Sacred Rituals exhibition features:\n- Ancient ceremonial masks\n- Ritual instruments & music\n- Spiritual healing practices\n- Interactive multimedia displays\n\nGuided tours available at 11 AM and 3 PM daily.\n\nWould you like to book a visit?"),
        ("user", "text", "Yes, I'll come tomorrow"),
        ("bot", "text", "Wonderful! The Sacred Rituals exhibition is a visitor favorite.\n\nWould you like to join our 11 AM or 3 PM guided tour? The curator leads these personally!"),
    ],
    
    # Conversation 3: Group Tour Request
    [
        ("user", "text", "Do you offer group tours for schools?"),
        ("bot", "text", "Yes! We have special educational programs for schools:\n\n🎓 Student Group Rates:\n- $5 per student\n- 1 teacher free per 10 students\n- Interactive workshops available\n- Curriculum-aligned content\n\nHow many students?"),
        ("user", "text", "We have 30 students, grade 8"),
        ("bot", "text", "Perfect for our \"Tribal Heritage\" program!\n\nFor 30 Grade 8 students:\n💰 $150 (student tickets)\n👨‍🏫 3 teachers free\n📚 Includes workbooks\n⏱️ 2-hour guided tour\n🎨 Hands-on pottery workshop\n\nAvailable dates?"),
        ("user", "text", "Next Tuesday, March 15th"),
        ("bot", "text", "Let me check availability... ✅ Tuesday, March 15th is available!\n\nTime slots:\n🕐 9 AM - 11 AM\n🕐 10 AM - 12 PM\n\nWhich works better for your class?"),
        ("user", "text", "9 AM to 11 AM please"),
        ("bot", "text", "Booked! 📚\n\nTo finalize:\n1. School name\n2. Contact person\n3. Phone number\n4. Email for confirmation\n\nPlease share these details."),
    ],
    
    # Conversation 4: Gift Shop Query
    [
        ("user", "text", "Do you have a gift shop?"),
        ("bot", "text", "Yes! Our Tribal Heritage Gift Shop offers:\n\n🎨 Handcrafted souvenirs\n📚 Books on tribal history\n🖼️ Art prints & postcards\n💍 Traditional jewelry\n🎭 Replica artifacts\n\nAll items support local tribal artisans!\n\nOpen during museum hours. Would you like to see our online catalog?"),
        ("user", "text", "Can I order online?"),
        ("bot", "text", "Currently, gift shop items are available in-person only to ensure authenticity and support our local community.\n\nHowever, you can:\n📧 Email us for specific items\n📞 Call to reserve items\n🚚 Local delivery available (within 10 miles)\n\nInterested in anything specific?"),
    ],
    
    # Conversation 5: Event Information
    [
        ("user", "text", "Do you host events or workshops?"),
        ("bot", "text", "Yes! We host regular cultural events:\n\n📅 Weekly Events:\n- Pottery workshops (Saturdays, 2 PM)\n- Traditional music (Fridays, 4 PM)\n- Storytelling sessions (Sundays, 11 AM)\n\n🎉 Monthly Special Events:\n- Tribal dance performances\n- Craft fairs\n- Cultural festivals\n\nNext big event: Spring Equinox Festival (March 20)\n\nInterested in any?"),
        ("user", "text", "The pottery workshop sounds fun!"),
        ("bot", "text", "Great! Our pottery workshops are very popular! 🏺\n\nDetails:\n🕐 Every Saturday at 2 PM\n⏱️ Duration: 90 minutes\n💰 $25 per person (includes materials)\n👥 Max 12 participants\n🎁 Take home your creation!\n\nThis Saturday has 4 spots left. Would you like to register?"),
        ("user", "text", "Yes! Sign me up"),
        ("bot", "text", "Wonderful! I'll need:\n1. Your name\n2. Phone number\n3. Email address\n\nWe'll send you preparation instructions and parking details."),
    ],
    
    # Conversation 6: Accessibility Question
    [
        ("user", "text", "Is the museum wheelchair accessible?"),
        ("bot", "text", "Yes! The Tribal Museum is fully accessible:\n\n♿ Wheelchair ramps at all entrances\n♿ Elevator to all floors\n♿ Accessible restrooms\n♿ Wheelchair rentals (free)\n♿ Priority seating for shows\n🅿️ Accessible parking spaces\n\nWe also offer:\n👂 Audio descriptions\n🤟 Sign language tours (by request)\n🐕 Service animals welcome\n\nAny specific needs we can help with?"),
        ("user", "text", "That's perfect, thank you!"),
        ("bot", "text", "You're welcome! We're committed to making tribal heritage accessible to everyone. 🏛️\n\nIf you need any special accommodations, please let us know 24 hours in advance.\n\nLooking forward to your visit!"),
    ],
]

def create_conversations_for_bot():
    """Fetch bot details and create conversations"""
    
    print("🏛️ Tribal Museum - Conversation Generator")
    print("=" * 60)
    
    try:
        # Fetch bot details
        bot = user_data_collection.find_one({'_id': ObjectId(BOT_OBJECT_ID)})
        
        if not bot:
            print(f"❌ No bot found with ObjectId: {BOT_OBJECT_ID}")
            return
        
        user_id = bot.get('ownerUserId')
        business_id = bot.get('businessId')
        business_name = bot.get('businessName', 'Unknown')
        bot_name = bot.get('botName', 'Unknown')
        
        print(f"✅ Found Bot:")
        print(f"   Business: {business_name}")
        print(f"   Bot Name: {bot_name}")
        print(f"   User ID: {user_id}")
        print(f"   Business ID: {business_id}")
        print()
        print(f"Generating {len(MUSEUM_CONVERSATIONS)} conversations...")
        print()
        
        total_messages = 0
        
        # Create conversations
        for idx, (phone, conversation) in enumerate(zip(PHONE_NUMBERS, MUSEUM_CONVERSATIONS), 1):
            print(f"\n📱 Customer {idx}: {phone}")
            print("-" * 60)
            
            # Spread conversations over last 7 days
            base_time = datetime.utcnow() - timedelta(days=random.randint(0, 7))
            
            for msg_idx, (sender, msg_type, content) in enumerate(conversation):
                # Add realistic time gaps (1-5 minutes between messages)
                timestamp_offset = timedelta(minutes=msg_idx * random.randint(1, 5))
                message_time = base_time + timestamp_offset
                
                # Create metadata
                metadata = {
                    "messageId": f"SM{random.randint(100000, 999999)}",
                    "accountSid": f"AC{random.randint(100000, 999999)}",
                }
                
                if msg_type in ['image', 'video', 'audio', 'document']:
                    metadata['mediaContentType'] = f"{msg_type}/jpeg" if msg_type == 'image' else f"{msg_type}/mp4"
                
                # Insert message
                message_doc = {
                    'userId': user_id,
                    'businessId': business_id,
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
            
            print(f"✅ Added {len(conversation)} messages")
        
        # Update bot with conversation stats
        user_data_collection.update_one(
            {'_id': ObjectId(BOT_OBJECT_ID)},
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
        print(f"✅ For business: {business_name}")
        print()
        print("🎯 View conversations at:")
        print(f"   /chats/{business_id}")
        print()
        
        # Get stats
        pipeline = [
            {
                '$match': {
                    'userId': user_id,
                    'businessId': business_id
                }
            },
            {
                '$group': {
                    '_id': None,
                    'totalMessages': {'$sum': 1},
                    'totalCustomers': {'$addToSet': '$phoneNumber'},
                    'botMessages': {
                        '$sum': {'$cond': [{'$eq': ['$sender', 'bot']}, 1, 0]}
                    },
                    'userMessages': {
                        '$sum': {'$cond': [{'$eq': ['$sender', 'user']}, 1, 0]}
                    },
                    'unreadMessages': {
                        '$sum': {'$cond': [{'$eq': ['$read', False]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = list(conversations_collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            print("📊 Conversation Stats:")
            print(f"   Total Messages: {stats['totalMessages']}")
            print(f"   Total Customers: {len(stats['totalCustomers'])}")
            print(f"   Bot Messages: {stats['botMessages']}")
            print(f"   User Messages: {stats['userMessages']}")
            print(f"   Unread Messages: {stats['unreadMessages']}")
        
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_conversations_for_bot()
    print("🎉 Done! Check your chat logs page.")
