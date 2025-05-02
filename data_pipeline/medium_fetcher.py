import requests
import pandas as pd
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

class MediumAPIClient:
    """
    Client for accessing Medium data using the unofficial Medium API (medium2.p.rapidapi.com)
    """
    
    def __init__(self, api_key):
        """
        Initialize the Medium API Client
        
        Args:
            api_key (str): API key for Medium API v2
        """
        self.api_key = api_key
        self.base_url = "https://medium2.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "medium2.p.rapidapi.com"
        }
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # seconds between requests
        
        self.logger.info("Initialized Medium API Client")
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the Medium API with proper error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            self._wait_for_rate_limit()
            self.logger.info(f"Making request to {url} with params: {params}")
            response = requests.get(url, headers=self.headers, params=params)
            
            # Log response details for debugging
            self.logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', self.min_request_interval))
                self.logger.warning(f"Rate limited. Waiting {retry_after} seconds.")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)  # Retry the request
            
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            
            # Try to parse JSON response
            try:
                return response.json()
            except ValueError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                self.logger.error(f"Response text: {response.text[:500]}...")
                raise
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to {url}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status code: {e.response.status_code}")
                self.logger.error(f"Response body: {e.response.text[:500]}...")
            raise
    
    def get_user_id(self, username):
        """Get the user ID for a given username."""
        try:
            # Search for user first
            search_response = self._make_request("/search/users", params={"query": username})
            users = search_response.get('users', [])
            
            if not users:
                raise ValueError(f"No user found with username: {username}")
            
            # Return the first user ID found
            return users[0]
        except Exception as e:
            self.logger.error(f"Error getting user ID for {username}: {str(e)}")
            raise
    
    def get_user_info(self, user_id):
        """Get user information for a given user ID."""
        try:
            endpoint = f"/user/{user_id}"
            return self._make_request(endpoint)
        except Exception as e:
            self.logger.error(f"Error getting user info for {user_id}: {str(e)}")
            raise
    
    def get_user_articles(self, user_id, next_token=None):
        """Get articles for a given user ID."""
        try:
            # Search for articles by user
            params = {"query": f"author:{user_id}"}
            if next_token:
                params["next"] = next_token
                
            response = self._make_request("/search/articles", params=params)
            articles = response.get('articles', [])
            
            # Check if there are more pages
            next_token = response.get('next')
            if next_token:
                self.logger.info(f"Found next page token: {next_token}")
                # Recursively get more articles
                more_articles = self.get_user_articles(user_id, next_token)
                articles.extend(more_articles)
            
            self.logger.info(f"Retrieved {len(articles)} articles for user {user_id}")
            return articles
        except Exception as e:
            self.logger.error(f"Error getting articles for user {user_id}: {str(e)}")
            raise
    
    def get_article_info(self, article_id):
        """Get information about a specific article."""
        try:
            endpoint = f"/article/{article_id}"
            return self._make_request(endpoint)
        except Exception as e:
            self.logger.error(f"Error getting article info for {article_id}: {str(e)}")
            raise
    
    def get_article_content(self, article_id):
        """Get the content of a specific article."""
        try:
            endpoint = f"/article/{article_id}/content"
            return self._make_request(endpoint)
        except Exception as e:
            self.logger.error(f"Error getting article content for {article_id}: {str(e)}")
            raise
    
    def search_articles(self, query, limit=20):
        """
        Search for articles
        
        Args:
            query (str): Search query
            limit (int, optional): Maximum number of articles to retrieve
            
        Returns:
            list: List of article data
        """
        try:
            response = self._make_request("/search/articles", params={"query": query})
            articles = response.get('articles', [])
            
            # Get detailed info for each article
            detailed_articles = []
            for article_id in articles[:limit]:
                try:
                    article_info = self.get_article_info(article_id)
                    if article_info:
                        # Parse date
                        published_at = None
                        if 'published_at' in article_info:
                            try:
                                published_at = datetime.strptime(article_info['published_at'], '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                self.logger.warning(f"Could not parse date: {article_info['published_at']}")
                        
                        # Create article object
                        article_data = {
                            'id': article_info.get('id'),
                            'title': article_info.get('title', 'Untitled'),
                            'url': article_info.get('url', ''),
                            'published_at': published_at,
                            'claps': article_info.get('claps', 0),
                            'voters': article_info.get('voters', 0),
                            'reading_time': article_info.get('reading_time', 0),
                            'responses': article_info.get('responses_count', 0)
                        }
                        
                        detailed_articles.append(article_data)
                        
                except Exception as e:
                    self.logger.error(f"Error processing article {article_id}: {e}")
            
            return detailed_articles
        except Exception as e:
            self.logger.error(f"Error searching articles: {str(e)}")
            return []
    
    def get_publication_id(self, publication_slug):
        """
        Get a publication's ID from its slug
        
        Args:
            publication_slug (str): Publication slug (part after medium.com/)
            
        Returns:
            str: Publication ID
        """
        self.logger.info(f"Getting publication ID for slug: {publication_slug}")
        
        # Clean up the slug
        publication_slug = publication_slug.replace('@', '').replace('-', '_')
        
        endpoint = "publication/id_for/slug"
        response = self._make_request(endpoint, params={"slug": publication_slug})
        
        if 'id' in response:
            self.logger.info(f"Publication ID for {publication_slug}: {response['id']}")
            return response['id']
        else:
            self.logger.error(f"Failed to get publication ID for {publication_slug}")
            self.logger.error(f"Response: {response}")
            raise ValueError(f"Could not get publication ID for {publication_slug}")
    
    def get_publication_info(self, publication_id):
        """
        Get detailed information about a publication
        
        Args:
            publication_id (str): Publication ID
            
        Returns:
            dict: Publication information
        """
        self.logger.info(f"Getting publication info for publication ID: {publication_id}")
        
        endpoint = f"publication/{publication_id}"
        return self._make_request(endpoint)
    
    def get_publication_articles(self, publication_id):
        """
        Get articles from a publication
        
        Args:
            publication_id (str): Publication ID
            
        Returns:
            list: List of article IDs
        """
        self.logger.info(f"Getting articles for publication ID: {publication_id}")
        
        endpoint = f"publication/{publication_id}/articles"
        response = self._make_request(endpoint)
        
        return response
    
    def get_user_followers(self, user_id, limit=100):
        """
        Get a user's followers
        
        Args:
            user_id (str): User ID
            limit (int, optional): Maximum number of followers to retrieve
            
        Returns:
            list: List of follower user IDs
        """
        self.logger.info(f"Getting followers for user ID: {user_id}")
        
        endpoint = f"user/{user_id}/followers"
        params = {"count": min(limit, 1000)}  # API has a limit
        
        return self._make_request(endpoint, params)


class MediumStatsClient:
    """
    A client for collecting statistics about Medium users and publications
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the Medium Stats Client
        
        Args:
            api_key (str, optional): API key for mediumapi.com
        """
        self.logger = logging.getLogger('MediumStatsClient')
        self.api_client = MediumAPIClient(api_key)
        
        self.logger.info("Initialized Medium Stats Client")
    
    def get_entity_info(self, entity_name):
        """
        Get information about a Medium entity (user or publication)
        
        Args:
            entity_name (str): Username or publication slug
            
        Returns:
            dict: Entity information
        """
        self.logger.info(f"Getting entity info for: {entity_name}")
        
        # Try as user first
        try:
            user_id = self.api_client.get_user_id(entity_name)
            user_info = self.api_client.get_user_info(user_id)
            return {
                'type': 'user',
                'id': user_id,
                'info': user_info
            }
        except Exception as e:
            self.logger.info(f"Not a user, trying as publication: {e}")
        
        # Then try as publication
        try:
            publication_id = self.api_client.get_publication_id(entity_name)
            publication_info = self.api_client.get_publication_info(publication_id)
            return {
                'type': 'publication',
                'id': publication_id,
                'info': publication_info
            }
        except Exception as e:
            self.logger.error(f"Not a publication either: {e}")
            raise ValueError(f"Could not find entity: {entity_name}")
    
    def get_entity_articles(self, entity_info, limit=100):
        """
        Get articles from a Medium entity
        
        Args:
            entity_info (dict): Entity information from get_entity_info
            limit (int, optional): Maximum number of articles to retrieve
            
        Returns:
            list: List of article data
        """
        self.logger.info(f"Getting articles for entity: {entity_info['type']} {entity_info['id']}")
        
        if entity_info['type'] == 'user':
            articles_response = self.api_client.get_user_articles(entity_info['id'])
        else:  # publication
            articles_response = self.api_client.get_publication_articles(entity_info['id'])
        
        # Get article IDs
        article_ids = articles_response[:limit]
        
        # Get article details
        articles = []
        for article_id in article_ids:
            try:
                article_info = self.api_client.get_article_info(article_id)
                
                # Parse date
                published_at = None
                if 'first_published_at' in article_info:
                    published_at = datetime.fromtimestamp(article_info['first_published_at'] / 1000)
                
                # Create article object
                article = {
                    'id': article_id,
                    'title': article_info.get('title', 'Untitled'),
                    'url': article_info.get('url', ''),
                    'published_at': published_at,
                    'claps': article_info.get('claps', 0),
                    'voters': article_info.get('voters', 0),
                    'reading_time': article_info.get('reading_time', 0),
                    'responses': article_info.get('responses_count', 0)
                }
                
                articles.append(article)
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)
            
            except Exception as e:
                self.logger.error(f"Error getting article info for {article_id}: {e}")
        
        self.logger.info(f"Fetched {len(articles)} articles")
        return articles
    
    def get_stats(self, entity_name):
        """
        Get statistics for a Medium entity
        
        Args:
            entity_name (str): Username or publication slug
            
        Returns:
            dict: Entity statistics
        """
        self.logger.info(f"Getting stats for: {entity_name}")
        
        try:
            # Get user ID first
            user_id = self.api_client.get_user_id(entity_name)
            self.logger.info(f"Found user ID: {user_id}")
            
            # Get user info for follower count
            try:
                user_info = self.api_client.get_user_info(user_id)
                follower_count = user_info.get('followers_count', 0)
                self.logger.info(f"Found follower count: {follower_count}")
            except Exception as e:
                self.logger.error(f"Error getting user info: {e}")
                follower_count = 0
            
            # Get all articles for the user
            articles = self.api_client.get_user_articles(user_id)
            self.logger.info(f"Found {len(articles)} articles")
            
            if articles:
                # Get detailed info for each article
                detailed_articles = []
                for article_id in articles:
                    try:
                        article_info = self.api_client.get_article_info(article_id)
                        if article_info:
                            # Parse date
                            published_at = None
                            if 'published_at' in article_info:
                                try:
                                    published_at = datetime.strptime(article_info['published_at'], '%Y-%m-%d %H:%M:%S')
                                    self.logger.debug(f"Parsed date for article {article_id}: {published_at}")
                                except ValueError:
                                    self.logger.warning(f"Could not parse date: {article_info['published_at']}")
                            
                            # Create article object
                            article_data = {
                                'id': article_info.get('id'),
                                'title': article_info.get('title', 'Untitled'),
                                'url': article_info.get('url', ''),
                                'published_at': published_at,
                                'claps': article_info.get('claps', 0),
                                'voters': article_info.get('voters', 0),
                                'reading_time': article_info.get('reading_time', 0),
                                'responses': article_info.get('responses_count', 0)
                            }
                            
                            detailed_articles.append(article_data)
                            self.logger.debug(f"Processed article: {article_data['title']} ({article_data['claps']} claps)")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing article {article_id}: {e}")
                
                # Create a DataFrame
                df = pd.DataFrame(detailed_articles)
                self.logger.info(f"Created DataFrame with {len(df)} articles")
                
                # Convert date column
                if 'published_at' in df.columns:
                    df['published_at'] = pd.to_datetime(df['published_at'])
                    df['year'] = df['published_at'].dt.year
                    df['quarter'] = df['published_at'].dt.quarter
                    
                    # Log year distribution
                    year_counts = df['year'].value_counts().sort_index()
                    self.logger.info(f"Year distribution:\n{year_counts}")
                
                # Create a range of years from 2019 to 2025
                years = range(2019, 2026)
                
                # Group by year
                if 'year' in df.columns:
                    yearly_stats = []
                    
                    # Calculate stats for each year
                    for year in years:
                        year_data = df[df['year'] == year]
                        if not year_data.empty:
                            stats = {
                                'year': year,
                                'total_articles': len(year_data),
                                'total_claps': year_data['claps'].sum(),
                                'total_voters': year_data['voters'].sum(),
                                'total_responses': year_data['responses'].sum()
                            }
                            self.logger.info(f"Year {year} stats: {stats}")
                        else:
                            # Add empty stats for future years
                            stats = {
                                'year': year,
                                'total_articles': 0,
                                'total_claps': 0,
                                'total_voters': 0,
                                'total_responses': 0
                            }
                        yearly_stats.append(stats)
                    
                    # Create DataFrame from yearly stats
                    stats_df = pd.DataFrame(yearly_stats)
                    
                    # Add total row
                    total_row = pd.DataFrame([{
                        'year': 'Total',
                        'total_articles': len(df),
                        'total_claps': df['claps'].sum(),
                        'total_voters': df['voters'].sum(),
                        'total_responses': df['responses'].sum()
                    }])
                    
                    # Combine yearly stats with total
                    stats_df = pd.concat([stats_df, total_row], ignore_index=True)
                    
                    # Add follower count to 'Total' row
                    mask = stats_df['year'] == 'Total'
                    stats_df.loc[mask, 'followers'] = follower_count
                    
                    self.logger.info(f"Final stats DataFrame:\n{stats_df}")
                    
                    return {
                        'info': {
                            'entity_type': 'user',
                            'entity_name': entity_name,
                            'follower_count': follower_count
                        },
                        'stats': stats_df
                    }
                else:
                    self.logger.warning("No year column in articles DataFrame")
            
            self.logger.warning(f"No articles found for {entity_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {str(e)}")
            return None


