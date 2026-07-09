"""
routes/conversations.py
-----------------------
Conversation history and thread management endpoints.

  GET    /api/conversations/<businessId>                      -- list all threads
  GET    /api/conversations/<businessId>/<phone>              -- full message thread
  PATCH  /api/conversations/<businessId>/<phone>/read         -- mark thread as read
  DELETE /api/conversations/<businessId>/<phone>              -- delete thread
"""

import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from pymongo import ASCENDING, DESCENDING

from database import conversations_col, sessions_col

log = logging.getLogger(__name__)

conversations_bp = Blueprint('conversations', __name__)


@conversations_bp.route('/api/conversations/<business_id>', methods=['GET'])
def get_conversations(business_id: str):
    """
    Return all unique conversations (grouped by customer phone) for a bot.
    Each entry includes the most recent message, counts, and unread count.

    Query params: limit (default 50)
    """
    limit = min(int(request.args.get('limit', 50)), 500)

    pipeline = [
        {'$match': {'businessId': business_id}},
        {'$sort':  {'timestamp': -1}},
        {
            '$group': {
                '_id':             '$phoneNumber',
                'lastMessage':     {'$first': '$messageContent'},
                'lastMessageTime': {'$first': '$timestamp'},
                'lastSender':      {'$first': '$sender'},
                'messageCount':    {'$sum': 1},
                'unreadCount':     {'$sum': {'$cond': [{'$eq': ['$read', False]}, 1, 0]}},
            }
        },
        {'$sort':  {'lastMessageTime': -1}},
        {'$limit': limit},
    ]

    result = [
        {
            'phoneNumber':     c['_id'],
            'lastMessage':     c.get('lastMessage', ''),
            'lastMessageTime': (
                c['lastMessageTime'].isoformat()
                if isinstance(c.get('lastMessageTime'), datetime)
                else c.get('lastMessageTime')
            ),
            'lastSender':   c.get('lastSender', ''),
            'messageCount': c.get('messageCount', 0),
            'unreadCount':  c.get('unreadCount', 0),
        }
        for c in conversations_col.aggregate(pipeline)
    ]

    return jsonify({'conversations': result, 'count': len(result)})


@conversations_bp.route('/api/conversations/<business_id>/<path:phone_number>', methods=['GET'])
def get_chat_history(business_id: str, phone_number: str):
    """Return the full chronological message thread for one customer."""
    limit = min(int(request.args.get('limit', 100)), 1000)

    messages = list(
        conversations_col.find(
            {'businessId': business_id, 'phoneNumber': phone_number},
            {'_id': 0},
        ).sort('timestamp', ASCENDING).limit(limit)
    )

    for m in messages:
        if isinstance(m.get('timestamp'), datetime):
            m['timestamp'] = m['timestamp'].isoformat()

    return jsonify({'messages': messages, 'count': len(messages)})


@conversations_bp.route(
    '/api/conversations/<business_id>/<path:phone_number>/read', methods=['PATCH']
)
def mark_read(business_id: str, phone_number: str):
    """Mark all messages from a customer as read."""
    result = conversations_col.update_many(
        {'businessId': business_id, 'phoneNumber': phone_number, 'read': False},
        {'$set': {'read': True}},
    )
    return jsonify({'success': True, 'marked': result.modified_count})


@conversations_bp.route(
    '/api/conversations/<business_id>/<path:phone_number>', methods=['DELETE']
)
def delete_conversation(business_id: str, phone_number: str):
    """Delete a full conversation thread and clear the customer session."""
    result = conversations_col.delete_many(
        {'businessId': business_id, 'phoneNumber': phone_number}
    )
    sessions_col.delete_one({'customerPhone': phone_number})
    log.info(
        "[CONV] Deleted %d messages for %s / %s",
        result.deleted_count, business_id, phone_number,
    )
    return jsonify({'success': True, 'deleted': result.deleted_count})
