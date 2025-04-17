import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from scraper import get_app_info, get_app_reviews
from analysis import analyze_sentiment, preprocess_reviews
import pandas as pd
import json
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

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
        
        app_info_list = get_app_info([app_id])
        
        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))
            
        app_info = app_info_list[0]
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
        
        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])
        
        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))
            
        return render_template('app_reviews.html', app_id=app_id, app_name=app_info_list[0]['title'])
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
        
        reviews = get_app_reviews(app_id, count=count, sort=sort)
        
        # Process reviews with sentiment analysis
        processed_reviews = preprocess_reviews(reviews)
        sentiment_results = analyze_sentiment(processed_reviews)
        
        # Combine reviews with sentiment scores
        for i, review in enumerate(reviews):
            review['sentiment_score'] = sentiment_results[i].polarity
            review['sentiment_label'] = 'positive' if sentiment_results[i].polarity > 0 else ('negative' if sentiment_results[i].polarity < 0 else 'neutral')
        
        # Calculate sentiment metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r['sentiment_label'] == 'positive'),
            'neutral': sum(1 for r in reviews if r['sentiment_label'] == 'neutral'),
            'negative': sum(1 for r in reviews if r['sentiment_label'] == 'negative')
        }
        
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts
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
