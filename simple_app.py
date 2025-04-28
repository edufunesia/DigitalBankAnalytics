import os
import logging
import csv
import io
import pandas as pd
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
import datetime
from scraper import get_app_info, get_app_reviews
from models import db, ScrapedApp, ScrapedReview

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.template_filter('date')
def format_date(value):
    """Format datetime to readable date"""
    if isinstance(value, (int, float)):
        try:
            # Convert timestamp to datetime (milliseconds)
            dt = datetime.datetime.fromtimestamp(value / 1000)
        except Exception:
            try:
                # Try as seconds if milliseconds fails
                dt = datetime.datetime.fromtimestamp(value)
            except Exception:
                # If all conversions fail, return the original value
                return str(value)
    else:
        dt = value

    # Format the datetime object
    try:
        return dt.strftime('%B %d, %Y') if dt else ""
    except Exception:
        # If formatting fails, return the string representation
        return str(dt) if dt else ""

@app.route('/')
def index():
    """Homepage with app list"""
    return "Simple App Running - Use /app/{app_id}/reviews to test review fetching"

@app.route('/app/<app_id>/reviews')
def app_reviews(app_id):
    """Page to display app reviews with sentiment analysis"""
    try:
        # Clean up app_id if it has query parameters
        if '?' in app_id:
            app_id = app_id.split('?')[0]
            # Redirect to the clean URL
            return redirect(url_for('app_reviews', app_id=app_id))

        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))

        return render_template('simple_reviews.html', app_id=app_id, app_name=app_info_list[0]['title'])
    except Exception as e:
        logger.error(f"Error accessing app reviews: {str(e)}")
        flash(f"Error accessing app reviews: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/fetch_app_reviews', methods=['POST'])
def fetch_app_reviews():
    """API endpoint to fetch app reviews with simplified processing"""
    try:
        app_id = request.json.get('app_id')
        if not app_id:
            logger.error("App ID is required but not provided")
            return jsonify({
                'status': 'error',
                'message': 'App ID is required'
            }), 400

        count = min(int(request.json.get('count', 50)), 200)  # Limit max reviews
        sort = request.json.get('sort', 'most_relevant')

        logger.debug(f"Fetching reviews for app: {app_id}, count: {count}, sort: {sort}")

        # Step 1: Fetch reviews - with detailed error handling
        try:
            reviews = get_app_reviews(app_id, count=count, sort=sort)
            logger.debug(f"Fetched {len(reviews)} reviews")

            if not reviews:
                logger.warning(f"No reviews found for app: {app_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'No reviews found or error fetching reviews'
                }), 404

        except Exception as e:
            logger.error(f"Error in get_app_reviews: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f"Failed to fetch reviews from Google Play: {str(e)}"
            }), 500

        # Step 2: Save reviews to database - with detailed error handling
        try:
            with app.app_context():
                for review in reviews:
                    # Convert timestamp to datetime for database storage
                    timestamp_ms = review.get('at')
                    if timestamp_ms is None:
                        logger.warning(f"Review missing 'at' timestamp: {review.get('reviewId', 'unknown')}")
                        date_obj = datetime.datetime.now()  # Use current time as fallback
                    elif isinstance(timestamp_ms, (int, float)):
                        try:
                            date_obj = datetime.datetime.fromtimestamp(timestamp_ms / 1000)
                        except Exception as date_error:
                            logger.warning(f"Error converting timestamp {timestamp_ms}: {str(date_error)}")
                            date_obj = datetime.datetime.now()  # Use current time as fallback
                    else:
                        # If it's already a datetime object, use it as is
                        date_obj = timestamp_ms

                    try:
                        new_review = ScrapedReview(
                            app_id = app_id,
                            review_id = review.get('reviewId', ''),
                            user_name = review.get('userName', 'Anonymous'),
                            rating = review.get('score', 0),
                            text = review.get('content', ''),
                            date = date_obj
                        )
                        db.session.add(new_review)
                    except Exception as db_error:
                        logger.error(f"Error adding review to database: {str(db_error)}")
                        # Continue with next review instead of failing completely
                        continue

                db.session.commit()
                logger.debug("Reviews saved to database")
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            # Continue processing even if database save fails

        # Step 3: Add simple sentiment scores (no NLTK required)
        for review in reviews:
            # Simple sentiment based on rating
            rating = review.get('score', 0)
            if rating >= 4:
                sentiment = 0.8  # Positive
            elif rating <= 2:
                sentiment = -0.8  # Negative
            else:
                sentiment = 0.0  # Neutral

            review['sentiment_score'] = sentiment
            review['sentiment_label'] = 'positive' if sentiment > 0 else ('negative' if sentiment < 0 else 'neutral')
            review['preprocessing'] = {
                'original': review.get('content', ''),
                'processed_token_count': len(review.get('content', '').split()),
                'original_token_count': len(review.get('content', '').split()),
                'removed_stopwords': []
            }
            review['processed_text'] = review.get('content', '')

        # Step 4: Calculate metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
            'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
            'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        }

        preprocessing_metrics = {
            'total_token_count': sum(len(r.get('content', '').split()) for r in reviews),
            'processed_token_count': sum(len(r.get('content', '').split()) for r in reviews),
            'removed_token_count': 0,
            'reduction_percentage': 0,
            'top_stopwords': []
        }

        # Step 5: Return the response
        logger.debug("Returning successful response")
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts,
            'preprocessing_metrics': preprocessing_metrics
        })
    except Exception as e:
        logger.error(f"Unhandled error fetching app reviews: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch app reviews: {str(e)}"
        }), 500

