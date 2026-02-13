"""
Add Dummy Payment Data for Testing

This script creates sample payment records for testing the payment tracking system.
It adds payments for existing bots in the database.
"""

from payment_manager import PaymentManager
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import random

# MongoDB connection
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['BotSetu']
user_data_collection = db['User-data']

# Initialize payment manager
payment_manager = PaymentManager()

def add_dummy_payments():
    """Add dummy payment data for all bots in the database"""
    
    print("\n" + "="*60)
    print("Adding Dummy Payment Data")
    print("="*60)
    
    # Get all bots from the database
    bots = list(user_data_collection.find())
    
    if not bots:
        print("\n✗ No bots found in database. Please create a bot first.")
        return
    
    print(f"\nFound {len(bots)} bot(s) in database")
    
    payment_statuses = ['completed', 'due', 'pending', 'paid']
    plan_types = ['starter', 'pro', 'enterprise']
    
    total_payments_created = 0
    
    for bot in bots:
        user_id = bot.get('ownerUserId')
        business_id = bot.get('businessId')
        plan_type = bot.get('planType', 'starter')
        
        if not user_id or not business_id:
            print(f"\n⚠ Skipping bot {bot.get('_id')} - missing user_id or business_id")
            continue
        
        print(f"\n📝 Creating payments for: {bot.get('businessName', 'Unknown Business')}")
        print(f"   User ID: {user_id}")
        print(f"   Business ID: {business_id}")
        print(f"   Plan: {plan_type}")
        
        # Create 2-5 payments for each bot
        num_payments = random.randint(2, 5)
        
        for i in range(num_payments):
            # Random status
            status = random.choice(payment_statuses)
            
            # Get plan amount
            if plan_type == 'starter':
                amount = 99
            elif plan_type == 'pro':
                amount = 499
            elif plan_type == 'enterprise':
                amount = 1999
            else:
                amount = 99
            
            # Random due date (some in past, some in future)
            days_offset = random.randint(-60, 60)
            due_date = datetime.utcnow() + timedelta(days=days_offset)
            
            # Create description
            if status in ['completed', 'paid']:
                description = f'{plan_type.capitalize()} plan - Payment received'
            elif status == 'pending':
                description = f'{plan_type.capitalize()} plan - Payment processing'
            else:
                description = f'{plan_type.capitalize()} plan - Monthly subscription'
            
            # Create payment
            payment_id = payment_manager.create_payment(
                user_id=user_id,
                business_id=business_id,
                amount=amount,
                plan_type=plan_type,
                description=description,
                due_date=due_date,
                status=status
            )
            
            total_payments_created += 1
            
            print(f"   ✓ Payment {i+1}/{num_payments}: ₹{amount} ({status})")
    
    print(f"\n" + "="*60)
    print(f"✓ Successfully created {total_payments_created} dummy payments")
    print("="*60)
    
    # Show summary stats
    print("\n📊 Payment Summary:")
    for bot in bots:
        user_id = bot.get('ownerUserId')
        if user_id:
            stats = payment_manager.get_payment_stats(user_id)
            print(f"\n  {bot.get('businessName', 'Unknown')}:")
            print(f"    Total Payments: {stats['totalPayments']}")
            print(f"    Total Due: ₹{stats['totalDue']}")
            print(f"    Total Completed: ₹{stats['totalCompleted']}")
            print(f"    Pending: {stats['pendingPayments']} | Completed: {stats['completedPayments']}")


if __name__ == '__main__':
    try:
        add_dummy_payments()
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
