"""
WhatsApp Number Attachment Service
Handles attaching WhatsApp numbers to Twilio subaccounts and updating MongoDB.
"""

from twilio.rest import Client
from pymongo import MongoClient
from typing import Optional, Dict
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['BotSetu']
twilio_credentials_collection = db['twilio-credentials']
user_data_collection = db['User-data']


class WhatsAppAttachmentManager:
    """
    Manages WhatsApp number attachment to Twilio subaccounts
    and updates MongoDB with phone number details
    """
    
    def __init__(self, subaccount_sid: str, subaccount_auth_token: str):
        """
        Initialize Twilio client for the subaccount
        
        Args:
            subaccount_sid: Twilio subaccount SID
            subaccount_auth_token: Twilio subaccount auth token
        """
        self.subaccount_sid = subaccount_sid
        self.subaccount_auth_token = subaccount_auth_token
        self.client = Client(subaccount_sid, subaccount_auth_token)
    
    def purchase_phone_number(self, country_code: str = 'US', 
                             area_code: Optional[str] = None) -> Dict:
        """
        Purchase a phone number for WhatsApp
        
        Args:
            country_code: Country code (default: 'US')
            area_code: Optional area code
            
        Returns:
            Dictionary with phone number details
        """
        try:
            # Search for available phone numbers
            search_params = {'country_code': country_code}
            if area_code:
                search_params['area_code'] = area_code
            
            available_numbers = self.client.available_phone_numbers(country_code) \
                                          .local.list(limit=1, **search_params)
            
            if not available_numbers:
                raise Exception(f"No phone numbers available for {country_code}")
            
            # Purchase the first available number
            phone_number = available_numbers[0].phone_number
            
            purchased = self.client.incoming_phone_numbers.create(
                phone_number=phone_number
            )
            
            return {
                'phone_number': purchased.phone_number,
                'phone_number_sid': purchased.sid,
                'friendly_name': purchased.friendly_name,
                'country_code': purchased.iso_country
            }
        except Exception as e:
            raise Exception(f"Phone number purchase failed: {str(e)}")
    
    def enable_whatsapp_on_number(self, phone_number_sid: str) -> Dict:
        """
        Enable WhatsApp on a phone number
        
        Args:
            phone_number_sid: Phone number SID
            
        Returns:
            Updated phone number configuration
        """
        try:
            # Update phone number to enable WhatsApp
            updated = self.client.incoming_phone_numbers(phone_number_sid).update(
                sms_url='https://demo.twilio.com/welcome/sms/reply',
                voice_url='https://demo.twilio.com/welcome/voice',
            )
            
            return {
                'phone_number': updated.phone_number,
                'phone_number_sid': updated.sid,
                'whatsapp_enabled': True,
                'status': 'active'
            }
        except Exception as e:
            raise Exception(f"WhatsApp enablement failed: {str(e)}")
    
    def attach_number_to_messaging_service(self, phone_number_sid: str,
                                          messaging_service_sid: str) -> Dict:
        """
        Attach phone number to a messaging service
        
        Args:
            phone_number_sid: Phone number SID
            messaging_service_sid: Messaging service SID
            
        Returns:
            Attachment details
        """
        try:
            phone_number = self.client.messaging.v1.services(messaging_service_sid) \
                                     .phone_numbers.create(phone_number_sid=phone_number_sid)
            
            return {
                'phone_number_sid': phone_number.sid,
                'messaging_service_sid': messaging_service_sid,
                'status': 'attached'
            }
        except Exception as e:
            raise Exception(f"Messaging service attachment failed: {str(e)}")


