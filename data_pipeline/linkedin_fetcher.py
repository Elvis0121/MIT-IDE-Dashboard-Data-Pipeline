import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from sheets_manager import SheetsManager
import logging
import time
import random

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

class LinkedInFetcher:
    def __init__(self):
        """Initialize the LinkedIn Fetcher"""
        # Get API credentials from environment variables
        self.client_id = os.getenv('LINKEDIN_CLIENT_ID')
        self.client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        
        if not all([self.client_id, self.client_secret, self.access_token]):
            raise ValueError("LinkedIn API credentials must be set in .env file")
        
        self.sheets_manager = SheetsManager()
        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEET_ID environment variable is not set")
            
        self._init_linkedin_sheet()
        self.company_ids = self._get_company_ids()

    def _init_linkedin_sheet(self):
        """Initialize the LinkedIn worksheet if it doesn't exist"""
        try:
            sheet = self.sheets_manager.client.open_by_key(self.spreadsheet_id)
            
            # Check if LinkedIn sheet exists
            try:
                worksheet = sheet.worksheet('LinkedIn')
                logging.info("Found existing LinkedIn worksheet")
            except Exception:
                logging.info("Creating new LinkedIn worksheet")
                worksheet = sheet.add_worksheet('LinkedIn', 1000, 20)
                
                # Get IDs from environment variables
                mit_ide_company_id = os.getenv('MIT_IDE_COMPANY_ID')
                
                if not mit_ide_company_id:
                    raise ValueError("MIT_IDE_COMPANY_ID must be set in .env file")
                
                # Initialize headers
                headers = [
                    ['Name', 'Segment', 'Company ID', 'Company URL', 'Notes'],
                    ['MIT IDE', 'Main', mit_ide_company_id, 'https://www.linkedin.com/company/mit-initiative-on-the-digital-economy', '']
                ]
                
                # Update headers and format
                worksheet.update('A1:E2', headers)
                worksheet.format('A1:E1', {'textFormat': {'bold': True}})
                
                # Set column widths
                worksheet.set_column_width(1, 150)  # Name
                worksheet.set_column_width(2, 100)  # Segment
                worksheet.set_column_width(3, 200)  # Company ID
                worksheet.set_column_width(4, 250)  # Company URL
                worksheet.set_column_width(5, 200)  # Notes
                
                logging.info("Initialized LinkedIn worksheet with headers and sample data")
                
        except Exception as e:
            logging.error(f"Error initializing LinkedIn sheet: {str(e)}")
            raise

    def validate_company_id(self, company_id):
        """
        Validate a LinkedIn company ID by making an API request
        
        Args:
            company_id (str): The company ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            response = requests.get(
                f'https://api.linkedin.com/v2/organizations/{company_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                company_name = response.json().get('localizedName', 'Unknown')
                logging.info(f"Validated company ID {company_id} for company: {company_name}")
                return True
            else:
                logging.warning(f"No company found for ID: {company_id}")
                return False
        except Exception as e:
            logging.error(f"Error validating company ID {company_id}: {str(e)}")
            return False

    def _get_company_ids(self):
        """Fetch company IDs from the Google Sheet"""
        try:
            sheet = self.sheets_manager.client.open_by_key(self.spreadsheet_id)
            worksheet = sheet.worksheet('LinkedIn')
            
            # Get all records
            records = worksheet.get_all_records()
            logging.info(f"Found {len(records)} records in the LinkedIn sheet")
            
            # Extract and validate company IDs
            company_ids = []
            for record in records:
                if record.get('Company ID') and record['Company ID'].strip():
                    company_id = record['Company ID'].strip()
                    
                    # Validate company ID
                    if self.validate_company_id(company_id):
                        company_ids.append({
                            'name': record['Name'],
                            'segment': record['Segment'],
                            'company_id': company_id
                        })
                        logging.info(f"Added company: {record['Name']} with ID: {company_id}")
                    else:
                        logging.warning(f"Skipping invalid company ID for {record['Name']}: {company_id}")
            
            if not company_ids:
                logging.warning("No valid company IDs found in the LinkedIn sheet")
            else:
                logging.info(f"Total valid companies found: {len(company_ids)}")
                
            return company_ids
        except Exception as e:
            logging.error(f"Error fetching company IDs: {str(e)}")
            return []

    def get_company_stats(self, company_id):
        """Get company statistics."""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            # Get company statistics
            response = requests.get(
                f'https://api.linkedin.com/v2/organizations/{company_id}',
                headers=headers
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to get company data: {response.text}")
            
            company_data = response.json()
            
            # Get follower statistics
            follower_response = requests.get(
                f'https://api.linkedin.com/v2/organizations/{company_id}/followerStatistics',
                headers=headers
            )
            
            if follower_response.status_code != 200:
                raise ValueError(f"Failed to get follower statistics: {follower_response.text}")
            
            follower_stats = follower_response.json()
            
            # Create yearly statistics
            yearly_stats = []
            
            # Include all years from 2020 to 2025
            for year in range(2020, 2026):
                yearly_stats.append({
                    'Year': year,
                    'Followers': int(follower_stats.get('followerCount', 0)),
                    'Posts': 0,  # LinkedIn API doesn't provide historical post counts
                    'Engagement': 0  # LinkedIn API doesn't provide historical engagement metrics
                })

            # Add totals row
            yearly_stats.append({
                'Year': 'Totals',
                'Followers': int(follower_stats.get('followerCount', 0)),
                'Posts': 0,  # LinkedIn API doesn't provide total post count
                'Engagement': 0  # LinkedIn API doesn't provide total engagement metrics
            })

            # Convert to DataFrame and sort
            df = pd.DataFrame(yearly_stats)
            return df

        except Exception as e:
            logging.error(f"Error getting company stats: {str(e)}")
            raise

    def save_to_google_sheets(self, stats):
        """
        Save the processed data to Google Sheets
        """
        if not stats.empty:
            try:
                # Open the spreadsheet
                sheet = self.sheets_manager.client.open_by_key(self.spreadsheet_id)
                logging.info(f"Opened spreadsheet: {sheet.title}")
                
                # Save stats
                try:
                    worksheet = sheet.worksheet('LinkedIn Yearly Stats')
                    logging.info("Found existing LinkedIn Yearly Stats worksheet")
                except Exception:
                    logging.info("Creating new LinkedIn Yearly Stats worksheet")
                    worksheet = sheet.add_worksheet('LinkedIn Yearly Stats', 1000, 20)
                
                logging.info(f"Saving {len(stats)} rows to LinkedIn Yearly Stats")
                self.sheets_manager.update_sheet(self.spreadsheet_id, 'LinkedIn Yearly Stats', stats)
                logging.info("LinkedIn data saved successfully")
                
            except Exception as e:
                logging.error(f"Error saving LinkedIn data: {str(e)}")
                raise
        else:
            logging.warning("No LinkedIn data to save")

if __name__ == "__main__":
    fetcher = LinkedInFetcher()
    company_stats = fetcher.get_company_stats()
    print(company_stats)
    fetcher.save_to_google_sheets(company_stats) 