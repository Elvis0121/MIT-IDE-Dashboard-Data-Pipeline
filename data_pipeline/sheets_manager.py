import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from dotenv import load_dotenv
import logging

load_dotenv()

class SheetsManager:
    def __init__(self):
        self.scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
        try:
            credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
            if not credentials_file:
                raise ValueError("GOOGLE_CREDENTIALS_FILE environment variable is not set")
            
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(f"Credentials file not found at: {credentials_file}")
            
            logging.info(f"Using credentials file: {credentials_file}")
            
            self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
                credentials_file, self.scope)
            self.client = gspread.authorize(self.credentials)
            logging.info("Successfully authorized with Google Sheets API")
        except Exception as e:
            logging.error(f"Failed to initialize Google Sheets client: {str(e)}")
            raise

    def update_sheet(self, spreadsheet_id, worksheet_name, data):
        """
        Update a specific worksheet in a Google Sheet with new data
        """
        try:
            logging.info(f"Attempting to update worksheet '{worksheet_name}' in spreadsheet '{spreadsheet_id}'")
            
            # Open the spreadsheet
            sheet = self.client.open_by_key(spreadsheet_id)
            logging.info(f"Successfully opened spreadsheet: {sheet.title}")
            
            # Get or create the worksheet
            try:
                worksheet = sheet.worksheet(worksheet_name)
                logging.info(f"Found existing worksheet: {worksheet_name}")
            except gspread.WorksheetNotFound:
                logging.info(f"Worksheet '{worksheet_name}' not found, creating new one")
                worksheet = sheet.add_worksheet(worksheet_name, 1000, 20)
            
            # Clear existing data
            worksheet.clear()
            logging.info("Cleared existing data from worksheet")
            
            # Convert DataFrame to list of lists
            if isinstance(data, pd.DataFrame):
                # Replace NaN values with empty strings
                data = data.fillna('')
                data = [data.columns.tolist()] + data.values.tolist()
            
            # Update the worksheet
            worksheet.update('A1', data)
            logging.info(f"Successfully updated worksheet with {len(data)} rows of data")
            
            return True
        except Exception as e:
            logging.error(f"Error updating sheet: {str(e)}")
            raise

    def create_sheets(self, spreadsheet_id):
        """
        Create necessary worksheets in the Google Sheet
        """
        try:
            logging.info(f"Creating sheets in spreadsheet '{spreadsheet_id}'")
            sheet = self.client.open_by_key(spreadsheet_id)
            logging.info(f"Successfully opened spreadsheet: {sheet.title}")
            
            # List of required worksheets
            required_sheets = [
                'Eventbrite Data',
                'Scholar Yearly Stats',
                'Scholar Author Stats',
                'LinkedIn Organization Stats',
                'LinkedIn Post Metrics',
                'Budget Summary',
                'Budget Trends'
            ]
            
            # Create or get worksheets
            worksheets = {}
            for sheet_name in required_sheets:
                try:
                    worksheet = sheet.worksheet(sheet_name)
                    logging.info(f"Found existing worksheet: {sheet_name}")
                except gspread.WorksheetNotFound:
                    logging.info(f"Creating new worksheet: {sheet_name}")
                    worksheet = sheet.add_worksheet(sheet_name, 1000, 20)
                worksheets[sheet_name] = worksheet
            
            logging.info("Successfully created/verified all required worksheets")
            return worksheets
        except Exception as e:
            logging.error(f"Error creating sheets: {str(e)}")
            raise 