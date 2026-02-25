"""Settings and user management"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import db, ApiKey

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/api-keys')
@login_required
def api_keys():
    """View and manage API keys"""
    api_keys = ApiKey.query.filter_by(user_id=current_user.id).all()

    # Check if there's a newly created key to show
    last_created_id = request.args.get('created_id', type=int)
    last_created_key = None
    if last_created_id:
        last_created = ApiKey.query.get(last_created_id)
        if last_created and last_created.user_id == current_user.id:
            last_created_key = last_created.key

    return render_template('settings/api_keys.html',
                         api_keys=api_keys,
                         last_created_id=last_created_id,
                         last_created_key=last_created_key)


@settings_bp.route('/api-keys', methods=['POST'])
@login_required
def create_api_key():
    """Create a new API key"""
    try:
        name = request.form.get('name', 'API Key').strip()
        if not name:
            flash('Please enter a key name', 'error')
            return redirect(url_for('settings.api_keys'))

        key = ApiKey(
            user_id=current_user.id,
            key=ApiKey.generate_key(),
            name=name
        )

        db.session.add(key)
        db.session.commit()

        flash(f'API key "{name}" created successfully', 'success')
        return redirect(url_for('settings.api_keys', created_id=key.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating API key: {str(e)}', 'error')
        return redirect(url_for('settings.api_keys'))


@settings_bp.route('/api-keys/<int:key_id>/delete', methods=['POST'])
@login_required
def delete_api_key(key_id):
    """Delete an API key"""
    key = ApiKey.query.get(key_id)
    if not key:
        flash('API key not found', 'error')
        return redirect(url_for('settings.api_keys'))

    if key.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('settings.api_keys'))

    try:
        key_name = key.name
        db.session.delete(key)
        db.session.commit()
        flash(f'API key "{key_name}" deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting API key: {str(e)}', 'error')

    return redirect(url_for('settings.api_keys'))


@settings_bp.route('/api-keys/<int:key_id>/disable', methods=['POST'])
@login_required
def disable_api_key(key_id):
    """Disable an API key"""
    key = ApiKey.query.get(key_id)
    if not key:
        flash('API key not found', 'error')
        return redirect(url_for('settings.api_keys'))

    if key.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('settings.api_keys'))

    try:
        key.is_active = False
        db.session.commit()
        flash(f'API key "{key.name}" disabled', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error disabling API key: {str(e)}', 'error')

    return redirect(url_for('settings.api_keys'))
