import os
import logging
import csv
import io
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
from scraper import get_app_info, get_app_reviews
from analysis import analyze_sentiment, preprocess_reviews, extract_aspects, generate_aspect_summary
# Import calculate_tf_idf function
try:
    from analysis import calculate_tf_idf
except ImportError:
    # Define a fallback function if the import fails
    def calculate_tf_idf(reviews, max_features=50, min_df=2):
        logger.error("calculate_tf_idf function not available in analysis module")
        return {
            'status': 'error',
            'message': 'TF-IDF analysis functionality not available'
        }
from models import db, ScrapedApp, ScrapedReview
import pandas as pd
import json
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

         # Save the app info into the database
        with app.app_context():
            for app_info in app_infos:
                # Extract only the fields that are in the ScrapedApp model
                app_data = {
                    'app_id': app_info.get('appId'),
                    'title': app_info.get('title'),
                    'developer': app_info.get('developer'),
                    'description': app_info.get('description'),
                    'summary': app_info.get('summary'),
                    'score': app_info.get('score'),
                    'reviews': app_info.get('reviews'),
                    'installs': app_info.get('installs'),
                    'minInstalls': app_info.get('minInstalls'),
                    'maxInstalls': app_info.get('maxInstalls'),
                    'free': app_info.get('free'),
                    'price': app_info.get('price'),
                    'currency': app_info.get('currency'),
                    'size': app_info.get('size'),
                    'androidVersion': app_info.get('androidVersion'),
                    'developerId': app_info.get('developerId'),
                    'developerEmail': app_info.get('developerEmail'),
                    'developerWebsite': app_info.get('developerWebsite'),
                    'developerAddress': app_info.get('developerAddress'),
                    'privacyPolicy': app_info.get('privacyPolicy'),
                    'genre': app_info.get('genre'),
                    'genreId': app_info.get('genreId'),
                    'icon': app_info.get('icon'),
                    'headerImage': app_info.get('headerImage'),
                    'contentRating': app_info.get('contentRating'),
                    'adSupported': app_info.get('adSupported'),
                    'containsAds': app_info.get('containsAds'),
                    'released': app_info.get('released'),
                    'updated': app_info.get('updated'),
                    'version': app_info.get('version'),
                    'recentChanges': app_info.get('recentChanges')
                }

                scraped_app = ScrapedApp(**app_data)
                existing_app = ScrapedApp.query.get(scraped_app.app_id)
                if not existing_app:
                    db.session.add(scraped_app)
            db.session.commit()


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

        # Step 3: Process reviews with sentiment analysis - with detailed error handling
        try:
            processed_texts, preprocessing_details = preprocess_reviews(reviews)
            logger.debug("Preprocessing completed")
            sentiment_results = analyze_sentiment(processed_texts)
            logger.debug("Sentiment analysis completed")
        except Exception as analysis_error:
            logger.error(f"Error in text processing or sentiment analysis: {str(analysis_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error processing reviews: {str(analysis_error)}"
            }), 500

        # Step 4: Combine reviews with sentiment scores and preprocessing details
        try:
            for i, review in enumerate(reviews):
                if i < len(sentiment_results):
                    review['sentiment_score'] = sentiment_results[i].polarity
                    review['sentiment_label'] = 'positive' if sentiment_results[i].polarity > 0 else ('negative' if sentiment_results[i].polarity < 0 else 'neutral')
                else:
                    # Handle case where sentiment_results is shorter than reviews
                    review['sentiment_score'] = 0.0
                    review['sentiment_label'] = 'neutral'

                if i < len(preprocessing_details):
                    review['preprocessing'] = preprocessing_details[i]
                    review['processed_text'] = processed_texts[i]
                else:
                    # Handle case where preprocessing_details is shorter than reviews
                    review['preprocessing'] = {
                        'original': review.get('content', ''),
                        'processed_token_count': 0,
                        'original_token_count': 0,
                        'removed_stopwords': []
                    }
                    review['processed_text'] = ''

            logger.debug("Reviews combined with sentiment scores and preprocessing details")
        except Exception as combine_error:
            logger.error(f"Error combining reviews with analysis results: {str(combine_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error combining reviews with analysis results: {str(combine_error)}"
            }), 500

        # Step 5: Calculate metrics - with detailed error handling
        try:
            # Calculate sentiment metrics
            sentiment_counts = {
                'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
                'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
                'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
            }

            # Calculate preprocessing metrics
            total_token_count = sum(detail.get('original_token_count', 0) for detail in preprocessing_details)
            processed_token_count = sum(detail.get('processed_token_count', 0) for detail in preprocessing_details)
            removed_token_count = total_token_count - processed_token_count

            preprocessing_metrics = {
                'total_token_count': total_token_count,
                'processed_token_count': processed_token_count,
                'removed_token_count': removed_token_count,
                'reduction_percentage': int((removed_token_count / total_token_count * 100) if total_token_count > 0 else 0)
            }

            # Get most common removed stopwords
            all_removed_stopwords = []
            for detail in preprocessing_details:
                all_removed_stopwords.extend(detail.get('removed_stopwords', []))

            # Count occurrences of each stopword
            from collections import Counter
            stopword_counts = Counter(all_removed_stopwords)
            top_stopwords = [{"word": word, "count": count} for word, count in stopword_counts.most_common(10)]

            preprocessing_metrics['top_stopwords'] = top_stopwords
            logger.debug("Metrics calculated successfully")
        except Exception as metrics_error:
            logger.error(f"Error calculating metrics: {str(metrics_error)}")
            # Use default metrics if calculation fails
            sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
            preprocessing_metrics = {
                'total_token_count': 0,
                'processed_token_count': 0,
                'removed_token_count': 0,
                'reduction_percentage': 0,
                'top_stopwords': []
            }

        # Step 6: Return the response
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

