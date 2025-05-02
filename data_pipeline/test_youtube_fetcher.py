import os
import logging
from dotenv import load_dotenv, find_dotenv
from youtube_fetcher import YouTubeFetcher

# Set up logging
logging.basicConfig(level=logging.INFO)

def main():
    try:
        # Initialize the YouTube fetcher
        fetcher = YouTubeFetcher()
        logging.info("Successfully initialized YouTube fetcher")
        
        # Get channel IDs from the fetcher
        channel_ids = fetcher.channel_ids
        if not channel_ids:
            raise ValueError("No valid channel IDs found")
            
        logging.info(f"Found {len(channel_ids)} valid channels")
        
        # Test getting video stats for each channel
        for channel in channel_ids:
            logging.info(f"Fetching stats for channel: {channel['name']}")
            
            # Get video statistics
            stats = fetcher.get_video_stats(channel['channel_id'])
            logging.info(f"Successfully retrieved video stats for {channel['name']}")
            
            # Keep only the desired columns
            stats = stats[['Year', 'Videos', 'Views', 'Subscribers']]
            logging.info(f"Stats shape: {stats.shape}")
            logging.info(f"Years covered: {stats['Year'].tolist()}")
            
            # Save to Google Sheets
            logging.info(f"Saving stats for {channel['name']} to Google Sheets")
            fetcher.save_to_google_sheets(stats)
            logging.info(f"Successfully saved stats for {channel['name']}")
            
    except Exception as e:
        logging.error(f"Error in test script: {str(e)}")
        raise

if __name__ == "__main__":
    main() 