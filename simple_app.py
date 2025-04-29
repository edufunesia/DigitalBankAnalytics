import os
import logging
import csv
import io
import pandas as pd
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
import datetime
from scraper import get_app_info, get_app_reviews
from models import db, ScrapedApp, ScrapedReview
from aspect_analysis import extract_aspects, generate_aspect_summary
from analysis import calculate_tf_idf

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.template_filter('format_number')
def format_number(value):
    """Format large numbers with commas as thousands separators"""
    return "{:,}".format(value) if value else 0

@app.route('/')
def index():
    """Homepage with app search form"""
    # Get recently analyzed apps from database
    try:
        with app.app_context():
            # Get distinct app_ids from the database
            recent_apps = db.session.query(ScrapedReview.app_id).distinct().limit(5).all()

            # Format for template
            recent_apps_list = []
            for app_id in recent_apps:
                # Try to get app info
                try:
                    app_info = get_app_info([app_id[0]])
                    if app_info:
                        recent_apps_list.append({
                            'id': app_id[0],
                            'name': app_info[0]['title']
                        })
                    else:
                        recent_apps_list.append({
                            'id': app_id[0],
                            'name': app_id[0]
                        })
                except:
                    # If we can't get app info, just use the ID
                    recent_apps_list.append({
                        'id': app_id[0],
                        'name': app_id[0]
                    })
    except Exception as e:
        logger.error(f"Error getting recent apps: {str(e)}")
        recent_apps_list = []

    return render_template('simple_index.html', recent_apps=recent_apps_list)

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





@app.route('/search', methods=['POST'])
def search_app():
    """Search for an app and redirect to its reviews page"""
    app_id = request.form.get('app_id')
    review_count = request.form.get('review_count', '100')

    if not app_id:
        flash("Please enter an app ID", "danger")
        return redirect(url_for('index'))

    # Clean up app_id
    app_id = app_id.strip()

    # If it's a URL, extract the ID
    if 'play.google.com' in app_id and 'id=' in app_id:
        try:
            app_id = app_id.split('id=')[1].split('&')[0]
        except:
            flash("Invalid Google Play URL. Please enter a valid app ID or URL.", "danger")
            return redirect(url_for('index'))

    # Verify that the app exists
    try:
        app_info = get_app_info([app_id])
        if not app_info:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error verifying app: {str(e)}")
        flash(f"Error verifying app: {str(e)}", "danger")
        return redirect(url_for('index'))

    # Validate review count
    try:
        review_count = int(review_count)
        if review_count not in [100, 200, 300]:
            review_count = 100  # Default to 100 if invalid value
    except:
        review_count = 100  # Default to 100 if conversion fails

    # Store review count in session for later use
    session = getattr(request, 'session', None)
    if session:
        session['review_count'] = review_count

    # Redirect to the app reviews page
    flash(f"Found app: {app_info[0]['title']} - Fetching {review_count} reviews", "success")
    return redirect(url_for('app_reviews', app_id=app_id, count=review_count))

@app.route('/app_info/<app_id>')
def app_info(app_id):
    """API endpoint to fetch app information"""
    try:
        # Clean up app_id if it has query parameters
        if '?' in app_id:
            app_id = app_id.split('?')[0]

        # Fetch app info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            return jsonify({
                'status': 'error',
                'message': f'No information found for app: {app_id}'
            }), 404

        # Return app info
        return jsonify({
            'status': 'success',
            'app_info': app_info_list[0]
        })
    except Exception as e:
        logger.error(f"Error fetching app info: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error fetching app info: {str(e)}'
        }), 500

