"""
routes/templates.py
-------------------
Bot template catalogue endpoints.

  GET /api/templates              -- list all templates
  GET /api/templates/<templateId> -- get one template by its `id` field
"""

import logging

from flask import Blueprint, jsonify

from database import templates_col

log = logging.getLogger(__name__)

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/api/templates', methods=['GET'])
def list_templates():
    """Return all templates from the templates collection."""
    templates = list(templates_col.find({}, {'_id': 0}))
    return jsonify({'templates': templates})


@templates_bp.route('/api/templates/<template_id>', methods=['GET'])
def get_template(template_id: str):
    """Return a single template by its `id` field."""
    tpl = templates_col.find_one({'id': template_id}, {'_id': 0})
    if not tpl:
        return jsonify({'error': 'Template not found'}), 404
    return jsonify(tpl)
