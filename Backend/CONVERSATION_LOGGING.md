# Conversation Logging System 💬

Complete system for logging and managing all user-bot conversations in BotSetu.

## 📋 Overview

The conversation logging system captures, stores, and manages all WhatsApp bot interactions with customers. It provides:

- **Message Logging** - Store all incoming and outgoing messages
- **Conversation History** - Retrieve full conversation threads
- **Search & Filter** - Find messages by content or metadata
- **Statistics** - Track conversation metrics
- **Read Receipts** - Mark and track read/unread messages

## 🗄️ Database Structure

### Collections

#### 1. `conversations`
Stores individual messages:

```javascript
{
  userId: "clerk_user_id",           // Clerk user ID
  businessId: "business_123",        // Business ID
  phoneNumber: "+1234567890",        // Customer phone number
  messageType: "text",               // text, image, video, audio, document, location
  messageContent: "Hello!",          // Message content or media URL
  sender: "user",                    // user or bot
  metadata: {                        // Optional additional data
    messageId: "SM...",
    accountSid: "AC...",
    mediaContentType: "image/jpeg"
  },
  timestamp: ISODate("2026-02-11"),
  read: false                        // Read status
}
```

#### 2. `User-data` (Updated Fields)
Additional fields added to track conversations:

```javascript
{
  // ... existing fields
  lastConversationAt: ISODate("2026-02-11"),  // Last message timestamp
  totalMessages: 150                          // Total message count
}
```

## 🐍 Python Backend Usage

### Basic Setup

```python
from conversation_logger import ConversationLogger

# Initialize logger for a user/business
logger = ConversationLogger(
    user_id="user_2abc123",
    business_id="business_xyz789"
)
```

### Log a Message

```python
# Log incoming user message
result = logger.log_message(
    phone_number="+1234567890",
    message_type="text",
    message_content="I need help with my order",
    sender="user"
)

# Log outgoing bot response
result = logger.log_message(
    phone_number="+1234567890",
    message_type="text",
    message_content="I'll help you with that!",
    sender="bot"
)
```

### Log Media Messages

```python
# Log image message
logger.log_message(
    phone_number="+1234567890",
    message_type="image",
    message_content="https://media.url/image.jpg",
    sender="user",
    metadata={
        "mediaContentType": "image/jpeg",
        "fileSize": "1024KB"
    }
)
```

### Get Conversation History

```python
# Get last 50 messages with a customer
messages = logger.get_conversation_history(
    phone_number="+1234567890",
    limit=50
)

for msg in messages:
    print(f"[{msg['sender']}] {msg['messageContent']}")
```

### Get All Conversations

```python
# Get all active conversations
conversations = logger.get_all_conversations(limit=50)

for conv in conversations:
    print(f"Phone: {conv['phoneNumber']}")
    print(f"Last: {conv['lastMessage']}")
    print(f"Unread: {conv['unreadCount']}")
```

### Search Conversations

```python
# Search for specific content
results = logger.search_conversations("order status", limit=20)

for msg in results:
    print(f"{msg['phoneNumber']}: {msg['messageContent']}")
```

### Mark Messages as Read

```python
# Mark all messages from a number as read
result = logger.mark_as_read("+1234567890")
print(f"Marked {result['marked_count']} messages as read")
```

### Get Statistics

```python
# Get conversation statistics
stats = logger.get_conversation_stats()

print(f"Total Messages: {stats['totalMessages']}")
print(f"Total Customers: {stats['totalCustomers']}")
print(f"Unread: {stats['unreadMessages']}")
```

### Delete Conversation

```python
# Delete entire conversation
result = logger.delete_conversation("+1234567890")
print(f"Deleted {result['deleted_count']} messages")
```

### Log from WhatsApp Webhook

```python
from conversation_logger import log_webhook_conversation

# Process webhook data
result = log_webhook_conversation(
    user_id="user_2abc123",
    business_id="business_xyz789",
    webhook_data={
        'From': 'whatsapp:+1234567890',
        'Body': 'Hello bot!',
        'MessageSid': 'SMxxx...',
        'AccountSid': 'ACxxx...',
        'NumMedia': '0'
    }
)
```

## 🌐 Frontend API Usage

### Get All Conversations

```typescript
// GET /api/conversations?businessId=xxx
const response = await fetch(
  '/api/conversations?businessId=business_123'
);
const data = await response.json();

console.log(data.conversations);
// [
//   {
//     phoneNumber: "+1234567890",
//     lastMessage: "Thank you!",
//     lastMessageTime: "2026-02-11T...",
//     messageCount: 45,
//     unreadCount: 3
//   }
// ]
```