@app.route('/app/<app_id>/reviews')
def app_reviews(app_id):
    """Page to display app reviews with sentiment analysis"""
    try:
        # Get review count from query parameters or session
        review_count = request.args.get('count', None)
        if not review_count:
            session = getattr(request, 'session', None)
            if session and 'review_count' in session:
                review_count = session['review_count']
            else:
                review_count = 100  # Default value

        try:
            review_count = int(review_count)
            if review_count not in [100, 200, 300]:
                review_count = 100  # Default to 100 if invalid value
        except:
            review_count = 100  # Default to 100 if conversion fails

        # Clean up app_id if it has query parameters
        if '?' in app_id:
            app_id = app_id.split('?')[0]
            # Redirect to the clean URL
            return redirect(url_for('app_reviews', app_id=app_id, count=review_count))

        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))

        return render_template('simple_reviews.html', app_id=app_id, app_name=app_info_list[0]['title'], review_count=review_count)
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

        count = min(int(request.json.get('count', 100)), 300)  # Limit max reviews to 300
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
        # Get count from query parameters
        count = request.args.get('count', None)
        if count:
            try:
                count = int(count)
                if count not in [100, 200, 300]:
                    count = 100  # Default to 100 if invalid value
            except:
                count = 100  # Default to 100 if conversion fails
        else:
            # Try to get review count from session
            session = getattr(request, 'session', None)
            count = 100  # Default value
            if session and 'review_count' in session:
                count = session['review_count']

        # Fetch reviews from database
        with app.app_context():
            reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if not reviews:
            # If no reviews in database, fetch them from Google Play
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
        # Get count from query parameters
        count = request.args.get('count', None)
        if count:
            try:
                count = int(count)
                if count not in [100, 200, 300]:
                    count = 100  # Default to 100 if invalid value
            except:
                count = 100  # Default to 100 if conversion fails
        else:
            # Try to get review count from session
            session = getattr(request, 'session', None)
            count = 100  # Default value
            if session and 'review_count' in session:
                count = session['review_count']

        # Fetch reviews from database
        with app.app_context():
            reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if not reviews:
            # If no reviews in database, fetch them from Google Play
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


@app.route('/app/<app_id>/aspect-analysis')
def app_aspect_analysis(app_id):
    """Page to display aspect-based sentiment analysis for app reviews"""
    try:
        # Clean up app_id if it has query parameters
        if '?' in app_id:
            app_id = app_id.split('?')[0]
            # Redirect to the clean URL
            return redirect(url_for('app_aspect_analysis', app_id=app_id))

        # Get review count from query parameters or session
        review_count = request.args.get('count', None)
        if not review_count:
            session = getattr(request, 'session', None)
            if session and 'review_count' in session:
                review_count = session['review_count']
            else:
                review_count = 100  # Default value

        try:
            review_count = int(review_count)
            if review_count not in [100, 200, 300]:
                review_count = 100  # Default to 100 if invalid value
        except:
            review_count = 100  # Default to 100 if conversion fails

        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))

        return render_template('app_aspect_analysis.html',
                              app_id=app_id,
                              app_name=app_info_list[0]['title'],
                              app_info=app_info_list[0],
                              review_count=review_count)
    except Exception as e:
        logger.error(f"Error accessing aspect analysis: {str(e)}")
        flash(f"Error accessing aspect analysis: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/fetch_aspect_analysis', methods=['POST'])
def fetch_aspect_analysis():
    """API endpoint to fetch aspect-based sentiment analysis for app reviews"""
    try:
        app_id = request.json.get('app_id')
        if not app_id:
            logger.error("App ID is required but not provided")
            return jsonify({
                'status': 'error',
                'message': 'App ID is required'
            }), 400

        count = min(int(request.json.get('count', 100)), 300)  # Limit max reviews to 300
        sort = request.json.get('sort', 'most_relevant')

        logger.debug(f"Fetching reviews for aspect analysis: {app_id}, count: {count}, sort: {sort}")

        # Step 1: Check if reviews are in database
        db_reviews = []
        try:
            with app.app_context():
                db_reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            # Continue with fetching from Google Play

        if db_reviews and len(db_reviews) >= count:
            # Use database reviews if available
            logger.debug(f"Using {len(db_reviews)} reviews from database for aspect analysis")

            # Convert to dictionary format
            reviews = []
            for review in db_reviews:
                # Add sentiment based on rating
                rating = review.rating
                if rating >= 4:
                    sentiment = 0.8  # Positive
                    sentiment_label = 'positive'
                elif rating <= 2:
                    sentiment = -0.8  # Negative
                    sentiment_label = 'negative'
                else:
                    sentiment = 0.0  # Neutral
                    sentiment_label = 'neutral'

                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'at': review.date.timestamp() * 1000 if review.date else None,
                    'sentiment_score': sentiment,
                    'sentiment_label': sentiment_label
                })
        else:
            # Fetch from Google Play if not in database
            try:
                reviews = get_app_reviews(app_id, count=count, sort=sort)
                logger.debug(f"Fetched {len(reviews)} reviews from Google Play for aspect analysis")

                if not reviews:
                    logger.warning(f"No reviews found for app: {app_id}")
                    return jsonify({
                        'status': 'error',
                        'message': 'No reviews found or error fetching reviews'
                    }), 404

                # Add simple sentiment scores
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
            except Exception as e:
                logger.error(f"Error fetching reviews from Google Play: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"Failed to fetch reviews from Google Play: {str(e)}"
                }), 500

        # Step 2: Perform aspect-based sentiment analysis
        try:
            aspect_results = extract_aspects(reviews)
            logger.debug("Aspect extraction completed")
            aspect_summary = generate_aspect_summary(aspect_results)
            logger.debug("Aspect summary generated")
        except Exception as aspect_error:
            logger.error(f"Error in aspect-based sentiment analysis: {str(aspect_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error in aspect-based sentiment analysis: {str(aspect_error)}"
            }), 500

        # Step 3: Calculate overall sentiment metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
            'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
            'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        }

        # Step 4: Return the response
        logger.debug("Returning successful aspect analysis response")
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts,
            'aspect_results': aspect_results,
            'aspect_summary': aspect_summary
        })
    except Exception as e:
        logger.error(f"Unhandled error in aspect analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to perform aspect analysis: {str(e)}"
        }), 500

