import pandas as pd
from sheets_manager import SheetsManager
import logging

class BudgetProcessor:
    def __init__(self):
        self.sheets_manager = SheetsManager()
        self.budget_data = None

    def load_from_google_sheets(self, spreadsheet_id):
        """
        Load budget data from Google Sheets
        """
        try:
            # Open the spreadsheet and worksheet
            sheet = self.sheets_manager.client.open_by_key(spreadsheet_id)
            worksheet = sheet.worksheet('Budget Data')
            
            # Get all records
            records = worksheet.get_all_records()
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Extract the annual budget row
            annual_budget_row = df[df.iloc[:, 0] == 'IDE Annual Budget']
            
            if not annual_budget_row.empty:
                # Get all budget values starting from 2020
                budget_values = []
                years = []
                current_year = 2020
                col_index = 1  # Start from the second column (first column is the label)
                
                while True:
                    try:
                        value = annual_budget_row.iloc[0, col_index]
                        if pd.isna(value):  # Stop if we hit an empty cell
                            break
                        budget_values.append(value)
                        years.append(str(current_year))
                        current_year += 1
                        col_index += 1
                    except IndexError:
                        break
                
                # Create a simple DataFrame with years and budget values
                self.budget_data = pd.DataFrame({
                    'Year': years,
                    'Budget': budget_values
                })
                logging.info("Budget data loaded successfully")
            else:
                logging.warning("Annual budget row not found in the sheet")
                self.budget_data = pd.DataFrame(columns=['Year', 'Budget'])
                
        except Exception as e:
            logging.error(f"Error loading budget data: {str(e)}")
            raise

    def save_to_google_sheets(self, spreadsheet_id):
        """
        Save processed budget data to Google Sheets
        """
        try:
            if self.budget_data is not None and not self.budget_data.empty:
                self.sheets_manager.update_sheet(spreadsheet_id, 'Processed Budget', self.budget_data)
                logging.info("Budget data saved successfully")
            else:
                logging.warning("No budget data to save")
        except Exception as e:
            logging.error(f"Error saving budget data: {str(e)}")
            raise

if __name__ == "__main__":
    processor = BudgetProcessor()
    
    # Example usage
    processor.load_from_google_sheets('spreadsheet_id')
    processor.save_to_google_sheets('spreadsheet_id') 