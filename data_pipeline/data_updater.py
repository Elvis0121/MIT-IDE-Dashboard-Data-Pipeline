"""
Data Pipeline for MIT IDE Dashboard

This module implements a data pipeline for the MIT Initiative on the Digital Economy (IDE) Dashboard.
It handles automated data collection and updates from various sources including LinkedIn, YouTube,
Medium, Google Scholar, and Eventbrite.

The pipeline is designed to:
1. Collect data from multiple sources
2. Process and transform the data
3. Store the data in Google Sheets
4. Schedule regular updates

Author: MIT IDE Team
Date: 2024
"""

import os
import schedule
import time
from datetime import datetime
from eventbrite_fetcher import EventbriteFetcher
from scholar_fetcher import ScholarFetcher
from linkedin_fetcher import LinkedInFetcher
from budget_processor import BudgetProcessor
from youtube_fetcher import YouTubeFetcher
from medium_fetcher import MediumFetcher
from sheets_manager import SheetsManager
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_update.log'),
        logging.StreamHandler()
    ]
)

def validate_env_variables():
    """
    Validate that all required environment variables are present.
    
    This function checks for the presence of essential environment variables
    needed for the data pipeline to function properly.
    
    Required Variables:
        - GOOGLE_CREDENTIALS_FILE: Path to Google API credentials
        - GOOGLE_SHEET_ID: ID of the target Google Sheet
        - EVENTBRITE_API_KEY: API key for Eventbrite
        - EVENTBRITE_PRIVATE_TOKEN: Private token for Eventbrite
        - YOUTUBE_API_KEY: API key for YouTube Data API
    
    Raises:
        ValueError: If any required environment variable is missing
    """
    required_vars = [
        'GOOGLE_CREDENTIALS_FILE',
        'GOOGLE_SHEET_ID',
        'EVENTBRITE_API_KEY',
        'EVENTBRITE_PRIVATE_TOKEN',
        'YOUTUBE_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class DataUpdater:
    """
    Main class for managing data updates across multiple platforms.
    
    This class coordinates the collection and storage of data from various sources
    including LinkedIn, YouTube, Medium, Google Scholar, and Eventbrite. It handles
    initialization of all fetchers, manages the update schedule, and ensures proper
    error handling and logging.
    
    Attributes:
        eventbrite_fetcher (EventbriteFetcher): Handler for Eventbrite data
        scholar_fetcher (ScholarFetcher): Handler for Google Scholar data
        linkedin_fetcher (LinkedInFetcher): Handler for LinkedIn data
        budget_processor (BudgetProcessor): Handler for budget data
        youtube_fetcher (YouTubeFetcher): Handler for YouTube data
        medium_fetcher (MediumFetcher): Handler for Medium data
        sheets_manager (SheetsManager): Handler for Google Sheets operations
        spreadsheet_id (str): ID of the target Google Sheet
    """
    
    def __init__(self):
        """
        Initialize the DataUpdater with all necessary fetchers and configurations.
        
        This method:
        1. Validates environment variables
        2. Initializes all data fetchers
        3. Sets up Google Sheets connection
        4. Configures logging
        
        Raises:
            ValueError: If required environment variables are missing
            Exception: For any other initialization errors
        """
        try:
            logging.info("Initializing DataUpdater...")
            
            # Validate environment variables
            validate_env_variables()
            
            self.eventbrite_fetcher = EventbriteFetcher()
            self.scholar_fetcher = ScholarFetcher()
            self.linkedin_fetcher = LinkedInFetcher()
            self.budget_processor = BudgetProcessor()
            self.youtube_fetcher = YouTubeFetcher()
            self.medium_fetcher = MediumFetcher()
            self.sheets_manager = SheetsManager()
            self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
            
            if not self.spreadsheet_id:
                raise ValueError("GOOGLE_SHEET_ID environment variable is not set")
            
            logging.info("DataUpdater initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize DataUpdater: {str(e)}")
            raise
        
    def update_all_data(self):
        """
        Update all data sources and save to Google Sheets.
        
        This method coordinates the update process for all data sources:
        1. Budget data
        2. LinkedIn data (MIT IDE account)
        
        Each data source is updated independently, with proper error handling
        for each source. If one source fails, the others will still be updated.
        
        The method logs the success or failure of each update operation.
        
        Raises:
            Exception: If there's an error in the overall update process
        """
        try:
            # Update budget data
            budget_data = self.budget_processor.load_from_google_sheets(self.spreadsheet_id)
            if budget_data is not None and not budget_data.empty:
                self.budget_processor.save_to_google_sheets(budget_data, self.spreadsheet_id)
                logging.info("Budget data updated successfully")
            else:
                logging.warning("No budget data to update")

            # Update LinkedIn data for MIT IDE
            try:
                mit_ide_company_id = os.getenv('MIT_IDE_COMPANY_ID')
                if not mit_ide_company_id:
                    raise ValueError("MIT_IDE_COMPANY_ID environment variable is not set")
                
                company_stats = self.linkedin_fetcher.get_company_stats(mit_ide_company_id)
                if not company_stats.empty:
                    self.linkedin_fetcher.save_to_google_sheets(company_stats)
                    logging.info("LinkedIn data updated successfully for MIT IDE")
                else:
                    logging.warning("No LinkedIn data to update for MIT IDE")
            except Exception as e:
                logging.error(f"Error updating LinkedIn data for MIT IDE: {str(e)}")

        except Exception as e:
            logging.error(f"Error updating data: {str(e)}")
            raise

    def schedule_updates(self):
        """
        Schedule automatic updates every 3 months.
        
        This method sets up a schedule for regular data updates:
        - Updates are scheduled for 2 AM every day
        - The actual update only runs on the 1st of January, April, July, and October
        - The schedule runs continuously in the background
        
        The method uses the schedule library to manage the update timing.
        """
        # Schedule updates for the 1st of January, April, July, and October at 2 AM
        schedule.every().day.at("02:00").do(self._check_and_update)
        
        while True:
            schedule.run_pending()
            time.sleep(60)

    def _check_and_update(self):
        """
        Check if it's time for an update and run if necessary.
        
        This internal method:
        1. Checks if the current month is one of the update months (1, 4, 7, 10)
        2. If it is, runs the update_all_data method
        3. Logs the start and completion of the update process
        """
        current_month = datetime.now().month
        if current_month in [1, 4, 7, 10]:
            logging.info("Starting scheduled data update...")
            self.update_all_data()
            logging.info("Scheduled data update completed.")

if __name__ == "__main__":
    try:
        updater = DataUpdater()
        
        # Run initial update
        updater.update_all_data()
        
        # Start scheduled updates
        updater.schedule_updates()
    except Exception as e:
        logging.error(f"Fatal error in main: {str(e)}")
        raise 