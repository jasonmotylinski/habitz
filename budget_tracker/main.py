import os
from datetime import date, datetime
from flask import Blueprint, render_template, request, flash, current_app
from flask_login import login_required

from .sheets import (
    get_weekly_tab_name,
    get_available_weeks,
    get_weekly_summary,
    get_weekly_transactions,
)

main_bp = Blueprint('main', __name__)


def _get_service():
    from .sheets import get_sheets_service
    path = current_app.config.get('GOOGLE_SERVICE_ACCOUNT_JSON', '')
    if not path or not os.path.exists(path):
        return None
    return get_sheets_service(path)


def _week_label(tab_name: str) -> str:
    """Convert YYYYMMDD to 'Week of Mon D' for display."""
    try:
        d = datetime.strptime(tab_name, '%Y%m%d')
        return d.strftime('Week of %b %-d')
    except ValueError:
        return tab_name


@main_bp.route('/')
@login_required
def index():
    sheet_id = current_app.config.get('GOOGLE_SHEET_ID', '')
    week_param = request.args.get('week')
    # Validate week param format (YYYYMMDD)
    if week_param and not (week_param.isdigit() and len(week_param) == 8):
        week_param = None
    tab_name = week_param if week_param else get_weekly_tab_name(date.today())
    current_tab = get_weekly_tab_name(date.today())
    is_current_week = (tab_name == current_tab)

    try:
        service = _get_service()
        if not service or not sheet_id:
            flash('Budget data is not configured.', 'error')
            return render_template('budget/index.html',
                                   summary=None, transactions=[],
                                   week_label=_week_label(tab_name),
                                   prev_week=None, next_week=None,
                                   is_current_week=is_current_week)

        available_weeks = get_available_weeks(service, sheet_id)

        if tab_name not in available_weeks:
            prev_weeks = [w for w in available_weeks if w < tab_name]
            return render_template('budget/index.html',
                                   summary=None, transactions=[],
                                   week_label=_week_label(tab_name),
                                   prev_week=prev_weeks[0] if prev_weeks else None,
                                   next_week=None,
                                   is_current_week=is_current_week)

        idx = available_weeks.index(tab_name)
        prev_week = available_weeks[idx + 1] if idx + 1 < len(available_weeks) else None
        next_week = available_weeks[idx - 1] if idx > 0 else None

        summary = get_weekly_summary(service, sheet_id, tab_name)
        transactions = get_weekly_transactions(service, sheet_id, tab_name)

        return render_template('budget/index.html',
                               summary=summary,
                               transactions=transactions,
                               week_label=_week_label(tab_name),
                               prev_week=prev_week,
                               next_week=next_week,
                               is_current_week=is_current_week)

    except Exception as e:
        current_app.logger.error(f'Budget sheets error: {e}')
        flash('Unable to load budget data. Please try again.', 'error')
        return render_template('budget/index.html',
                               summary=None, transactions=[],
                               week_label=_week_label(tab_name),
                               prev_week=None, next_week=None,
                               is_current_week=is_current_week)
