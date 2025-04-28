from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class ScrapedApp(db.Model):
    __tablename__ = 'scraped_apps'
    app_id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    developer = db.Column(db.String)
    description = db.Column(db.Text)
    summary = db.Column(db.Text)
    score = db.Column(db.Float)
    reviews = db.Column(db.Integer)
    installs = db.Column(db.Integer)
    minInstalls = db.Column(db.Integer)
    maxInstalls = db.Column(db.Integer)
    free = db.Column(db.Boolean)
    price = db.Column(db.Float)
    currency = db.Column(db.String)
    size = db.Column(db.String)
    androidVersion = db.Column(db.String)
    developerId = db.Column(db.String)
    developerEmail = db.Column(db.String)
    developerWebsite = db.Column(db.String)
    developerAddress = db.Column(db.String)
    privacyPolicy = db.Column(db.String)
    genre = db.Column(db.String)
    genreId = db.Column(db.String)
    icon = db.Column(db.String)
    headerImage = db.Column(db.String)
    contentRating = db.Column(db.String)
    adSupported = db.Column(db.Boolean)
    containsAds = db.Column(db.Boolean)
    released = db.Column(db.String)
    updated = db.Column(db.Integer)
    version = db.Column(db.String)
    recentChanges = db.Column(db.Text)

    def __repr__(self):
        return f'<ScrapedApp {self.app_id}>'

class ScrapedReview(db.Model):
    __tablename__ = 'scraped_reviews'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    app_id = db.Column(db.String)
    review_id = db.Column(db.String)
    user_name = db.Column(db.String)
    rating = db.Column(db.Integer)
    text = db.Column(db.String)
    date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<ScrapedReview {self.id}>'