@app.route('/preprocessing')
def preprocessing():
    """Page to show the preprocessing step by step"""
    return render_template('preprocessing.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/app/<app_id>/tfidf')
def app_tfidf_analysis(app_id):
    """Page to display TF-IDF analysis for app reviews"""
    try:
        # Clean up app_id if it has query parameters
        if '?' in app_id:
            app_id = app_id.split('?')[0]
            # Redirect to the clean URL
            return redirect(url_for('app_tfidf_analysis', app_id=app_id))

        # Get review count from query parameters or session
        review_count = request.args.get('count', None)
        if not review_count:
            session = getattr(request, 'session', None)
            if session and 'review_count' in session:
                review_count = session['review_count']
            else:
                review_count = 100  # Default value

        try:
            review_count = int(review_count)
            if review_count not in [100, 200, 300]:
                review_count = 100  # Default to 100 if invalid value
        except:
            review_count = 100  # Default to 100 if conversion fails

        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))

        return render_template('app_tfidf_analysis.html',
                              app_id=app_id,
                              app_name=app_info_list[0]['title'],
                              app_info=app_info_list[0],
                              review_count=review_count)
    except Exception as e:
        logger.error(f"Error accessing TF-IDF analysis: {str(e)}")
        flash(f"Error accessing TF-IDF analysis: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/fetch_tfidf_analysis', methods=['POST'])
def fetch_tfidf_analysis():
    """API endpoint to fetch TF-IDF analysis for app reviews"""
    try:
        app_id = request.json.get('app_id')
        if not app_id:
            logger.error("App ID is required but not provided")
            return jsonify({
                'status': 'error',
                'message': 'App ID is required'
            }), 400

        count = min(int(request.json.get('count', 100)), 300)  # Limit max reviews to 300
        max_features = min(int(request.json.get('max_features', 50)), 100)  # Limit max features
        min_df = max(int(request.json.get('min_df', 2)), 1)  # Ensure min_df is at least 1

        logger.debug(f"Fetching reviews for TF-IDF analysis: {app_id}, count: {count}")

        # Step 1: Fetch reviews from database first
        with app.app_context():
            db_reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if db_reviews and len(db_reviews) >= count:
            # Use database reviews if available
            logger.debug(f"Using {len(db_reviews)} reviews from database for TF-IDF analysis")

            # Convert to dictionary format
            reviews = []
            for review in db_reviews:
                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'at': review.date.timestamp() * 1000 if review.date else None
                })
        else:
            # Fetch from Google Play if not in database
            try:
                reviews = get_app_reviews(app_id, count=count, sort='most_relevant')
                logger.debug(f"Fetched {len(reviews)} reviews from Google Play for TF-IDF analysis")

                if not reviews:
                    logger.warning(f"No reviews found for app: {app_id}")
                    return jsonify({
                        'status': 'error',
                        'message': 'No reviews found or error fetching reviews'
                    }), 404

            except Exception as e:
                logger.error(f"Error fetching reviews for TF-IDF analysis: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"Failed to fetch reviews from Google Play: {str(e)}"
                }), 500

        # Step 2: Calculate TF-IDF
        tfidf_results = calculate_tf_idf(reviews, max_features=max_features, min_df=min_df)

        if tfidf_results['status'] != 'success':
            return jsonify(tfidf_results), 500

        # Step 3: Return the response
        return jsonify({
            'status': 'success',
            'data': tfidf_results
        })
    except Exception as e:
        logger.error(f"Unhandled error in TF-IDF analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to perform TF-IDF analysis: {str(e)}"
        }), 500

