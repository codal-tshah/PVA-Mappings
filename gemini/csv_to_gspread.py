import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv
import os

# --- CONFIGURATION ---
# Path to the JSON key you download from Google Cloud Console
SERVICE_ACCOUNT_FILE = '/Users/tshah/Documents/PVA Mappings/service_account.json' 
# The exact URL or ID of your Google Sheet Template
GOOGLE_SHEET_ID = '1UkVoXcVWArr1s3gR73hU1DDL79XAV_ULWrhsEXS6UR0'
OUTPUT_DIR = "Workbench_Analysis_Output"
def upload_csvs_to_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        print(f"Connected to Google Sheet: {spreadsheet.title}")
        
        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith(".csv"):
                tab_name = filename.replace(".csv", "")
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                try:
                    worksheet = spreadsheet.worksheet(tab_name)
                except gspread.exceptions.WorksheetNotFound:
                    print(f"Tab '{tab_name}' not found in Google Sheet. Creating it...")
                    worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="20")
                
                # Read CSV and push
                with open(filepath, 'r', encoding='utf-8') as f:
                    csv_data = list(csv.reader(f))
                    
                if csv_data:
                    print(f"Uploading {len(csv_data)} rows to tab '{tab_name}'...")
                    worksheet.clear() # Clear existing data
                    worksheet.update(values=csv_data, range_name='A1')
                    
        print("All CSVs successfully synced to Google Sheets!")
        
    except Exception as e:
        print(f"Google Sheets Sync Failed: {e}")

if __name__ == "__main__":
    upload_csvs_to_gsheets()