# BotSetu Backend - Twilio & WhatsApp Integration

## Quick Start

### Installation
```bash
cd Backend
pip install -r requirements.txt
```

### Configuration
Create/update `.env` file:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
MONGODB_URI=mongodb://localhost:27017/
```

**Where to Find Twilio Credentials:**
1. Log in to [Twilio Console](https://console.twilio.com/)
2. Go to Dashboard
3. Find "Account Info" section
4. Copy your Account SID and Auth Token

## Files

### 1. `creation.py` 🔧
**Purpose:** Create and manage Twilio subaccounts

**Features:**
- Create Twilio subaccounts
- Store credentials in MongoDB
- Link to user accounts (Clerk userId + businessId)
- Manage subaccount lifecycle (suspend, activate, close)

**Interactive Usage:**
```bash
python creation.py
# Interactive menu with options:
# 1. Create New Subaccount
# 2. List All Subaccounts
# 3. Get Subaccount Details
# 4. Update Subaccount Name
# 5. Suspend Subaccount
# 6. Activate Subaccount
# 7. Close Subaccount (Irreversible)
# 8. Exit
```

**Programmatic Usage:**
```python
from creation import TwilioSubaccountManager

# Initialize manager
manager = TwilioSubaccountManager()

# Create subaccount
result = manager.create_subaccount(
    friendly_name="Coffee Shop Bot",
    user_id="user_2abc123xyz",      # Clerk user ID
    business_id="BIZ001"             # Business ID from bot form
)

# Result includes:
# - sid: Subaccount SID (AC...)
# - auth_token: Subaccount auth token
# - status: active/suspended/closed
# - type: Full/Trial
# ✅ Automatically stored in MongoDB
```

**Other Operations:**
```python
# List all subaccounts
subaccounts = manager.list_subaccounts(limit=20)

# Get specific subaccount details
details = manager.get_subaccount('AC...')

# Update subaccount name
updated = manager.update_subaccount('AC...', friendly_name='New Name')

# Suspend subaccount (reversible)
manager.suspend_subaccount('AC...')

# Reactivate suspended subaccount
manager.activate_subaccount('AC...')

# Close subaccount (IRREVERSIBLE - cannot be reopened)
manager.close_subaccount('AC...')
```

### 2. `attach.py` 📱
**Purpose:** Attach WhatsApp numbers to subaccounts

**Features:**
- Attach existing WhatsApp numbers
- Purchase new phone numbers from Twilio
- Enable WhatsApp on numbers
- Update MongoDB with phone details

**Interactive Usage:**
```bash
python attach.py
# Interactive menu with options:
# 1. Attach Existing WhatsApp Number
# 2. Purchase & Attach New Phone Number
# 3. View User's WhatsApp Numbers
# 4. Exit
```

**Programmatic Usage:**
```python
from attach import attach_whatsapp_to_user_account, WhatsAppAttachmentManager

# Option A: Attach existing number
result = attach_whatsapp_to_user_account(
    user_id="user_2abc123xyz",
    business_id="BIZ001",
    phone_number="+14155238886",
    phone_number_sid="PN...",
    messaging_service_sid="MG..."  # Optional
)

# Option B: Purchase new number
from attach import get_subaccount_credentials

# Get credentials first
creds = get_subaccount_credentials(user_id, business_id)

# Initialize manager with subaccount credentials
manager = WhatsAppAttachmentManager(
    creds['twilioAccountSid'],
    creds['twilioAuthToken']
)

# Purchase phone number
number_info = manager.purchase_phone_number(
    country_code='US',
    area_code='415'  # Optional
)

# Enable WhatsApp
whatsapp_info = manager.enable_whatsapp_on_number(
    number_info['phone_number_sid']
)

# Attach to user account
attach_whatsapp_to_user_account(
    user_id, business_id,
    number_info['phone_number'],
    number_info['phone_number_sid']
)
```

### 3. `conversation_logger.py` 💬
**Purpose:** Log and manage all user-bot conversations

**Features:**
- Log all incoming and outgoing messages
- Retrieve conversation history
- Search conversations by content
- Track read/unread messages
- Get conversation statistics
- Support for text, images, videos, audio, documents

**Interactive Usage:**
```bash
python conversation_logger.py
# Interactive menu with options:
# 1. Log New Message
# 2. View Conversation History
# 3. View All Conversations
# 4. Search Conversations
# 5. Mark Conversation as Read
# 6. Get Conversation Statistics
# 7. Delete Conversation
# 8. Exit
```

**Programmatic Usage:**
```python
from conversation_logger import ConversationLogger

