# Twilio Subaccount Management

## Requirements to Create Twilio Subaccounts

### 1. **Main Account Credentials** (Required)
- **Account SID** (starts with `AC`) - Your master account identifier
- **Auth Token** - Secret authentication token for your master account

### 2. **Where to Find Credentials**
1. Log in to [Twilio Console](https://console.twilio.com/)
2. Go to Dashboard
3. Find "Account Info" section
4. Copy your Account SID and Auth Token

### 3. **What You Need to Provide When Creating Subaccount**
- **Friendly Name** - A descriptive name for the subaccount (e.g., "Customer XYZ Account")

### 4. **What You Get After Creating Subaccount**
- **Subaccount SID** - Unique identifier for the subaccount
- **Subaccount Auth Token** - Authentication token for the subaccount
- **Status** - Account status (active, suspended, closed)
- **Type** - Account type (Full or Trial)

## Setup Instructions

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   ```

### Step 3: Run the Script
```bash
python creation.py
```

## Usage Examples

### Basic Usage
```python
from creation import TwilioSubaccountManager

# Initialize manager
manager = TwilioSubaccountManager()

# Create a subaccount
subaccount = manager.create_subaccount("My New Subaccount")
print(f"Created: {subaccount['sid']}")
```

### Bot Integration Example
```python
# For chatbot/automated systems
def handle_create_subaccount_request(user_input):
    manager = TwilioSubaccountManager()
    
    # Extract name from user input
    account_name = user_input.get('account_name', 'Default Bot Account')
    
    # Create subaccount
    result = manager.create_subaccount(account_name)
    
    # Return formatted response
    return {
        'success': True,
        'message': f"Subaccount '{account_name}' created successfully",
        'sid': result['sid'],
        'auth_token': result['auth_token']
    }
```

### List Subaccounts
```python
manager = TwilioSubaccountManager()
subaccounts = manager.list_subaccounts()

for account in subaccounts:
    print(f"{account['friendly_name']}: {account['sid']}")
```

### Manage Subaccounts
```python
manager = TwilioSubaccountManager()

# Suspend a subaccount
manager.suspend_subaccount('AC...')

# Reactivate a subaccount
manager.activate_subaccount('AC...')

# Close a subaccount (IRREVERSIBLE)
manager.close_subaccount('AC...')
```

## Important Notes

### Account Types
- **Master Account**: Your main Twilio account that owns all subaccounts
- **Subaccount**: Child account that can have its own phone numbers, API credentials, and usage

### Limitations
- Subaccounts cannot create their own subaccounts
- Each subaccount has its own SID and Auth Token
- Billing rolls up to the master account
- Subaccounts inherit the master account's pricing

### Security Best Practices
1. Never commit `.env` file to version control
2. Store credentials securely (use environment variables)
3. Rotate Auth Tokens periodically
4. Use subaccounts to isolate customer/project resources
5. Monitor subaccount usage through Twilio Console

### Status Options
- **active**: Subaccount is operational
- **suspended**: Temporarily disabled (can be reactivated)
- **closed**: Permanently closed (cannot be reopened)

## API Rate Limits
Twilio has rate limits on API calls. For production bots:
- Implement retry logic with exponential backoff
- Cache subaccount information when possible
- Monitor your API usage in Twilio Console

## Troubleshooting

### Common Errors
1. **Authentication Error**: Check your Account SID and Auth Token
2. **Insufficient Permissions**: Ensure your account has permission to create subaccounts
3. **Invalid Status**: Status must be 'active', 'suspended', or 'closed'

### Need Help?
- [Twilio Subaccounts Documentation](https://www.twilio.com/docs/iam/api/subaccounts)
- [Twilio API Reference](https://www.twilio.com/docs/iam/api)
- [Twilio Support](https://support.twilio.com/)
