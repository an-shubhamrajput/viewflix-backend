from app import db

class UpcommingMovies(db.Model):
    __tablename__ = 'upcomming_movies'
    adult = db.Column(db.Boolean)
    backdrop_path = db.Column(db.String)
    genre_ids = db.Column(db.String)
    id = db.Column(db.BigInteger, primary_key=True)
    original_language = db.Column(db.String)
    original_title = db.Column(db.String)
    overview = db.Column(db.Text)
    popularity = db.Column(db.Float)
    poster_path = db.Column(db.String)
    release_date = db.Column(db.String)
    title = db.Column(db.String)
    video = db.Column(db.Boolean)
    vote_average = db.Column(db.Float)
    vote_count = db.Column(db.Float)
    translated_plot = db.Column(db.Text, default=None, nullable=True)
    translated_cast = db.Column(db.Text, default=None, nullable=True)
    translated_crew = db.Column(db.Text, default=None, nullable=True)
