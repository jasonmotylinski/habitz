from datetime import date, timedelta, datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_sheets_service(service_account_path: str):
    """Create an authenticated read-only Google Sheets service."""
    creds = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'],
    )
    return build('sheets', 'v4', credentials=creds)


def get_weekly_tab_name(for_date: date) -> str:
    """Return YYYYMMDD of the most recent Saturday on or before for_date."""
    days_since_saturday = (for_date.weekday() - 5) % 7
    saturday = for_date - timedelta(days=days_since_saturday)
    return saturday.strftime('%Y%m%d')


def get_available_weeks(service, sheet_id: str) -> list[str]:
    """Return all YYYYMMDD tab names sorted descending."""
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    tabs = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
    weeks = []
    for t in tabs:
        try:
            datetime.strptime(t, '%Y%m%d')
            weeks.append(t)
        except ValueError:
            pass
    return sorted(weeks, reverse=True)


def get_weekly_summary(service, sheet_id: str, tab_name: str) -> dict:
    """Return budget summary for the given weekly tab.

    Sheet column F structure:
      F1 = =SUM(D2:D98)   total expenses (includes overage row)
      F2 = =1600+150       budget for the week
      F3 = =F2-F1          remaining
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f'{tab_name}!F1:F3',
        valueRenderOption='UNFORMATTED_VALUE',
    ).execute()
    rows = result.get('values', [])

    def val(i: int) -> float:
        try:
            return float(rows[i][0]) if i < len(rows) and rows[i] else 0.0
        except (ValueError, TypeError):
            return 0.0

    total_spent = val(0)
    budget = val(1)
    remaining = val(2)
    pct = round((total_spent / budget * 100)) if budget else 0

    return {
        'budget': budget,
        'total_spent': total_spent,
        'remaining': remaining,
        'pct_spent': pct,
    }


def get_weekly_transactions(service, sheet_id: str, tab_name: str) -> list[dict]:
    """Return transactions from row 3 onwards (skips header + overage rows).

    Columns: A=Date, B=Expense/name, C=Source, D=Amount
    Returns list sorted by date descending.
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f'{tab_name}!A3:D',
        valueRenderOption='UNFORMATTED_VALUE',
    ).execute()
    rows = result.get('values', [])

    def _normalize_date(val) -> str:
        """Convert a raw date cell value to YYYY-MM-DD string.

        Google Sheets returns date cells as integer serials with UNFORMATTED_VALUE
        (epoch: Dec 30 1899). String dates (e.g. '2026-03-20') are passed through.
        """
        if isinstance(val, (int, float)):
            return (date(1899, 12, 30) + timedelta(days=int(val))).isoformat()
        return str(val)

    transactions = [
        {
            'date': _normalize_date(r[0]) if len(r) > 0 else '',
            'name': r[1] if len(r) > 1 else '',
            'source': r[2] if len(r) > 2 else '',
            'amount': r[3] if len(r) > 3 else '',
        }
        for r in rows if r
    ]
    transactions.sort(key=lambda t: t['date'], reverse=True)
    return transactions