@app.route('/app/<app_id>/data-analysis')
def app_data_analysis(app_id):
    """Page to display data analysis for app reviews"""
    try:
        # Clean up app_id if it has query parameters
        if '?' in app_id:
            app_id = app_id.split('?')[0]
            # Redirect to the clean URL
            return redirect(url_for('app_data_analysis', app_id=app_id))

        # Get review count from query parameters or session
        review_count = request.args.get('count', None)
        if not review_count:
            session = getattr(request, 'session', None)
            if session and 'review_count' in session:
                review_count = session['review_count']
            else:
                review_count = 100  # Default value

        try:
            review_count = int(review_count)
            if review_count not in [100, 200, 300]:
                review_count = 100  # Default to 100 if invalid value
        except:
            review_count = 100  # Default to 100 if conversion fails

        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))

        return render_template('app_data_analysis.html',
                              app_id=app_id,
                              app_name=app_info_list[0]['title'],
                              app_info=app_info_list[0],
                              review_count=review_count)
    except Exception as e:
        logger.error(f"Error accessing data analysis: {str(e)}")
        flash(f"Error accessing data analysis: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/comparison')
def app_comparison():
    """Page for comparing multiple apps"""
    return render_template('app_comparison.html')

@app.route('/fetch_app_reviews_for_data_analysis', methods=['POST'])
def fetch_app_reviews_for_data_analysis():
    """API endpoint to fetch app reviews with detailed sentiment analysis for data analysis page"""
    try:
        app_id = request.json.get('app_id')
        if not app_id:
            logger.error("App ID is required but not provided")
            return jsonify({
                'status': 'error',
                'message': 'App ID is required'
            }), 400

        count = min(int(request.json.get('count', 100)), 300)  # Limit max reviews to 300
        sort = request.json.get('sort', 'most_relevant')

        logger.debug(f"Fetching reviews for data analysis - app: {app_id}, count: {count}, sort: {sort}")

        # Fetch reviews from database first
        with app.app_context():
            db_reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if db_reviews and len(db_reviews) >= count:
            # Use database reviews if available
            logger.debug(f"Using {len(db_reviews)} reviews from database for data analysis")

            # Convert to dictionary format
            reviews = []
            for review in db_reviews:
                # Add sentiment based on rating
                rating = review.rating
                if rating >= 4:
                    sentiment = 0.8  # Positive
                    sentiment_label = 'positive'
                elif rating <= 2:
                    sentiment = -0.8  # Negative
                    sentiment_label = 'negative'
                else:
                    sentiment = 0.0  # Neutral
                    sentiment_label = 'neutral'

                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'at': review.date.timestamp() * 1000 if review.date else None,
                    'sentiment_score': sentiment,
                    'sentiment_label': sentiment_label
                })
        else:
            # Fetch from Google Play if not in database
            try:
                reviews = get_app_reviews(app_id, count=count, sort=sort)
                logger.debug(f"Fetched {len(reviews)} reviews from Google Play for data analysis")

                if not reviews:
                    logger.warning(f"No reviews found for app: {app_id}")
                    return jsonify({
                        'status': 'error',
                        'message': 'No reviews found or error fetching reviews'
                    }), 404

                # Add simple sentiment scores
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

            except Exception as e:
                logger.error(f"Error fetching reviews for data analysis: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"Failed to fetch reviews from Google Play: {str(e)}"
                }), 500

        # Calculate sentiment metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
            'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
            'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        }

        # Calculate rating distribution
        rating_distribution = {
            '5': sum(1 for r in reviews if r.get('score') == 5),
            '4': sum(1 for r in reviews if r.get('score') == 4),
            '3': sum(1 for r in reviews if r.get('score') == 3),
            '2': sum(1 for r in reviews if r.get('score') == 2),
            '1': sum(1 for r in reviews if r.get('score') == 1)
        }

        # Calculate average rating
        total_ratings = sum(r.get('score', 0) for r in reviews)
        avg_rating = total_ratings / len(reviews) if reviews else 0

        # Calculate review length statistics
        review_lengths = [len(r.get('content', '').split()) for r in reviews]
        avg_review_length = sum(review_lengths) / len(review_lengths) if review_lengths else 0
        max_review_length = max(review_lengths) if review_lengths else 0
        min_review_length = min(review_lengths) if review_lengths else 0

        # Return the response
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts,
            'rating_distribution': rating_distribution,
            'avg_rating': avg_rating,
            'review_length_stats': {
                'avg': avg_review_length,
                'max': max_review_length,
                'min': min_review_length
            }
        })
    except Exception as e:
        logger.error(f"Unhandled error fetching app reviews for data analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch app reviews: {str(e)}"
        }), 500

