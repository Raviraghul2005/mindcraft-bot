"""
services/sheets.py — Google Sheets read/write operations.
"""
import gspread
from google.oauth2.service_account import Credentials
import config


def get_client():
    """Create and return an authorized gspread client."""
    cred_path = config.get_google_credentials_path()
    creds = Credentials.from_service_account_file(cred_path, scopes=config.GOOGLE_SCOPES)
    return gspread.authorize(creds)


def get_next_quote(client=None):
    """
    Fetch the next unprocessed quote from the Google Sheet.
    Returns (quote_text, row_index) or (None, None) if all are complete.
    """
    if client is None:
        client = get_client()
    
    sheet = client.open(config.SHEET_NAME).sheet1
    headers = sheet.row_values(1)
    
    status_col = headers.index("Status") + 1
    quote_col = headers.index("Quote") + 1
    
    all_rows = sheet.get_all_values()
    for idx, row in enumerate(all_rows[1:], start=2):
        status = row[status_col - 1].strip().lower()
        if status != "complete":
            quote = row[quote_col - 1].strip()
            if quote:
                return quote, idx, sheet
    
    return None, None, sheet


def mark_complete(sheet, row_index):
    """Mark a row as 'Complete' in the Status column."""
    headers = sheet.row_values(1)
    status_col = headers.index("Status") + 1
    sheet.update_cell(row_index, status_col, "Complete")
    print(f"✅ Marked row {row_index} as Complete in Google Sheets.")


def append_quotes(sheet, quotes):
    """Append a list of quotes to the sheet as new rows."""
    headers = sheet.row_values(1)
    quote_col = headers.index("Quote") + 1
    status_col = headers.index("Status") + 1
    
    for q in quotes:
        row = [""] * max(quote_col, status_col)
        row[quote_col - 1] = q
        row[status_col - 1] = "Pending"
        sheet.append_row(row, value_input_option="RAW")
    
    print(f"📝 Appended {len(quotes)} new quotes to the sheet.")


# ---- Music History Tracking (persists across GitHub Actions runs) ----

MUSIC_HISTORY_TAB = "Music_History"


def _get_music_history_sheet(client):
    """Get or create the Music_History worksheet tab."""
    spreadsheet = client.open(config.SHEET_NAME)
    try:
        return spreadsheet.worksheet(MUSIC_HISTORY_TAB)
    except gspread.exceptions.WorksheetNotFound:
        # Auto-create the tab with a header
        ws = spreadsheet.add_worksheet(title=MUSIC_HISTORY_TAB, rows=20, cols=1)
        ws.update_cell(1, 1, "Track")
        print(f"📋 Created '{MUSIC_HISTORY_TAB}' tab in Google Sheets.")
        return ws


def get_music_history(client):
    """Read the list of used track filenames from the Music_History sheet."""
    ws = _get_music_history_sheet(client)
    all_values = ws.col_values(1)
    # Skip header row
    return all_values[1:] if len(all_values) > 1 else []


def add_to_music_history(client, track_name):
    """Append a track filename to the Music_History sheet."""
    ws = _get_music_history_sheet(client)
    ws.append_row([track_name], value_input_option="RAW")


def reset_music_history(client):
    """Clear all track entries from the Music_History sheet (keep header)."""
    ws = _get_music_history_sheet(client)
    # Clear everything below the header
    all_values = ws.col_values(1)
    if len(all_values) > 1:
        # Batch clear rows 2 to end
        ws.batch_clear([f"A2:A{len(all_values)}"])
    print(f"🔄 Reset music history in Google Sheets.")

