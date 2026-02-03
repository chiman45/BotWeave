"""
Helper functions to integrate Twilio subaccount creation with user bot creation
This module can be called from the Next.js backend API routes
"""

from creation import TwilioSubaccountManager
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['BotSetu']


def create_twilio_subaccount_for_user(user_id: str, business_name: str, business_id: str) -> dict:
    """
    Create a Twilio subaccount for a user when they create a bot
    
    Args:
        user_id: Clerk user ID
        business_name: Business name from the bot creation form
        business_id: Generated business ID
        
    Returns:
        Dictionary with Twilio credentials and status
    """
    try:
        # Initialize Twilio manager
        manager = TwilioSubaccountManager()
        
        # Create friendly name combining business name and timestamp
        friendly_name = f"{business_name} - {business_id}"
        
        # Create subaccount and store in MongoDB
        subaccount = manager.create_subaccount(
            friendly_name=friendly_name,
            user_id=user_id,
            business_id=business_id
        )
        
        return {
            'success': True,
            'twilioAccountSid': subaccount['sid'],
            'twilioAuthToken': subaccount['auth_token'],
            'twilioAccountStatus': subaccount['status'],
            'message': 'Twilio subaccount created successfully'
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create Twilio subaccount'
        }


def get_user_twilio_credentials(user_id: str, business_id: str = None) -> dict:
    """
    Retrieve Twilio credentials for a user's bot
    
    Args:
        user_id: Clerk user ID
        business_id: Optional business ID to filter
        
    Returns:
        Dictionary with Twilio credentials or error
    """
    try:
        query = {'userId': user_id}
        if business_id:
            query['businessId'] = business_id
        
        credentials = db['twilio-credentials'].find_one(query, {'_id': 0})
        
        if credentials:
            return {
                'success': True,
                'credentials': credentials
            }
        else:
            return {
                'success': False,
                'message': 'No Twilio credentials found for this user'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve Twilio credentials'
        }


def update_whatsapp_number_in_db(user_id: str, business_id: str, phone_number: str, 
                                  phone_number_sid: str, messaging_service_sid: str = None) -> dict:
    """
    Update WhatsApp phone number details in MongoDB
    
    Args:
        user_id: Clerk user ID
        business_id: Business ID
        phone_number: WhatsApp phone number (e.g., +1234567890)
        phone_number_sid: Twilio Phone Number SID
        messaging_service_sid: Optional Messaging Service SID
        
    Returns:
        Dictionary with success status
    """
    try:
        # Update User-data collection
        result = db['User-data'].update_one(
            {
                'ownerUserId': user_id,
                'businessId': business_id
            },
            {
                '$set': {
                    'whatsappPhoneNumber': phone_number,
                    'whatsappPhoneNumberSid': phone_number_sid,
                    'messagingServiceSid': messaging_service_sid,
                    'whatsappStatus': 'active',
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        # Also update twilio-credentials collection
        db['twilio-credentials'].update_one(
            {
                'userId': user_id,
                'businessId': business_id
            },
            {
                '$set': {
                    'whatsappPhoneNumber': phone_number,
                    'whatsappPhoneNumberSid': phone_number_sid,
                    'messagingServiceSid': messaging_service_sid,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            return {
                'success': True,
                'message': 'WhatsApp number updated successfully'
            }
        else:
            return {
                'success': False,
                'message': 'No matching record found to update'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to update WhatsApp number'
        }


def list_user_subaccounts(user_id: str) -> dict:
    """
    List all Twilio subaccounts for a specific user
    
    Args:
        user_id: Clerk user ID
        
    Returns:
        Dictionary with list of subaccounts
    """
    try:
        credentials_list = list(db['twilio-credentials'].find(
            {'userId': user_id},
            {'_id': 0}
        ))
        
        return {
            'success': True,
            'count': len(credentials_list),
            'subaccounts': credentials_list
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve subaccounts'
        }


if __name__ == "__main__":
    # Example usage
    print("\n🧪 Twilio User Integration Test\n")
    
    # Test creating subaccount
    test_user_id = "user_test123"
    test_business_name = "Test Coffee Shop"
    test_business_id = "BIZ-001"
    
    print("Creating Twilio subaccount...")
    result = create_twilio_subaccount_for_user(test_user_id, test_business_name, test_business_id)
    print(result)
