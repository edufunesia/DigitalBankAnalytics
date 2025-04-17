import logging
import pandas as pd
import numpy as np
import re
import string
import nltk
from textblob import TextBlob
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Download NLTK resources if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

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
            
            # Step 7: Stemming with Sastrawi
            stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]
            
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
