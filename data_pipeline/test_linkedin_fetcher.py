import os
import logging
from dotenv import load_dotenv, find_dotenv
from linkedin_fetcher import LinkedInFetcher

# Set up logging
logging.basicConfig(level=logging.INFO)

def main():
    try:
        # Initialize the LinkedIn fetcher
        fetcher = LinkedInFetcher()
        logging.info("Successfully initialized LinkedIn fetcher")
        
        # Get company IDs from the fetcher
        company_ids = fetcher.company_ids
        if not company_ids:
            raise ValueError("No valid company IDs found")
            
        logging.info(f"Found {len(company_ids)} valid companies")
        
        # Test getting company stats for each company
        for company in company_ids:
            logging.info(f"Fetching stats for company: {company['name']}")
            
            # Get company statistics
            stats = fetcher.get_company_stats(company['company_id'])
            logging.info(f"Successfully retrieved company stats for {company['name']}")
            
            # Keep only the desired columns
            stats = stats[['Year', 'Followers', 'Posts', 'Engagement']]
            logging.info(f"Stats shape: {stats.shape}")
            logging.info(f"Years covered: {stats['Year'].tolist()}")
            
            # Save to Google Sheets
            logging.info(f"Saving stats for {company['name']} to Google Sheets")
            fetcher.save_to_google_sheets(stats)
            logging.info(f"Successfully saved stats for {company['name']}")
            
    except Exception as e:
        logging.error(f"Error in test script: {str(e)}")
        raise

if __name__ == "__main__":
    main() 