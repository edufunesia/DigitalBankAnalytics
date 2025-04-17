import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from scraper import get_app_info, get_app_reviews
from analysis import analyze_sentiment, preprocess_reviews
import pandas as pd
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

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
        
        app_infos = get_app_info(app_packages)
        
        # Convert to dataframe for easy manipulation
        df = pd.DataFrame(app_infos)
        
        # Calculate additional metrics for overview
        app_count = len(df)
        avg_rating = df['score'].mean()
        avg_reviews = df['reviews'].mean()
        
        return jsonify({
            'status': 'success',
            'data': app_infos,
            'metrics': {
                'app_count': app_count,
                'avg_rating': round(avg_rating, 2),
                'avg_reviews': int(avg_reviews)
            }
        })
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
        app_info = get_app_info([app_id])[0]
        return render_template('app_details.html', app=app_info)
    except Exception as e:
        flash(f"Error retrieving app details: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/app/<app_id>/reviews')
def app_reviews(app_id):
    """View for app reviews with sentiment analysis"""
    return render_template('app_reviews.html', app_id=app_id)

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
