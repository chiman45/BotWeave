# Payment Tracking System

Complete payment management system for BotSetu WhatsApp bot platform.

## Overview

The payment tracking system manages subscription payments, tracks due and completed payments, and provides comprehensive payment analytics. It integrates with the dashboard to display payment statistics and supports multiple payment statuses.

## Features

- ✅ Payment creation and tracking
- ✅ Multiple payment statuses (due, pending, completed, paid, failed)
- ✅ Recurring payment support (monthly/yearly)
- ✅ Payment statistics and analytics
- ✅ Overdue payment detection
- ✅ User and business-level payment tracking
- ✅ Dashboard integration
- ✅ RESTful API endpoints

## Database Schema

### Collection: `payments`

```javascript
{
  "_id": ObjectId,
  "userId": "user_clerk_id",           // Clerk user ID
  "businessId": "business_id",         // Bot/Business ID
  "amount": 499.00,                    // Payment amount in INR
  "planType": "pro",                   // starter|pro|enterprise
  "description": "Pro plan subscription",
  "status": "completed",               // due|pending|completed|paid|failed
  "dueDate": ISODate("2026-02-13"),
  "paidAt": ISODate("2026-02-10"),    // Optional, set when paid
  "transactionId": "txn_123456",       // Optional, from payment gateway
  "paymentMethod": "upi",              // Optional, card|upi|netbanking
  "createdAt": ISODate("2026-01-13"),
  "updatedAt": ISODate("2026-02-10")
}
```

## Payment Statuses

| Status | Description |
|--------|-------------|
| `due` | Payment is due but not yet initiated |
| `pending` | Payment is being processed |
| `completed` | Payment successfully completed |
| `paid` | Payment received and confirmed |
| `failed` | Payment attempt failed |

## Plan Pricing

| Plan | Monthly Price | Yearly Price (20% off) |
|------|--------------|------------------------|
| Starter | ₹99 | ₹950 |
| Pro | ₹499 | ₹4,790 |
| Enterprise | ₹1,999 | ₹19,190 |

## Backend (Python)

### Installation

```bash
cd Backend
pip install pymongo python-dotenv
```

### Usage

#### Interactive CLI

```bash
python payment_manager.py
```

The CLI provides options to:
1. Create payments
2. Update payment status
3. View user payments
4. View payment statistics
5. View business payments
6. Create recurring payments
7. View overdue payments
8. Delete payments

#### Programmatic Usage

```python
from payment_manager import PaymentManager

manager = PaymentManager()

# Create a payment
payment_id = manager.create_payment(
    user_id="user_123",
    business_id="business_456",
    amount=499.00,
    plan_type="pro",
    description="Pro plan - Monthly subscription",
    status="due"
)

# Update payment status
manager.update_payment_status(
    payment_id=payment_id,
    status="completed",
    transaction_id="txn_789",
    payment_method="upi"
)

# Get user payment stats
stats = manager.get_payment_stats("user_123")
print(f"Total Due: ₹{stats['totalDue']}")
print(f"Total Completed: ₹{stats['totalCompleted']}")

# Create recurring payment
payment_id = manager.create_recurring_payment(
    user_id="user_123",
    business_id="business_456",
    plan_type="pro",
    billing_cycle="monthly"  # or "yearly"
)

# Get overdue payments
overdue = manager.get_overdue_payments()
for payment in overdue:
    print(f"Overdue: ₹{payment['amount']} - {payment['businessId']}")
```

### Add Dummy Data

```bash
python add_dummy_payments.py
```

This script:
- Finds all bots in the database
- Creates 2-5 random payments for each bot
- Uses various statuses (due, pending, completed, paid)
- Sets random due dates (past and future)
- Displays payment summary

## Frontend (Next.js API)

### API Endpoints

#### GET /api/payments

Get all payments and statistics for the current user.

**Response:**
```json
{
  "totalDue": 1498.00,
  "totalCompleted": 2494.00,
  "payments": [...],
  "count": 8
}
```

#### POST /api/payments

