# sheets.py
import os, json, datetime
from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = os.getenv("SHEET_ID")
SHEET_TAB = os.getenv("SHEET_TAB", "Sheet1")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _client():
    if not (SERVICE_JSON and SHEET_ID):
        raise RuntimeError("Google Sheets env not configured")
    info = json.loads(SERVICE_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc

def _ws():
    gc = _client()
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(SHEET_TAB)

def append_session(row):
    """
    row: dict with keys Date, Type, Details, Avg_HR, Avg_Split, Meters, RPE, Notes
    """
    ws = _ws()
    headers = ws.row_values(1)
    if not headers:
        headers = ["Date","Type","Details","Avg_HR","Avg_Split","Meters","RPE","Notes"]
        ws.append_row(headers)
    values = [row.get(h, "") for h in headers]
    ws.append_row(values, value_input_option="USER_ENTERED")

def recent_sessions(days=14):
    """
    Return a list[dict] of last N days of rows.
    """
    ws = _ws()
    headers = ws.row_values(1)
    rows = ws.get_all_values()[1:]  # skip header
    out = []
    cutoff = datetime.date.today() - relativedelta(days=days)
    for r in rows:
        if not r or not (len(r) > 0 and r[0]):
            continue
        try:
            d = parse_dt(r[0]).date()
        except Exception:
            continue
        if d >= cutoff:
            out.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})
    return out
