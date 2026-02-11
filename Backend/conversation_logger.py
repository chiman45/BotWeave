"""
Conversation Logging Service
Logs and stores all user-bot conversations in MongoDB with user data integration.
"""

from pymongo import MongoClient
from typing import Optional, Dict, List
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['BotSetu']
conversations_collection = db['conversations']
user_data_collection = db['User-data']


class ConversationLogger:
    """Manages conversation logging and retrieval for WhatsApp bot interactions."""
    
    def __init__(self, user_id: str, business_id: str):
        """
        Initialize conversation logger for a specific user and business.
        
        Args:
            user_id: Clerk user ID
            business_id: Business ID
        """
        self.user_id = user_id
        self.business_id = business_id
    
    def log_message(self, phone_number: str, message_type: str, 
                   message_content: str, sender: str, 
                   metadata: Optional[Dict] = None) -> Dict:
        """
        Log a single message in the conversation.
        
        Args:
            phone_number: Customer's WhatsApp phone number
            message_type: Type of message ('text', 'image', 'video', 'audio', 'document', 'location')
            message_content: The actual message content or media URL
            sender: Who sent the message ('user' or 'bot')
            metadata: Optional additional metadata (media info, location coords, etc.)
            
        Returns:
            Dictionary with logged message details
        """
        try:
            message_doc = {
                'userId': self.user_id,
                'businessId': self.business_id,
                'phoneNumber': phone_number,
                'messageType': message_type,
                'messageContent': message_content,
                'sender': sender,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow(),
                'read': False
            }
            
            result = conversations_collection.insert_one(message_doc)
            
            # Update last interaction in User-data
            user_data_collection.update_one(
                {
                    'ownerUserId': self.user_id,
                    'businessId': self.business_id
                },
                {
                    '$set': {
                        'lastConversationAt': datetime.utcnow()
                    },
                    '$inc': {
                        'totalMessages': 1
                    }
                }
            )
            
            return {
                'success': True,
                'message_id': str(result.inserted_id),
                'timestamp': message_doc['timestamp']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_conversation_history(self, phone_number: str, 
                                 limit: int = 100,
                                 skip: int = 0) -> List[Dict]:
        """
        Retrieve conversation history for a specific phone number.
        
        Args:
            phone_number: Customer's WhatsApp phone number
            limit: Maximum number of messages to retrieve
            skip: Number of messages to skip (for pagination)
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = conversations_collection.find(
                {
                    'userId': self.user_id,
                    'businessId': self.business_id,
                    'phoneNumber': phone_number
                },
                {'_id': 0}
            ).sort('timestamp', -1).skip(skip).limit(limit)
            
            return list(messages)
        except Exception as e:
            print(f"Error retrieving conversation: {str(e)}")
            return []
    
    def get_all_conversations(self, limit: int = 50) -> List[Dict]:
        """
        Get all unique conversations (grouped by phone number).
        
        Args:
            limit: Maximum number of conversations to retrieve
            
        Returns:
            List of conversation summaries
        """
        try:
            pipeline = [
                {
                    '$match': {
                        'userId': self.user_id,
                        'businessId': self.business_id
                    }
                },
                {
                    '$sort': {'timestamp': -1}
                },
                {
                    '$group': {
                        '_id': '$phoneNumber',
                        'lastMessage': {'$first': '$messageContent'},
                        'lastMessageTime': {'$first': '$timestamp'},
                        'lastSender': {'$first': '$sender'},
                        'messageCount': {'$sum': 1},
                        'unreadCount': {
                            '$sum': {'$cond': [{'$eq': ['$read', False]}, 1, 0]}
                        }
                    }
                },
                {
                    '$sort': {'lastMessageTime': -1}
                },
                {
                    '$limit': limit
                }
            ]
            
            conversations = list(conversations_collection.aggregate(pipeline))
            
            # Format output
            return [
                {
                    'phoneNumber': conv['_id'],
                    'lastMessage': conv['lastMessage'],
                    'lastMessageTime': conv['lastMessageTime'],
                    'lastSender': conv['lastSender'],
                    'messageCount': conv['messageCount'],
                    'unreadCount': conv['unreadCount']
                }
                for conv in conversations
            ]
        except Exception as e:
            print(f"Error retrieving conversations: {str(e)}")
            return []
    
    def mark_as_read(self, phone_number: str) -> Dict:
        """
        Mark all messages from a phone number as read.
        
        Args:
            phone_number: Customer's WhatsApp phone number
            
        Returns:
            Update result
        """
        try:
            result = conversations_collection.update_many(
                {
                    'userId': self.user_id,
                    'businessId': self.business_id,
                    'phoneNumber': phone_number,
                    'read': False
                },
                {
                    '$set': {'read': True}
                }
            )
            
            return {
                'success': True,
                'marked_count': result.modified_count
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_conversations(self, search_query: str, limit: int = 50) -> List[Dict]:
        """
        Search conversations by message content.
        
        Args:
            search_query: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of matching messages
        """
        try:
            messages = conversations_collection.find(
                {
                    'userId': self.user_id,
                    'businessId': self.business_id,
                    'messageContent': {'$regex': search_query, '$options': 'i'}
                },
                {'_id': 0}
            ).sort('timestamp', -1).limit(limit)
            
            return list(messages)
        except Exception as e:
            print(f"Error searching conversations: {str(e)}")
            return []
    
    def delete_conversation(self, phone_number: str) -> Dict:
        """
        Delete entire conversation with a phone number.
        
        Args:
            phone_number: Customer's WhatsApp phone number
            
        Returns:
            Deletion result
        """
        try:
            result = conversations_collection.delete_many(
                {
                    'userId': self.user_id,
                    'businessId': self.business_id,
                    'phoneNumber': phone_number
                }
            )
            
            return {
                'success': True,
                'deleted_count': result.deleted_count
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_conversation_stats(self) -> Dict:
        """
        Get conversation statistics for the business.
        
        Returns:
            Dictionary with conversation statistics
        """
        try:
            pipeline = [
                {
                    '$match': {
                        'userId': self.user_id,
                        'businessId': self.business_id
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
                return {
                    'totalMessages': stats['totalMessages'],
                    'totalCustomers': len(stats['totalCustomers']),
                    'botMessages': stats['botMessages'],
                    'userMessages': stats['userMessages'],
                    'unreadMessages': stats['unreadMessages']
                }
            else:
                return {
                    'totalMessages': 0,
                    'totalCustomers': 0,
                    'botMessages': 0,
                    'userMessages': 0,
                    'unreadMessages': 0
                }
        except Exception as e:
            print(f"Error getting stats: {str(e)}")
            return {}


def log_webhook_conversation(user_id: str, business_id: str, 
                             webhook_data: Dict) -> Dict:
    """
    Log conversation from WhatsApp webhook data.
    
    Args:
        user_id: Clerk user ID
        business_id: Business ID
        webhook_data: Webhook payload from WhatsApp
        
    Returns:
        Logging result
    """
    try:
        logger = ConversationLogger(user_id, business_id)
        
        # Extract message details from webhook
        from_number = webhook_data.get('From', '')
        message_body = webhook_data.get('Body', '')
        media_url = webhook_data.get('MediaUrl0', '')
        message_type = 'text'
        
        if media_url:
            media_content_type = webhook_data.get('MediaContentType0', '')
            if 'image' in media_content_type:
                message_type = 'image'
            elif 'video' in media_content_type:
                message_type = 'video'
            elif 'audio' in media_content_type:
                message_type = 'audio'
            else:
                message_type = 'document'
            
            message_content = media_url
        else:
            message_content = message_body
        
        metadata = {
            'messageId': webhook_data.get('MessageSid', ''),
            'accountSid': webhook_data.get('AccountSid', ''),
            'mediaContentType': webhook_data.get('MediaContentType0', ''),
            'numMedia': webhook_data.get('NumMedia', '0')
        }
        
        return logger.log_message(
            phone_number=from_number,
            message_type=message_type,
            message_content=message_content,
            sender='user',
            metadata=metadata
        )
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def print_menu():
    """Display the main menu"""
    print("\n" + "="*60)
    print("     CONVERSATION LOGGER SYSTEM")
    print("="*60)
    print("\n📋 MENU OPTIONS:\n")
    print("  1. Log New Message")
    print("  2. View Conversation History")
    print("  3. View All Conversations")
    print("  4. Search Conversations")
    print("  5. Mark Conversation as Read")
    print("  6. Get Conversation Statistics")
    print("  7. Delete Conversation")
    print("  8. Exit")
    print("\n" + "-"*60)


def log_message_menu(logger):
    """Handle logging a new message"""
    print("\n💬 LOG NEW MESSAGE")
    print("-"*60)
    
    phone_number = input("Enter customer phone number (e.g., +1234567890): ").strip()
    message_content = input("Enter message content: ").strip()
    
    print("\nMessage Type:")
    print("  1. Text")
    print("  2. Image")
    print("  3. Video")
    print("  4. Audio")
    print("  5. Document")
    
    type_choice = input("Select type (1-5): ").strip()
    message_types = {'1': 'text', '2': 'image', '3': 'video', '4': 'audio', '5': 'document'}
    message_type = message_types.get(type_choice, 'text')
    
    sender = input("Sender (user/bot) [default: user]: ").strip() or 'user'
    
    if not all([phone_number, message_content]):
        print("❌ Error: Phone number and message content are required!")
        return
    
    try:
        result = logger.log_message(phone_number, message_type, message_content, sender)
        
        if result['success']:
            print("\n✅ Message logged successfully!")
            print(f"  📌 Message ID: {result['message_id']}")
            print(f"  ⏰ Timestamp: {result['timestamp']}")
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def view_history_menu(logger):
    """Handle viewing conversation history"""
    print("\n📜 VIEW CONVERSATION HISTORY")
    print("-"*60)
    
    phone_number = input("Enter customer phone number: ").strip()
    limit = input("Number of messages to show (default: 20): ").strip()
    limit = int(limit) if limit.isdigit() else 20
    
    if not phone_number:
        print("❌ Error: Phone number is required!")
        return
    
    try:
        messages = logger.get_conversation_history(phone_number, limit)
        
        if not messages:
            print(f"\n📭 No conversation found for {phone_number}")
            return
        
        print(f"\n✅ Found {len(messages)} message(s):\n")
        
        for i, msg in enumerate(reversed(messages), 1):
            sender_icon = "🤖" if msg['sender'] == 'bot' else "👤"
            read_status = "✓" if msg.get('read', False) else "○"
            print(f"{i}. {sender_icon} [{msg['sender'].upper()}] {read_status}")
            print(f"   Time: {msg['timestamp']}")
            print(f"   Type: {msg['messageType']}")
            print(f"   Message: {msg['messageContent'][:100]}")
            print()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def view_all_conversations_menu(logger):
    """Handle viewing all conversations"""
    print("\n📊 ALL CONVERSATIONS")
    print("-"*60)
    
    try:
        conversations = logger.get_all_conversations()
        
        if not conversations:
            print("\n📭 No conversations found")
            return
        
        print(f"\n✅ Found {len(conversations)} conversation(s):\n")
        
        for i, conv in enumerate(conversations, 1):
            unread_badge = f" ({conv['unreadCount']} unread)" if conv['unreadCount'] > 0 else ""
            print(f"{i}. {conv['phoneNumber']}{unread_badge}")
            print(f"   Last: [{conv['lastSender']}] {conv['lastMessage'][:50]}")
            print(f"   Time: {conv['lastMessageTime']}")
            print(f"   Total Messages: {conv['messageCount']}")
            print()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def search_conversations_menu(logger):
    """Handle searching conversations"""
    print("\n🔍 SEARCH CONVERSATIONS")
    print("-"*60)
    
    search_query = input("Enter search query: ").strip()
    
    if not search_query:
        print("❌ Error: Search query cannot be empty!")
        return
    
    try:
        results = logger.search_conversations(search_query)
        
        if not results:
            print(f"\n📭 No messages found matching '{search_query}'")
            return
        
        print(f"\n✅ Found {len(results)} matching message(s):\n")
        
        for i, msg in enumerate(results, 1):
            print(f"{i}. From: {msg['phoneNumber']}")
            print(f"   [{msg['sender']}] {msg['messageContent']}")
            print(f"   Time: {msg['timestamp']}")
            print()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def mark_read_menu(logger):
    """Handle marking conversation as read"""
    print("\n✓ MARK AS READ")
    print("-"*60)
    
    phone_number = input("Enter customer phone number: ").strip()
    
    if not phone_number:
        print("❌ Error: Phone number is required!")
        return
    
    try:
        result = logger.mark_as_read(phone_number)
        
        if result['success']:
            print(f"\n✅ Marked {result['marked_count']} message(s) as read")
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def show_stats_menu(logger):
    """Handle showing conversation statistics"""
    print("\n📊 CONVERSATION STATISTICS")
    print("-"*60)
    
    try:
        stats = logger.get_conversation_stats()
        
        print("\n✅ Statistics:\n")
        print(f"  📨 Total Messages: {stats.get('totalMessages', 0)}")
        print(f"  👥 Total Customers: {stats.get('totalCustomers', 0)}")
        print(f"  🤖 Bot Messages: {stats.get('botMessages', 0)}")
        print(f"  👤 User Messages: {stats.get('userMessages', 0)}")
        print(f"  ⭕ Unread Messages: {stats.get('unreadMessages', 0)}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def delete_conversation_menu(logger):
    """Handle deleting a conversation"""
    print("\n🗑️  DELETE CONVERSATION")
    print("-"*60)
    print("⚠️  Warning: This will permanently delete all messages!")
    
    phone_number = input("\nEnter customer phone number: ").strip()
    
    if not phone_number:
        print("❌ Error: Phone number is required!")
        return
    
    confirm = input(f"Are you sure you want to delete conversation with {phone_number}? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Operation cancelled")
        return
    
    try:
        result = logger.delete_conversation(phone_number)
        
        if result['success']:
            print(f"\n✅ Deleted {result['deleted_count']} message(s)")
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def main():
    """Main menu-driven program"""
    print("\n🚀 Initializing Conversation Logger...")
    print("✅ Connected to MongoDB!\n")
    
    user_id = input("Enter User ID (Clerk): ").strip()
    business_id = input("Enter Business ID: ").strip()
    
    if not all([user_id, business_id]):
        print("❌ Error: User ID and Business ID are required!")
        return
    
    logger = ConversationLogger(user_id, business_id)
    print(f"\n✅ Logger initialized for User: {user_id}, Business: {business_id}")
    
    while True:
        print_menu()
        choice = input("Enter your choice (1-8): ").strip()
        
        if choice == '1':
            log_message_menu(logger)
        elif choice == '2':
            view_history_menu(logger)
        elif choice == '3':
            view_all_conversations_menu(logger)
        elif choice == '4':
            search_conversations_menu(logger)
        elif choice == '5':
            mark_read_menu(logger)
        elif choice == '6':
            show_stats_menu(logger)
        elif choice == '7':
            delete_conversation_menu(logger)
        elif choice == '8':
            print("\n👋 Thank you for using Conversation Logger!")
            print("="*60)
            break
        else:
            print("\n❌ Invalid choice! Please select 1-8.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
