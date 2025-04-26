
from google_play_scraper import app, Sort, reviews
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_app_info(app_packages):
    """
    Scrape app information from Google Play Store
    
    Args:
        app_packages (list): List of app package names
        
    Returns:
        list: List of dictionaries containing app information
    """
    app_info_list = []
    
    for package in app_packages:
        try:
            result = app(package, lang='id', country='id')
            app_info_list.append(result)
        except Exception as e:
            logger.error(f"Error fetching info for app {package}: {str(e)}")
    
    return app_info_list

def get_app_reviews(app_package, count=100, score=None, sort='most_relevant'):
    """
    Scrape reviews for an app from Google Play Store
    
    Args:
        app_package (str): App package name
        count (int): Number of reviews to fetch
        score (int, optional): Filter by score (1-5)
        sort (str): Sort by 'most_relevant' or 'newest'
        
    Returns:
        list: List of dictionaries containing review information
    """
    app_reviews = []
    
    try:
        # Validate input parameters
        if not app_package:
            logger.error("App package name is required")
            return []
            
        sort_order = Sort.MOST_RELEVANT if sort == 'most_relevant' else Sort.NEWEST
        
        # If score is provided, filter by that score
        if score:
            scores = [score]
        else:
            scores = list(range(1, 6))
        
        # Reduce reviews per score and add delay between requests
        per_score_count = min(10, count // len(scores))
        
        for score_filter in scores:
            try:
                logger.debug(f"Fetching reviews for {app_package} with score {score_filter}")
                
                # Add more specific error handling for the reviews fetch
                try:
                    rvs, continuation_token = reviews(
                        app_package,
                        lang='id',
                        country='id',
                        sort=sort_order,
                        count=per_score_count,
                        filter_score_with=score_filter
                    )
                    
                    if not rvs:
                        logger.warning(f"No reviews found for score {score_filter}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Error in reviews API call: {str(e)}")
                    continue
                
                for r in rvs:
                    if r and isinstance(r, dict):
                        r['sortOrder'] = 'most_relevant' if sort_order == Sort.MOST_RELEVANT else 'newest'
                        r['appId'] = app_package
                        app_reviews.append(r)
                
            except Exception as e:
                logger.warning(f"Error fetching reviews for score {score_filter}: {str(e)}")
                continue
            
    except Exception as e:
        logger.error(f"Error fetching reviews for app {app_package}: {str(e)}")
        raise
    
    return app_reviews[:count]  # Ensure we don't exceed requested count
