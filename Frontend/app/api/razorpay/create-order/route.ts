import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import Razorpay from 'razorpay'
import { paymentLogger } from '@/lib/payment-logger'

export async function POST(request: Request) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      paymentLogger.warning('Unauthorized order creation attempt')
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { amount, currency = 'INR', planName, planType } = body

    if (!amount) {
      paymentLogger.error('Order creation failed - Missing amount', { userId })
      return NextResponse.json(
        { error: 'Amount is required' },
        { status: 400 }
      )
    }

    // Initialize Razorpay instance
    const razorpay = new Razorpay({
      key_id: process.env.RAZORPAY_KEY_ID!,
      key_secret: process.env.RAZORPAY_KEY_SECRET!
    })

    // Create Razorpay order
    const options = {
      amount: Math.round(amount * 100), // Convert to paise (smallest currency unit)
      currency,
      receipt: `receipt_${Date.now()}`,
      notes: {
        userId,
        planName: planName || 'Unknown',
        planType: planType || 'subscription'
      }
    }

    const order = await razorpay.orders.create(options)

    const orderAmount = typeof order.amount === 'number' ? order.amount / 100 : parseFloat(String(order.amount || 0)) / 100

    paymentLogger.success('Razorpay order created successfully', {
      userId,
      orderId: order.id,
      amount: orderAmount,
      currency: order.currency,
      planName,
      status: 'created'
    })

    return NextResponse.json({
      success: true,
      orderId: order.id,
      amount: order.amount,
      currency: order.currency,
      keyId: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID
    })
  } catch (error) {
    console.error('Error creating Razorpay order:', error)
    paymentLogger.error('Failed to create Razorpay order', {
      details: error instanceof Error ? error.message : 'Unknown error'
    })
    return NextResponse.json(
      { error: 'Failed to create order' },
      { status: 500 }
    )
  }
}
