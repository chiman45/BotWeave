"""
routes/bookings.py
------------------
Mandi booking read endpoints.

  GET /api/bookings/<businessId>    -- list bookings, optionally filtered by date
"""

import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from pymongo import DESCENDING

from database import bookings_col

log = logging.getLogger(__name__)

bookings_bp = Blueprint('bookings', __name__)


@bookings_bp.route('/api/bookings/<business_id>', methods=['GET'])
def get_bookings(business_id: str):
    """
    Return mandi bookings for a bot.

    Query params:
      date   -- filter by date string (YYYY-MM-DD)
      limit  -- max records to return (default 200)
    """
    date_filter = request.args.get('date')
    limit       = min(int(request.args.get('limit', 200)), 1000)

    query = {'businessId': business_id}
    if date_filter:
        query['date'] = date_filter

    docs = list(
        bookings_col.find(query, {'_id': 0})
                    .sort('createdAt', DESCENDING)
                    .limit(limit)
    )

    for d in docs:
        if isinstance(d.get('createdAt'), datetime):
            d['createdAt'] = d['createdAt'].isoformat()

    return jsonify({'bookings': docs, 'count': len(docs)})
