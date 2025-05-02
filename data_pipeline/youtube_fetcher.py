import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from sheets_manager import SheetsManager
import logging
from googleapiclient.discovery import build # type: ignore
import time
import random

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

class YouTubeFetcher:
    def __init__(self):
        """Initialize the YouTube Fetcher"""
        # Use hardcoded API key for testing
        self.api_key = 'AIzaSyCQm4fnNSCVUb11NnFWM2_HAoP7gFy3a2E'
        
        try:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            logging.info("Successfully initialized YouTube API client")
        except Exception as e:
            raise ValueError(f"Failed to initialize YouTube API client. Please check your API key: {str(e)}")
        
        self.sheets_manager = SheetsManager()
        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEET_ID environment variable is not set")
            
        self._init_youtube_sheet()
        self.channel_ids = self._get_channel_ids()

    def _init_youtube_sheet(self):
        """Initialize the YouTube worksheet if it doesn't exist"""
        try:
            sheet = self.sheets_manager.client.open_by_key(self.spreadsheet_id)
            
            # Check if YouTube sheet exists
            try:
                worksheet = sheet.worksheet('YouTube')
                logging.info("Found existing YouTube worksheet")
            except Exception:
                logging.info("Creating new YouTube worksheet")
                worksheet = sheet.add_worksheet('YouTube', 1000, 20)
                
                # Get IDs from environment variables
                mit_ide_user_id = os.getenv('MIT_IDE_USER_ID')
                mit_ide_channel_id = os.getenv('MIT_IDE_CHANNEL_ID')
                
                if not all([mit_ide_user_id, mit_ide_channel_id]):
                    raise ValueError("MIT_IDE_USER_ID and MIT_IDE_CHANNEL_ID must be set in .env file")
                
                # Initialize headers
                headers = [
                    ['Name', 'Segment', 'User ID', 'Channel ID', 'Channel URL', 'Notes'],
                    ['MIT IDE', 'Main', mit_ide_user_id, mit_ide_channel_id, 'https://www.youtube.com/@MITIDE', '']
                ]
                
                # Update headers and format
                worksheet.update('A1:F2', headers)
                worksheet.format('A1:F1', {'textFormat': {'bold': True}})
                
                # Set column widths
                worksheet.set_column_width(1, 150)  # Name
                worksheet.set_column_width(2, 100)  # Segment
                worksheet.set_column_width(3, 200)  # User ID
                worksheet.set_column_width(4, 200)  # Channel ID
                worksheet.set_column_width(5, 250)  # Channel URL
                worksheet.set_column_width(6, 200)  # Notes
                
                logging.info("Initialized YouTube worksheet with headers and sample data")
                
        except Exception as e:
            logging.error(f"Error initializing YouTube sheet: {str(e)}")
            raise

    def validate_channel_id(self, channel_id):
        """
        Validate a YouTube channel ID by making an API request
        
        Args:
            channel_id (str): The channel ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            response = self.youtube.channels().list(
                part='snippet',
                id=channel_id
            ).execute()
            
            if response['items']:
                channel_title = response['items'][0]['snippet']['title']
                logging.info(f"Validated channel ID {channel_id} for channel: {channel_title}")
                return True
            else:
                logging.warning(f"No channel found for ID: {channel_id}")
                return False
        except Exception as e:
            logging.error(f"Error validating channel ID {channel_id}: {str(e)}")
            return False

    def _get_channel_ids(self):
        """Fetch channel IDs from the Google Sheet"""
        try:
            sheet = self.sheets_manager.client.open_by_key(self.spreadsheet_id)
            worksheet = sheet.worksheet('YouTube')
            
            # Get all records
            records = worksheet.get_all_records()
            logging.info(f"Found {len(records)} records in the YouTube sheet")
            
            # Extract and validate channel IDs
            channel_ids = []
            for record in records:
                if record.get('Channel ID') and record['Channel ID'].strip():
                    channel_id = record['Channel ID'].strip()
                    
                    # Validate channel ID
                    if self.validate_channel_id(channel_id):
                        channel_ids.append({
                            'name': record['Name'],
                            'segment': record['Segment'],
                            'channel_id': channel_id
                        })
                        logging.info(f"Added channel: {record['Name']} with ID: {channel_id}")
                    else:
                        logging.warning(f"Skipping invalid channel ID for {record['Name']}: {channel_id}")
            
            if not channel_ids:
                logging.warning("No valid channel IDs found in the YouTube sheet")
            else:
                logging.info(f"Total valid channels found: {len(channel_ids)}")
                
            return channel_ids
        except Exception as e:
            logging.error(f"Error fetching channel IDs: {str(e)}")
            return []

    def get_video_stats(self, channel_id):
        """Get video statistics for a channel."""
        try:
            # Get channel statistics
            channel_response = self.youtube.channels().list(
                part='statistics',
                id=channel_id
            ).execute()

            channel_stats = {
                'subscribers': int(channel_response['items'][0]['statistics']['subscriberCount']),
                'total_views': int(channel_response['items'][0]['statistics']['viewCount']),
                'total_videos': int(channel_response['items'][0]['statistics']['videoCount'])
            }

            # Get all videos for the channel
            videos = []
            next_page_token = None
            total_videos_fetched = 0

            while True:
                request = self.youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    maxResults=50,
                    type='video',
                    pageToken=next_page_token,
                    order='date'  # Get videos in chronological order
                )
                response = request.execute()

                for item in response['items']:
                    video_id = item['id']['videoId']
                    published_at = item['snippet']['publishedAt']
                    year = int(published_at[:4])
                    
                    # Get video statistics
                    video_response = self.youtube.videos().list(
                        part='statistics',
                        id=video_id
                    ).execute()
                    
                    if video_response['items']:
                        stats = video_response['items'][0]['statistics']
                        videos.append({
                            'year': year,
                            'views': int(stats.get('viewCount', 0))
                        })
                        total_videos_fetched += 1

                next_page_token = response.get('nextPageToken')
                if not next_page_token or total_videos_fetched >= channel_stats['total_videos']:
                    break

            # Create yearly statistics
            yearly_stats = []
            
            # Include all years from 2020 to 2025, even if there are no videos
            for year in range(2020, 2026):
                year_videos = [v for v in videos if v['year'] == year]
                yearly_stats.append({
                    'Year': year,
                    'Videos': int(len(year_videos)),
                    'Views': int(sum(v['views'] for v in year_videos))
                })

            # Add totals row with all videos and current subscribers
            yearly_stats.append({
                'Year': 'Totals',
                'Videos': int(channel_stats['total_videos']),  # Use channel's total video count
                'Views': int(channel_stats['total_views']),  # Use channel's total view count
                'Subscribers': int(channel_stats['subscribers'])  # Add current subscriber count
            })

            # Convert to DataFrame and sort
            df = pd.DataFrame(yearly_stats)
            return df

        except Exception as e:
            logging.error(f"Error getting video stats: {str(e)}")
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
                    worksheet = sheet.worksheet('YouTube Yearly Stats')
                    logging.info("Found existing YouTube Yearly Stats worksheet")
                except Exception:
                    logging.info("Creating new YouTube Yearly Stats worksheet")
                    worksheet = sheet.add_worksheet('YouTube Yearly Stats', 1000, 20)
                
                logging.info(f"Saving {len(stats)} rows to YouTube Yearly Stats")
                self.sheets_manager.update_sheet(self.spreadsheet_id, 'YouTube Yearly Stats', stats)
                logging.info("YouTube data saved successfully")
                
            except Exception as e:
                logging.error(f"Error saving YouTube data: {str(e)}")
                raise
        else:
            logging.warning("No YouTube data to save")

if __name__ == "__main__":
    fetcher = YouTubeFetcher()
    video_stats = fetcher.get_video_stats()
    print(video_stats)
    fetcher.save_to_google_sheets(video_stats) 