@app.route('/export/<app_id>/reviews/csv')
def export_reviews_csv(app_id):
    """Export app reviews to CSV format"""
    try:
        # Fetch reviews from database
        with app.app_context():
            reviews = ScrapedReview.query.filter_by(app_id=app_id).all()

        if not reviews:
            # If no reviews in database, fetch them from Google Play
            count = 100
            sort = 'most_relevant'
            reviews_data = get_app_reviews(app_id, count=count, sort=sort)

            # Process reviews for export
            processed_reviews = []
            for review in reviews_data:
                # Convert timestamp to datetime
                timestamp_ms = review.get('at')
                if timestamp_ms is not None and isinstance(timestamp_ms, (int, float)):
                    try:
                        date_str = datetime.datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
                    except:
                        date_str = str(timestamp_ms)
                else:
                    date_str = str(timestamp_ms)

                # Add sentiment
                rating = review.get('score', 0)
                if rating >= 4:
                    sentiment = 'positive'
                elif rating <= 2:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'

                processed_reviews.append({
                    'review_id': review.get('reviewId', ''),
                    'user_name': review.get('userName', 'Anonymous'),
                    'rating': review.get('score', 0),
                    'text': review.get('content', ''),
                    'date': date_str,
                    'sentiment': sentiment
                })
        else:
            # Convert database objects to dictionaries
            processed_reviews = []
            for review in reviews:
                processed_reviews.append({
                    'review_id': review.review_id,
                    'user_name': review.user_name,
                    'rating': review.rating,
                    'text': review.text,
                    'date': review.date.strftime('%Y-%m-%d') if review.date else '',
                    'sentiment': 'positive' if review.rating >= 4 else ('negative' if review.rating <= 2 else 'neutral')
                })

        # Create CSV in memory
        output = io.StringIO()
        fieldnames = ['review_id', 'user_name', 'rating', 'text', 'date', 'sentiment']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for review in processed_reviews:
            writer.writerow(review)

        # Create response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            content_type='text/csv'
        )
        response.headers['Content-Disposition'] = f'attachment; filename={app_id}_reviews.csv'
        return response

    except Exception as e:
        logger.error(f"Error exporting reviews to CSV: {str(e)}")
        flash(f"Error exporting reviews: {str(e)}", "danger")
        return redirect(url_for('app_reviews', app_id=app_id))

@app.route('/export/<app_id>/reviews/excel')
def export_reviews_excel(app_id):
    """Export app reviews to Excel format"""
    try:
        # Fetch reviews from database
        with app.app_context():
            reviews = ScrapedReview.query.filter_by(app_id=app_id).all()

        if not reviews:
            # If no reviews in database, fetch them from Google Play
            count = 100
            sort = 'most_relevant'
            reviews_data = get_app_reviews(app_id, count=count, sort=sort)

            # Process reviews for export
            processed_reviews = []
            for review in reviews_data:
                # Convert timestamp to datetime
                timestamp_ms = review.get('at')
                if timestamp_ms is not None and isinstance(timestamp_ms, (int, float)):
                    try:
                        date_str = datetime.datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
                    except:
                        date_str = str(timestamp_ms)
                else:
                    date_str = str(timestamp_ms)

                # Add sentiment
                rating = review.get('score', 0)
                if rating >= 4:
                    sentiment = 'positive'
                elif rating <= 2:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'

                processed_reviews.append({
                    'review_id': review.get('reviewId', ''),
                    'user_name': review.get('userName', 'Anonymous'),
                    'rating': review.get('score', 0),
                    'text': review.get('content', ''),
                    'date': date_str,
                    'sentiment': sentiment
                })
        else:
            # Convert database objects to dictionaries
            processed_reviews = []
            for review in reviews:
                processed_reviews.append({
                    'review_id': review.review_id,
                    'user_name': review.user_name,
                    'rating': review.rating,
                    'text': review.text,
                    'date': review.date.strftime('%Y-%m-%d') if review.date else '',
                    'sentiment': 'positive' if review.rating >= 4 else ('negative' if review.rating <= 2 else 'neutral')
                })

        # Create Excel file in memory using pandas
        output = io.BytesIO()

        # Create a DataFrame from the processed reviews
        df = pd.DataFrame(processed_reviews)

        # Rename columns for better readability
        df = df.rename(columns={
            'review_id': 'Review ID',
            'user_name': 'User Name',
            'rating': 'Rating',
            'text': 'Review Text',
            'date': 'Date',
            'sentiment': 'Sentiment'
        })

        # Export to Excel
        df.to_excel(output, index=False, sheet_name='Reviews')

        # Reset file pointer
        output.seek(0)

        # Create response
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{app_id}_reviews.xlsx'
        )

    except Exception as e:
        logger.error(f"Error exporting reviews to Excel: {str(e)}")
        flash(f"Error exporting reviews: {str(e)}", "danger")
        return redirect(url_for('app_reviews', app_id=app_id))

if __name__ == '__main__':
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)