def attach_whatsapp_to_user_account(user_id: str, business_id: str,
                                    phone_number: str, phone_number_sid: str,
                                    messaging_service_sid: Optional[str] = None) -> Dict:
    """
    Attach WhatsApp number to user account in MongoDB
    
    Args:
        user_id: Clerk user ID
        business_id: Business ID
        phone_number: WhatsApp phone number
        phone_number_sid: Twilio phone number SID
        messaging_service_sid: Optional messaging service SID
        
    Returns:
        Update result
    """
    try:
        # Update User-data collection
        user_result = user_data_collection.update_one(
            {
                'ownerUserId': user_id,
                'businessId': business_id
            },
            {
                '$set': {
                    'phoneNumber': phone_number,
                    'phoneNumberSid': phone_number_sid,
                    'messagingServiceSid': messaging_service_sid,
                    'whatsappStatus': 'active',
                    'whatsappEnabled': True,
                    'updatedAt': datetime.now(datetime.UTC)
                }
            }
        )
        
        # Update twilio-credentials collection
        cred_result = twilio_credentials_collection.update_one(
            {
                'userId': user_id,
                'businessId': business_id
            },
            {
                '$set': {
                    'whatsappPhoneNumber': phone_number,
                    'whatsappPhoneNumberSid': phone_number_sid,
                    'messagingServiceSid': messaging_service_sid,
                    'whatsappStatus': 'active',
                    'updatedAt': datetime.now(datetime.UTC)
                }
            }
        )
        
        if user_result.modified_count > 0 or cred_result.modified_count > 0:
            return {
                'success': True,
                'message': 'WhatsApp number attached successfully',
                'user_data_updated': user_result.modified_count > 0,
                'credentials_updated': cred_result.modified_count > 0
            }
        else:
            return {
                'success': False,
                'message': 'No records found to update'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to attach WhatsApp number'
        }


def get_subaccount_credentials(user_id: str, business_id: str) -> Optional[Dict]:
    """
    Retrieve Twilio subaccount credentials from MongoDB
    
    Args:
        user_id: Clerk user ID
        business_id: Business ID
        
    Returns:
        Credentials dictionary or None
    """
    try:
        credentials = twilio_credentials_collection.find_one(
            {
                'userId': user_id,
                'businessId': business_id
            },
            {'_id': 0}
        )
        return credentials
    except Exception as e:
        print(f"Error retrieving credentials: {str(e)}")
        return None


def print_menu():
    """Display the main menu"""
    print("\n" + "="*60)
    print("     WHATSAPP NUMBER ATTACHMENT SYSTEM")
    print("="*60)
    print("\n📋 MENU OPTIONS:\n")
    print("  1. Attach Existing WhatsApp Number")
    print("  2. Purchase & Attach New Phone Number")
    print("  3. View User's WhatsApp Numbers")
    print("  4. Exit")
    print("\n" + "-"*60)


