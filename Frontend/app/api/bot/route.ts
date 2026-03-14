import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import { auth } from '@clerk/nextjs/server';

export async function POST(request: NextRequest) {
  try {
    // Verify user is authenticated
    const { userId } = await auth();
    
    if (!userId) {
      return NextResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    // Connect to MongoDB
    const client = await clientPromise;
    const db = client.db('BotSetu');
    const collection = db.collection('User-data');

    // Create document with business ID
    const botData = {
      ...body,
      businessId: `business_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      ownerUserId: userId,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    // Insert into MongoDB
    const result = await collection.insertOne(botData);

    return NextResponse.json(
      { 
        message: 'Bot created successfully',
        businessId: botData.businessId,
        id: result.insertedId 
      },
      { status: 201 }
    );

  } catch (error) {
    console.error('Error creating bot:', error);
    return NextResponse.json(
      { message: 'Internal server error', error: String(error) },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    // Verify user is authenticated
    const { userId } = await auth();
    
    if (!userId) {
      return NextResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Connect to MongoDB
    const client = await clientPromise;
    const db = client.db('BotSetu');
    const collection = db.collection('User-data');

    // Get all bots for this user
    const bots = await collection
      .find({ ownerUserId: userId })
      .sort({ createdAt: -1 })
      .toArray();

    return NextResponse.json({ bots }, { status: 200 });

  } catch (error) {
    console.error('Error fetching bots:', error);
    return NextResponse.json(
      { message: 'Internal server error', error: String(error) },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })

    const { businessId, ...updates } = await request.json()
    if (!businessId) return NextResponse.json({ message: 'businessId is required' }, { status: 400 })

    const client = await clientPromise
    const db = client.db('BotSetu')

    // Verify ownership before updating
    const existing = await db.collection('User-data').findOne({ businessId, ownerUserId: userId })
    if (!existing) return NextResponse.json({ message: 'Bot not found' }, { status: 404 })

    // Only allow safe editable fields — never let callers overwrite ownerUserId/businessId
    const ALLOWED = [
      'botName', 'useCaseType', 'autoReply', 'humanHandoff',
      'welcomeMessage', 'fallbackMessage', 'humanHandoffMessage',
      'keywordResponses', 'mandis', 'slots', 'maxBookingsPerSlot',
      'businessName', 'category', 'city', 'country',
      'defaultLanguage', 'businessHours', 'planType',
      'botType', 'aiModel', 'aiSystemPrompt', 'aiRagEnabled',
    ]
    const patch: Record<string, unknown> = { updatedAt: new Date() }
    for (const key of ALLOWED) {
      if (key in updates) patch[key] = updates[key]
    }

    await db.collection('User-data').updateOne({ businessId }, { $set: patch })
    const updated = await db.collection('User-data').findOne({ businessId }, { projection: { _id: 0 } })
    return NextResponse.json({ message: 'Bot updated successfully', bot: updated })
  } catch (error) {
    console.error('Error updating bot:', error)
    return NextResponse.json({ message: 'Internal server error', error: String(error) }, { status: 500 })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ message: 'Unauthorized' }, { status: 401 });
    }

    const { businessId } = await request.json();
    if (!businessId) {
      return NextResponse.json({ message: 'businessId is required' }, { status: 400 });
    }

    const client = await clientPromise;
    const db = client.db('BotSetu');

    // Only delete if it belongs to this user
    const result = await db.collection('User-data').deleteOne({ businessId, ownerUserId: userId });
    if (result.deletedCount === 0) {
      return NextResponse.json({ message: 'Bot not found' }, { status: 404 });
    }

    // Also clean up related conversations and sessions
    await db.collection('conversations').deleteMany({ businessId });
    await db.collection('bot-sessions').deleteMany({ businessId });

    return NextResponse.json({ message: 'Bot deleted successfully' }, { status: 200 });
  } catch (error) {
    console.error('Error deleting bot:', error);
    return NextResponse.json(
      { message: 'Internal server error', error: String(error) },
      { status: 500 }
    );
  }
}
