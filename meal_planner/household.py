from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import User, Household, HouseholdInvite, db
from datetime import datetime, timedelta
import secrets

household_bp = Blueprint('household', __name__, url_prefix='/household')

@household_bp.route('/')
@login_required
def index():
    """View household and members"""
    if not current_user.household:
        return render_template('household/create.html')

    household = current_user.household
    members = household.members.all()

    return render_template('household/index.html', household=household, members=members)

@household_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new household"""
    if current_user.household:
        flash('You are already part of a household', 'info')
        return redirect(url_for('household.index'))

    if request.method == 'POST':
        household_name = request.form.get('household_name', '').strip()

        if not household_name:
            flash('Please enter a household name', 'danger')
            return redirect(url_for('household.create'))

        household = Household(name=household_name, created_by=current_user.id)
        db.session.add(household)
        db.session.flush()  # Get the household ID without committing
        current_user.household_id = household.id
        db.session.commit()

        flash(f'Household "{household_name}" created! Share your invite code with your partner.', 'success')
        return redirect(url_for('household.index'))

    return render_template('household/create.html')

@household_bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite():
    """Generate secure invite token"""
    if not current_user.household:
        flash('You must create a household first', 'danger')
        return redirect(url_for('household.create'))

    household = current_user.household

    # Get active (non-accepted) invites
    active_invites = HouseholdInvite.query.filter_by(
        household_id=household.id,
        accepted=False
    ).filter(HouseholdInvite.expires_at > datetime.utcnow()).all()

    if request.method == 'POST':
        # Generate a new secure token (256-bit, URL-safe)
        token = secrets.token_urlsafe(32)

        # Create invite that expires in 7 days
        invite = HouseholdInvite(
            household_id=household.id,
            token=token,
            created_by=current_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(invite)
        db.session.commit()

        flash(f'New invite link generated! It expires in 7 days.', 'success')
        return redirect(url_for('household.invite'))

    return render_template('household/invite.html', household=household, active_invites=active_invites)

@household_bp.route('/join/<token>', methods=['GET', 'POST'])
@login_required
def join(token):
    """Join a household via secure invite token"""
    if current_user.household:
        flash('You are already part of a household', 'warning')
        return redirect(url_for('household.index'))

    # Find and validate the invite token
    invite = HouseholdInvite.query.filter_by(token=token).first()

    if not invite:
        flash('Invalid invite link', 'danger')
        return redirect(url_for('main.index'))

    # Check if invite is still valid
    if not invite.is_valid():
        if invite.accepted:
            flash('This invite has already been used', 'danger')
        else:
            flash('This invite has expired', 'danger')
        return redirect(url_for('main.index'))

    household = invite.household

    if request.method == 'POST':
        # Add user to household
        current_user.household_id = household.id

        # Mark invite as accepted
        invite.accepted = True
        invite.accepted_by = current_user.id
        invite.accepted_at = datetime.utcnow()

        db.session.commit()

        flash(f'✓ Successfully joined household "{household.name}"!', 'success')
        return redirect(url_for('household.index'))

    # Show confirmation page (GET request)
    return render_template('household/join_confirm.html', household=household, invite=invite)

@household_bp.route('/leave', methods=['POST'])
@login_required
def leave():
    """Leave a household"""
    if not current_user.household:
        flash('You are not part of any household', 'info')
        return redirect(url_for('main.index'))

    household = current_user.household
    household_name = household.name
    current_user.household_id = None
    db.session.commit()

    flash(f'You have left the household "{household_name}"', 'info')
    return redirect(url_for('main.index'))

@household_bp.route('/invite/<token>/revoke', methods=['POST'])
@login_required
def revoke_invite(token):
    """Revoke an invite (only household creator)"""
    if not current_user.household:
        flash('You are not part of any household', 'danger')
        return redirect(url_for('household.index'))

    household = current_user.household

    if household.created_by != current_user.id:
        flash('Only the household creator can revoke invites', 'danger')
        return redirect(url_for('household.index'))

    invite = HouseholdInvite.query.filter_by(token=token, household_id=household.id).first_or_404()

    if invite.accepted:
        flash('Cannot revoke an already-accepted invite', 'warning')
    else:
        db.session.delete(invite)
        db.session.commit()
        flash('Invite revoked', 'success')

    return redirect(url_for('household.invite'))

@household_bp.route('/remove-member/<int:user_id>', methods=['POST'])
@login_required
def remove_member(user_id):
    """Remove a member from household (only household creator)"""
    if not current_user.household:
        flash('You are not part of any household', 'danger')
        return redirect(url_for('household.index'))

    household = current_user.household

    if household.created_by != current_user.id:
        flash('Only the household creator can remove members', 'danger')
        return redirect(url_for('household.index'))

    user = User.query.get_or_404(user_id)

    if user.household_id != household.id:
        flash('User is not part of this household', 'danger')
        return redirect(url_for('household.index'))

    if user.id == current_user.id:
        flash('You cannot remove yourself. Leave the household instead.', 'warning')
        return redirect(url_for('household.index'))

    user.household_id = None
    db.session.commit()

    flash(f'Removed {user.username} from the household', 'success')
    return redirect(url_for('household.index'))
