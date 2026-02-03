# Twilio & WhatsApp Integration Guide

## Overview
Simplified two-file system for managing Twilio subaccounts and WhatsApp numbers with MongoDB integration.

## File Structure

### 1. **creation.py** - Subaccount Creation & Management
- Create Twilio subaccounts
- Store credentials in MongoDB
- Link to user accounts (via Clerk userId)
- Manage subaccount lifecycle (suspend, activate, close)

### 2. **attach.py** - WhatsApp Number Attachment
- Attach existing WhatsApp numbers to subaccounts
- Purchase new phone numbers
- Enable WhatsApp on numbers
- Update MongoDB with phone number details

## MongoDB Collections

### `twilio-credentials` Collection
```javascript
{
  userId: String,              // Clerk user ID
  businessId: String,          // Business ID from bot creation
  twilioAccountSid: String,    // Twilio subaccount SID
  twilioAuthToken: String,     // Twilio auth token
  twilioAccountName: String,   // Friendly name
  twilioAccountStatus: String, // active/suspended/closed
  twilioAccountType: String,   // Trial/Full
  ownerAccountSid: String,     // Parent account SID
  whatsappPhoneNumber: String, // WhatsApp number (optional)
  whatsappPhoneNumberSid: String, // Phone number SID (optional)
  messagingServiceSid: String, // Messaging service SID (optional)
  whatsappStatus: String,      // active/inactive
  createdAt: Date,
  updatedAt: Date
}
```

### `User-data` Collection (WhatsApp Fields)
```javascript
{
  // ... existing bot fields ...
  twilioAccountSid: String,    // Linked Twilio SID
  twilioAuthToken: String,     // Twilio auth token
  twilioAccountStatus: String, // Account status
  phoneNumber: String,         // WhatsApp number
  phoneNumberSid: String,      // Phone number SID
  messagingServiceSid: String, // Messaging service SID
  whatsappStatus: String,      // active/inactive
  whatsappEnabled: Boolean,    // true/false
  // ...
}
```

## Usage

### Step 1: Create Twilio Subaccount

```bash
cd Backend
python creation.py
```

**Interactive Menu:**
```
1. Create New Subaccount
   - Enter friendly name (e.g., "My Coffee Shop - BIZ001")
   - Link to user? yes
   - Enter Clerk User ID (e.g., "user_2abc123xyz")
   - Enter Business ID (e.g., "BIZ001")
   
✅ Result: Subaccount created and stored in MongoDB
```

### Step 2: Attach WhatsApp Number

```bash
python attach.py
```

**Option A - Attach Existing Number:**
```
1. Attach Existing WhatsApp Number
   - Enter User ID: user_2abc123xyz
   - Enter Business ID: BIZ001
   - Enter WhatsApp Number: +14155238886
   - Enter Phone Number SID: PN...
   
✅ Result: Number linked to account in MongoDB
```

**Option B - Purchase New Number:**
```
2. Purchase & Attach New Phone Number
   - Enter User ID: user_2abc123xyz
   - Enter Business ID: BIZ001
   - Enter Country Code: US
   - Enter Area Code (optional): 415
   
✅ Result: Number purchased, WhatsApp enabled, stored in MongoDB
```

## Programmatic Usage

### From Python

```python
# Create subaccount
from creation import TwilioSubaccountManager

manager = TwilioSubaccountManager()
result = manager.create_subaccount(
    friendly_name="Coffee Shop Bot",
    user_id="user_2abc123xyz",
    business_id="BIZ001"
)
# Returns: {'sid': 'AC...', 'auth_token': '...', ...}
```

```python
# Attach WhatsApp number
from attach import attach_whatsapp_to_user_account

result = attach_whatsapp_to_user_account(
    user_id="user_2abc123xyz",
    business_id="BIZ001",
    phone_number="+14155238886",
    phone_number_sid="PN..."
)
# Returns: {'success': True, 'message': '...'}
```

### From Next.js API Routes

Create `Frontend/app/api/twilio/create-subaccount/route.ts`:

```typescript
import { auth } from '@clerk/nextjs/server'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

export async function POST(req: Request) {
  const { userId } = auth()
  if (!userId) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { businessName, businessId } = await req.json()

  try {
    const script = `
from creation import TwilioSubaccountManager
import json
manager = TwilioSubaccountManager()
result = manager.create_subaccount(
    friendly_name="${businessName} - ${businessId}",
    user_id="${userId}",
    business_id="${businessId}"
)
print(json.dumps(result))
`
    const { stdout } = await execAsync(
      `cd ../Backend && python -c "${script.replace(/\n/g, '; ')}"`,
      { shell: 'powershell.exe' }
    )
    
    return Response.json(JSON.parse(stdout))
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 })
  }
}
```

## Complete Workflow

### 1. User Creates Bot (Next.js Frontend)
```typescript
// In app/create/page.tsx
const handleSubmit = async () => {
  // Create bot in MongoDB
  const botResponse = await fetch('/api/bot', {
    method: 'POST',
    body: JSON.stringify(formData)
  })
  
  const { businessId } = await botResponse.json()
  
  // Create Twilio subaccount
  const twilioResponse = await fetch('/api/twilio/create-subaccount', {
    method: 'POST',
    body: JSON.stringify({
      businessName: formData.businessName,
      businessId: businessId
    })
  })
  
  // Credentials automatically stored in MongoDB ✅
}
```

### 2. Admin Attaches WhatsApp Number (Python CLI)
```bash
python attach.py
# Choose option 2 (Purchase & Attach)
# Enter user_id and business_id
# Number purchased and stored ✅
```

### 3. User Views Dashboard
```typescript
// Dashboard automatically shows WhatsApp status
// Data fetched from MongoDB User-data collection
// Shows phone number, status, message count, etc.
```

## Environment Variables

`Backend/.env`:
```env
TWILIO_ACCOUNT_SID=AC4aabcab05afa3219e47288360e6ed3ed
TWILIO_AUTH_TOKEN=f9cd26c1aec186f62d67dd89dcd4269d
MONGODB_URI=mongodb://localhost:27017/
```

## Installation

```bash
cd Backend
pip install -r requirements.txt
```

**Required packages:**
```
twilio>=8.0.0
python-dotenv>=1.0.0
pymongo>=4.0.0
```

## Key Functions

### creation.py
- `create_subaccount(friendly_name, user_id, business_id)` - Create & store subaccount
- `list_subaccounts(limit)` - List all subaccounts
- `get_subaccount(subaccount_sid)` - Get details
- `update_subaccount(sid, name, status)` - Update & sync to MongoDB
- `suspend_subaccount(sid)` - Suspend account
- `activate_subaccount(sid)` - Reactivate account
- `close_subaccount(sid)` - Permanently close

### attach.py
- `attach_whatsapp_to_user_account(user_id, business_id, phone, sid)` - Attach number to DB
- `purchase_phone_number(country, area_code)` - Buy new number
- `enable_whatsapp_on_number(phone_sid)` - Enable WhatsApp
- `get_subaccount_credentials(user_id, business_id)` - Retrieve credentials

## Benefits

✅ **Two Files Only** - Simple, focused architecture  
✅ **Automatic MongoDB Sync** - Credentials stored immediately  
✅ **User Linking** - Tied to Clerk authentication  
✅ **Business Association** - Per-bot credentials  
✅ **Status Management** - Real-time sync with Twilio  
✅ **WhatsApp Ready** - Purchase & attach in one flow  

## Security Notes

- Keep `.env` secure, never commit
- Encrypt auth tokens in production
- Use environment variables
- Implement API authentication
- Validate user permissions before operations

