import os
import logging
from googleapiclient.discovery import build

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_channel_id():
    """Test the YouTube channel ID directly"""
    try:
        # Use API key directly for testing
        api_key = 'AIzaSyCQm4fnNSCVUb11NnFWM2_HAoP7gFy3a2E'
        channel_id = 'UC8DqDLFZCni7Jkys3N3818w'
        
        # Print API key details to verify it's loaded correctly
        logging.info(f"API key length: {len(api_key)}")
        
        # Initialize YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        logging.info("Successfully initialized YouTube API client")
        
        # Test channel ID
        logging.info(f"Testing channel ID: {channel_id}")
        response = youtube.channels().list(
            part='snippet',
            id=channel_id
        ).execute()
        
        if response['items']:
            channel_title = response['items'][0]['snippet']['title']
            logging.info(f"Successfully validated channel ID. Channel title: {channel_title}")
        else:
            logging.warning(f"No channel found for ID: {channel_id}")
        
    except Exception as e:
        logging.error(f"Error testing channel ID: {str(e)}")
        raise

if __name__ == "__main__":
    test_channel_id() 