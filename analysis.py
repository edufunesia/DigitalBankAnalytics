import logging
import pandas as pd
import numpy as np
import re
import string
import nltk
import threading
import time
from queue import Queue
from textblob import TextBlob
from collections import Counter, defaultdict
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Define a timeout function to prevent stemming from hanging
def stem_with_timeout(stemmer, word, timeout=0.5):
    """Stem a word with a timeout to prevent hanging"""
    # Skip stemming for very short words or non-alphabetic strings
    if len(word) <= 3 or not word.isalpha():
        return word, False

    result_queue = Queue()

    def worker():
        try:
            result = stemmer.stem(word)
            result_queue.put(result)
        except Exception as e:
            result_queue.put(word)  # Return original word on error

    # Start worker thread
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()

    try:
        # Wait for result with timeout
        result = result_queue.get(timeout=timeout)
        return result, False
    except:
        return word, True  # Return original word on timeout

# Download NLTK resources if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Initialize Sastrawi components
stemmer_factory = StemmerFactory()
stemmer = stemmer_factory.create_stemmer()

stopword_factory = StopWordRemoverFactory()
stopword_remover = stopword_factory.create_stop_word_remover()
stopwords_list = stopword_factory.get_stop_words()

# Add custom stopwords - common words in reviews that don't contribute to sentiment
custom_stopwords = [
    'app', 'aplikasi', 'bank', 'jago', 'allo', 'blu', 'btpn', 'bca', 'jenius',
    'seabank', 'raya', 'neo', 'update', 'version', 'versi', 'download', 'user',
    'please', 'tolong', 'mohon', 'ya', 'iya', 'ok', 'oke', 'okay'
]
all_stopwords = stopwords_list + custom_stopwords

logger = logging.getLogger(__name__)

def preprocess_reviews(reviews):
    """
    Preprocess review text for sentiment analysis with detailed Indonesian language processing

    Args:
        reviews (list): List of review dictionaries

    Returns:
        list: List of preprocessed review texts and processing details
    """
    processed_texts = []
    preprocessing_details = []

    for review in reviews:
        if 'content' in review and review['content']:
            text = review['content']

            # Store original text for comparison
            original_text = text

            # Step 1: Convert to lowercase
            text = text.lower()

            # Step 2: Remove URLs
            text = re.sub(r'https?://\S+|www\.\S+', '', text)

            # Step 3: Remove punctuation and special characters
            text = text.translate(str.maketrans('', '', string.punctuation))

            # Step 4: Remove numbers
            text = re.sub(r'\d+', '', text)

            # Step 5: Tokenization
            tokens = nltk.word_tokenize(text)

            # Step 6: Remove stopwords
            filtered_tokens = [word for word in tokens if word not in all_stopwords]

            # Step 7: Stemming with Sastrawi (with error handling and timeout)
            stemmed_tokens = []
            for word in filtered_tokens:
                try:
                    # Skip very short words (likely not Indonesian)
                    if len(word) <= 2:
                        stemmed_tokens.append(word)
                    else:
                        # Use threaded stemmer with timeout
                        stemmed_word, timed_out = stem_with_timeout(stemmer, word, timeout=1.0)
                        stemmed_tokens.append(stemmed_word)

                        if timed_out:
                            logger.warning(f"Stemming timed out for word: {word}")
                except Exception as e:
                    logger.error(f"Error stemming word '{word}': {str(e)}")
                    stemmed_tokens.append(word)  # Use original word if stemming fails

            # Step 8: Join tokens back to text
            preprocessed_text = ' '.join(stemmed_tokens)

            # Step 9: Remove extra spaces
            preprocessed_text = re.sub(r'\s+', ' ', preprocessed_text).strip()

            # Store processing details for display
            processing_detail = {
                'original': original_text,
                'lowercase': text,
                'after_tokenization': ' '.join(tokens),
                'after_stopword_removal': ' '.join(filtered_tokens),
                'after_stemming': preprocessed_text,
                'original_token_count': len(tokens),
                'processed_token_count': len(stemmed_tokens),
                'removed_stopwords': [word for word in tokens if word in all_stopwords]
            }

            processed_texts.append(preprocessed_text)
            preprocessing_details.append(processing_detail)
        else:
            # Handle empty reviews
            processed_texts.append("")
            preprocessing_details.append({
                'original': "",
                'lowercase': "",
                'after_tokenization': "",
                'after_stopword_removal': "",
                'after_stemming': "",
                'original_token_count': 0,
                'processed_token_count': 0,
                'removed_stopwords': []
            })

    return processed_texts, preprocessing_details

