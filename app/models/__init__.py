import os
# Import the shared db instance from app
from app import db  # noqa: F401

# Conditionally import movie models based on MODEL_SCOPE to avoid polluting metadata
_scope = os.environ.get('MODEL_SCOPE', 'all').lower()
if _scope in ('movies', 'all'):
    from .movie_rating import MovieRating  # noqa: F401
    from .popular_movie import PopularMovies  # noqa: F401
    from .recently_added_movies import RecentAddedMovies  # noqa: F401
    from .top_rated_movie import TopRatedMovies  # noqa: F401
    from .upcoming_movie import UpcommingMovies  # noqa: F401
    from .movie_detail import MovieDetails  # noqa: F401
    from .free_movie_detail import FreeMoviesDetails  # noqa: F401
    from .tmdb_free_movie import TmdbFreeMovies  # noqa: F401
    from .videos import Videos  # noqa: F401
    from .classical_movie import ClassicMovies  # noqa: F401

