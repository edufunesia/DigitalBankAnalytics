
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
        sort_order = Sort.MOST_RELEVANT if sort == 'most_relevant' else Sort.NEWEST
        
        # If score is provided, filter by that score
        if score:
            scores = [score]
        else:
            scores = list(range(1, 6))
            
        for score_filter in scores:
            logger.debug(f"Fetching reviews for {app_package} with score {score_filter}")
            
            # Calculate how many reviews to fetch per score to maintain roughly equal distribution
            per_score_count = count // len(scores)
            
            rvs, _ = reviews(
                app_package,
                lang='id',
                country='id',
                sort=sort_order,
                count=per_score_count,
                filter_score_with=score_filter
            )
            
            for r in rvs:
                r['sortOrder'] = 'most_relevant' if sort_order == Sort.MOST_RELEVANT else 'newest'
                r['appId'] = app_package
                
            app_reviews.extend(rvs)
            
    except Exception as e:
        logger.error(f"Error fetching reviews for app {app_package}: {str(e)}")
    
    return app_reviews
