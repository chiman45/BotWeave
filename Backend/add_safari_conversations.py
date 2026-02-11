"""
Add dummy conversations for Jungle Safari bot to the database.
This script creates realistic safari booking conversations for testing purposes.
"""

import os
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bson import ObjectId
import random

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGODB_URI)
db = client['BotSetu']
conversations_collection = db['conversations']
user_data_collection = db['User-data']

# Bot details from the database
BOT_OBJECT_ID = "6980ff1300473ab63f2d661b"
USER_ID = "user_397tEZICayhXBEAOjUh22IIgbUY"
BUSINESS_ID = "business_1770061587558_4gpp08w1d"
BUSINESS_NAME = "Jungle Safari"
BOT_NAME = "Safari"
PHONE_NUMBER = "8770441755"
CITY = "Bhilai"
COUNTRY = "India"
BUSINESS_HOURS = "9 - 12"

# Sample conversation templates for safari booking
SAFARI_CONVERSATIONS = [
    {
        "phone": "+919876543210",
        "name": "Rahul Kumar",
        "messages": [
            {
                "role": "user",
                "content": "Hi, I want to book a jungle safari for this weekend",
                "timestamp_offset": -30
            },
            {
                "role": "bot",
                "content": f"Hello! Welcome to {BUSINESS_NAME}. I'd be happy to help you book a safari. We have morning (6 AM - 9 AM) and evening (4 PM - 7 PM) slots available. Which would you prefer?",
                "timestamp_offset": -29
            },
            {
                "role": "user",
                "content": "Morning safari sounds great. How many people can join?",
                "timestamp_offset": -28
            },
            {
                "role": "bot",
                "content": "Our safari jeeps can accommodate up to 6 people. How many people will be in your group?",
                "timestamp_offset": -27
            },
            {
                "role": "user",
                "content": "We are 4 people - 2 adults and 2 kids",
                "timestamp_offset": -26
            },
            {
                "role": "bot",
                "content": "Perfect! The pricing is ₹800 per adult and ₹400 per child for the morning safari. Total would be ₹2,400. Would you like to proceed with the booking for this Saturday?",
                "timestamp_offset": -25
            },
            {
                "role": "user",
                "content": "Yes, please book it",
                "timestamp_offset": -24
            },
            {
                "role": "bot",
                "content": "Great! Your safari is booked for Saturday morning (6 AM). Please arrive 15 minutes early. Confirmation details will be sent to your WhatsApp. See you soon! 🦁🌿",
                "timestamp_offset": -23
            }
        ]
    },
    {
        "phone": "+919123456789",
        "name": "Priya Sharma",
        "messages": [
            {
                "role": "user",
                "content": "What animals can we see in the safari?",
                "timestamp_offset": -48
            },
            {
                "role": "bot",
                "content": f"Welcome to {BUSINESS_NAME}! In our safari zone, you can spot deer, peacocks, wild boars, various bird species, and if you're lucky, leopards too! We also have a rich variety of flora.",
                "timestamp_offset": -47
            },
            {
                "role": "user",
                "content": "Wow! Are leopards commonly seen?",
                "timestamp_offset": -46
            },
            {
                "role": "bot",
                "content": "Leopard sightings are more common during early morning safaris, especially in winter months. While we can't guarantee sightings, our experienced guides know the best spots!",
                "timestamp_offset": -45
            },
            {
                "role": "user",
                "content": "Great! When is the best season to visit?",
                "timestamp_offset": -44
            },
            {
                "role": "bot",
                "content": "November to March is ideal - pleasant weather and higher wildlife activity. Summer (April-June) offers better tiger/leopard sightings near water sources. Would you like to book a safari?",
                "timestamp_offset": -43
            },
            {
                "role": "user",
                "content": "I'll check dates and get back. Thanks!",
                "timestamp_offset": -42
            },
            {
                "role": "bot",
                "content": "You're welcome! Feel free to reach out anytime. Happy to help with your booking! 🐆",
                "timestamp_offset": -41
            }
        ]
    },
    {
        "phone": "+918765432109",
        "name": "Amit Patel",
        "messages": [
            {
                "role": "user",
                "content": "Can I bring my camera for photography?",
                "timestamp_offset": -72
            },
            {
                "role": "bot",
                "content": f"Hello! Yes, absolutely! {BUSINESS_NAME} encourages wildlife photography. You can bring cameras, DSLRs, and binoculars. Professional equipment is also allowed.",
                "timestamp_offset": -71
            },
            {
                "role": "user",
                "content": "Is there any extra charge for cameras?",
                "timestamp_offset": -70
            },
            {
                "role": "bot",
                "content": "Personal cameras are free. For professional/commercial shoots, there's a permit fee of ₹2,000. Regular tourist photography has no extra charges!",
                "timestamp_offset": -69
            },
            {
                "role": "user",
                "content": "That's reasonable. Can I book for tomorrow?",
                "timestamp_offset": -68
            },
            {
                "role": "bot",
                "content": "Yes! We have slots available tomorrow. Morning (6 AM) or Evening (4 PM)? And how many people?",
                "timestamp_offset": -67
            },
            {
                "role": "user",
                "content": "Morning slot, just me alone",
                "timestamp_offset": -66
            },
            {
                "role": "bot",
                "content": "Perfect! Booking confirmed for tomorrow morning at 6 AM - 1 adult (₹800). Please carry ID proof. Your booking ID is #JS2024. See you tomorrow! 📸🦌",
                "timestamp_offset": -65
            }
        ]
    },
    {
        "phone": "+917890123456",
        "name": "Neha Verma",
        "messages": [
            {
                "role": "user",
                "content": "Is the safari safe for children?",
                "timestamp_offset": -96
            },
            {
                "role": "bot",
                "content": f"Hello! Yes, {BUSINESS_NAME} is completely safe for children. Our experienced guides ensure safety protocols are followed. Kids 5+ can join with adult supervision.",
                "timestamp_offset": -95
            },
            {
                "role": "user",
                "content": "My kids are 6 and 8 years old. What precautions should I take?",
                "timestamp_offset": -94
            },
            {
                "role": "bot",
                "content": "Perfect age! Please ensure they: 1) Stay seated during safari 2) Keep voices low to not disturb wildlife 3) Follow guide's instructions 4) Wear comfortable clothes & shoes",
                "timestamp_offset": -93
            },
            {
                "role": "user",
                "content": "Should I bring snacks and water?",
                "timestamp_offset": -92
            },
            {
                "role": "bot",
                "content": "Yes, please carry water bottles (essential!). Light snacks are fine but avoid strong-smelling food. We provide basic refreshments at the starting point.",
                "timestamp_offset": -91
            },
            {
                "role": "user",
                "content": "Thanks for the info! I'll book this week",
                "timestamp_offset": -90
            },
            {
                "role": "bot",
                "content": "You're welcome! Your kids will love it! 🦜 Call us when ready to book: 8770441755",
                "timestamp_offset": -89
            }
        ]
    },
    {
        "phone": "+919988776655",
        "name": "Vikram Singh",
        "messages": [
            {
                "role": "user",
                "content": "Do you have group discounts?",
                "timestamp_offset": -120
            },
            {
                "role": "bot",
                "content": f"Welcome to {BUSINESS_NAME}! Yes, we offer group discounts: 10% off for 10+ people, 15% off for 20+ people. Are you planning a group tour?",
                "timestamp_offset": -119
            },
            {
                "role": "user",
                "content": "Yes, we have a corporate team outing - around 25 people",
                "timestamp_offset": -118
            },
            {
                "role": "bot",
                "content": "Excellent! For 25 people, you'll get 15% discount. We can arrange multiple jeeps. Would you prefer morning or evening safari?",
                "timestamp_offset": -117
            },
            {
                "role": "user",
                "content": "Morning on February 20th. What's the total cost?",
                "timestamp_offset": -116
            },
            {
                "role": "bot",
                "content": "For 25 adults: Regular ₹20,000, with 15% discount = ₹17,000 total. We'll need 5 jeeps. Shall I block February 20th morning slot for your team?",
                "timestamp_offset": -115
            },
            {
                "role": "user",
                "content": "Yes please. How much advance payment?",
                "timestamp_offset": -114
            },
            {
                "role": "bot",
                "content": "We need 30% advance (₹5,100) to confirm. Full payment 2 days before. I'll send payment details via WhatsApp. Booking ID: #JS2025GRP",
                "timestamp_offset": -113
            },
            {
                "role": "user",
                "content": "Perfect! Will make the payment today",
                "timestamp_offset": -112
            },
            {
                "role": "bot",
                "content": "Thank you! Looking forward to hosting your team! 🌳🐘",
                "timestamp_offset": -111
            }
        ]
    },
    {
        "phone": "+918877665544",
        "name": "Anjali Desai",
        "messages": [
            {
                "role": "user",
                "content": "What time should we reach for morning safari?",
                "timestamp_offset": -15
            },
            {
                "role": "bot",
                "content": f"Hello! For morning safari (6 AM start), please arrive by 5:45 AM at {BUSINESS_NAME} main gate, Bhilai. This gives time for check-in and safety briefing.",
                "timestamp_offset": -14
            },
            {
                "role": "user",
                "content": "How long does the safari last?",
                "timestamp_offset": -13
            },
            {
                "role": "bot",
                "content": "The safari duration is approximately 3 hours. Morning: 6 AM - 9 AM, Evening: 4 PM - 7 PM. You'll have plenty of time to explore!",
                "timestamp_offset": -12
            },
            {
                "role": "user",
                "content": "Great! Book for 2 adults this Sunday morning",
                "timestamp_offset": -11
            },
            {
                "role": "bot",
                "content": "Booking confirmed! Sunday morning (6 AM) - 2 adults (₹1,600). Booking ID: #JS2026. Please carry ID proof. See you soon! 🦚",
                "timestamp_offset": -10
            }
        ]
    }
]