def analyze_sentiment(texts):
    """
    Perform sentiment analysis on preprocessed texts

    Args:
        texts (list): List of preprocessed texts

    Returns:
        list: List of sentiment analysis results
    """
    sentiment_results = []

    for text in texts:
        try:
            if text:
                # Use TextBlob for sentiment analysis
                analysis = TextBlob(text)
                sentiment_results.append(analysis.sentiment)
            else:
                # Handle empty texts
                from collections import namedtuple
                Sentiment = namedtuple('Sentiment', ['polarity', 'subjectivity'])
                sentiment_results.append(Sentiment(polarity=0.0, subjectivity=0.0))
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            # Return neutral sentiment if analysis fails
            from collections import namedtuple
            Sentiment = namedtuple('Sentiment', ['polarity', 'subjectivity'])
            sentiment_results.append(Sentiment(polarity=0.0, subjectivity=0.0))

    return sentiment_results

def generate_summary_statistics(app_data):
    """
    Generate summary statistics from app data

    Args:
        app_data (list): List of app information dictionaries

    Returns:
        dict: Dictionary containing summary statistics
    """
    try:
        df = pd.DataFrame(app_data)

        summary = {
            'count': len(df),
            'avg_rating': df['score'].mean(),
            'max_rating': df['score'].max(),
            'min_rating': df['score'].min(),
            'avg_installs': df['installs'].mean(),
            'total_installs': df['installs'].sum(),
            'avg_reviews': df['reviews'].mean(),
            'total_reviews': df['reviews'].sum()
        }

        return summary
    except Exception as e:
        logger.error(f"Error generating summary statistics: {str(e)}")
        return {}

def categorize_sentiment(sentiment_score):
    """
    Categorize sentiment scores into positive, neutral, or negative

    Args:
        sentiment_score (float): Sentiment polarity score

    Returns:
        str: Sentiment category
    """
    if sentiment_score > 0.1:
        return 'positive'
    elif sentiment_score < -0.1:
        return 'negative'
    else:
        return 'neutral'

def generate_review_sentiment_summary(reviews):
    """
    Generate a summary of review sentiment analysis

    Args:
        reviews (list): List of review dictionaries with sentiment scores

    Returns:
        dict: Dictionary containing sentiment summary
    """
    try:
        sentiments = [r.get('sentiment_score', 0) for r in reviews]
        categories = [categorize_sentiment(score) for score in sentiments]

        summary = {
            'positive_count': categories.count('positive'),
            'neutral_count': categories.count('neutral'),
            'negative_count': categories.count('negative'),
            'avg_sentiment': sum(sentiments) / len(sentiments) if sentiments else 0
        }

        return summary
    except Exception as e:
        logger.error(f"Error generating review sentiment summary: {str(e)}")
        return {}

# Define common aspects for banking apps
BANKING_ASPECTS = {
    'ui': ['ui', 'interface', 'design', 'tampilan', 'layout', 'antarmuka', 'desain', 'tema', 'warna', 'color'],
    'performance': ['performance', 'speed', 'fast', 'slow', 'lag', 'crash', 'hang', 'kinerja', 'cepat', 'lambat', 'loading', 'berat', 'ringan', 'lancar'],
    'security': ['security', 'secure', 'keamanan', 'aman', 'password', 'pin', 'otp', 'verification', 'verifikasi', 'biometric', 'fingerprint', 'face'],
    'features': ['feature', 'fitur', 'function', 'fungsi', 'kemampuan', 'capability', 'tools', 'alat'],
    'usability': ['usability', 'user-friendly', 'easy', 'difficult', 'mudah', 'sulit', 'simple', 'sederhana', 'kompleks', 'complex', 'intuitive', 'intuitif'],
    'customer_service': ['customer service', 'support', 'help', 'bantuan', 'layanan', 'service', 'cs', 'call center', 'chat', 'response', 'respon'],
    'transaction': ['transaction', 'transfer', 'payment', 'pembayaran', 'transaksi', 'bayar', 'kirim', 'terima', 'receive', 'send', 'bill', 'tagihan'],
    'reliability': ['reliable', 'reliability', 'stable', 'stabil', 'konsisten', 'consistent', 'dependable', 'andal', 'error', 'bug', 'issue', 'masalah', 'problem'],
    'updates': ['update', 'upgrade', 'version', 'versi', 'pembaruan', 'perbaikan', 'improvement', 'enhancement', 'peningkatan']
}