Create a new payment.

**Request Body:**
```json
{
  "businessId": "business_123",
  "amount": 499.00,
  "planType": "pro",
  "description": "Pro plan subscription",
  "dueDate": "2026-03-13",
  "status": "due"
}
```

**Response:**
```json
{
  "success": true,
  "paymentId": "payment_id_123",
  "payment": {...}
}
```

#### PATCH /api/payments

Update payment status.

**Request Body:**
```json
{
  "paymentId": "payment_id_123",
  "status": "completed",
  "transactionId": "txn_789",
  "paymentMethod": "upi"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment updated successfully"
}
```

#### DELETE /api/payments?paymentId=xxx

Delete a payment.

**Response:**
```json
{
  "success": true,
  "message": "Payment deleted successfully"
}
```

### Frontend Usage

```typescript
// Fetch payment stats
const response = await fetch('/api/payments')
const data = await response.json()
console.log(`Due: ₹${data.totalDue}`)
console.log(`Completed: ₹${data.totalCompleted}`)

// Create payment
const createResponse = await fetch('/api/payments', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    businessId: 'business_123',
    amount: 499,
    planType: 'pro',
    status: 'due'
  })
})

// Update payment
await fetch('/api/payments', {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    paymentId: 'payment_id_123',
    status: 'completed',
    transactionId: 'txn_789'
  })
})
```

## Dashboard Integration

The dashboard displays two payment stat cards:

### Payment Due
- Shows total pending payment amount
- Red indicator for urgency
- Includes all payments with status `due` or `pending`

### Payment Completed
- Shows total completed payment amount
- Green indicator for success
- Includes all payments with status `completed` or `paid`

## Payment Workflow

### 1. Create Bot
When a user creates a bot, a payment record should be created:

```python
from payment_manager import PaymentManager

manager = PaymentManager()

# Create payment for new bot
payment_id = manager.create_recurring_payment(
    user_id=user_id,
    business_id=business_id,
    plan_type=plan_type,
    billing_cycle='monthly'
)
```

### 2. Process Payment
When user initiates payment:

```python
# Update to pending
manager.update_payment_status(payment_id, 'pending')

# After payment gateway confirmation
manager.update_payment_status(
    payment_id=payment_id,
    status='completed',
    transaction_id=transaction_id,
    payment_method='upi'
)
```

### 3. Track Overdue
Regularly check for overdue payments:

```python
overdue = manager.get_overdue_payments()
# Send reminder emails or notifications
```

## Statistics

### User-Level Stats

```python
stats = manager.get_payment_stats(user_id)
# Returns:
# - totalPayments
# - totalDue
# - totalCompleted
# - totalFailed
# - pendingPayments
# - completedPayments
# - failedPayments
```

### Business-Level Payments

```python
payments = manager.get_business_payments(business_id)
# Returns all payments for a specific bot
```

## Security

- All API endpoints require Clerk authentication
- User can only access their own payment data
- Payment IDs are verified against user ownership
- Sensitive payment data is not exposed in logs

## Future Enhancements

- [ ] Integration with payment gateways (Razorpay, Stripe)
- [ ] Automatic invoice generation
- [ ] Email notifications for due payments
- [ ] Payment reminders for overdue payments
- [ ] Refund support
- [ ] Payment history export
- [ ] Webhook support for payment gateway callbacks
- [ ] Multiple currency support

## Troubleshooting

### No payments showing in dashboard

1. Check if payment data exists:
```bash
python payment_manager.py
# Choose option 3 to view user payments
```

2. Add dummy data for testing:
```bash
python add_dummy_payments.py
```

3. Verify API endpoint is accessible:
```bash
curl http://localhost:3000/api/payments
```

### Payment stats showing 0

- Ensure MongoDB connection is working
- Check that userId matches between payments and user session
- Verify payment collection exists in database
- Check browser console for API errors

## Support

For issues or questions:
1. Check the Backend README
2. Review API endpoint responses
3. Verify MongoDB connection
4. Check Clerk authentication setup