def create_conversations_for_bot():
    """Create and insert dummy conversations for the Jungle Safari bot"""
    
    print(f"\n{'='*60}")
    print(f"Creating Dummy Conversations for {BUSINESS_NAME}")
    print(f"{'='*60}\n")
    
    # Verify bot exists
    bot = user_data_collection.find_one({"_id": ObjectId(BOT_OBJECT_ID)})
    if not bot:
        print(f"❌ Error: Bot with ID {BOT_OBJECT_ID} not found!")
        return
    
    print(f"✓ Found bot: {bot['businessName']}")
    print(f"✓ Owner User ID: {USER_ID}")
    print(f"✓ Business ID: {BUSINESS_ID}")
    print(f"\nCreating {len(SAFARI_CONVERSATIONS)} conversation threads...\n")
    
    total_messages = 0
    base_time = datetime.utcnow()
    
    for idx, conv_template in enumerate(SAFARI_CONVERSATIONS, 1):
        phone = conv_template["phone"]
        customer_name = conv_template["name"]
        messages = conv_template["messages"]
        
        print(f"\n[{idx}/{len(SAFARI_CONVERSATIONS)}] Creating conversation with {customer_name} ({phone})")
        print(f"     Messages: {len(messages)}")
        
        # Generate unique conversation ID
        conversation_id = f"conv_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}"
        
        # Insert each message
        for msg in messages:
            # Calculate timestamp based on offset (in minutes)
            msg_time = base_time + timedelta(minutes=msg["timestamp_offset"])
            
            message_doc = {
                "conversationId": conversation_id,
                "userId": USER_ID,
                "businessId": BUSINESS_ID,
                "phoneNumber": phone,
                "customerName": customer_name,
                "sender": msg["role"],
                "message": msg["content"],
                "timestamp": msg_time,
                "isRead": random.choice([True, False]),
                "metadata": {
                    "businessName": BUSINESS_NAME,
                    "botName": BOT_NAME,
                    "source": "whatsapp"
                }
            }
            
            conversations_collection.insert_one(message_doc)
            total_messages += 1
        
        print(f"     ✓ Inserted {len(messages)} messages")
        
        # Update bot's last message time and conversation count
        user_data_collection.update_one(
            {"_id": ObjectId(BOT_OBJECT_ID)},
            {
                "$set": {
                    "lastUserMessageTime": base_time.isoformat(),
                    "conversationState": "active"
                },
                "$inc": {
                    "messageBalance": len(messages)
                }
            }
        )
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully created {len(SAFARI_CONVERSATIONS)} conversations")
    print(f"✅ Total messages inserted: {total_messages}")
    print(f"{'='*60}\n")
    
    # Display summary
    print("📊 Summary:")
    for idx, conv in enumerate(SAFARI_CONVERSATIONS, 1):
        print(f"  {idx}. {conv['name']} ({conv['phone']}) - {len(conv['messages'])} messages")
    
    print(f"\n💡 You can now view these chats in the admin panel:")
    print(f"   Dashboard → View Chats → {BUSINESS_NAME}")
    print(f"   Or directly at: /chats/{BUSINESS_ID}\n")


if __name__ == "__main__":
    try:
        create_conversations_for_bot()
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