# Initialize logger
logger = ConversationLogger(
    user_id="user_2abc123xyz",
    business_id="BIZ001"
)

# Log incoming user message
logger.log_message(
    phone_number="+1234567890",
    message_type="text",
    message_content="Hello bot!",
    sender="user"
)

# Log outgoing bot response
logger.log_message(
    phone_number="+1234567890",
    message_type="text",
    message_content="Hi! How can I help?",
    sender="bot"
)

# Get conversation history
messages = logger.get_conversation_history(
    phone_number="+1234567890",
    limit=50
)

# Get all conversations
conversations = logger.get_all_conversations(limit=20)

# Search messages
results = logger.search_conversations("order status")

# Get statistics
stats = logger.get_conversation_stats()
print(f"Total Messages: {stats['totalMessages']}")
print(f"Unread: {stats['unreadMessages']}")
```

**Webhook Integration:**
```python
from conversation_logger import log_webhook_conversation

# Log from WhatsApp webhook
result = log_webhook_conversation(
    user_id="user_2abc123xyz",
    business_id="BIZ001",
    webhook_data=request.form.to_dict()  # Twilio webhook data
)
```

**📖 See CONVERSATION_LOGGING.md for complete documentation**

### 4. `requirements.txt` 📦
**Dependencies:**
```
twilio>=8.0.0          # Twilio API client
python-dotenv>=1.0.0   # Environment variable management
pymongo>=4.0.0         # MongoDB driver
flask>=3.0.0           # Web framework (optional)
flask-cors>=4.0.0      # CORS support (optional)
```

## Complete Workflow

### Step 1: User Creates Bot (Frontend)
User fills bot creation form in Next.js → Data saved to MongoDB `User-data` collection

### Step 2: Create Twilio Subaccount
```bash
python creation.py
# Choose option 1: Create New Subaccount
# Enter friendly name: "My Coffee Shop - BIZ001"
# Link to user? yes
# Enter User ID: user_2abc123xyz
# Enter Business ID: BIZ001
# ✅ Subaccount created and credentials stored in MongoDB
```

**What happens:**
- Twilio subaccount created
- Credentials stored in `twilio-credentials` collection
- `User-data` collection updated with Twilio SID and auth token

### Step 3: Attach WhatsApp Number
```bash
python attach.py
# Choose option 2: Purchase & Attach New Phone Number
# Enter User ID: user_2abc123xyz
# Enter Business ID: BIZ001
# Enter Country Code: US
# Enter Area Code: 415
# ✅ Number purchased, WhatsApp enabled, stored in MongoDB
```

**What happens:**
- Phone number purchased from Twilio
- WhatsApp enabled on the number
- Phone number details added to both MongoDB collections

### Step 4: Conversations Start Logging Automatically
```python
# In your webhook handler or bot logic
from conversation_logger import ConversationLogger

logger = ConversationLogger(user_id, business_id)

