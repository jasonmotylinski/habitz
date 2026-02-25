"""
API key management endpoints
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from .models import db, ApiKey

api_keys_bp = Blueprint('api_keys', __name__, url_prefix='/api-keys')


@api_keys_bp.route('', methods=['GET'])
@login_required
def list_api_keys():
    """List all API keys for current user"""
    keys = ApiKey.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        "total": len(keys),
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "created_at": k.created_at.isoformat(),
                "last_used": k.last_used.isoformat() if k.last_used else None,
                "is_active": k.is_active
            }
            for k in keys
        ]
    })


@api_keys_bp.route('', methods=['POST'])
@login_required
def create_api_key():
    """Create a new API key"""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'API Key')

        key = ApiKey(
            user_id=current_user.id,
            key=ApiKey.generate_key(),
            name=name
        )

        db.session.add(key)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"API key '{name}' created",
            "key": {
                "id": key.id,
                "name": key.name,
                "token": key.key,  # Only shown on creation
                "created_at": key.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_keys_bp.route('/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    """Delete an API key"""
    key = ApiKey.query.get(key_id)
    if not key:
        return jsonify({"error": "API key not found"}), 404

    if key.user_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    try:
        db.session.delete(key)
        db.session.commit()
        return jsonify({"success": True, "message": f"API key '{key.name}' deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_keys_bp.route('/<int:key_id>/disable', methods=['POST'])
@login_required
def disable_api_key(key_id):
    """Disable an API key"""
    key = ApiKey.query.get(key_id)
    if not key:
        return jsonify({"error": "API key not found"}), 404

    if key.user_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    try:
        key.is_active = False
        db.session.commit()
        return jsonify({"success": True, "message": f"API key '{key.name}' disabled"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
