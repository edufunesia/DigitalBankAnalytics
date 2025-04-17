import os
import logging
import json
import datetime
import pandas as pd
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from scraper import get_app_info, get_app_reviews
from analysis import analyze_sentiment, preprocess_reviews

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)

# Import models (after db is created to avoid circular imports)
from models import App, Review

# Custom template filters
@app.template_filter('format_number')
def format_number(value):
    """Format large numbers with commas as thousands separators"""
    return "{:,}".format(value) if value else 0

@app.template_filter('date')
def format_date(value):
    """Format datetime to readable date"""
    if isinstance(value, (int, float)):
        # Convert timestamp to datetime
        dt = datetime.datetime.fromtimestamp(value / 1000)
    else:
        dt = value
    return dt.strftime('%B %d, %Y') if dt else ""

# Default banking app packages to analyze
DEFAULT_APP_PACKAGES = [
    'com.alloapp.yump',  # allo bank
    'com.jago.digitalBanking',  # bank jago
    'id.co.bankbkemobile.digitalbank',  # seabank
    'com.btpn.dc',  # btpn jenius
    'com.bcadigital.blu',  # bank bca
    'id.co.bankraya.apps',  # rayabank
    'com.bnc.finance'  # neobank
]

@app.route('/')
def index():
    """Homepage showing the list of banking apps to analyze"""
    return render_template('index.html', app_packages=DEFAULT_APP_PACKAGES)

@app.route('/fetch_app_info', methods=['POST'])
def fetch_app_info():
    """API endpoint to fetch app information"""
    try:
        app_packages = request.json.get('app_packages', DEFAULT_APP_PACKAGES)
        logger.debug(f"Fetching info for apps: {app_packages}")
        
        # Validate app packages - check if they're not empty and have valid format
        validated_packages = []
        invalid_packages = []
        
        for pkg in app_packages:
            # Basic validation - ensure it's a string and has at least one period
            if isinstance(pkg, str) and pkg.strip():
                # If it's a URL, try to extract the package ID
                if 'play.google.com' in pkg:
                    # Try to extract package ID from URL
                    import re
                    match = re.search(r'id=([^&]+)', pkg)
                    if match:
                        pkg = match.group(1)
                
                # Simple format validation - most valid package names have at least one dot
                # But allow custom apps without dots too (like 'instagram')
                validated_packages.append(pkg)
            else:
                invalid_packages.append(pkg)
        
        if not validated_packages:
            return jsonify({
                'status': 'error',
                'message': 'No valid app packages provided'
            }), 400
        
        app_infos = get_app_info(validated_packages)
        
        # If no apps were found, return error
        if not app_infos:
            return jsonify({
                'status': 'error',
                'message': 'No app information found. Please check the app IDs or URLs provided.'
            }), 404
        
        # Store apps in database
        saved_apps = []
        for app_data in app_infos:
            # Check if app already exists in database
            existing_app = App.query.filter_by(app_id=app_data['appId']).first()
            
            if existing_app:
                # Update existing app with new data
                app_obj = App.from_scraper_data(app_data)
                existing_app.title = app_obj.title
                existing_app.developer = app_obj.developer
                existing_app.description = app_obj.description
                existing_app.summary = app_obj.summary
                existing_app.icon = app_obj.icon
                existing_app.score = app_obj.score
                existing_app.ratings_count = app_obj.ratings_count
                existing_app.reviews_count = app_obj.reviews_count
                existing_app.installs = app_obj.installs
                existing_app.price = app_obj.price
                existing_app.free = app_obj.free
                existing_app.currency = app_obj.currency
                existing_app.size = app_obj.size
                existing_app.min_android = app_obj.min_android
                existing_app.genre = app_obj.genre
                existing_app.genre_id = app_obj.genre_id
                existing_app.content_rating = app_obj.content_rating
                existing_app.version = app_obj.version
                existing_app.released = app_obj.released
                existing_app.updated = app_obj.updated
                existing_app.url = app_obj.url
                existing_app.screenshots = app_obj.screenshots
                existing_app.ratings = app_obj.ratings
                existing_app.recent_changes = app_obj.recent_changes
                existing_app.updated_at = datetime.datetime.utcnow()
                
                try:
                    db.session.commit()
                    logger.debug(f"Updated app in database: {app_data['appId']}")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error updating app in database: {str(e)}")
                
                saved_apps.append(existing_app)
            else:
                # Create new app
                app_obj = App.from_scraper_data(app_data)
                
                try:
                    db.session.add(app_obj)
                    db.session.commit()
                    logger.debug(f"Saved new app to database: {app_data['appId']}")
                    saved_apps.append(app_obj)
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error saving app to database: {str(e)}")
        
        # Convert to dataframe for easy manipulation
        df = pd.DataFrame(app_infos)
        
        # Calculate additional metrics for overview
        app_count = len(df)
        avg_rating = df['score'].mean()
        avg_reviews = df['reviews'].mean()
        
        response_data = {
            'status': 'success',
            'data': app_infos,
            'metrics': {
                'app_count': app_count,
                'avg_rating': round(avg_rating, 2),
                'avg_reviews': int(avg_reviews)
            }
        }
        
        # Add warning if some packages were invalid
        if invalid_packages:
            response_data['warnings'] = {
                'invalid_packages': invalid_packages,
                'message': 'Some app packages were invalid and were not processed'
            }
            
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error fetching app info: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch app info: {str(e)}"
        }), 500

