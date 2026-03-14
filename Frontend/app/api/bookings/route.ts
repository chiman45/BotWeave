import { NextRequest, NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { auth } from '@clerk/nextjs/server'

export async function GET(request: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(request.url)
  const businessId = searchParams.get('businessId')
  const dateFilter = searchParams.get('date')

  const client = await clientPromise
  const db = client.db('BotSetu')

  // Build base query — always scope to the authenticated user's bots
  let businessIds: string[]

  if (businessId) {
    // Verify the requested bot belongs to the signed-in user
    const bot = await db.collection('User-data').findOne({ businessId, ownerUserId: userId })
    if (!bot) return NextResponse.json({ message: 'Bot not found or access denied' }, { status: 404 })
    businessIds = [businessId]
  } else {
    // Fetch all bots owned by this user
    const bots = await db.collection('User-data').find({ ownerUserId: userId }).toArray()
    businessIds = bots.map(b => b.businessId as string).filter(Boolean)
  }

  const query: Record<string, unknown> = { businessId: { $in: businessIds } }
  if (dateFilter) query.date = dateFilter

  const bookings = await db
    .collection('mandi-bookings')
    .find(query)
    .sort({ createdAt: -1 })
    .limit(500)
    .toArray()

  const serialized = bookings.map(b => ({
    ...b,
    _id: b._id.toString(),
    createdAt: b.createdAt instanceof Date ? b.createdAt.toISOString() : b.createdAt,
  }))

  return NextResponse.json({ bookings: serialized })
}
