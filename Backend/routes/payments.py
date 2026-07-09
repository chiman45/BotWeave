"""
routes/payments.py
------------------
Payment record CRUD and plan-price reference.

  GET    /api/payments/<userId>         -- list all payment records for a user
  POST   /api/payments                  -- create a new payment record
  PATCH  /api/payments/<paymentId>      -- update status / transaction info
  DELETE /api/payments/<paymentId>      -- delete a payment record
  GET    /api/payments/plans            -- return plan price catalogue
"""

import logging
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, request, jsonify

from database import payments_col, get_system_config
from utils.helpers import now

log = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__)


def _get_plan_prices() -> dict:
    """
    Return plan prices from system-config if seeded, otherwise fall back to defaults.
    Prices are stored as a single doc: { key: 'plan_prices', value: {starter: 99, ...} }
    """
    prices = get_system_config('plan_prices', None)
    if isinstance(prices, dict):
        return prices
    return {'starter': 99, 'pro': 499, 'enterprise': 1999}


@payments_bp.route('/api/payments/plans', methods=['GET'])
def list_plans():
    """Return the plan price catalogue."""
    return jsonify({'plans': _get_plan_prices()})


@payments_bp.route('/api/payments/<user_id>', methods=['GET'])
def get_payments(user_id: str):
    """Return all payment records for a user with running totals."""
    docs = list(payments_col.find({'userId': user_id}, {'_id': 0}))

    for d in docs:
        for field in ('dueDate', 'paidAt', 'createdAt', 'updatedAt'):
            if isinstance(d.get(field), datetime):
                d[field] = d[field].isoformat()

    total_due       = sum(d.get('amount', 0) for d in docs if d.get('status') in ('due', 'pending'))
    total_completed = sum(d.get('amount', 0) for d in docs if d.get('status') in ('completed', 'paid'))

    return jsonify({
        'payments':       docs,
        'totalDue':       total_due,
        'totalCompleted': total_completed,
        'count':          len(docs),
    })


@payments_bp.route('/api/payments', methods=['POST'])
def create_payment():
    """Create a new payment record."""
    data = request.get_json(force=True) or {}

    for field in ('userId', 'businessId', 'amount'):
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    plan_type = data.get('planType', 'starter')
    ts        = now()

    payment = {
        'userId':      data['userId'],
        'businessId':  data['businessId'],
        'amount':      float(data['amount']),
        'planType':    plan_type,
        'description': data.get('description', f"{plan_type.capitalize()} plan subscription"),
        'status':      data.get('status', 'due'),
        'dueDate':     ts,
        'createdAt':   ts,
        'updatedAt':   ts,
    }

    result = payments_col.insert_one(payment)
    log.info("[PAYMENTS] Created payment %s for user %s", result.inserted_id, data['userId'])
    return jsonify({'success': True, 'paymentId': str(result.inserted_id)}), 201


@payments_bp.route('/api/payments/<payment_id>', methods=['PATCH'])
def update_payment(payment_id: str):
    """Update the status (and optional transaction details) of a payment."""
    data   = request.get_json(force=True) or {}
    status = data.get('status')

    if not status:
        return jsonify({'error': 'status is required'}), 400

    ts     = now()
    update = {'status': status, 'updatedAt': ts}

    if status in ('completed', 'paid'):
        update['paidAt'] = ts
    if data.get('transactionId'):
        update['transactionId'] = data['transactionId']
    if data.get('paymentMethod'):
        update['paymentMethod'] = data['paymentMethod']

    try:
        result = payments_col.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': update},
        )
        if result.matched_count == 0:
            return jsonify({'error': 'Payment not found'}), 404
        log.info("[PAYMENTS] Updated payment %s -> status=%s", payment_id, status)
        return jsonify({'success': True})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@payments_bp.route('/api/payments/<payment_id>', methods=['DELETE'])
def delete_payment(payment_id: str):
    """Delete a payment record."""
    try:
        result = payments_col.delete_one({'_id': ObjectId(payment_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Payment not found'}), 404
        log.info("[PAYMENTS] Deleted payment %s", payment_id)
        return jsonify({'success': True})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400