def extract_aspects(reviews, aspect_keywords=BANKING_ASPECTS):
    """
    Extract aspects from review texts and analyze sentiment for each aspect

    Args:
        reviews (list): List of review dictionaries with content and sentiment scores
        aspect_keywords (dict): Dictionary mapping aspect categories to keywords

    Returns:
        dict: Dictionary containing aspect-based sentiment analysis results
    """
    try:
        # Initialize results structure
        aspect_results = {
            'aspects': {},
            'review_aspects': []
        }

        # Initialize counters for each aspect
        for aspect in aspect_keywords:
            aspect_results['aspects'][aspect] = {
                'positive': 0,
                'neutral': 0,
                'negative': 0,
                'total': 0,
                'avg_sentiment': 0.0,
                'keywords': []
            }

        # Process each review
        for review in reviews:
            content = review.get('content', '').lower()
            sentiment_score = review.get('sentiment_score', 0)
            sentiment_category = categorize_sentiment(sentiment_score)

            # Skip empty reviews
            if not content:
                continue

            # Find aspects in the review
            review_aspects = []

            for aspect, keywords in aspect_keywords.items():
                # Check if any keyword is in the review
                found_keywords = [keyword for keyword in keywords if keyword in content]

                if found_keywords:
                    # Add aspect to review's aspects
                    review_aspects.append({
                        'aspect': aspect,
                        'sentiment': sentiment_category,
                        'score': sentiment_score,
                        'keywords': found_keywords
                    })

                    # Update aspect counters
                    aspect_results['aspects'][aspect][sentiment_category] += 1
                    aspect_results['aspects'][aspect]['total'] += 1
                    aspect_results['aspects'][aspect]['avg_sentiment'] += sentiment_score

                    # Track keywords found
                    aspect_results['aspects'][aspect]['keywords'].extend(found_keywords)

            # Add aspects to review if any were found
            if review_aspects:
                aspect_results['review_aspects'].append({
                    'review_id': review.get('reviewId', ''),
                    'aspects': review_aspects
                })

        # Calculate average sentiment for each aspect
        for aspect in aspect_keywords:
            total = aspect_results['aspects'][aspect]['total']
            if total > 0:
                aspect_results['aspects'][aspect]['avg_sentiment'] /= total

            # Count keyword frequencies
            keyword_counter = Counter(aspect_results['aspects'][aspect]['keywords'])
            aspect_results['aspects'][aspect]['keywords'] = [
                {'keyword': k, 'count': c}
                for k, c in keyword_counter.most_common(5)
            ]

        return aspect_results
    except Exception as e:
        logger.error(f"Error in aspect-based sentiment analysis: {str(e)}")
        return {'aspects': {}, 'review_aspects': []}

def generate_aspect_summary(aspect_results):
    """
    Generate a summary of aspect-based sentiment analysis

    Args:
        aspect_results (dict): Results from extract_aspects function

    Returns:
        dict: Dictionary containing aspect summary statistics
    """
    try:
        summary = {
            'most_positive_aspect': None,
            'most_negative_aspect': None,
            'most_mentioned_aspect': None,
            'aspect_count': len(aspect_results['aspects']),
            'aspects_by_sentiment': []
        }

        # Find most positive, negative, and mentioned aspects
        max_positive_ratio = -1
        max_negative_ratio = -1
        max_mentions = -1

        for aspect, data in aspect_results['aspects'].items():
            total = data['total']

            # Skip aspects with no mentions
            if total == 0:
                continue

            positive_ratio = data['positive'] / total if total > 0 else 0
            negative_ratio = data['negative'] / total if total > 0 else 0

            # Check if this is the most positive aspect
            if positive_ratio > max_positive_ratio:
                max_positive_ratio = positive_ratio
                summary['most_positive_aspect'] = aspect

            # Check if this is the most negative aspect
            if negative_ratio > max_negative_ratio:
                max_negative_ratio = negative_ratio
                summary['most_negative_aspect'] = aspect

            # Check if this is the most mentioned aspect
            if total > max_mentions:
                max_mentions = total
                summary['most_mentioned_aspect'] = aspect

            # Add to sorted list
            summary['aspects_by_sentiment'].append({
                'aspect': aspect,
                'sentiment_score': data['avg_sentiment'],
                'total_mentions': total,
                'positive_ratio': positive_ratio,
                'negative_ratio': negative_ratio
            })

        # Sort aspects by sentiment score (descending)
        summary['aspects_by_sentiment'].sort(key=lambda x: x['sentiment_score'], reverse=True)

        return summary
    except Exception as e:
        logger.error(f"Error generating aspect summary: {str(e)}")
        return {
            'most_positive_aspect': None,
            'most_negative_aspect': None,
            'most_mentioned_aspect': None,
            'aspect_count': 0,
            'aspects_by_sentiment': []
        }

