import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';
import clientPromise from '@/lib/mongodb';

/**
 * GET /api/conversations
 * Retrieve all conversations or specific conversation history
 */
export async function GET(request: NextRequest) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const searchParams = request.nextUrl.searchParams;
    const businessId = searchParams.get('businessId');
    const phoneNumber = searchParams.get('phoneNumber');
    const limit = parseInt(searchParams.get('limit') || '50');

    if (!businessId) {
      return NextResponse.json({ error: 'Business ID is required' }, { status: 400 });
    }

    const client = await clientPromise;
    const db = client.db('BotSetu');
    const conversationsCollection = db.collection('conversations');

    // Get specific conversation history
    if (phoneNumber) {
      const messages = await conversationsCollection
        .find({
          userId,
          businessId,
          phoneNumber,
        })
        .sort({ timestamp: -1 })
        .limit(limit)
        .toArray();

      return NextResponse.json({
        success: true,
        phoneNumber,
        messages,
        count: messages.length,
      });
    }

    // Get all conversations summary
    const conversations = await conversationsCollection
      .aggregate([
        {
          $match: {
            userId,
            businessId,
          },
        },
        {
          $sort: { timestamp: -1 },
        },
        {
          $group: {
            _id: '$phoneNumber',
            lastMessage: { $first: '$messageContent' },
            lastMessageTime: { $first: '$timestamp' },
            lastSender: { $first: '$sender' },
            messageCount: { $sum: 1 },
            unreadCount: {
              $sum: { $cond: [{ $eq: ['$read', false] }, 1, 0] },
            },
          },
        },
        {
          $sort: { lastMessageTime: -1 },
        },
        {
          $limit: limit,
        },
      ])
      .toArray();

    const formattedConversations = conversations.map((conv) => ({
      phoneNumber: conv._id,
      lastMessage: conv.lastMessage,
      lastMessageTime: conv.lastMessageTime,
      lastSender: conv.lastSender,
      messageCount: conv.messageCount,
      unreadCount: conv.unreadCount,
    }));

    return NextResponse.json({
      success: true,
      conversations: formattedConversations,
      count: formattedConversations.length,
    });
  } catch (error: any) {
    console.error('Error fetching conversations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch conversations', details: error.message },
      { status: 500 }
    );
  }
}

/**
 * POST /api/conversations
 * Log a new message in the conversation
 */
export async function POST(request: NextRequest) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const {
      businessId,
      phoneNumber,
      messageType = 'text',
      messageContent,
      sender,
      metadata = {},
    } = body;

    if (!businessId || !phoneNumber || !messageContent || !sender) {
      return NextResponse.json(
        { error: 'Missing required fields: businessId, phoneNumber, messageContent, sender' },
        { status: 400 }
      );
    }

    const client = await clientPromise;
    const db = client.db('BotSetu');
    const conversationsCollection = db.collection('conversations');
    const userDataCollection = db.collection('User-data');

    // Insert message
    const messageDoc = {
      userId,
      businessId,
      phoneNumber,
      messageType,
      messageContent,
      sender,
      metadata,
      timestamp: new Date(),
      read: false,
    };

    const result = await conversationsCollection.insertOne(messageDoc);

    // Update last interaction in User-data
    await userDataCollection.updateOne(
      {
        ownerUserId: userId,
        businessId,
      },
      {
        $set: {
          lastConversationAt: new Date(),
        },
        $inc: {
          totalMessages: 1,
        },
      }
    );

    return NextResponse.json({
      success: true,
      messageId: result.insertedId.toString(),
      timestamp: messageDoc.timestamp,
    });
  } catch (error: any) {
    console.error('Error logging message:', error);
    return NextResponse.json(
      { error: 'Failed to log message', details: error.message },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/conversations
 * Mark messages as read or update conversation
 */
export async function PATCH(request: NextRequest) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { businessId, phoneNumber, action } = body;

    if (!businessId || !phoneNumber) {
      return NextResponse.json(
        { error: 'Missing required fields: businessId, phoneNumber' },
        { status: 400 }
      );
    }

    const client = await clientPromise;
    const db = client.db('BotSetu');
    const conversationsCollection = db.collection('conversations');

    if (action === 'mark_read') {
      const result = await conversationsCollection.updateMany(
        {
          userId,
          businessId,
          phoneNumber,
          read: false,
        },
        {
          $set: { read: true },
        }
      );

      return NextResponse.json({
        success: true,
        markedCount: result.modifiedCount,
      });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error: any) {
    console.error('Error updating conversation:', error);
    return NextResponse.json(
      { error: 'Failed to update conversation', details: error.message },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/conversations
 * Delete a conversation
 */
export async function DELETE(request: NextRequest) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const searchParams = request.nextUrl.searchParams;
    const businessId = searchParams.get('businessId');
    const phoneNumber = searchParams.get('phoneNumber');

    if (!businessId || !phoneNumber) {
      return NextResponse.json(
        { error: 'Missing required parameters: businessId, phoneNumber' },
        { status: 400 }
      );
    }

    const client = await clientPromise;
    const db = client.db('BotSetu');
    const conversationsCollection = db.collection('conversations');

    const result = await conversationsCollection.deleteMany({
      userId,
      businessId,
      phoneNumber,
    });

    return NextResponse.json({
      success: true,
      deletedCount: result.deletedCount,
    });
  } catch (error: any) {
    console.error('Error deleting conversation:', error);
    return NextResponse.json(
      { error: 'Failed to delete conversation', details: error.message },
      { status: 500 }
    );
  }
}
