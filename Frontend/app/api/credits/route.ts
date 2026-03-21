import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import clientPromise from '@/lib/mongodb'

const INITIAL_CREDITS = 100

export async function GET() {
  try {
    const { userId } = await auth()
    if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

    const client = await clientPromise
    const db = client.db('BotSetu')
    const creditsCol = db.collection('credits')

    let doc = await creditsCol.findOne({ userId })
    if (!doc) {
      // First time — give 100 free credits
      const now = new Date()
      await creditsCol.insertOne({
        userId,
        credits: INITIAL_CREDITS,
        totalEarned: INITIAL_CREDITS,
        totalUsed: 0,
        createdAt: now,
        updatedAt: now,
      })
      return NextResponse.json({ credits: INITIAL_CREDITS, isNew: true })
    }

    return NextResponse.json({ credits: doc.credits, totalEarned: doc.totalEarned, totalUsed: doc.totalUsed })
  } catch {
    return NextResponse.json({ error: 'Failed to fetch credits' }, { status: 500 })
  }
}
