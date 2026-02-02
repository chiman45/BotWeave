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
