from app import db
from datetime import datetime

class ClassicMovies(db.Model):
    __tablename__ = 'classic_movies'

    adult = db.Column(db.Boolean, nullable=True, default=None)
    backdrop_path = db.Column(db.String(255), nullable=True)
    genre_ids = db.Column(db.String(255), nullable=True)  # comma separated genre IDs string
    id = db.Column(db.Float, primary_key=True, nullable=False)
    original_language = db.Column(db.String(255), nullable=True)
    original_title = db.Column(db.String(255), nullable=True)
    overview = db.Column(db.Text, nullable=True)
    popularity = db.Column(db.Float, nullable=True)
    poster_path = db.Column(db.String(255), nullable=True)
    release_date = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(255), nullable=True)
    video = db.Column(db.Boolean, nullable=True, default=None)
    vote_average = db.Column(db.Float, nullable=True)
    vote_count = db.Column(db.Float, nullable=True)
    createdAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    translated_plot = db.Column(db.Text, nullable=True, default=None)
    translated_cast = db.Column(db.Text, nullable=True, default=None)
    translated_crew = db.Column(db.Text, nullable=True, default=None)
