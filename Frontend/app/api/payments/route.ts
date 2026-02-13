import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import clientPromise from '@/lib/mongodb'

export async function GET() {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const client = await clientPromise
    const db = client.db('BotSetu')
    
    // Get payments for this user
    const payments = await db.collection('payments').find({ 
      userId 
    }).toArray()
    
    // Calculate totals
    const totalDue = payments
      .filter(p => p.status === 'due' || p.status === 'pending')
      .reduce((sum, p) => sum + (p.amount || 0), 0)
    
    const totalCompleted = payments
      .filter(p => p.status === 'completed' || p.status === 'paid')
      .reduce((sum, p) => sum + (p.amount || 0), 0)
    
    const allPayments = payments.map(payment => ({
      ...payment,
      _id: payment._id.toString()
    }))
    
    return NextResponse.json({
      totalDue,
      totalCompleted,
      payments: allPayments,
      count: payments.length
    })
  } catch (error) {
    console.error('Error fetching payments:', error)
    return NextResponse.json({ 
      totalDue: 0, 
      totalCompleted: 0, 
      payments: [], 
      count: 0 
    }, { status: 200 })
  }
}

export async function POST(request: Request) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { businessId, amount, planType, description, dueDate, status = 'due' } = body

    if (!businessId || !amount) {
      return NextResponse.json(
        { error: 'businessId and amount are required' },
        { status: 400 }
      )
    }

    const client = await clientPromise
    const db = client.db('BotSetu')
    
    const payment = {
      userId,
      businessId,
      amount: parseFloat(amount),
      planType: planType || 'unknown',
      description: description || 'Bot subscription payment',
      status, // 'due', 'pending', 'completed', 'paid', 'failed'
      dueDate: dueDate ? new Date(dueDate) : new Date(),
      createdAt: new Date(),
      updatedAt: new Date()
    }
    
    const result = await db.collection('payments').insertOne(payment)
    
    return NextResponse.json({
      success: true,
      paymentId: result.insertedId.toString(),
      payment: {
        ...payment,
        _id: result.insertedId.toString()
      }
    }, { status: 201 })
  } catch (error) {
    console.error('Error creating payment:', error)
    return NextResponse.json(
      { error: 'Failed to create payment' },
      { status: 500 }
    )
  }
}

export async function PATCH(request: Request) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { paymentId, status, transactionId, paymentMethod } = body

    if (!paymentId || !status) {
      return NextResponse.json(
        { error: 'paymentId and status are required' },
        { status: 400 }
      )
    }

    const client = await clientPromise
    const db = client.db('BotSetu')
    const { ObjectId } = require('mongodb')
    
    const updateData: any = {
      status,
      updatedAt: new Date()
    }
    
    if (status === 'completed' || status === 'paid') {
      updateData.paidAt = new Date()
    }
    
    if (transactionId) {
      updateData.transactionId = transactionId
    }
    
    if (paymentMethod) {
      updateData.paymentMethod = paymentMethod
    }
    
    const result = await db.collection('payments').updateOne(
      { _id: new ObjectId(paymentId), userId },
      { $set: updateData }
    )
    
    if (result.matchedCount === 0) {
      return NextResponse.json(
        { error: 'Payment not found' },
        { status: 404 }
      )
    }
    
    return NextResponse.json({
      success: true,
      message: 'Payment updated successfully'
    })
  } catch (error) {
    console.error('Error updating payment:', error)
    return NextResponse.json(
      { error: 'Failed to update payment' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: Request) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const paymentId = searchParams.get('paymentId')

    if (!paymentId) {
      return NextResponse.json(
        { error: 'paymentId is required' },
        { status: 400 }
      )
    }

    const client = await clientPromise
    const db = client.db('BotSetu')
    const { ObjectId } = require('mongodb')
    
    const result = await db.collection('payments').deleteOne({
      _id: new ObjectId(paymentId),
      userId
    })
    
    if (result.deletedCount === 0) {
      return NextResponse.json(
        { error: 'Payment not found' },
        { status: 404 }
      )
    }
    
    return NextResponse.json({
      success: true,
      message: 'Payment deleted successfully'
    })
  } catch (error) {
    console.error('Error deleting payment:', error)
    return NextResponse.json(
      { error: 'Failed to delete payment' },
      { status: 500 }
    )
  }
}