@app.route('/about')
def about():
    """About page with information about the project"""
    return render_template('about.html')

@app.route('/preprocessing')
def preprocessing():
    """Page to show the preprocessing step by step"""
    return render_template('preprocessing.html')

@app.route('/app/<app_id>/aspect-analysis')
def app_aspect_analysis(app_id):
    """View for aspect-based sentiment analysis of app reviews"""
    try:
        # Validate app ID
        if 'play.google.com' in app_id:
            # Try to extract package ID from URL
            import re
            match = re.search(r'id=([^&]+)', app_id)
            if match:
                app_id = match.group(1)
                # Redirect to the clean URL
                return redirect(url_for('app_aspect_analysis', app_id=app_id))

        # Verify that the app exists by fetching its info
        app_info_list = get_app_info([app_id])

        if not app_info_list:
            flash(f"No information found for app: {app_id}", "danger")
            return redirect(url_for('index'))

        return render_template('app_aspect_analysis.html', app_id=app_id, app_name=app_info_list[0]['title'], app_info=app_info_list[0])
    except Exception as e:
        logger.error(f"Error accessing aspect analysis: {str(e)}")
        flash(f"Error accessing aspect analysis: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/app/<app_id>/data-analysis')
def app_data_analysis(app_id):
    """Page to display data analysis for app reviews"""
    try:
        # Validate app ID
        if 'play.google.com' in app_id:
            # Try to extract package ID from URL
            import re
            match = re.search(r'id=([^&]+)', app_id)
            if match:
                app_id = match.group(1)
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

        # Step 1: Fetch reviews
        try:
            reviews = get_app_reviews(app_id, count=count, sort=sort)
            logger.debug(f"Fetched {len(reviews)} reviews for data analysis")

            if not reviews:
                logger.warning(f"No reviews found for app: {app_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'No reviews found or error fetching reviews'
                }), 404

        except Exception as e:
            logger.error(f"Error in get_app_reviews for data analysis: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f"Failed to fetch reviews from Google Play: {str(e)}"
            }), 500

        # Step 2: Process reviews with sentiment analysis
        try:
            processed_texts, preprocessing_details = preprocess_reviews(reviews)
            logger.debug("Preprocessing completed for data analysis")
            sentiment_results = analyze_sentiment(processed_texts)
            logger.debug("Sentiment analysis completed for data analysis")
        except Exception as analysis_error:
            logger.error(f"Error in text processing or sentiment analysis for data analysis: {str(analysis_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error processing reviews: {str(analysis_error)}"
            }), 500

        # Step 3: Combine reviews with sentiment scores
        try:
            for i, review in enumerate(reviews):
                if i < len(sentiment_results):
                    review['sentiment_score'] = sentiment_results[i].polarity
                    review['sentiment_label'] = 'positive' if sentiment_results[i].polarity > 0 else ('negative' if sentiment_results[i].polarity < 0 else 'neutral')
                else:
                    # Handle case where sentiment_results is shorter than reviews
                    review['sentiment_score'] = 0.0
                    review['sentiment_label'] = 'neutral'

            logger.debug("Reviews combined with sentiment scores for data analysis")
        except Exception as combine_error:
            logger.error(f"Error combining reviews with analysis results for data analysis: {str(combine_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error combining reviews with analysis results: {str(combine_error)}"
            }), 500

        # Step 4: Calculate rating distribution
        rating_distribution = {
            '5': 0,
            '4': 0,
            '3': 0,
            '2': 0,
            '1': 0
        }

        for review in reviews:
            score = str(int(review.get('score', 0)))
            if score in rating_distribution:
                rating_distribution[score] += 1

        # Step 5: Calculate sentiment metrics and average rating
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
            'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
            'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        }

        avg_rating = sum(r.get('score', 0) for r in reviews) / len(reviews) if reviews else 0

        # Step 6: Return the response
        logger.debug("Returning successful data analysis response")
        return jsonify({
            'status': 'success',
            'data': reviews,
            'sentiment_metrics': sentiment_counts,
            'rating_distribution': rating_distribution,
            'avg_rating': avg_rating
        })
    except Exception as e:
        logger.error(f"Unhandled error in data analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to perform data analysis: {str(e)}"
        }), 500