### Get Specific Conversation

```typescript
// GET /api/conversations?businessId=xxx&phoneNumber=xxx
const response = await fetch(
  '/api/conversations?businessId=business_123&phoneNumber=%2B1234567890'
);
const data = await response.json();

console.log(data.messages);
```

### Log New Message

```typescript
// POST /api/conversations
const response = await fetch('/api/conversations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    businessId: 'business_123',
    phoneNumber: '+1234567890',
    messageType: 'text',
    messageContent: 'Hello from bot!',
    sender: 'bot',
    metadata: {}
  })
});

const data = await response.json();
console.log(data.messageId);
```

### Mark as Read

```typescript
// PATCH /api/conversations
const response = await fetch('/api/conversations', {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    businessId: 'business_123',
    phoneNumber: '+1234567890',
    action: 'mark_read'
  })
});

const data = await response.json();
console.log(`Marked ${data.markedCount} messages as read`);
```

### Delete Conversation

```typescript
// DELETE /api/conversations?businessId=xxx&phoneNumber=xxx
const response = await fetch(
  '/api/conversations?businessId=business_123&phoneNumber=%2B1234567890',
  { method: 'DELETE' }
);

const data = await response.json();
console.log(`Deleted ${data.deletedCount} messages`);
```

## 🚀 Running the CLI Tool

```bash
cd Backend
python conversation_logger.py
```

The CLI provides:
1. Log New Message
2. View Conversation History
3. View All Conversations
4. Search Conversations
5. Mark Conversation as Read
6. Get Conversation Statistics
7. Delete Conversation

## 📊 Use Cases

### Customer Support Dashboard
```python
# Get all unread conversations
conversations = logger.get_all_conversations(limit=100)
unread = [c for c in conversations if c['unreadCount'] > 0]

for conv in unread:
    print(f"🔔 {conv['phoneNumber']} - {conv['unreadCount']} unread")
```

### Analytics & Reporting
```python
# Get conversation metrics
stats = logger.get_conversation_stats()

response_rate = (stats['botMessages'] / stats['userMessages'] * 100)
print(f"Bot Response Rate: {response_rate:.1f}%")
```

### Conversation Export
```python
# Export full conversation
messages = logger.get_conversation_history(
    phone_number="+1234567890",
    limit=1000
)

import json
with open('conversation_export.json', 'w') as f:
    json.dump(messages, f, indent=2, default=str)
```

## 🔐 Security

- All conversations are user-isolated (by `userId` and `businessId`)
- API routes are protected with Clerk authentication
- Phone numbers should be validated before storage
- Sensitive data in metadata should be encrypted

## 🎯 Best Practices

1. **Always log both sides** - Log user messages AND bot responses
2. **Include metadata** - Store message IDs, timestamps, media info
3. **Mark as read** - Update read status when messages are viewed
4. **Regular cleanup** - Archive or delete old conversations
5. **Monitor stats** - Track conversation metrics for insights

## 🔧 Indexing

For optimal performance, create these MongoDB indexes:

```javascript
// In MongoDB shell
db.conversations.createIndex({ userId: 1, businessId: 1, phoneNumber: 1 });
db.conversations.createIndex({ userId: 1, businessId: 1, timestamp: -1 });
db.conversations.createIndex({ userId: 1, businessId: 1, read: 1 });
db.conversations.createIndex({ messageContent: "text" });
```

## 📝 Notes

- Messages are stored indefinitely unless manually deleted
- Media files are stored as URLs (actual files should be in cloud storage)
- Timestamps are in UTC
- Phone numbers should include country code
- The system supports pagination for large datasets

## 🤝 Integration with Other Services

### With Twilio Webhook
```python
# In your webhook handler
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    webhook_data = request.form.to_dict()
    
    # Log incoming message
    log_webhook_conversation(
        user_id=get_user_for_number(webhook_data['From']),
        business_id=get_business_for_number(webhook_data['To']),
        webhook_data=webhook_data
    )
    
    # Process and send response
    bot_response = process_message(webhook_data['Body'])
    
    # Log bot response
    logger.log_message(
        phone_number=webhook_data['From'],
        message_type='text',
        message_content=bot_response,
        sender='bot'
    )
    
    return bot_response
```

---

Built with ❤️ for BotSetu