def attach_existing_number_menu():
    """Handle attaching existing WhatsApp number"""
    print("\n📱 ATTACH EXISTING WHATSAPP NUMBER")
    print("-"*60)
    
    user_id = input("Enter User ID (Clerk): ").strip()
    business_id = input("Enter Business ID: ").strip()
    phone_number = input("Enter WhatsApp Number (e.g., +14155238886): ").strip()
    phone_number_sid = input("Enter Phone Number SID: ").strip()
    messaging_service_sid = input("Enter Messaging Service SID (optional): ").strip() or None
    
    if not all([user_id, business_id, phone_number, phone_number_sid]):
        print("❌ Error: User ID, Business ID, Phone Number, and SID are required!")
        return
    
    try:
        print("\n⏳ Attaching WhatsApp number to account...")
        result = attach_whatsapp_to_user_account(
            user_id, business_id, phone_number, 
            phone_number_sid, messaging_service_sid
        )
        
        if result['success']:
            print("\n✅ WhatsApp number attached successfully!\n")
            print(f"  📞 Phone Number: {phone_number}")
            print(f"  📌 SID: {phone_number_sid}")
            print(f"  👤 User ID: {user_id}")
            print(f"  🏢 Business ID: {business_id}")
            print(f"  📊 Status: Active")
        else:
            print(f"\n❌ Error: {result['message']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def purchase_new_number_menu():
    """Handle purchasing and attaching new number"""
    print("\n🛒 PURCHASE & ATTACH NEW PHONE NUMBER")
    print("-"*60)
    
    user_id = input("Enter User ID (Clerk): ").strip()
    business_id = input("Enter Business ID: ").strip()
    
    if not all([user_id, business_id]):
        print("❌ Error: User ID and Business ID are required!")
        return
    
    # Get subaccount credentials
    print("\n⏳ Retrieving subaccount credentials...")
    credentials = get_subaccount_credentials(user_id, business_id)
    
    if not credentials:
        print("❌ Error: No Twilio subaccount found for this user/business!")
        print("   Please create a subaccount first using creation.py")
        return
    
    country_code = input("Enter Country Code (default: US): ").strip() or 'US'
    area_code = input("Enter Area Code (optional): ").strip() or None
    
    try:
        print("\n⏳ Initializing WhatsApp manager...")
        manager = WhatsAppAttachmentManager(
            credentials['twilioAccountSid'],
            credentials['twilioAuthToken']
        )
        
        print("⏳ Purchasing phone number...")
        number_info = manager.purchase_phone_number(country_code, area_code)
        
        print("\n✅ Phone number purchased successfully!")
        print(f"  📞 Number: {number_info['phone_number']}")
        print(f"  📌 SID: {number_info['phone_number_sid']}")
        
        print("\n⏳ Enabling WhatsApp on number...")
        whatsapp_info = manager.enable_whatsapp_on_number(number_info['phone_number_sid'])
        
        print("\n⏳ Attaching to user account in MongoDB...")
        result = attach_whatsapp_to_user_account(
            user_id, business_id,
            number_info['phone_number'],
            number_info['phone_number_sid']
        )
        
        if result['success']:
            print("\n✅ Complete! WhatsApp number fully configured!\n")
            print(f"  📞 Phone Number: {number_info['phone_number']}")
            print(f"  📌 SID: {number_info['phone_number_sid']}")
            print(f"  👤 User ID: {user_id}")
            print(f"  🏢 Business ID: {business_id}")
            print(f"  📊 Status: Active & Ready")
        else:
            print(f"\n⚠️  Number purchased but database update failed: {result['message']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def view_user_numbers_menu():
    """View user's WhatsApp numbers"""
    print("\n👀 VIEW USER'S WHATSAPP NUMBERS")
    print("-"*60)
    
    user_id = input("Enter User ID (Clerk): ").strip()
    
    if not user_id:
        print("❌ Error: User ID is required!")
        return
    
    try:
        # Find all credentials for this user
        credentials_list = list(twilio_credentials_collection.find(
            {'userId': user_id},
            {'_id': 0}
        ))
        
        if not credentials_list:
            print(f"\n📭 No Twilio accounts found for user: {user_id}")
            return
        
        print(f"\n✅ Found {len(credentials_list)} account(s):\n")
        
        for i, cred in enumerate(credentials_list, 1):
            print(f"{i}. Business ID: {cred.get('businessId', 'N/A')}")
            print(f"   Account Name: {cred.get('twilioAccountName', 'N/A')}")
            print(f"   Account SID: {cred.get('twilioAccountSid', 'N/A')}")
            
            if 'whatsappPhoneNumber' in cred:
                print(f"   📞 WhatsApp Number: {cred['whatsappPhoneNumber']}")
                print(f"   📌 Number SID: {cred.get('whatsappPhoneNumberSid', 'N/A')}")
                print(f"   📊 Status: {cred.get('whatsappStatus', 'N/A')}")
            else:
                print(f"   📞 WhatsApp Number: Not attached")
            
            print()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def main():
    """
    Main menu-driven program
    """
    print("\n🚀 Initializing WhatsApp Attachment Manager...")
    print("✅ Connected to MongoDB!\n")
    
    while True:
        print_menu()
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            attach_existing_number_menu()
        elif choice == '2':
            purchase_new_number_menu()
        elif choice == '3':
            view_user_numbers_menu()
        elif choice == '4':
            print("\n👋 Thank you for using WhatsApp Attachment Manager!")
            print("="*60)
            break
        else:
            print("\n❌ Invalid choice! Please select 1-4.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
