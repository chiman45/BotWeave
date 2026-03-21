import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import crypto from 'crypto'
import clientPromise from '@/lib/mongodb'
import { paymentLogger } from '@/lib/payment-logger'

export async function POST(request: Request) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      paymentLogger.warning('Unauthorized payment verification attempt')
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const {
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature,
      amount,
      planName,
      planType,
      creditsAmount
    } = body

    if (!razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
      paymentLogger.error('Payment verification failed - Missing payment details', { userId })
      return NextResponse.json(
        { error: 'Missing payment details' },
        { status: 400 }
      )
    }

    // Verify signature
    const generatedSignature = crypto
      .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET!)
      .update(`${razorpay_order_id}|${razorpay_payment_id}`)
      .digest('hex')

    if (generatedSignature !== razorpay_signature) {
      paymentLogger.error('Payment verification failed - Invalid signature', {
        userId,
        orderId: razorpay_order_id,
        paymentId: razorpay_payment_id,
        status: 'signature_mismatch'
      })
      return NextResponse.json(
        { error: 'Invalid payment signature' },
        { status: 400 }
      )
    }

    // Payment is verified, save to database
    const client = await clientPromise
    const db = client.db('BotSetu')
    
    const payment = {
      userId,
      amount: amount ? parseFloat(amount) / 100 : 0, // Convert from paise to rupees
      planName: planName || 'Unknown',
      planType: planType || 'subscription',
      description: `${planName || 'Unknown'} plan subscription`,
      status: 'completed',
      paymentMethod: 'razorpay',
      transactionId: razorpay_payment_id,
      orderId: razorpay_order_id,
      paidAt: new Date(),
      createdAt: new Date(),
      updatedAt: new Date()
    }
    
    const result = await db.collection('payments').insertOne(payment)

    // If this is a credits purchase, top up the user's credit balance
    if (planType === 'credits' && creditsAmount && creditsAmount > 0) {
      const now = new Date()
      await db.collection('credits').updateOne(
        { userId },
        {
          $inc: { credits: creditsAmount, totalEarned: creditsAmount },
          $set: { updatedAt: now },
          $setOnInsert: { totalUsed: 0, createdAt: now },
        },
        { upsert: true }
      )
    }

    paymentLogger.success('Payment verified and saved successfully', {
      userId,
      orderId: razorpay_order_id,
      paymentId: razorpay_payment_id,
      amount: payment.amount,
      currency: 'INR',
      planName: payment.planName,
      status: 'completed'
    })
    
    return NextResponse.json({
      success: true,
      message: 'Payment verified successfully',
      paymentId: result.insertedId.toString(),
      creditsAdded: planType === 'credits' ? (creditsAmount || 0) : 0,
      payment: {
        ...payment,
        _id: result.insertedId.toString()
      }
    })
  } catch (error) {
    console.error('Error verifying payment:', error)
    paymentLogger.error('Payment verification failed', {
      details: error instanceof Error ? error.message : 'Unknown error'
    })
    return NextResponse.json(
      { error: 'Failed to verify payment' },
      { status: 500 }
    )
  }
}
