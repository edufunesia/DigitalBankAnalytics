from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class ScrapedApp(db.Model):
    __tablename__ = 'scraped_apps'
    app_id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    developer = db.Column(db.String)
    score = db.Column(db.Float)
    reviews = db.Column(db.Integer)

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


