from datetime import datetime
import json
from app import db

class App(db.Model):
    """Model for banking app information"""
    __tablename__ = 'apps'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    developer = db.Column(db.String(255))
    description = db.Column(db.Text)
    summary = db.Column(db.Text)
    icon = db.Column(db.String(255))
    score = db.Column(db.Float)
    ratings_count = db.Column(db.Integer)
    reviews_count = db.Column(db.Integer)
    installs = db.Column(db.Integer)
    price = db.Column(db.Float)
    free = db.Column(db.Boolean)
    currency = db.Column(db.String(10))
    size = db.Column(db.String(50))
    min_android = db.Column(db.String(50))
    genre = db.Column(db.String(100))
    genre_id = db.Column(db.String(100))
    content_rating = db.Column(db.String(50))
    released = db.Column(db.DateTime)
    updated = db.Column(db.DateTime)
    version = db.Column(db.String(50))
    recent_changes = db.Column(db.Text)
    url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Screenshots stored as JSON string
    _screenshots = db.Column(db.Text)
    
    # Ratings breakdown stored as JSON
    _ratings = db.Column(db.Text)
    
    # Relationships
    reviews = db.relationship('Review', backref='app', lazy=True, cascade='all, delete-orphan')
    
    @property
    def screenshots(self):
        """Get screenshots as list"""
        return json.loads(self._screenshots) if self._screenshots else []
    
    @screenshots.setter
    def screenshots(self, value):
        """Set screenshots from list"""
        self._screenshots = json.dumps(value) if value else None
    
    @property
    def ratings(self):
        """Get ratings as dict"""
        return json.loads(self._ratings) if self._ratings else {}
    
    @ratings.setter
    def ratings(self, value):
        """Set ratings from dict"""
        self._ratings = json.dumps(value) if value else None
    
    @classmethod
    def from_scraper_data(cls, data):
        """Create App instance from google-play-scraper data"""
        app = cls(
            app_id=data.get('appId'),
            title=data.get('title'),
            developer=data.get('developer'),
            description=data.get('description', ''),
            summary=data.get('summary', ''),
            icon=data.get('icon'),
            score=data.get('score'),
            ratings_count=data.get('ratings'),
            reviews_count=data.get('reviews'),
            installs=data.get('installs'),
            price=data.get('price'),
            free=data.get('free'),
            currency=data.get('currency'),
            size=data.get('size'),
            min_android=data.get('androidVersion'),
            genre=data.get('genre'),
            genre_id=data.get('genreId'),
            content_rating=data.get('contentRating'),
            version=data.get('version')
        )
        
        # Handle timestamps
        if 'released' in data:
            try:
                app.released = datetime.fromtimestamp(data['released'] / 1000)
            except (TypeError, ValueError):
                app.released = None
                
        if 'updated' in data:
            try:
                app.updated = datetime.fromtimestamp(data['updated'] / 1000)
            except (TypeError, ValueError):
                app.updated = None
        
        # Handle URL
        app.url = data.get('url')
        
        # Handle screenshots (stored as JSON string)
        app.screenshots = data.get('screenshots', [])
        
        # Handle ratings (stored as JSON string)
        app.ratings = data.get('ratings', {})
        
        # Handle recent changes
        app.recent_changes = data.get('recentChanges', '')
        
        return app

class Review(db.Model):
    """Model for app reviews"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False)
    review_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(255))
    user_image = db.Column(db.String(255))
    content = db.Column(db.Text)
    score = db.Column(db.Integer)  # 1-5 stars
    thumbs_up = db.Column(db.Integer)
    version = db.Column(db.String(50))
    at = db.Column(db.DateTime)
    reply_content = db.Column(db.Text)
    reply_at = db.Column(db.DateTime)
    
    # Sentiment analysis
    sentiment_score = db.Column(db.Float)
    sentiment_label = db.Column(db.String(20))  # positive, negative, neutral
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def from_scraper_data(cls, data, app_id, sentiment_score=0.0, sentiment_label='neutral'):
        """Create Review instance from google-play-scraper data"""
        review = cls(
            app_id=app_id,
            review_id=data.get('reviewId'),
            username=data.get('userName'),
            user_image=data.get('userImage'),
            content=data.get('content', ''),
            score=data.get('score'),
            thumbs_up=data.get('thumbsUp'),
            version=data.get('reviewCreatedVersion'),
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label
        )
        
        # Handle timestamps
        if 'at' in data:
            try:
                review.at = datetime.fromtimestamp(data['at'] / 1000)
            except (TypeError, ValueError):
                review.at = None
                
        # Handle reply data
        if 'replyContent' in data and data['replyContent']:
            review.reply_content = data['replyContent']
            
            if 'repliedAt' in data:
                try:
                    review.reply_at = datetime.fromtimestamp(data['repliedAt'] / 1000)
                except (TypeError, ValueError):
                    review.reply_at = None
        
        return review