# Every message is logged automatically
logger.log_message(
    phone_number=customer_number,
    message_type="text",
    message_content=message,
    sender="user"  # or "bot"
)
```

**What happens:**
- All messages stored in `conversations` collection
- Last conversation time tracked in `User-data`
- Total message count incremented
- Can retrieve full history anytime

### Step 5: User Views Dashboard (Frontend)
Dashboard automatically shows:
- WhatsApp number
- Connection status
- Message count
- Bot configuration

## MongoDB Collections

### `conversations` Collection
Stores all user-bot conversation messages:
```javascript
{
  userId: "user_2abc123xyz",
  businessId: "BIZ001",
  phoneNumber: "+1234567890",
  messageType: "text",              // text, image, video, audio, document
  messageContent: "Hello bot!",
  sender: "user",                   // user or bot
  metadata: {
    messageId: "SM...",
    accountSid: "AC...",
    mediaContentType: "image/jpeg"
  },
  timestamp: ISODate("2026-02-11T..."),
  read: false
}
```

### `twilio-credentials` Collection
Dedicated collection for Twilio data:
```javascript
{
  userId: "user_2abc123xyz",
  businessId: "BIZ001",
  twilioAccountSid: "AC...",
  twilioAuthToken: "...",
  twilioAccountName: "Coffee Shop Bot",
  twilioAccountStatus: "active",
  twilioAccountType: "Full",
  ownerAccountSid: "AC...",
  whatsappPhoneNumber: "+14155238886",
  whatsappPhoneNumberSid: "PN...",
  messagingServiceSid: "MG...",
  whatsappStatus: "active",
  createdAt: ISODate("2026-02-04T..."),
  updatedAt: ISODate("2026-02-04T...")
}
```

### `User-data` Collection
Bot data with integrated Twilio fields:
```javascript
{
  // Bot creation fields
  ownerUserId: "user_2abc123xyz",
  businessId: "BIZ001",
  businessName: "My Coffee Shop",
  botName: "Coffee Bot",
  // ... other bot fields ...
  
  // Twilio fields (added automatically)
  twilioAccountSid: "AC...",
  twilioAuthToken: "...",
  twilioAccountStatus: "active",
  phoneNumber: "+14155238886",
  phoneNumberSid: "PN...",
  messagingServiceSid: "MG...",
  whatsappStatus: "active",
  whatsappEnabled: true,
  
  // Conversation tracking (added automatically)
  lastConversationAt: ISODate("2026-02-11T..."),
  totalMessages: 150,
  
  updatedAt: ISODate("2026-02-04T...")
}
```

## Twilio Account Information

### Account Types
- **Master Account**: Your main Twilio account (owns all subaccounts)
- **Subaccount**: Child account with own credentials, phone numbers, and usage

### What You Get After Creating Subaccount
- **Subaccount SID** (starts with `AC`) - Unique identifier
- **Auth Token** - Authentication token for API calls
- **Status** - active/suspended/closed
- **Type** - Full or Trial account

### Limitations & Important Notes
- Subaccounts cannot create their own subaccounts
- Each subaccount has separate credentials
- Billing rolls up to master account
- Subaccounts inherit master account pricing
- Closed subaccounts cannot be reopened

### Status Options
- **active**: Subaccount is operational and can make API calls
- **suspended**: Temporarily disabled, can be reactivated
- **closed**: Permanently closed (IRREVERSIBLE)

## Security Best Practices

⚠️ **Critical Security Guidelines:**

1. **Environment Variables**
   - Never commit `.env` to Git
   - Use `.gitignore` to exclude `.env`
   - Store production credentials in secure vaults

2. **Credential Management**
   - Rotate Auth Tokens periodically
   - Use different credentials for dev/staging/production
   - Never log credentials in production

3. **Access Control**
   - Use subaccounts to isolate customer resources
   - Implement proper authentication in API routes
   - Validate user permissions before operations

4. **MongoDB Security**
   - Use strong MongoDB passwords
   - Enable MongoDB authentication
   - Use SSL/TLS for production connections
   - Restrict network access to MongoDB

5. **Monitoring**
   - Monitor API usage in Twilio Console
   - Set up usage alerts
   - Track subaccount creation/deletion
   - Log all administrative actions

## API Rate Limits

Twilio has rate limits on API calls. For production:
- Implement retry logic with exponential backoff
- Cache subaccount information when possible
- Monitor API usage in Twilio Console
- Use webhooks instead of polling where possible

## Integration with Next.js Frontend

See **INTEGRATION_GUIDE.md** for detailed Next.js integration examples including:
- Creating API routes to call Python scripts
- Handling user authentication with Clerk
- Storing and retrieving credentials
- Error handling and user feedback

## Troubleshooting

### Common Errors

**Authentication Error**
```
Error: Authentication failed
```
✅ Solution: Check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in `.env`

**MongoDB Connection Error**
```
Error: Failed to connect to MongoDB
```
✅ Solution: 
- Ensure MongoDB is running: `mongod` or check service status
- Verify MONGODB_URI in `.env`
- Check network/firewall settings

**Insufficient Permissions**
```
Error: Account does not have permission to create subaccounts
```
✅ Solution: Ensure your Twilio account has subaccount creation enabled

**Invalid Status**
```
Error: Invalid status value
```
✅ Solution: Status must be 'active', 'suspended', or 'closed'

**No Credentials Found**
```
Error: No Twilio subaccount found for this user/business
```
✅ Solution: Create a subaccount first using `creation.py` before attaching numbers

## Documentation & Resources

### Project Documentation
- **INTEGRATION_GUIDE.md** - Complete integration guide with code examples
- **README.md** - This file

### Twilio Resources
- [Twilio Subaccounts Documentation](https://www.twilio.com/docs/iam/api/subaccounts)
- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp)
- [Twilio API Reference](https://www.twilio.com/docs/iam/api)
- [Twilio Support](https://support.twilio.com/)

### MongoDB Resources
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

## Support & Help

For issues or questions:

1. Check **INTEGRATION_GUIDE.md** for detailed examples
2. Verify MongoDB is running and accessible
3. Confirm Twilio credentials are correct
4. Ensure all Python dependencies are installed
5. Check Twilio Console for API errors
6. Review MongoDB logs for connection issues

## License

This project is part of BotSetu. All rights reserved.
