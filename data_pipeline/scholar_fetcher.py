import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sheets_manager import SheetsManager
import requests
import logging
from bs4 import BeautifulSoup
import time
import random

load_dotenv()

class ScholarFetcher:
    def __init__(self):
        self.scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            os.getenv('GOOGLE_CREDENTIALS_FILE'), self.scope)
        self.client = gspread.authorize(self.credentials)
        self.sheets_manager = SheetsManager()
        # Use the main spreadsheet ID for both reading and writing
        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.researcher_ids = self._get_researcher_ids()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _get_researcher_ids(self):
        """
        Fetch researcher IDs from the Google Sheet
        """
        try:
            sheet = self.client.open_by_key(self.spreadsheet_id)
            worksheet = sheet.worksheet('Scholars')
            
            # Get all records
            records = worksheet.get_all_records()
            logging.info(f"Found {len(records)} records in the source sheet")
            
            # Extract researcher IDs from Google Scholar URLs
            researcher_ids = []
            for record in records:
                if record.get('Google Scholar') and record['Google Scholar'].strip():
                    # Extract the user ID from the Google Scholar URL
                    url = record['Google Scholar']
                    if 'user=' in url:
                        user_id = url.split('user=')[1].split('&')[0]
                        researcher_ids.append({
                            'name': record['Name'],
                            'segment': record['Segment'],
                            'scholar_id': user_id
                        })
                        logging.info(f"Found researcher: {record['Name']} with ID: {user_id}")
            
            logging.info(f"Total researchers found: {len(researcher_ids)}")
            return researcher_ids
        except Exception as e:
            logging.error(f"Error fetching researcher IDs: {str(e)}")
            return []

    def get_publications(self):
        """
        Fetch publication data for all researchers
        """
        try:
            all_publications = []
            logging.info(f"Starting to fetch publications for {len(self.researcher_ids)} researchers")
            
            for researcher in self.researcher_ids:
                try:
                    # Add random delay to avoid rate limiting
                    delay = random.uniform(2, 5)
                    logging.info(f"Waiting {delay:.2f} seconds before fetching {researcher['name']}'s publications")
                    time.sleep(delay)
                    
                    # Fetch all pages of publications
                    page = 0
                    has_more = True
                    while has_more:
                        # Fetch publications for each researcher
                        url = f"https://scholar.google.com/citations?user={researcher['scholar_id']}&hl=en&cstart={page*100}&pagesize=100"
                        logging.info(f"Fetching URL: {url}")
                        response = requests.get(url, headers=self.headers)
                        
                        if response.status_code == 200:
                            publications, h_index = self._parse_publications(response.text, researcher)
                            if page == 0:  # Only set h-index once
                                researcher['h_index'] = h_index
                            
                            if publications:
                                all_publications.extend(publications)
                                logging.info(f"Found {len(publications)} publications on page {page+1} for {researcher['name']}")
                                page += 1
                            else:
                                has_more = False
                        else:
                            logging.error(f"Failed to fetch publications for {researcher['name']}. Status code: {response.status_code}")
                            has_more = False
                    
                    logging.info(f"Total publications found for {researcher['name']}: {len([p for p in all_publications if p['researcher_name'] == researcher['name']])}")
                        
                except Exception as e:
                    logging.error(f"Error fetching publications for {researcher['name']}: {str(e)}")
                    continue
            
            logging.info(f"Total publications found: {len(all_publications)}")
            if all_publications:
                # Create DataFrame
                df = pd.DataFrame(all_publications)
                df['date'] = pd.to_datetime(df['date'])
                
                # Get unique years
                years = sorted(df['year'].unique())
                
                # Create yearly stats with years as columns
                yearly_stats = df.groupby(['researcher_name', 'researcher_segment']).agg({
                    'citations': 'sum',
                    'title': 'count'
                }).reset_index()
                yearly_stats.rename(columns={'title': 'total_publications', 'citations': 'total_citations'}, inplace=True)
                
                # Add yearly columns
                for year in years:
                    year_data = df[df['year'] == year].groupby(['researcher_name']).agg({
                        'citations': 'sum',
                        'title': 'count'
                    }).reset_index()
                    yearly_stats[f'publications_{year}'] = yearly_stats['researcher_name'].map(
                        year_data.set_index('researcher_name')['title']
                    ).fillna(0).astype(int)
                    yearly_stats[f'citations_{year}'] = yearly_stats['researcher_name'].map(
                        year_data.set_index('researcher_name')['citations']
                    ).fillna(0).astype(int)
                
                # Add h-index to stats
                h_index_df = pd.DataFrame(self.researcher_ids)
                yearly_stats = yearly_stats.merge(h_index_df[['name', 'h_index']], 
                                                left_on='researcher_name', 
                                                right_on='name', 
                                                how='left')
                yearly_stats.drop('name', axis=1, inplace=True)
                
                return yearly_stats
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logging.error(f"Error fetching publications: {str(e)}")
            return pd.DataFrame()

    def _parse_publications(self, html_content, researcher):
        """
        Parse HTML content to extract publication data using BeautifulSoup
        """
        publications = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find h-index from the citations table
        h_index = 0
        try:
            # Find the citations table
            citations_table = soup.find('table', {'id': 'gsc_rsb_st'})
            if citations_table:
                # Find the row containing h-index
                rows = citations_table.find_all('tr')
                for row in rows:
                    if 'h-index' in row.text:
                        h_index_cell = row.find_all('td')[1]  # Second cell contains the value
                        h_index = int(h_index_cell.text.strip())
                        break
        except Exception as e:
            logging.error(f"Error extracting h-index for {researcher['name']}: {str(e)}")
        
        # Find all publication entries
        entries = soup.find_all('tr', class_='gsc_a_tr')
        logging.info(f"Found {len(entries)} publication entries in HTML")
        
        for entry in entries:
            try:
                # Extract title and link
                title_elem = entry.find('a', class_='gsc_a_at')
                title = title_elem.text if title_elem else ''
                
                # Extract authors and venue
                authors_venue = entry.find('div', class_='gs_gray').text
                authors, venue = authors_venue.split(' - ') if ' - ' in authors_venue else (authors_venue, '')
                
                # Extract citations
                citations_elem = entry.find('a', class_='gsc_a_ac')
                citations = int(citations_elem.text) if citations_elem and citations_elem.text.strip() else 0
                
                # Extract year
                year_elem = entry.find('span', class_='gsc_a_h')
                year = int(year_elem.text) if year_elem and year_elem.text.strip() else None
                
                if year and year >= 2020:  # Only include publications from 2020 onwards
                    publication = {
                        'title': title,
                        'authors': authors,
                        'venue': venue,
                        'citations': citations,
                        'year': year,
                        'researcher_name': researcher['name'],
                        'researcher_segment': researcher['segment'],
                        'date': f"{year}-01-01"  # Using January 1st as default date
                    }
                    publications.append(publication)
                    logging.debug(f"Added publication: {title} ({year}) with {citations} citations")
                    
            except Exception as e:
                logging.error(f"Error parsing publication entry: {str(e)}")
                continue
                
        return publications, h_index

    def save_to_google_sheets(self, stats):
        """
        Save the processed data to Google Sheets
        """
        if not stats.empty:
            try:
                # Open the spreadsheet
                sheet = self.client.open_by_key(self.spreadsheet_id)
                logging.info(f"Opened spreadsheet: {sheet.title}")
                
                # Save stats
                try:
                    worksheet = sheet.worksheet('Scholar Yearly Stats')
                    logging.info("Found existing Scholar Yearly Stats worksheet")
                except gspread.WorksheetNotFound:
                    logging.info("Creating new Scholar Yearly Stats worksheet")
                    worksheet = sheet.add_worksheet('Scholar Yearly Stats', 1000, 20)
                
                logging.info(f"Saving {len(stats)} rows to Scholar Yearly Stats")
                self.sheets_manager.update_sheet(self.spreadsheet_id, 'Scholar Yearly Stats', stats)
                logging.info("Scholar data saved successfully")
                
            except Exception as e:
                logging.error(f"Error saving scholar data: {str(e)}")
                raise
        else:
            logging.warning("No scholar data to save")

if __name__ == "__main__":
    fetcher = ScholarFetcher()
    publications_data = fetcher.get_publications()
    print(publications_data)
    # Use the main spreadsheet ID from environment variables
    fetcher.save_to_google_sheets(publications_data) 