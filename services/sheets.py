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


def get_processed_count(client=None):
    """Return the total number of 'Complete' rows (used for music rotation)."""
    if client is None:
        client = get_client()
    
    sheet = client.open(config.SHEET_NAME).sheet1
    headers = sheet.row_values(1)
    status_col = headers.index("Status") + 1
    
    all_rows = sheet.get_all_values()
    count = sum(1 for row in all_rows[1:] if row[status_col - 1].strip().lower() == "complete")
    return count
