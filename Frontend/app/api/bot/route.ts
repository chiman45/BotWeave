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
    const { userId } = await auth();
    if (!userId) return NextResponse.json({ message: 'Unauthorized' }, { status: 401 });

    const { businessId } = await request.json();
    if (!businessId) return NextResponse.json({ message: 'businessId is required' }, { status: 400 });

    const client = await clientPromise;
    const db = client.db('BotSetu');
    const collection = db.collection('User-data');

    const bot = await collection.findOne({ businessId, ownerUserId: userId });
    if (!bot) return NextResponse.json({ message: 'Bot not found' }, { status: 404 });

    if (bot.verificationStatus === 'verified' && bot.allocatedNumber) {
      return NextResponse.json({ message: 'Already active', allocatedNumber: bot.allocatedNumber }, { status: 200 });
    }

    // Generate a new random virtual WhatsApp number
    const prefixes = ['98','97','96','95','94','93','91','90','89','88','87','86','85','84','82','81','80','79','78','77','76'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const rand = Math.floor(10000000 + Math.random() * 89999999).toString();
    const allocatedNumber = `+91-${prefix}${rand.slice(0,4)}-${rand.slice(4,8)}`;

    const now = new Date();
    await collection.updateOne(
      { businessId, ownerUserId: userId },
      { $set: { verificationStatus: 'verified', allocatedNumber, activatedAt: now, updatedAt: now } }
    );

    return NextResponse.json({ message: 'Bot activated successfully', allocatedNumber }, { status: 200 });
  } catch (error) {
    console.error('Error activating bot:', error);
    return NextResponse.json({ message: 'Internal server error', error: String(error) }, { status: 500 });
  }
}
