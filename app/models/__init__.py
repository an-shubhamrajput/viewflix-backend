# Import the shared db instance from app
from app import db

# Import all models so they're registered with SQLAlchemy
from .movie_rating import MovieRating
from .popular_movie import PopularMovies
from .recently_added_movies import RecentAddedMovies
from .top_rated_movie import TopRatedMovies
from .upcoming_movie import UpcommingMovies
from .movie_detail import MovieDetails
from .free_movie_detail import FreeMoviesDetails
from .tmdb_free_movie import TmdbFreeMovies
from .videos import Videos

__all__ = [
    'db',
    'MovieRating',
    'PopularMovies',
    'RecentAddedMovies',
    'TopRatedMovies',
    'UpcommingMovies',
    'MovieDetails',
    'FreeMoviesDetails',
    'TmdbFreeMovies',
    'Videos',
]