@app.route('/app/<app_id>')
def app_details(app_id):
    """View for detailed information about a specific app"""
    try:
        # Validate app ID
        if 'play.google.com' in app_id:
            # Try to extract package ID from URL
            import re
            match = re.search(r'id=([^&]+)', app_id)
            if match:
                app_id = match.group(1)
            else:
                flash("Invalid app URL. Please provide a valid Google Play Store app URL or package ID.", "danger")
                return redirect(url_for('index'))
        
        # First check if app exists in our database
        db_app = App.query.filter_by(app_id=app_id).first()
        
        if db_app:
            # Convert to dictionary format for template (like what comes from the scraper)
            app_info = {
                'appId': db_app.app_id,
                'title': db_app.title,
                'developer': db_app.developer,
                'description': db_app.description,
                'summary': db_app.summary,
                'icon': db_app.icon,
                'score': db_app.score,
                'ratings': db_app.ratings_count,
                'reviews': db_app.reviews_count,
                'installs': db_app.installs,
                'price': db_app.price,
                'free': db_app.free,
                'currency': db_app.currency,
                'size': db_app.size,
                'androidVersion': db_app.min_android,
                'genre': db_app.genre,
                'genreId': db_app.genre_id,
                'contentRating': db_app.content_rating,
                'version': db_app.version,
                'released': db_app.released.timestamp() * 1000 if db_app.released else None,
                'updated': db_app.updated.timestamp() * 1000 if db_app.updated else None,
                'url': db_app.url,
                'screenshots': db_app.screenshots,
                'ratings': db_app.ratings,
                'recentChanges': db_app.recent_changes
            }
            
            logger.debug(f"Loaded app details from database: {app_id}")
            return render_template('app_details.html', app=app_info)
        
        # If not in database, fetch from API
        app_info_list = get_app_info([app_id])
        
        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))
        
        # Save the app to database for future use
        app_info = app_info_list[0]
        app_obj = App.from_scraper_data(app_info)
        
        try:
            db.session.add(app_obj)
            db.session.commit()
            logger.debug(f"Saved new app to database: {app_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving app to database: {str(e)}")
            
        return render_template('app_details.html', app=app_info)
    except IndexError:
        flash(f"No information found for app: {app_id}", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error retrieving app details: {str(e)}")
        flash(f"Error retrieving app details: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/app/<app_id>/reviews')
def app_reviews(app_id):
    """View for app reviews with sentiment analysis"""
    try:
        # Validate app ID
        if 'play.google.com' in app_id:
            # Try to extract package ID from URL
            import re
            match = re.search(r'id=([^&]+)', app_id)
            if match:
                app_id = match.group(1)
                # Redirect to the clean URL
                return redirect(url_for('app_reviews', app_id=app_id))
        
        # First check if app exists in our database
        db_app = App.query.filter_by(app_id=app_id).first()
        
        if db_app:
            logger.debug(f"Loaded app data from database for reviews page: {app_id}")
            return render_template('app_reviews.html', app_id=app_id, app_name=db_app.title)
        
        # If not in database, fetch from API
        app_info_list = get_app_info([app_id])
        
        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))
        
        # Save the app to database for future use
        app_info = app_info_list[0]
        app_obj = App.from_scraper_data(app_info)
        
        try:
            db.session.add(app_obj)
            db.session.commit()
            logger.debug(f"Saved new app to database from reviews page: {app_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving app to database from reviews page: {str(e)}")
            
        return render_template('app_reviews.html', app_id=app_id, app_name=app_info['title'])
    except Exception as e:
        logger.error(f"Error accessing app reviews: {str(e)}")
        flash(f"Error accessing app reviews: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/fetch_app_reviews', methods=['POST'])
def fetch_app_reviews():
    """API endpoint to fetch app reviews with sentiment analysis"""
    try:
        app_id = request.json.get('app_id')
        count = request.json.get('count', 50)
        sort = request.json.get('sort', 'most_relevant')
        
        logger.debug(f"Fetching reviews for app: {app_id}, count: {count}, sort: {sort}")
        
        # First, check if the app exists in our database
        app = App.query.filter_by(app_id=app_id).first()
        
        if not app:
            # Fetch app info and create app in database if it doesn't exist
            app_info_list = get_app_info([app_id])
            if app_info_list:
                app_obj = App.from_scraper_data(app_info_list[0])
                try:
                    db.session.add(app_obj)
                    db.session.commit()
                    logger.debug(f"Created app in database before fetching reviews: {app_id}")
                    app = app_obj
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error creating app in database: {str(e)}")
        
        if not app:
            return jsonify({
                'status': 'error',
                'message': f"App not found: {app_id}"
            }), 404
        
        # Now fetch the reviews
        reviews = get_app_reviews(app_id, count=count, sort=sort)
        
        # Process reviews with sentiment analysis
        processed_reviews = preprocess_reviews(reviews)
        sentiment_results = analyze_sentiment(processed_reviews)
        
        # Combine reviews with sentiment scores and store in database
        saved_reviews = []
        for i, review_data in enumerate(reviews):
            sentiment_score = sentiment_results[i].polarity
            sentiment_label = 'positive' if sentiment_score > 0 else ('negative' if sentiment_score < 0 else 'neutral')
            
            # Add sentiment data to the review object for response
            review_data['sentiment_score'] = sentiment_score
            review_data['sentiment_label'] = sentiment_label
            
            # Check if review already exists in database
            existing_review = Review.query.filter_by(review_id=review_data['reviewId']).first()
            
            if existing_review:
                # Update sentiment analysis if it exists
                existing_review.sentiment_score = sentiment_score
                existing_review.sentiment_label = sentiment_label
                existing_review.updated_at = datetime.datetime.utcnow()
                
                try:
                    db.session.commit()
                    logger.debug(f"Updated review sentiment in database: {review_data['reviewId']}")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error updating review in database: {str(e)}")
                
                saved_reviews.append(existing_review)
            else:
                # Create new review
                review_obj = Review.from_scraper_data(
                    review_data, 
                    app.id, 
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label
                )
                
                try:
                    db.session.add(review_obj)
                    db.session.commit()
                    logger.debug(f"Saved new review to database: {review_data['reviewId']}")
                    saved_reviews.append(review_obj)
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error saving review to database: {str(e)}")
        
        # Calculate sentiment metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r['sentiment_label'] == 'positive'),
            'neutral': sum(1 for r in reviews if r['sentiment_label'] == 'neutral'),
            'negative': sum(1 for r in reviews if r['sentiment_label'] == 'negative')
        }
        
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts,
            'saved_count': len(saved_reviews)
        })
    except Exception as e:
        logger.error(f"Error fetching app reviews: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch app reviews: {str(e)}"
        }), 500

@app.route('/about')
def about():
    """About page with information about the project"""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
