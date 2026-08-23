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


def _get_or_add_column(sheet, headers, column_name):
    """Return the 1-indexed column number for `column_name`, creating the
    header (appending a new column) if it doesn't exist yet."""
    if column_name in headers:
        return headers.index(column_name) + 1
    col = len(headers) + 1
    sheet.update_cell(1, col, column_name)
    headers.append(column_name)
    return col


def mark_complete(sheet, row_index, youtube_url=None):
    """Mark a row as 'Complete' in the Status column.
    Optionally records the published YouTube URL in a 'YouTube_URL' column
    (auto-created if missing) so performance can later be filtered by style.
    """
    headers = sheet.row_values(1)
    status_col = headers.index("Status") + 1
    sheet.update_cell(row_index, status_col, "Complete")

    if youtube_url:
        url_col = _get_or_add_column(sheet, headers, "YouTube_URL")
        sheet.update_cell(row_index, url_col, youtube_url)

    print(f"✅ Marked row {row_index} as Complete in Google Sheets.")


def append_quotes(sheet, quotes):
    """Append a list of quotes to the sheet as new rows.

    `quotes` may be a list of strings, or a list of (quote_text, style)
    tuples — in the latter case the style is recorded in a 'Style' column
    (auto-created if missing) for later performance comparison.
    """
    headers = sheet.row_values(1)
    quote_col = headers.index("Quote") + 1
    status_col = headers.index("Status") + 1

    has_style = quotes and isinstance(quotes[0], (tuple, list))
    style_col = _get_or_add_column(sheet, headers, "Style") if has_style else None

    for entry in quotes:
        quote_text, style = entry if has_style else (entry, None)
        row = [""] * max(quote_col, status_col, style_col or 0)
        row[quote_col - 1] = quote_text
        row[status_col - 1] = "Pending"
        if style_col:
            row[style_col - 1] = style
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