class MediumFetcher:
    """
    A class to fetch and process Medium stats for a publication or user
    """
    
    def __init__(self):
        """Initialize the Medium Fetcher"""
        # Setup logging
        self.logger = logging.getLogger('MediumFetcher')
        
        # Get Medium profile name from env
        self.medium_entity = os.getenv('MEDIUM_ENTITY_NAME')
        if not self.medium_entity:
            raise ValueError("MEDIUM_ENTITY_NAME environment variable is not set")
        
        # Get API key from env
        self.api_key = os.getenv('MEDIUM_API_KEY')
        if not self.api_key:
            raise ValueError("MEDIUM_API_KEY environment variable is not set")
        
        # Initialize the Medium Stats Client
        self.client = MediumStatsClient(self.api_key)
        self.logger.info(f"Initialized MediumFetcher for entity: {self.medium_entity}")

    def get_article_stats(self):
        """
        Fetch article statistics for Medium entity
        
        Returns:
            pandas.DataFrame: DataFrame with article stats
        """
        try:
            # Get entity stats
            stats_data = self.client.get_stats(self.medium_entity)
            
            if stats_data:
                # Extract information
                entity_info = stats_data['info']
                stats_df = stats_data['stats']
                
                # Log basic info
                self.logger.info(f"Entity type: {entity_info['entity_type']}")
                self.logger.info(f"Entity name: {entity_info['entity_name']}")
                self.logger.info(f"Followers: {entity_info['follower_count']}")
                
                # Add follower count to 'Total' row
                mask = stats_df['year'] == 'Total'
                stats_df.loc[mask, 'followers'] = entity_info['follower_count']
                
                return stats_df
            else:
                self.logger.warning("No stats data returned")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error fetching articles: {str(e)}")
            return pd.DataFrame()

    def save_to_google_sheets(self, stats):
        """
        Save the processed data to Google Sheets
        """
        if stats.empty:
            self.logger.warning("No Medium data to save")
            return
            
        try:
            from sheets_manager import SheetsManager
            self.logger.info("Initializing SheetsManager...")
            self.sheets_manager = SheetsManager()
            
            self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
            if not self.spreadsheet_id:
                raise ValueError("GOOGLE_SHEET_ID environment variable is not set")
            
            self.logger.info(f"Using spreadsheet ID: {self.spreadsheet_id}")
            
            try:
                self.logger.info("Attempting to open spreadsheet...")
                sheet = self.sheets_manager.client.open_by_key(self.spreadsheet_id)
                self.logger.info(f"Successfully opened spreadsheet: {sheet.title}")
                
                try:
                    self.logger.info("Looking for 'Medium Stats' worksheet...")
                    worksheet = sheet.worksheet('Medium Stats')
                    self.logger.info("Found existing Medium Stats worksheet")
                except Exception as e:
                    self.logger.info(f"Creating new Medium Stats worksheet: {str(e)}")
                    worksheet = sheet.add_worksheet('Medium Stats', 1000, 20)
                
                self.logger.info(f"Preparing to save {len(stats)} rows to Medium Stats")
                self.logger.info(f"Data preview:\n{stats.head()}")
                
                self.sheets_manager.update_sheet(self.spreadsheet_id, 'Medium Stats', stats)
                self.logger.info("Medium data saved successfully to Google Sheets")
                
            except Exception as e:
                self.logger.error(f"Error during Google Sheets operation: {str(e)}")
                if hasattr(e, 'response'):
                    self.logger.error(f"Response status: {e.response.status_code}")
                    self.logger.error(f"Response body: {e.response.text}")
                raise
                
        except ImportError as e:
            self.logger.error(f"Failed to import SheetsManager: {str(e)}")
            self.logger.warning("SheetsManager not available - skipping Google Sheets export")
            self.logger.info("Here's the data instead:")
            print(stats)
            
            # Save to CSV instead
            csv_file = 'medium_stats.csv'
            stats.to_csv(csv_file, index=False)
            self.logger.info(f"Saved data to {csv_file}")
        except Exception as e:
            self.logger.error(f"Unexpected error saving to Google Sheets: {str(e)}")
            # Save to CSV as fallback
            csv_file = 'medium_stats.csv'
            stats.to_csv(csv_file, index=False)
            self.logger.info(f"Saved data to {csv_file} as fallback")


if __name__ == "__main__":
    try:
        # Initialize the fetcher
        fetcher = MediumFetcher()
        
        # Get article stats
        article_stats = fetcher.get_article_stats()
        
        # Print stats
        print("\nMedium Article Statistics:")
        print(article_stats)
        
        # Save to Google Sheets
        try:
            fetcher.save_to_google_sheets(article_stats)
        except Exception as e:
            logging.error(f"Could not save to Google Sheets: {e}")
            # Save to CSV instead
            if not article_stats.empty:
                csv_file = 'medium_stats.csv'
                article_stats.to_csv(csv_file, index=False)
                logging.info(f"Saved data to {csv_file}")
    except Exception as e:
        logging.error(f"Error running MediumFetcher: {e}")