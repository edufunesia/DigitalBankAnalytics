import logging
import pandas as pd
import numpy as np
import re
from textblob import TextBlob

logger = logging.getLogger(__name__)

def preprocess_reviews(reviews):
    """
    Preprocess review text for sentiment analysis
    
    Args:
        reviews (list): List of review dictionaries
        
    Returns:
        list: List of preprocessed review texts
    """
    processed_texts = []
    
    for review in reviews:
        if 'content' in review and review['content']:
            text = review['content']
            
            # Convert to lowercase
            text = text.lower()
            
            # Remove special characters and numbers
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\d+', '', text)
            
            # Remove extra spaces
            text = re.sub(r'\s+', ' ', text).strip()
            
            processed_texts.append(text)
        else:
            # Handle empty reviews
            processed_texts.append("")
    
    return processed_texts

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
