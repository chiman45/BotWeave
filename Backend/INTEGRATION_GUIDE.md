# Twilio Subaccount & User Integration Guide

## Overview
The `creation.py` file now integrates Twilio subaccount creation with MongoDB to store credentials linked to user accounts.

## Features

### 1. **Automatic MongoDB Storage**
When creating a Twilio subaccount, credentials are automatically stored in:
- `twilio-credentials` collection (dedicated Twilio data)
- `User-data` collection (linked to bot creation)

### 2. **User Account Linking**
Each Twilio subaccount is linked to:
- **User ID** (Clerk authentication ID)
- **Business ID** (from bot creation form)

## MongoDB Collections

### `twilio-credentials` Collection Schema
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
  createdAt: Date,
  updatedAt: Date
}
```

### `User-data` Collection (Updated Fields)
```javascript
{
  // ... existing fields ...
  twilioAccountSid: String,    // Added
  twilioAuthToken: String,     // Added
  twilioAccountStatus: String, // Added
  whatsappPhoneNumber: String, // Added
  whatsappPhoneNumberSid: String, // Added
  messagingServiceSid: String, // Added
  whatsappStatus: String,      // Added
  // ... other fields ...
}
```

## Usage

### Interactive CLI Usage
```bash
cd Backend
python creation.py
```

**Menu Options:**
1. Create New Subaccount - Now asks for User ID and Business ID
2. List All Subaccounts
3. Get Subaccount Details
4. Update Subaccount Name
5. Suspend Subaccount
6. Activate Subaccount
7. Close Subaccount
8. Exit

### Programmatic Usage from Next.js

#### Option 1: Direct Import (Python Backend)
```python
from creation import TwilioSubaccountManager

manager = TwilioSubaccountManager()

# Create subaccount with user linking
result = manager.create_subaccount(
    friendly_name="My Coffee Shop - BIZ001",
    user_id="user_2abc123xyz",  # Clerk user ID
    business_id="BIZ001"         # From bot creation form
)
```

#### Option 2: Use Helper Functions
```python
from twilio_user_integration import create_twilio_subaccount_for_user

result = create_twilio_subaccount_for_user(
    user_id="user_2abc123xyz",
    business_name="My Coffee Shop",
    business_id="BIZ001"
)

# Returns:
# {
#   'success': True,
#   'twilioAccountSid': 'AC...',
#   'twilioAuthToken': 'xxxx',
#   'twilioAccountStatus': 'active',
#   'message': 'Twilio subaccount created successfully'
# }
```

## Integration with Next.js Bot Creation

### Step 1: Create API Route (Recommended)
Create `Frontend/app/api/twilio/create-subaccount/route.ts`:

```typescript
import { auth } from '@clerk/nextjs/server'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

export async function POST(req: Request) {
  const { userId } = auth()
  
  if (!userId) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { businessName, businessId } = await req.json()

  try {
    // Call Python script
    const pythonScript = `
from twilio_user_integration import create_twilio_subaccount_for_user
import json

result = create_twilio_subaccount_for_user(
    user_id="${userId}",
    business_name="${businessName}",
    business_id="${businessId}"
)
print(json.dumps(result))
`
    
    const { stdout } = await execAsync(
      `cd ../Backend && python -c "${pythonScript}"`,
      { shell: 'powershell.exe' }
    )
    
    const result = JSON.parse(stdout)
    
    return Response.json(result)
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 })
  }
}
```

### Step 2: Call from Bot Creation Form
In `Frontend/app/create/page.tsx`, after creating bot:

```typescript
const handleSubmit = async () => {
  // ... existing bot creation code ...
  
  // Create Twilio subaccount
  const twilioResponse = await fetch('/api/twilio/create-subaccount', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      businessName: formData.businessName,
      businessId: businessId
    })
  })
  
  const twilioResult = await twilioResponse.json()
  
  if (twilioResult.success) {
    console.log('Twilio credentials:', twilioResult)
    // Credentials are already stored in MongoDB
  }
}
```

## Helper Functions Available

### 1. Create Subaccount
```python
create_twilio_subaccount_for_user(user_id, business_name, business_id)
```

### 2. Get User Credentials
```python
get_user_twilio_credentials(user_id, business_id=None)
```

### 3. Update WhatsApp Number
```python
update_whatsapp_number_in_db(
    user_id, 
    business_id, 
    phone_number, 
    phone_number_sid,
    messaging_service_sid=None
)
```

### 4. List User Subaccounts
```python
list_user_subaccounts(user_id)
```

## Environment Variables

Update `Backend/.env`:
```env
# Twilio API Credentials
TWILIO_ACCOUNT_SID=AC4aabcab05afa3219e47288360e6ed3ed
TWILIO_AUTH_TOKEN=f9cd26c1aec186f62d67dd89dcd4269d

# MongoDB Connection
MONGODB_URI=mongodb://localhost:27017/
```

## Installation

```bash
cd Backend
pip install -r requirements.txt
```

Required packages:
- `twilio>=8.0.0`
- `python-dotenv>=1.0.0`
- `pymongo>=4.0.0`

## Workflow Example

1. **User creates bot** in Next.js form
2. **Bot data saved** to `User-data` collection
3. **Twilio subaccount created** via `creation.py`
4. **Credentials stored** in both collections with `userId` and `businessId`
5. **User can access** Twilio credentials from dashboard

## Benefits

✅ **Automatic Storage** - Credentials stored immediately after creation  
✅ **User Linking** - Each subaccount tied to specific user  
✅ **Business Association** - Linked to bot/business ID  
✅ **Status Sync** - MongoDB updated when Twilio status changes  
✅ **Easy Retrieval** - Query credentials by userId or businessId  

## Security Notes

- Store `.env` securely, never commit to Git
- Twilio auth tokens are sensitive - encrypt in production
- Use environment variables for MongoDB URI
- Implement proper authentication in API routes
