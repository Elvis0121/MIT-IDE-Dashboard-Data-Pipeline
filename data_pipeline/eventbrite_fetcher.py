import os
import requests
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from sheets_manager import SheetsManager
import logging

load_dotenv()

class EventbriteFetcher:
    def __init__(self):
        self.api_key = os.getenv('EVENTBRITE_API_KEY')
        self.private_token = os.getenv('EVENTBRITE_PRIVATE_TOKEN')
        self.base_url = 'https://www.eventbriteapi.com/v3'
        self.headers = {
            'Authorization': f'Bearer {self.private_token}',
            'Content-Type': 'application/json'
        }
        self.sheets_manager = SheetsManager()
        self.organization_id = self._get_organization_id()

    def _get_organization_id(self):
        """
        Get the organization ID associated with the private token
        """
        url = f"{self.base_url}/users/me/organizations/"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching organization ID: {response.text}")
        
        data = response.json()
        if not data.get('organizations'):
            raise Exception("No organizations found for this token")
        
        return data['organizations'][0]['id']

    def get_events(self, start_date='2020-01-01'):
        """
        Fetch all events from Eventbrite since the specified start date
        """
        events = []
        page = 1
        
        while True:
            url = f"{self.base_url}/organizations/{self.organization_id}/events/"
            params = {
                'start_date.range_start': start_date,
                'page': page,
                'expand': 'venue,ticket_classes'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Error fetching events: {response.text}")
            
            data = response.json()
            events.extend(data['events'])
            
            if not data['pagination']['has_more_items']:
                break
                
            page += 1
        
        return self._process_events(events)

    def _process_events(self, events):
        """
        Process raw event data into a structured format
        """
        processed_events = []
        for event in events:
            # Safely get venue name with proper null checking
            venue = event.get('venue')
            venue_name = venue.get('name', '') if venue else ''
            
            # Safely get ticket classes data
            ticket_classes = event.get('ticket_classes', [])
            quantity_sold = ticket_classes[0].get('quantity_sold', 0) if ticket_classes else 0
            
            processed_event = {
                'name': event['name']['text'],
                'date': event['start']['utc'],
                'attendees': quantity_sold,
                'venue': venue_name,
                'status': event['status']
            }
            processed_events.append(processed_event)
        
        df = pd.DataFrame(processed_events)
        # Convert datetime to string format for Google Sheets
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M:%S')
        return df

    def save_to_google_sheets(self, df, spreadsheet_id):
        """
        Save the processed data to Google Sheets
        """
        return self.sheets_manager.update_sheet(spreadsheet_id, 'Eventbrite Data', df)

if __name__ == "__main__":
    fetcher = EventbriteFetcher()
    events_df = fetcher.get_events()
    print(events_df) 