
from google_play_scraper import app, Sort, reviews
import logging
import time

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

    Raises:
        Exception: If no valid app information could be retrieved
    """
    app_info_list = []
    failed_packages = []

    for package in app_packages:
        try:
            # First try with Indonesian locale
            try:
                result = app(package, lang='id', country='id')
                app_info_list.append(result)
                logger.info(f"Successfully fetched info for app {package}")
            except Exception as e_id:
                # If Indonesian locale fails, try with English/US locale
                logger.warning(f"Failed to fetch app {package} with ID locale: {str(e_id)}")
                try:
                    result = app(package, lang='en', country='us')
                    app_info_list.append(result)
                    logger.info(f"Successfully fetched info for app {package} with EN locale")
                except Exception as e_en:
                    # Both locales failed
                    logger.error(f"Failed to fetch app {package} with both locales: {str(e_en)}")
                    failed_packages.append(package)
                    raise Exception(f"Could not fetch app info for {package}: {str(e_en)}")
        except Exception as e:
            logger.error(f"Error fetching info for app {package}: {str(e)}")
            failed_packages.append(package)

    # If we couldn't fetch any app info, raise an exception
    if not app_info_list and failed_packages:
        error_msg = f"Could not fetch information for any of the provided app IDs: {', '.join(failed_packages)}"
        logger.error(error_msg)
        raise Exception(error_msg)

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

        logger.info(f"Starting review fetch for {app_package}, count={count}, score={score}, sort={sort}")

        sort_order = Sort.MOST_RELEVANT if sort == 'most_relevant' else Sort.NEWEST

        # If score is provided, filter by that score
        if score:
            scores = [score]
        else:
            scores = list(range(1, 6))

        # Reduce reviews per score and add delay between requests
        per_score_count = max(5, min(20, count // len(scores)))
        logger.debug(f"Will fetch {per_score_count} reviews per score rating")

        # If we can't get enough reviews with filtering, try without filtering
        total_fetched = 0

        # First try with score filtering
        for score_filter in scores:
            try:
                logger.debug(f"Fetching reviews for {app_package} with score {score_filter}")

                # Add more specific error handling for the reviews fetch
                try:
                    rvs, _ = reviews(  # _ to ignore continuation_token
                        app_package,
                        lang='id',  # Try Indonesian first
                        country='id',
                        sort=sort_order,
                        count=per_score_count,
                        filter_score_with=score_filter
                    )

                    if not rvs:
                        logger.warning(f"No reviews found for score {score_filter} with lang=id")
                        # Try with English as fallback
                        try:
                            rvs, _ = reviews(  # _ to ignore continuation_token
                                app_package,
                                lang='en',
                                country='us',
                                sort=sort_order,
                                count=per_score_count,
                                filter_score_with=score_filter
                            )
                        except Exception as e_fallback:
                            logger.warning(f"Fallback to English also failed: {str(e_fallback)}")
                            continue

                except Exception as e:
                    logger.error(f"Error in reviews API call: {str(e)}")
                    # Try with English as fallback
                    try:
                        rvs, _ = reviews(  # _ to ignore continuation_token
                            app_package,
                            lang='en',
                            country='us',
                            sort=sort_order,
                            count=per_score_count,
                            filter_score_with=score_filter
                        )
                    except Exception as e_fallback:
                        logger.warning(f"Fallback to English also failed: {str(e_fallback)}")
                        continue

                # Process the reviews
                if rvs:
                    logger.info(f"Found {len(rvs)} reviews for score {score_filter}")
                    for r in rvs:
                        if r and isinstance(r, dict):
                            # Ensure all required fields exist
                            r['sortOrder'] = 'most_relevant' if sort_order == Sort.MOST_RELEVANT else 'newest'
                            r['appId'] = app_package

                            # Ensure all required fields have valid values
                            if 'reviewId' not in r or not r['reviewId']:
                                r['reviewId'] = f"generated-{len(app_reviews)}-{int(time.time())}"

                            if 'userName' not in r or not r['userName']:
                                r['userName'] = "Anonymous"

                            if 'score' not in r or not isinstance(r['score'], (int, float)):
                                r['score'] = score_filter

                            if 'content' not in r or not r['content']:
                                r['content'] = ""

                            if 'at' not in r:
                                r['at'] = int(time.time() * 1000)  # Current time in milliseconds

                            app_reviews.append(r)
                            total_fetched += 1
                else:
                    logger.warning(f"No reviews found for score {score_filter} after fallback attempts")

            except Exception as e:
                logger.warning(f"Error fetching reviews for score {score_filter}: {str(e)}")
                continue

        # If we didn't get enough reviews with filtering, try without filtering
        if total_fetched < count // 2:
            logger.info(f"Only fetched {total_fetched} reviews with filtering, trying without filtering")
            try:
                # Try without score filtering
                rvs, _ = reviews(  # _ to ignore continuation_token
                    app_package,
                    lang='id',
                    country='id',
                    sort=sort_order,
                    count=count - total_fetched
                )

                if rvs:
                    logger.info(f"Found {len(rvs)} additional reviews without filtering")
                    for r in rvs:
                        if r and isinstance(r, dict):
                            # Ensure all required fields exist
                            r['sortOrder'] = 'most_relevant' if sort_order == Sort.MOST_RELEVANT else 'newest'
                            r['appId'] = app_package

                            # Ensure all required fields have valid values
                            if 'reviewId' not in r or not r['reviewId']:
                                r['reviewId'] = f"generated-{len(app_reviews)}-{int(time.time())}"

                            if 'userName' not in r or not r['userName']:
                                r['userName'] = "Anonymous"

                            if 'score' not in r or not isinstance(r['score'], (int, float)):
                                r['score'] = 3  # Default to neutral

                            if 'content' not in r or not r['content']:
                                r['content'] = ""

                            if 'at' not in r:
                                r['at'] = int(time.time() * 1000)  # Current time in milliseconds

                            app_reviews.append(r)
            except Exception as e:
                logger.warning(f"Error fetching additional reviews without filtering: {str(e)}")

        # If we still don't have any reviews, create a dummy review
        if not app_reviews:
            logger.warning(f"No reviews found for {app_package}, creating dummy review")
            dummy_review = {
                'reviewId': f"dummy-{int(time.time())}",
                'userName': "No Reviews Available",
                'score': 0,
                'content': "No reviews are currently available for this app.",
                'at': int(time.time() * 1000),  # Current time in milliseconds
                'sortOrder': sort,
                'appId': app_package
            }
            app_reviews.append(dummy_review)

    except Exception as e:
        logger.error(f"Error fetching reviews for app {app_package}: {str(e)}")
        # Create a dummy review instead of raising an exception
        dummy_review = {
            'reviewId': f"error-{int(time.time())}",
            'userName': "Error Fetching Reviews",
            'score': 0,
            'content': f"An error occurred while fetching reviews: {str(e)}",
            'at': int(time.time() * 1000),  # Current time in milliseconds
            'sortOrder': sort,
            'appId': app_package
        }
        app_reviews.append(dummy_review)

    logger.info(f"Returning {len(app_reviews[:count])} reviews for {app_package}")
    return app_reviews[:count]  # Ensure we don't exceed requested count
