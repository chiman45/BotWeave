"""
Twilio-MongoDB Integration Service
This service handles Twilio subaccount creation and stores credentials in MongoDB
"""

from twilio.rest import Client
from pymongo import MongoClient
from typing import Optional, Dict, Any
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TwilioMongoDBService:
    """
    Service to create Twilio subaccounts and store credentials in MongoDB
    """
    
    def __init__(self):
        """Initialize Twilio client and MongoDB connection"""
        # Twilio credentials
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        if not self.twilio_account_sid or not self.twilio_auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")
        
        self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        
        # MongoDB connection
        self.mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client['BotSetu']
        self.users_collection = self.db['User-data']
        self.credentials_collection = self.db['Twilio-Credentials']
    
    def create_subaccount_for_user(
        self, 
        user_id: str, 
        business_name: str,
        bot_name: str,
        business_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Twilio subaccount for a user and store credentials in MongoDB
        
        Args:
            user_id: Clerk user ID
            business_name: Name of the business
            bot_name: Name of the bot
            business_id: Optional business ID (will be generated if not provided)
            
        Returns:
            Dictionary containing subaccount details and MongoDB update result
        """
        try:
            # Generate business_id if not provided
            if not business_id:
                business_id = f"business_{datetime.now().timestamp()}_{os.urandom(4).hex()}"
            
            # Create friendly name for Twilio subaccount
            friendly_name = f"{business_name} - {bot_name}"
            
            # Create Twilio subaccount
            print(f"Creating Twilio subaccount: {friendly_name}")
            subaccount = self.twilio_client.api.accounts.create(
                friendly_name=friendly_name
            )
            
            # Prepare credentials data
            twilio_credentials = {
                'user_id': user_id,
                'business_id': business_id,
                'business_name': business_name,
                'bot_name': bot_name,
                'subaccount_sid': subaccount.sid,
                'subaccount_auth_token': subaccount.auth_token,
                'subaccount_friendly_name': subaccount.friendly_name,
                'subaccount_status': subaccount.status,
                'subaccount_type': subaccount.type,
                'owner_account_sid': subaccount.owner_account_sid,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Store credentials in separate collection
            credentials_result = self.credentials_collection.insert_one(twilio_credentials)
            
            # Update user's bot data with Twilio credentials
            update_data = {
                'twilio_subaccount_sid': subaccount.sid,
                'twilio_auth_token': subaccount.auth_token,
                'twilio_status': subaccount.status,
                'twilio_created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            user_update_result = self.users_collection.update_one(
                {
                    'ownerUserId': user_id,
                    'businessId': business_id
                },
                {
                    '$set': update_data
                }
            )
            
            print(f"✅ Subaccount created successfully!")
            print(f"   SID: {subaccount.sid}")
            print(f"   Credentials stored in MongoDB")
            
            return {
                'success': True,
                'subaccount': {
                    'sid': subaccount.sid,
                    'auth_token': subaccount.auth_token,
                    'friendly_name': subaccount.friendly_name,
                    'status': subaccount.status,
                    'type': subaccount.type
                },
                'business_id': business_id,
                'credentials_id': str(credentials_result.inserted_id),
                'user_updated': user_update_result.modified_count > 0
            }
            
        except Exception as e:
            print(f"❌ Error creating subaccount: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_credentials(self, user_id: str, business_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve Twilio credentials for a user
        
        Args:
            user_id: Clerk user ID
            business_id: Optional business ID to filter by specific bot
            
        Returns:
            Dictionary containing credentials or list of credentials
        """
        try:
            query = {'user_id': user_id}
            if business_id:
                query['business_id'] = business_id
                credentials = self.credentials_collection.find_one(query)
                if credentials:
                    credentials['_id'] = str(credentials['_id'])
                return credentials
            else:
                credentials = list(self.credentials_collection.find(query))
                for cred in credentials:
                    cred['_id'] = str(cred['_id'])
                return credentials
                
        except Exception as e:
            print(f"❌ Error fetching credentials: {str(e)}")
            return None
    
    def attach_phone_number_to_subaccount(
        self,
        subaccount_sid: str,
        phone_number: str,
        business_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Attach a WhatsApp phone number to a subaccount and update MongoDB
        
        Args:
            subaccount_sid: Twilio subaccount SID
            phone_number: WhatsApp phone number (E.164 format)
            business_id: Business ID
            user_id: Clerk user ID
            
        Returns:
            Dictionary containing update result
        """
        try:
            # Update MongoDB with phone number information
            phone_update = {
                'whatsapp_phone_number': phone_number,
                'phone_number_attached_at': datetime.utcnow(),
                'phone_number_status': 'active',
                'updated_at': datetime.utcnow()
            }
            
            # Update in User-data collection
            user_result = self.users_collection.update_one(
                {
                    'ownerUserId': user_id,
                    'businessId': business_id
                },
                {
                    '$set': phone_update
                }
            )
            
            # Update in Twilio-Credentials collection
            creds_result = self.credentials_collection.update_one(
                {
                    'user_id': user_id,
                    'business_id': business_id,
                    'subaccount_sid': subaccount_sid
                },
                {
                    '$set': phone_update
                }
            )
            
            print(f"✅ Phone number {phone_number} attached successfully!")
            
            return {
                'success': True,
                'phone_number': phone_number,
                'subaccount_sid': subaccount_sid,
                'user_updated': user_result.modified_count > 0,
                'credentials_updated': creds_result.modified_count > 0
            }
            
        except Exception as e:
            print(f"❌ Error attaching phone number: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_subaccount_status(
        self,
        user_id: str,
        business_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        Update subaccount status in MongoDB
        
        Args:
            user_id: Clerk user ID
            business_id: Business ID
            status: New status (active, suspended, closed)
            
        Returns:
            Dictionary containing update result
        """
        try:
            update_data = {
                'twilio_status': status,
                'status_updated_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Update both collections
            user_result = self.users_collection.update_one(
                {
                    'ownerUserId': user_id,
                    'businessId': business_id
                },
                {
                    '$set': update_data
                }
            )
            
            creds_result = self.credentials_collection.update_one(
                {
                    'user_id': user_id,
                    'business_id': business_id
                },
                {
                    '$set': {
                        'subaccount_status': status,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            print(f"✅ Status updated to {status}")
            
            return {
                'success': True,
                'status': status,
                'user_updated': user_result.modified_count > 0,
                'credentials_updated': creds_result.modified_count > 0
            }
            
        except Exception as e:
            print(f"❌ Error updating status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_all_user_bots_with_credentials(self, user_id: str) -> list:
        """
        Get all bots for a user with their Twilio credentials
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            List of bot documents with credentials
        """
        try:
            bots = list(self.users_collection.find({'ownerUserId': user_id}))
            
            for bot in bots:
                bot['_id'] = str(bot['_id'])
                
                # Fetch associated credentials
                if 'businessId' in bot:
                    credentials = self.credentials_collection.find_one({
                        'user_id': user_id,
                        'business_id': bot['businessId']
                    })
                    if credentials:
                        credentials['_id'] = str(credentials['_id'])
                        bot['twilio_credentials'] = credentials
            
            return bots
            
        except Exception as e:
            print(f"❌ Error fetching bots: {str(e)}")
            return []
    
    def close(self):
        """Close MongoDB connection"""
        self.mongo_client.close()


def main():
    """
    Example usage of the TwilioMongoDBService
    """
    print("\n🚀 Twilio-MongoDB Integration Service")
    print("="*60)
    
    try:
        service = TwilioMongoDBService()
        
        # Example: Create subaccount for a user
        print("\n📝 Example: Creating subaccount for user...")
        result = service.create_subaccount_for_user(
            user_id='user_test123',  # Replace with actual Clerk user ID
            business_name='Test Business',
            bot_name='Customer Support Bot'
        )
        
        if result['success']:
            print(f"\n✅ Success!")
            print(f"   Business ID: {result['business_id']}")
            print(f"   Subaccount SID: {result['subaccount']['sid']}")
            
            # Example: Attach phone number
            if result.get('subaccount'):
                print("\n📞 Attaching phone number...")
                phone_result = service.attach_phone_number_to_subaccount(
                    subaccount_sid=result['subaccount']['sid'],
                    phone_number='+1234567890',  # Replace with actual number
                    business_id=result['business_id'],
                    user_id='user_test123'
                )
                print(f"   Phone attached: {phone_result['success']}")
            
            # Example: Get credentials
            print("\n🔐 Fetching credentials...")
            credentials = service.get_user_credentials(
                user_id='user_test123',
                business_id=result['business_id']
            )
            if credentials:
                print(f"   Found credentials for: {credentials.get('business_name')}")
        else:
            print(f"\n❌ Failed: {result.get('error')}")
        
        service.close()
        print("\n✅ Service closed successfully")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