@app.route('/fetch_app_reviews_for_comparison', methods=['POST'])
def fetch_app_reviews_for_comparison():
    """API endpoint to fetch app reviews for comparison"""
    try:
        app_id = request.json.get('app_id')
        if not app_id:
            logger.error("App ID is required but not provided")
            return jsonify({
                'status': 'error',
                'message': 'App ID is required'
            }), 400

        count = min(int(request.json.get('count', 100)), 300)  # Limit max reviews to 300
        sort = request.json.get('sort', 'most_relevant')

        logger.debug(f"Fetching reviews for comparison - app: {app_id}, count: {count}, sort: {sort}")

        # Fetch reviews from database first
        with app.app_context():
            db_reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if db_reviews and len(db_reviews) >= count:
            # Use database reviews if available
            logger.debug(f"Using {len(db_reviews)} reviews from database for comparison")

            # Convert to dictionary format
            reviews = []
            for review in db_reviews:
                # Add sentiment based on rating
                rating = review.rating
                if rating >= 4:
                    sentiment = 0.8  # Positive
                    sentiment_label = 'positive'
                elif rating <= 2:
                    sentiment = -0.8  # Negative
                    sentiment_label = 'negative'
                else:
                    sentiment = 0.0  # Neutral
                    sentiment_label = 'neutral'

                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'at': review.date.timestamp() * 1000 if review.date else None,
                    'sentiment_score': sentiment,
                    'sentiment_label': sentiment_label
                })
        else:
            # Fetch from Google Play if not in database
            try:
                reviews = get_app_reviews(app_id, count=count, sort=sort)
                logger.debug(f"Fetched {len(reviews)} reviews from Google Play for comparison")

                if not reviews:
                    logger.warning(f"No reviews found for app: {app_id}")
                    return jsonify({
                        'status': 'error',
                        'message': 'No reviews found or error fetching reviews'
                    }), 404

                # Add simple sentiment scores
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

            except Exception as e:
                logger.error(f"Error fetching reviews for comparison: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"Failed to fetch reviews from Google Play: {str(e)}"
                }), 500

        # Calculate sentiment metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
            'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
            'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        }

        # Return the response
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts
        })
    except Exception as e:
        logger.error(f"Unhandled error fetching app reviews for comparison: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch app reviews: {str(e)}"
        }), 500

if __name__ == '__main__':
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)