def calculate_tf_idf(reviews, max_features=50, min_df=2):
    """
    Calculate TF-IDF scores for review texts

    Args:
        reviews (list): List of review dictionaries with content
        max_features (int): Maximum number of features to extract
        min_df (int): Minimum document frequency for a term to be included

    Returns:
        dict: Dictionary containing TF-IDF results and calculation details
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        # Extract review texts
        review_texts = [review.get('content', '') for review in reviews if review.get('content')]

        if not review_texts:
            logger.warning("No review texts found for TF-IDF analysis")
            return {
                'status': 'error',
                'message': 'No review texts found for analysis'
            }

        # Preprocess texts
        processed_texts, preprocessing_details = preprocess_reviews(reviews)

        # Initialize TF-IDF vectorizer
        tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            min_df=min_df,
            stop_words='english',  # Use English stopwords in addition to our custom ones
            ngram_range=(1, 1)     # Only use unigrams for simplicity
        )

        # Calculate TF-IDF
        tfidf_matrix = tfidf_vectorizer.fit_transform(processed_texts)

        # Get feature names
        feature_names = tfidf_vectorizer.get_feature_names_out()

        # Calculate document frequencies
        df = np.bincount(tfidf_matrix.nonzero()[1], minlength=len(feature_names))

        # Calculate IDF values
        idf = tfidf_vectorizer.idf_

        # Calculate average TF-IDF score for each term
        tfidf_means = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

        # Create results dictionary with term details
        term_details = []
        for i, term in enumerate(feature_names):
            # Calculate term frequency in each document
            term_indices = np.where(tfidf_matrix.toarray()[:, i] > 0)[0]
            term_tfidf_values = tfidf_matrix.toarray()[term_indices, i]

            # Get document examples for this term
            doc_examples = []
            for doc_idx in term_indices[:3]:  # Limit to 3 examples
                doc_examples.append({
                    'text': review_texts[doc_idx][:100] + '...' if len(review_texts[doc_idx]) > 100 else review_texts[doc_idx],
                    'tfidf_score': float(tfidf_matrix.toarray()[doc_idx, i]),
                    'review_id': reviews[doc_idx].get('reviewId', '')
                })

            # Calculate TF for example calculation
            example_tf = 1 / len(processed_texts[0].split()) if processed_texts and processed_texts[0] else 0

            term_details.append({
                'term': term,
                'avg_tfidf': float(tfidf_means[i]),
                'document_frequency': int(df[i]),
                'idf': float(idf[i]),
                'document_examples': doc_examples,
                'calculation_example': {
                    'term': term,
                    'tf_explanation': f"TF = (Number of times '{term}' appears in document) / (Total number of terms in document)",
                    'example_tf': example_tf,
                    'idf_explanation': f"IDF = log(Total number of documents / Number of documents containing '{term}') + 1",
                    'example_idf': float(idf[i]),
                    'tfidf_explanation': f"TF-IDF = TF × IDF",
                    'example_tfidf': example_tf * float(idf[i])
                }
            })

        # Sort terms by average TF-IDF score
        term_details.sort(key=lambda x: x['avg_tfidf'], reverse=True)

        # Calculate corpus statistics
        corpus_stats = {
            'num_documents': len(processed_texts),
            'avg_document_length': np.mean([len(text.split()) for text in processed_texts]) if processed_texts else 0,
            'vocabulary_size': len(feature_names),
            'max_idf': float(np.max(idf)) if len(idf) > 0 else 0,
            'min_idf': float(np.min(idf)) if len(idf) > 0 else 0
        }

        # Return results
        return {
            'status': 'success',
            'term_details': term_details,
            'corpus_stats': corpus_stats,
            'top_terms': [term['term'] for term in term_details[:10]]
        }
    except Exception as e:
        logger.error(f"Error calculating TF-IDF: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error calculating TF-IDF: {str(e)}"
        }