@app.route('/export_reviews_csv/<app_id>')
def export_reviews_csv(app_id):
    """Export app reviews to CSV file"""
    try:
        count = min(int(request.args.get('count', 100)), 300)  # Limit max reviews to 300

        # Fetch reviews from database first
        with app.app_context():
            db_reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if db_reviews and len(db_reviews) >= count:
            # Use database reviews if available
            reviews = []
            for review in db_reviews:
                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'date': review.date.strftime('%Y-%m-%d') if review.date else ''
                })
        else:
            # Fetch from Google Play if not in database
            reviews = get_app_reviews(app_id, count=count)

        if not reviews:
            flash("No reviews found to export", "warning")
            return redirect(url_for('app_data_analysis', app_id=app_id))

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['User', 'Rating', 'Review', 'Date'])

        # Write data
        for review in reviews:
            writer.writerow([
                review.get('userName', ''),
                review.get('score', ''),
                review.get('content', ''),
                review.get('date', '')
            ])

        # Prepare response
        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=reviews_{app_id}.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting reviews to CSV: {str(e)}")
        flash(f"Error exporting reviews: {str(e)}", "danger")
        return redirect(url_for('app_data_analysis', app_id=app_id))

@app.route('/export_reviews_excel/<app_id>')
def export_reviews_excel(app_id):
    """Export app reviews to Excel file"""
    try:
        count = min(int(request.args.get('count', 100)), 300)  # Limit max reviews to 300

        # Fetch reviews from database first
        with app.app_context():
            db_reviews = ScrapedReview.query.filter_by(app_id=app_id).limit(count).all()

        if db_reviews and len(db_reviews) >= count:
            # Use database reviews if available
            reviews = []
            for review in db_reviews:
                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'date': review.date.strftime('%Y-%m-%d') if review.date else ''
                })
        else:
            # Fetch from Google Play if not in database
            reviews = get_app_reviews(app_id, count=count)

        if not reviews:
            flash("No reviews found to export", "warning")
            return redirect(url_for('app_data_analysis', app_id=app_id))

        # Create DataFrame
        df = pd.DataFrame([
            {
                'User': review.get('userName', ''),
                'Rating': review.get('score', ''),
                'Review': review.get('content', ''),
                'Date': review.get('date', '')
            }
            for review in reviews
        ])

        # Create Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Reviews', index=False)

        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"reviews_{app_id}.xlsx"
        )
    except Exception as e:
        logger.error(f"Error exporting reviews to Excel: {str(e)}")
        flash(f"Error exporting reviews: {str(e)}", "danger")
        return redirect(url_for('app_data_analysis', app_id=app_id))

