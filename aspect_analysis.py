import logging
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define common aspects for app reviews
APP_ASPECTS = {
    'ui': ['ui', 'interface', 'design', 'layout', 'screen', 'theme', 'color', 'dark mode', 'light mode', 'appearance', 'look', 'visual'],
    'performance': ['performance', 'speed', 'fast', 'slow', 'lag', 'crash', 'hang', 'freeze', 'loading', 'battery', 'memory', 'responsive'],
    'usability': ['usability', 'user-friendly', 'easy', 'difficult', 'simple', 'complex', 'intuitive', 'confusing', 'navigation', 'accessible'],
    'features': ['feature', 'function', 'functionality', 'capability', 'option', 'setting', 'tool', 'ability', 'control'],
    'reliability': ['reliable', 'stability', 'stable', 'consistent', 'dependable', 'error', 'bug', 'issue', 'problem', 'glitch', 'fix'],
    'updates': ['update', 'upgrade', 'version', 'release', 'improvement', 'enhancement', 'change', 'new', 'latest'],
    'content': ['content', 'post', 'photo', 'video', 'story', 'feed', 'timeline', 'quality', 'relevance', 'recommendation'],
    'privacy': ['privacy', 'security', 'data', 'permission', 'tracking', 'safe', 'secure', 'protection', 'personal'],
    'ads': ['ad', 'ads', 'advertisement', 'commercial', 'promotion', 'sponsored', 'marketing', 'popup']
}

def extract_aspects(reviews, aspect_keywords=APP_ASPECTS):
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
            sentiment_category = 'positive' if sentiment_score > 0 else ('negative' if sentiment_score < 0 else 'neutral')
            
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
