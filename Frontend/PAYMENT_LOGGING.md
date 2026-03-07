# Payment Gateway Logging System

## Overview

This payment gateway logging system tracks all payment-related transactions and events in the BotSetu application. All logs are stored in a centralized log file for auditing, debugging, and monitoring purposes.

## Log File Location

```
Frontend/logs/payment-gateway.log
```

## Features

- ✅ **Comprehensive Logging**: Tracks order creation, payment verification, successes, and errors
- ✅ **Structured Format**: Easy-to-parse log format with timestamps, levels, and metadata
- ✅ **Multiple Log Levels**: INFO, SUCCESS, ERROR, WARNING
- ✅ **Transaction Tracking**: Includes userId, orderId, paymentId, amount, and plan details
- ✅ **Date Range Queries**: Fetch logs by specific date ranges
- ✅ **API Access**: View logs programmatically via REST API

## Log Levels

| Level   | Description                                    | Example Use Case                    |
|---------|------------------------------------------------|-------------------------------------|
| INFO    | Informational messages                         | System events, configuration        |
| SUCCESS | Successful operations                          | Payment verified, order created     |
| ERROR   | Error conditions                               | Failed payments, invalid signatures |
| WARNING | Warning conditions                             | Unauthorized access attempts        |

## Log Entry Format

Each log entry follows this format:

```
[TIMESTAMP] [LEVEL] MESSAGE | UserId: xxx | OrderId: xxx | PaymentId: xxx | Amount: xxx INR | Plan: xxx | Status: xxx | Details: {...}
```

### Example Log Entries

```
[2026-03-07T14:30:45.123Z] [SUCCESS] Razorpay order created successfully | UserId: user_123 | OrderId: order_abc123 | Amount: 149 INR | Plan: Pro | Status: created

[2026-03-07T14:31:12.456Z] [SUCCESS] Payment verified and saved successfully | UserId: user_123 | OrderId: order_abc123 | PaymentId: pay_xyz789 | Amount: 149 INR | Plan: Pro | Status: completed

[2026-03-07T14:32:01.789Z] [ERROR] Payment verification failed - Invalid signature | UserId: user_456 | OrderId: order_def456 | PaymentId: pay_abc123 | Status: signature_mismatch
```

## Logged Events

### Order Creation
- ✅ Successful order creation
- ✅ Failed order creation (missing amount, API errors)
- ✅ Unauthorized attempts

### Payment Verification
- ✅ Successful payment verification
- ✅ Failed verification (invalid signature, missing details)
- ✅ Database save operations
- ✅ Unauthorized attempts

### Tracked Data Points

For each payment event, the following data is logged when available:

- **timestamp**: ISO 8601 timestamp
- **userId**: Clerk user identifier
- **orderId**: Razorpay order ID
- **paymentId**: Razorpay payment ID
- **amount**: Payment amount in currency units
- **currency**: Currency code (default: INR)
- **planName**: Subscription plan name
- **status**: Transaction status
- **details**: Additional error or context information

## API Endpoints

### Get Recent Logs

```http
GET /api/payment-logs?lines=100
```

**Query Parameters:**
- `lines` (optional): Number of recent log entries to fetch (default: 100)

**Response:**
```json
{
  "success": true,
  "count": 25,
  "logs": [
    {
      "timestamp": "2026-03-07T14:30:45.123Z",
      "level": "SUCCESS",
      "message": "Payment verified and saved successfully",
      "raw": "[2026-03-07T14:30:45.123Z] [SUCCESS] Payment verified..."
    }
  ]
}
```

### Get Logs by Date Range

```http
GET /api/payment-logs?startDate=2026-03-01&endDate=2026-03-07
```

**Query Parameters:**
- `startDate`: ISO 8601 date string (start of range)
- `endDate`: ISO 8601 date string (end of range)

**Response:**
Same format as above

## Usage in Code

### Import the Logger

```typescript
import { paymentLogger } from '@/lib/payment-logger'
```

### Log a Success

```typescript
paymentLogger.success('Payment verified successfully', {
  userId: 'user_123',
  orderId: 'order_abc',
  paymentId: 'pay_xyz',
  amount: 149,
  currency: 'INR',
  planName: 'Pro',
  status: 'completed'
})
```

### Log an Error

```typescript
paymentLogger.error('Payment verification failed', {
  userId: 'user_123',
  orderId: 'order_abc',
  status: 'signature_mismatch',
  details: { reason: 'Invalid signature' }
})
```

### Log Info

```typescript
paymentLogger.info('Order creation initiated', {
  userId: 'user_123',
  planName: 'Starter',
  amount: 49
})
```

### Log Warning

```typescript
paymentLogger.warning('Unauthorized access attempt', {
  details: { ip: '192.168.1.1' }
})
```

## Viewing Logs

### Via API (Recommended)

Use the REST API endpoint to fetch and display logs in your admin dashboard:

```javascript
const response = await fetch('/api/payment-logs?lines=50')
const data = await response.json()
console.log(data.logs)
```

### Via File System

Directly access the log file:

```bash
# View recent logs
tail -100 Frontend/logs/payment-gateway.log

# Search for errors
grep "ERROR" Frontend/logs/payment-gateway.log

# Search for specific user
grep "user_123" Frontend/logs/payment-gateway.log

# Search for specific order
grep "order_abc123" Frontend/logs/payment-gateway.log
```

## Log Rotation

The current implementation appends to a single log file. For production use, consider implementing log rotation:

1. **By Size**: Rotate when file reaches a certain size
2. **By Time**: Create new log file daily/weekly
3. **By Count**: Keep only last N log files

## Security Considerations

- ✅ Logs contain sensitive payment information
- ✅ Restrict access to authorized users only
- ✅ API endpoint requires authentication
- ✅ Do not expose logs to public endpoints
- ⚠ Consider encrypting log files in production
- ⚠ Regular log archival and cleanup recommended

## Monitoring & Alerts

Consider setting up monitoring for:

- High error rates in payment verification
- Unauthorized access attempts
- Failed signature validations
- Unusual payment patterns

## Troubleshooting

### Log File Not Created

- Check write permissions on the `logs/` directory
- Ensure the application has permission to create files

### Missing Log Entries

- Check console for logger errors
- Verify imports are correct
- Ensure logger is called in try/catch blocks

### Performance Concerns

- Large log files may impact read performance
- Implement log rotation for production
- Consider using a dedicated logging service for high-volume applications

## Future Enhancements

- [ ] Log rotation implementation
- [ ] Database storage option
- [ ] Real-time log streaming
- [ ] Advanced filtering and search
- [ ] Integration with monitoring services (e.g., Sentry, LogRocket)
- [ ] Email alerts for critical errors
- [ ] Log export functionality (CSV, JSON)