@app.route('/app/<app_id>/tfidf')
def app_tfidf_analysis(app_id):
    """Page to display TF-IDF analysis for app reviews"""
    try:
        # Validate app ID
        if 'play.google.com' in app_id:
            # Try to extract package ID from URL
            import re
            match = re.search(r'id=([^&]+)', app_id)
            if match:
                app_id = match.group(1)
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
            reviews = []
            for review in db_reviews:
                reviews.append({
                    'reviewId': review.review_id,
                    'userName': review.user_name,
                    'score': review.rating,
                    'content': review.text,
                    'at': review.date.strftime('%Y-%m-%d') if review.date else ''
                })
        else:
            # Fetch from Google Play if not in database
            logger.debug("Fetching reviews from Google Play for TF-IDF analysis")
            reviews = get_app_reviews(app_id, count=count)

        if not reviews:
            logger.warning(f"No reviews found for app: {app_id}")
            return jsonify({
                'status': 'error',
                'message': 'No reviews found or error fetching reviews'
            }), 404

        # Step 2: Perform TF-IDF analysis
        try:
            logger.debug(f"Performing TF-IDF analysis with max_features={max_features}, min_df={min_df}")
            tfidf_results = calculate_tf_idf(reviews, max_features=max_features, min_df=min_df)

            if tfidf_results.get('status') == 'error':
                logger.error(f"Error in TF-IDF analysis: {tfidf_results.get('message')}")
                return jsonify(tfidf_results), 500

            logger.debug("TF-IDF analysis completed successfully")
            return jsonify({
                'status': 'success',
                'data': tfidf_results
            })
        except Exception as analysis_error:
            logger.error(f"Error in TF-IDF analysis: {str(analysis_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error in TF-IDF analysis: {str(analysis_error)}"
            }), 500
    except Exception as e:
        logger.error(f"Unhandled error in TF-IDF analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to perform TF-IDF analysis: {str(e)}"
        }), 500

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

        # Step 1: Fetch reviews
        try:
            reviews = get_app_reviews(app_id, count=count, sort=sort)
            logger.debug(f"Fetched {len(reviews)} reviews for aspect analysis")

            if not reviews:
                logger.warning(f"No reviews found for app: {app_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'No reviews found or error fetching reviews'
                }), 404

        except Exception as e:
            logger.error(f"Error in get_app_reviews for aspect analysis: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f"Failed to fetch reviews from Google Play: {str(e)}"
            }), 500

        # Step 2: Process reviews with sentiment analysis
        try:
            processed_texts, preprocessing_details = preprocess_reviews(reviews)
            logger.debug("Preprocessing completed for aspect analysis")
            sentiment_results = analyze_sentiment(processed_texts)
            logger.debug("Sentiment analysis completed for aspect analysis")
        except Exception as analysis_error:
            logger.error(f"Error in text processing or sentiment analysis for aspect analysis: {str(analysis_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error processing reviews: {str(analysis_error)}"
            }), 500

        # Step 3: Combine reviews with sentiment scores
        try:
            for i, review in enumerate(reviews):
                if i < len(sentiment_results):
                    review['sentiment_score'] = sentiment_results[i].polarity
                    review['sentiment_label'] = 'positive' if sentiment_results[i].polarity > 0 else ('negative' if sentiment_results[i].polarity < 0 else 'neutral')
                else:
                    # Handle case where sentiment_results is shorter than reviews
                    review['sentiment_score'] = 0.0
                    review['sentiment_label'] = 'neutral'

            logger.debug("Reviews combined with sentiment scores for aspect analysis")
        except Exception as combine_error:
            logger.error(f"Error combining reviews with analysis results for aspect analysis: {str(combine_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Error combining reviews with analysis results: {str(combine_error)}"
            }), 500

        # Step 4: Perform aspect-based sentiment analysis
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

        # Step 5: Calculate overall sentiment metrics
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.get('sentiment_label') == 'positive'),
            'neutral': sum(1 for r in reviews if r.get('sentiment_label') == 'neutral'),
            'negative': sum(1 for r in reviews if r.get('sentiment_label') == 'negative')
        }

        # Step 6: Return the response
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

if __name__ == '__main__':
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)

