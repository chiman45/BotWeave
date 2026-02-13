"""
Payment Tracking System for BotSetu

This module provides functionality to manage payments for WhatsApp bot subscriptions.
It tracks payments, calculates dues, and manages payment status.

Database Collection: payments
Schema:
{
    "_id": ObjectId,
    "userId": "user_clerk_id",
    "businessId": "business_id",
    "amount": float,
    "planType": "starter|pro|enterprise",
    "description": "Payment description",
    "status": "due|pending|completed|paid|failed",
    "dueDate": datetime,
    "paidAt": datetime (optional),
    "transactionId": "transaction_id" (optional),
    "paymentMethod": "card|upi|netbanking" (optional),
    "createdAt": datetime,
    "updatedAt": datetime
}
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
import os
from typing import List, Dict, Optional

# MongoDB connection
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['BotSetu']
payments_collection = db['payments']
user_data_collection = db['User-data']


class PaymentManager:
    """Manages payment operations for BotSetu"""
    
    # Plan pricing (in INR)
    PLAN_PRICES = {
        'starter': 99,
        'pro': 499,
        'enterprise': 1999
    }
    
    def __init__(self):
        self.payments = payments_collection
        self.user_data = user_data_collection
    
    def create_payment(
        self, 
        user_id: str,
        business_id: str,
        amount: float,
        plan_type: str = 'starter',
        description: str = '',
        due_date: datetime = None,
        status: str = 'due'
    ) -> str:
        """
        Create a new payment record
        
        Args:
            user_id: Clerk user ID
            business_id: Business/Bot ID
            amount: Payment amount in INR
            plan_type: Plan type (starter, pro, enterprise)
            description: Payment description
            due_date: Payment due date
            status: Payment status (due, pending, completed, paid, failed)
        
        Returns:
            Payment ID as string
        """
        if due_date is None:
            due_date = datetime.utcnow()
        
        payment = {
            'userId': user_id,
            'businessId': business_id,
            'amount': float(amount),
            'planType': plan_type,
            'description': description or f'{plan_type.capitalize()} plan subscription',
            'status': status,
            'dueDate': due_date,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        result = self.payments.insert_one(payment)
        print(f"✓ Payment created: {result.inserted_id} - ₹{amount} ({status})")
        return str(result.inserted_id)
    
    def update_payment_status(
        self,
        payment_id: str,
        status: str,
        transaction_id: str = None,
        payment_method: str = None
    ) -> bool:
        """
        Update payment status
        
        Args:
            payment_id: Payment ID
            status: New status (due, pending, completed, paid, failed)
            transaction_id: Transaction ID from payment gateway
            payment_method: Payment method used
        
        Returns:
            True if updated, False otherwise
        """
        update_data = {
            'status': status,
            'updatedAt': datetime.utcnow()
        }
        
        # If payment is completed, record the payment time
        if status in ['completed', 'paid']:
            update_data['paidAt'] = datetime.utcnow()
        
        if transaction_id:
            update_data['transactionId'] = transaction_id
        
        if payment_method:
            update_data['paymentMethod'] = payment_method
        
        result = self.payments.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            print(f"✓ Payment {payment_id} updated to {status}")
            return True
        else:
            print(f"✗ Payment {payment_id} not found or not updated")
            return False
    
    def get_user_payments(
        self,
        user_id: str,
        status: str = None
    ) -> List[Dict]:
        """
        Get all payments for a user
        
        Args:
            user_id: Clerk user ID
            status: Filter by status (optional)
        
        Returns:
            List of payment documents
        """
        query = {'userId': user_id}
        if status:
            query['status'] = status
        
        payments = list(self.payments.find(query).sort('createdAt', -1))
        
        # Convert ObjectId to string for JSON serialization
        for payment in payments:
            payment['_id'] = str(payment['_id'])
        
        return payments
    
    def get_payment_by_id(self, payment_id: str) -> Optional[Dict]:
        """Get a specific payment by ID"""
        payment = self.payments.find_one({'_id': ObjectId(payment_id)})
        if payment:
            payment['_id'] = str(payment['_id'])
        return payment
    
    def get_payment_stats(self, user_id: str) -> Dict:
        """
        Get payment statistics for a user
        
        Args:
            user_id: Clerk user ID
        
        Returns:
            Dict with payment statistics
        """
        payments = self.get_user_payments(user_id)
        
        total_due = sum(
            p['amount'] for p in payments 
            if p['status'] in ['due', 'pending']
        )
        
        total_completed = sum(
            p['amount'] for p in payments 
            if p['status'] in ['completed', 'paid']
        )
        
        total_failed = sum(
            p['amount'] for p in payments 
            if p['status'] == 'failed'
        )
        
        return {
            'totalPayments': len(payments),
            'totalDue': total_due,
            'totalCompleted': total_completed,
            'totalFailed': total_failed,
            'pendingPayments': len([p for p in payments if p['status'] in ['due', 'pending']]),
            'completedPayments': len([p for p in payments if p['status'] in ['completed', 'paid']]),
            'failedPayments': len([p for p in payments if p['status'] == 'failed'])
        }
    
    def get_business_payments(self, business_id: str) -> List[Dict]:
        """Get all payments for a specific business/bot"""
        payments = list(self.payments.find({'businessId': business_id}).sort('createdAt', -1))
        
        for payment in payments:
            payment['_id'] = str(payment['_id'])
        
        return payments
    
    def delete_payment(self, payment_id: str) -> bool:
        """Delete a payment record"""
        result = self.payments.delete_one({'_id': ObjectId(payment_id)})
        
        if result.deleted_count > 0:
            print(f"✓ Payment {payment_id} deleted")
            return True
        else:
            print(f"✗ Payment {payment_id} not found")
            return False
    
    def create_recurring_payment(
        self,
        user_id: str,
        business_id: str,
        plan_type: str,
        billing_cycle: str = 'monthly'
    ) -> str:
        """
        Create a recurring payment based on plan type and billing cycle
        
        Args:
            user_id: Clerk user ID
            business_id: Business/Bot ID
            plan_type: Plan type (starter, pro, enterprise)
            billing_cycle: Billing cycle (monthly, yearly)
        
        Returns:
            Payment ID
        """
        amount = self.PLAN_PRICES.get(plan_type.lower(), 99)
        
        # Apply yearly discount (20% off)
        if billing_cycle == 'yearly':
            amount = amount * 12 * 0.8
        
        # Set due date based on billing cycle
        if billing_cycle == 'yearly':
            due_date = datetime.utcnow() + timedelta(days=365)
        else:
            due_date = datetime.utcnow() + timedelta(days=30)
        
        description = f'{plan_type.capitalize()} plan - {billing_cycle.capitalize()} subscription'
        
        return self.create_payment(
            user_id=user_id,
            business_id=business_id,
            amount=amount,
            plan_type=plan_type,
            description=description,
            due_date=due_date,
            status='due'
        )
    
    def get_overdue_payments(self) -> List[Dict]:
        """Get all overdue payments"""
        overdue = list(self.payments.find({
            'status': {'$in': ['due', 'pending']},
            'dueDate': {'$lt': datetime.utcnow()}
        }).sort('dueDate', 1))
        
        for payment in overdue:
            payment['_id'] = str(payment['_id'])
        
        return overdue


def main():
    """Interactive CLI for payment management"""
    manager = PaymentManager()
    
    print("\n" + "="*60)
    print("BotSetu Payment Management System")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Create Payment")
        print("2. Update Payment Status")
        print("3. View User Payments")
        print("4. View Payment Stats")
        print("5. View Business Payments")
        print("6. Create Recurring Payment")
        print("7. View Overdue Payments")
        print("8. Delete Payment")
        print("9. Exit")
        
        choice = input("\nEnter your choice (1-9): ").strip()
        
        if choice == '1':
            print("\n--- Create Payment ---")
            user_id = input("User ID: ").strip()
            business_id = input("Business ID: ").strip()
            amount = float(input("Amount (INR): ").strip())
            plan_type = input("Plan Type (starter/pro/enterprise) [starter]: ").strip() or 'starter'
            description = input("Description (optional): ").strip()
            status = input("Status (due/pending/completed) [due]: ").strip() or 'due'
            
            payment_id = manager.create_payment(
                user_id=user_id,
                business_id=business_id,
                amount=amount,
                plan_type=plan_type,
                description=description,
                status=status
            )
            print(f"\nPayment created with ID: {payment_id}")
        
        elif choice == '2':
            print("\n--- Update Payment Status ---")
            payment_id = input("Payment ID: ").strip()
            status = input("New Status (due/pending/completed/paid/failed): ").strip()
            transaction_id = input("Transaction ID (optional): ").strip() or None
            payment_method = input("Payment Method (optional): ").strip() or None
            
            success = manager.update_payment_status(
                payment_id=payment_id,
                status=status,
                transaction_id=transaction_id,
                payment_method=payment_method
            )
            
            if not success:
                print("\nFailed to update payment")
        
        elif choice == '3':
            print("\n--- View User Payments ---")
            user_id = input("User ID: ").strip()
            status = input("Filter by status (optional, press Enter to skip): ").strip() or None
            
            payments = manager.get_user_payments(user_id, status)
            
            if payments:
                print(f"\nFound {len(payments)} payment(s):")
                for p in payments:
                    print(f"\n  ID: {p['_id']}")
                    print(f"  Business: {p['businessId']}")
                    print(f"  Amount: ₹{p['amount']}")
                    print(f"  Plan: {p['planType']}")
                    print(f"  Status: {p['status']}")
                    print(f"  Due Date: {p['dueDate']}")
                    print(f"  Description: {p['description']}")
            else:
                print("\nNo payments found")
        
        elif choice == '4':
            print("\n--- Payment Statistics ---")
            user_id = input("User ID: ").strip()
            
            stats = manager.get_payment_stats(user_id)
            print(f"\n  Total Payments: {stats['totalPayments']}")
            print(f"  Total Due: ₹{stats['totalDue']}")
            print(f"  Total Completed: ₹{stats['totalCompleted']}")
            print(f"  Total Failed: ₹{stats['totalFailed']}")
            print(f"  Pending Payments: {stats['pendingPayments']}")
            print(f"  Completed Payments: {stats['completedPayments']}")
            print(f"  Failed Payments: {stats['failedPayments']}")
        
        elif choice == '5':
            print("\n--- View Business Payments ---")
            business_id = input("Business ID: ").strip()
            
            payments = manager.get_business_payments(business_id)
            
            if payments:
                print(f"\nFound {len(payments)} payment(s):")
                for p in payments:
                    print(f"\n  ID: {p['_id']}")
                    print(f"  Amount: ₹{p['amount']}")
                    print(f"  Status: {p['status']}")
                    print(f"  Due Date: {p['dueDate']}")
            else:
                print("\nNo payments found for this business")
        
        elif choice == '6':
            print("\n--- Create Recurring Payment ---")
            user_id = input("User ID: ").strip()
            business_id = input("Business ID: ").strip()
            plan_type = input("Plan Type (starter/pro/enterprise): ").strip()
            billing_cycle = input("Billing Cycle (monthly/yearly) [monthly]: ").strip() or 'monthly'
            
            payment_id = manager.create_recurring_payment(
                user_id=user_id,
                business_id=business_id,
                plan_type=plan_type,
                billing_cycle=billing_cycle
            )
            print(f"\nRecurring payment created with ID: {payment_id}")
        
        elif choice == '7':
            print("\n--- Overdue Payments ---")
            overdue = manager.get_overdue_payments()
            
            if overdue:
                print(f"\nFound {len(overdue)} overdue payment(s):")
                for p in overdue:
                    print(f"\n  ID: {p['_id']}")
                    print(f"  User: {p['userId']}")
                    print(f"  Business: {p['businessId']}")
                    print(f"  Amount: ₹{p['amount']}")
                    print(f"  Status: {p['status']}")
                    print(f"  Due Date: {p['dueDate']}")
                    days_overdue = (datetime.utcnow() - p['dueDate']).days
                    print(f"  Days Overdue: {days_overdue}")
            else:
                print("\nNo overdue payments")
        
        elif choice == '8':
            print("\n--- Delete Payment ---")
            payment_id = input("Payment ID: ").strip()
            confirm = input(f"Are you sure you want to delete payment {payment_id}? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                manager.delete_payment(payment_id)
            else:
                print("Deletion cancelled")
        
        elif choice == '9':
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Please try again.")


if __name__ == '__main__':
    main()
