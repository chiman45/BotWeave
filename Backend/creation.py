"""
Twilio Subaccount Creation and Management Bot
This module handles creating and managing Twilio subaccounts via API
"""

from twilio.rest import Client
from typing import Optional, Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TwilioSubaccountManager:
    """
    Manages Twilio subaccount creation and operations
    
    Required credentials:
    - TWILIO_ACCOUNT_SID: Your main Twilio Account SID
    - TWILIO_AUTH_TOKEN: Your main Twilio Auth Token
    """
    
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize Twilio client
        
        Args:
            account_sid: Twilio Account SID (optional, reads from env if not provided)
            auth_token: Twilio Auth Token (optional, reads from env if not provided)
        """
        self.account_sid = account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        
        if not self.account_sid or not self.auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be provided")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def create_subaccount(self, friendly_name: str) -> Dict:
        """
        Create a new Twilio subaccount
        
        Args:
            friendly_name: A human-readable name for the subaccount
            
        Returns:
            Dictionary containing subaccount details:
            - sid: Subaccount SID
            - friendly_name: Subaccount name
            - status: Account status
            - auth_token: Subaccount auth token
            - date_created: Creation timestamp
        """
        try:
            subaccount = self.client.api.accounts.create(
                friendly_name=friendly_name
            )
            
            return {
                'sid': subaccount.sid,
                'friendly_name': subaccount.friendly_name,
                'status': subaccount.status,
                'auth_token': subaccount.auth_token,
                'date_created': str(subaccount.date_created),
                'type': subaccount.type,
                'owner_account_sid': subaccount.owner_account_sid
            }
        except Exception as e:
            error_msg = str(e)
            if "Test Account Credentials" in error_msg or "20008" in error_msg:
                raise Exception(
                    "⚠️  TRIAL ACCOUNT LIMITATION\n\n"
                    "Subaccounts cannot be created with a Twilio Trial Account.\n\n"
                    "To create subaccounts, you need to:\n"
                    "1. Upgrade to a paid Twilio account\n"
                    "2. Go to: https://console.twilio.com/billing/upgrade\n"
                    "3. Add payment information and upgrade your account\n\n"
                    "Twilio Trial accounts have limitations:\n"
                    "• Cannot create subaccounts\n"
                    "• Cannot send SMS to non-verified numbers\n"
                    "• Cannot make calls to non-verified numbers\n\n"
                    "More info: https://www.twilio.com/docs/errors/20008"
                )
            raise Exception(f"Failed to create subaccount: {error_msg}")
    
    def list_subaccounts(self, limit: int = 20) -> list:
        """
        List all subaccounts under the main account
        
        Args:
            limit: Maximum number of subaccounts to retrieve
            
        Returns:
            List of subaccount dictionaries
        """
        try:
            subaccounts = self.client.api.accounts.list(limit=limit)
            
            return [
                {
                    'sid': acc.sid,
                    'friendly_name': acc.friendly_name,
                    'status': acc.status,
                    'type': acc.type,
                    'date_created': str(acc.date_created)
                }
                for acc in subaccounts
            ]
        except Exception as e:
            raise Exception(f"Failed to list subaccounts: {str(e)}")
    
    def get_subaccount(self, subaccount_sid: str) -> Dict:
        """
        Get details of a specific subaccount
        
        Args:
            subaccount_sid: The SID of the subaccount
            
        Returns:
            Dictionary containing subaccount details
        """
        try:
            subaccount = self.client.api.accounts(subaccount_sid).fetch()
            
            return {
                'sid': subaccount.sid,
                'friendly_name': subaccount.friendly_name,
                'status': subaccount.status,
                'auth_token': subaccount.auth_token,
                'date_created': str(subaccount.date_created),
                'type': subaccount.type
            }
        except Exception as e:
            raise Exception(f"Failed to get subaccount: {str(e)}")
    
    def update_subaccount(self, subaccount_sid: str, 
                         friendly_name: Optional[str] = None,
                         status: Optional[str] = None) -> Dict:
        """
        Update a subaccount's properties
        
        Args:
            subaccount_sid: The SID of the subaccount to update
            friendly_name: New friendly name (optional)
            status: New status - 'active', 'suspended', or 'closed' (optional)
            
        Returns:
            Updated subaccount details
        """
        try:
            update_params = {}
            if friendly_name:
                update_params['friendly_name'] = friendly_name
            if status:
                update_params['status'] = status
            
            subaccount = self.client.api.accounts(subaccount_sid).update(**update_params)
            
            return {
                'sid': subaccount.sid,
                'friendly_name': subaccount.friendly_name,
                'status': subaccount.status,
                'date_updated': str(subaccount.date_updated)
            }
        except Exception as e:
            raise Exception(f"Failed to update subaccount: {str(e)}")
    
    def close_subaccount(self, subaccount_sid: str) -> Dict:
        """
        Close a subaccount (this action is irreversible)
        
        Args:
            subaccount_sid: The SID of the subaccount to close
            
        Returns:
            Closed subaccount details
        """
        return self.update_subaccount(subaccount_sid, status='closed')
    
    def suspend_subaccount(self, subaccount_sid: str) -> Dict:
        """
        Suspend a subaccount (can be reactivated later)
        
        Args:
            subaccount_sid: The SID of the subaccount to suspend
            
        Returns:
            Suspended subaccount details
        """
        return self.update_subaccount(subaccount_sid, status='suspended')
    
    def activate_subaccount(self, subaccount_sid: str) -> Dict:
        """
        Activate a suspended subaccount
        
        Args:
            subaccount_sid: The SID of the subaccount to activate
            
        Returns:
            Activated subaccount details
        """
        return self.update_subaccount(subaccount_sid, status='active')


def print_menu():
    """Display the main menu"""
    print("\n" + "="*60)
    print("     TWILIO SUBACCOUNT MANAGEMENT SYSTEM")
    print("="*60)
    print("\n📋 MENU OPTIONS:\n")
    print("  1. Create New Subaccount")
    print("  2. List All Subaccounts")
    print("  3. Get Subaccount Details")
    print("  4. Update Subaccount Name")
    print("  5. Suspend Subaccount")
    print("  6. Activate Subaccount")
    print("  7. Close Subaccount (Irreversible)")
    print("  8. Exit")
    print("\n" + "-"*60)


def create_subaccount_menu(manager):
    """Handle subaccount creation"""
    print("\n📝 CREATE NEW SUBACCOUNT")
    print("-"*60)
    friendly_name = input("Enter a friendly name for the subaccount: ").strip()
    
    if not friendly_name:
        print("❌ Error: Friendly name cannot be empty!")
        return
    
    try:
        print("\n⏳ Creating subaccount...")
        subaccount = manager.create_subaccount(friendly_name)
        print("\n✅ Subaccount created successfully!\n")
        print(f"  📌 SID: {subaccount['sid']}")
        print(f"  📝 Name: {subaccount['friendly_name']}")
        print(f"  🔑 Auth Token: {subaccount['auth_token']}")
        print(f"  📊 Status: {subaccount['status']}")
        print(f"  📅 Created: {subaccount['date_created']}")
        print(f"  🏷️  Type: {subaccount['type']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def list_subaccounts_menu(manager):
    """Handle listing subaccounts"""
    print("\n📋 LIST ALL SUBACCOUNTS")
    print("-"*60)
    
    limit_input = input("Enter maximum number to display (default 20): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else 20
    
    try:
        print("\n⏳ Fetching subaccounts...")
        subaccounts = manager.list_subaccounts(limit=limit)
        
        if not subaccounts:
            print("\n📭 No subaccounts found.")
            return
        
        print(f"\n✅ Found {len(subaccounts)} subaccount(s):\n")
        for i, acc in enumerate(subaccounts, 1):
            print(f"{i}. {acc['friendly_name']}")
            print(f"   SID: {acc['sid']}")
            print(f"   Status: {acc['status']} | Type: {acc['type']}")
            print(f"   Created: {acc['date_created']}")
            print()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def get_subaccount_menu(manager):
    """Handle getting subaccount details"""
    print("\n🔍 GET SUBACCOUNT DETAILS")
    print("-"*60)
    subaccount_sid = input("Enter Subaccount SID: ").strip()
    
    if not subaccount_sid:
        print("❌ Error: SID cannot be empty!")
        return
    
    try:
        print("\n⏳ Fetching subaccount details...")
        details = manager.get_subaccount(subaccount_sid)
        print("\n✅ Subaccount Details:\n")
        print(f"  📌 SID: {details['sid']}")
        print(f"  📝 Name: {details['friendly_name']}")
        print(f"  🔑 Auth Token: {details['auth_token']}")
        print(f"  📊 Status: {details['status']}")
        print(f"  🏷️  Type: {details['type']}")
        print(f"  📅 Created: {details['date_created']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def update_subaccount_menu(manager):
    """Handle updating subaccount name"""
    print("\n✏️  UPDATE SUBACCOUNT NAME")
    print("-"*60)
    subaccount_sid = input("Enter Subaccount SID: ").strip()
    
    if not subaccount_sid:
        print("❌ Error: SID cannot be empty!")
        return
    
    new_name = input("Enter new friendly name: ").strip()
    
    if not new_name:
        print("❌ Error: New name cannot be empty!")
        return
    
    try:
        print("\n⏳ Updating subaccount...")
        updated = manager.update_subaccount(subaccount_sid, friendly_name=new_name)
        print("\n✅ Subaccount updated successfully!\n")
        print(f"  📌 SID: {updated['sid']}")
        print(f"  📝 New Name: {updated['friendly_name']}")
        print(f"  📊 Status: {updated['status']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def suspend_subaccount_menu(manager):
    """Handle suspending subaccount"""
    print("\n⏸️  SUSPEND SUBACCOUNT")
    print("-"*60)
    print("⚠️  Warning: This will temporarily disable the subaccount.")
    subaccount_sid = input("Enter Subaccount SID to suspend: ").strip()
    
    if not subaccount_sid:
        print("❌ Error: SID cannot be empty!")
        return
    
    confirm = input("Are you sure you want to suspend this account? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Operation cancelled.")
        return
    
    try:
        print("\n⏳ Suspending subaccount...")
        result = manager.suspend_subaccount(subaccount_sid)
        print("\n✅ Subaccount suspended successfully!\n")
        print(f"  📌 SID: {result['sid']}")
        print(f"  📝 Name: {result['friendly_name']}")
        print(f"  📊 Status: {result['status']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def activate_subaccount_menu(manager):
    """Handle activating subaccount"""
    print("\n▶️  ACTIVATE SUBACCOUNT")
    print("-"*60)
    subaccount_sid = input("Enter Subaccount SID to activate: ").strip()
    
    if not subaccount_sid:
        print("❌ Error: SID cannot be empty!")
        return
    
    try:
        print("\n⏳ Activating subaccount...")
        result = manager.activate_subaccount(subaccount_sid)
        print("\n✅ Subaccount activated successfully!\n")
        print(f"  📌 SID: {result['sid']}")
        print(f"  📝 Name: {result['friendly_name']}")
        print(f"  📊 Status: {result['status']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def close_subaccount_menu(manager):
    """Handle closing subaccount"""
    print("\n🚫 CLOSE SUBACCOUNT")
    print("-"*60)
    print("⚠️  WARNING: This action is IRREVERSIBLE!")
    print("⚠️  The subaccount cannot be reopened once closed.")
    subaccount_sid = input("\nEnter Subaccount SID to close: ").strip()
    
    if not subaccount_sid:
        print("❌ Error: SID cannot be empty!")
        return
    
    confirm1 = input("\n⚠️  Are you absolutely sure? (yes/no): ").strip().lower()
    
    if confirm1 != 'yes':
        print("❌ Operation cancelled.")
        return
    
    confirm2 = input("⚠️  Type 'CLOSE' in capital letters to confirm: ").strip()
    
    if confirm2 != 'CLOSE':
        print("❌ Operation cancelled.")
        return
    
    try:
        print("\n⏳ Closing subaccount...")
        result = manager.close_subaccount(subaccount_sid)
        print("\n✅ Subaccount closed successfully!\n")
        print(f"  📌 SID: {result['sid']}")
        print(f"  📝 Name: {result['friendly_name']}")
        print(f"  📊 Status: {result['status']}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def main():
    """
    Main menu-driven program
    """
    print("\n🚀 Initializing Twilio Subaccount Manager...")
    
    try:
        manager = TwilioSubaccountManager()
        print("✅ Successfully connected to Twilio!\n")
    except ValueError as e:
        print(f"\n❌ Configuration Error: {str(e)}")
        print("\n📝 Please ensure your .env file contains:")
        print("   TWILIO_ACCOUNT_SID=your_account_sid")
        print("   TWILIO_AUTH_TOKEN=your_auth_token")
        return
    except Exception as e:
        print(f"\n❌ Initialization Error: {str(e)}")
        return
    
    while True:
        print_menu()
        choice = input("Enter your choice (1-8): ").strip()
        
        if choice == '1':
            create_subaccount_menu(manager)
        elif choice == '2':
            list_subaccounts_menu(manager)
        elif choice == '3':
            get_subaccount_menu(manager)
        elif choice == '4':
            update_subaccount_menu(manager)
        elif choice == '5':
            suspend_subaccount_menu(manager)
        elif choice == '6':
            activate_subaccount_menu(manager)
        elif choice == '7':
            close_subaccount_menu(manager)
        elif choice == '8':
            print("\n👋 Thank you for using Twilio Subaccount Manager!")
            print("="*60)
            break
        else:
            print("\n❌ Invalid choice! Please select 1-8.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
