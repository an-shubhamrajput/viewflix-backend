import sys
import os
from unittest.mock import MagicMock, patch
import json

# Add backend dir to path
sys.path.append('/home/nexususer/Desktop/Shubham/ViewFlix UI/flask-backend')

# Set env var BEFORE importing app because app/__init__.py reads it at module level
os.environ["FE_URL"] = "http://localhost:3000"
os.environ["DB_HOST"] = "localhost" # Dummy values to pass config validation
os.environ["DB_USER"] = "root"
os.environ["DB_PASSWORD"] = "pass"
os.environ["DB_DATABASE"] = "db"

from app import create_app
from route.movie_language import movie_language_bp

def test_multi_language_logic():
    print(">>> Starting Verification with MOCK DB...")

    # Mock DB helper methods
    with patch('route.movie_language.get_model_query_by_db_name') as mock_query_helper, \
         patch('route.movie_language.DB_BY_LANGUAGE', {"LangA": "db_a", "LangB": "db_b"}):
        
        # Setup mock db behaviors
        mock_query_a = MagicMock()
        mock_query_b = MagicMock()
        
        # Mock Movie objects
        class MockMovie:
            def __init__(self, id, title):
                self.id = id
                self.title = title
                self.__table__ = MagicMock()
                col1 = MagicMock(); col1.name = 'id'
                col2 = MagicMock(); col2.name = 'title'
                self.__table__.columns = [col1, col2]
        
        mo1 = MockMovie(1, "Movie A1")
        mo2 = MockMovie(2, "Movie B1")
        
        mock_query_a.limit.return_value.all.return_value = [mo1]
        mock_query_b.limit.return_value.all.return_value = [mo2]
        
        # Side effect: if db_name is db_a return query_a, else query_b
        def side_effect(model, db_name):
            if db_name == "db_a":
                return mock_query_a
            return mock_query_b
            
        mock_query_helper.side_effect = side_effect

        # Create app and test client
        app = create_app()
        app.register_blueprint(movie_language_bp, url_prefix="/movie-language")
        client = app.test_client()
        
        # Test /movie-language/popular with multiple languages
        params = {
            "languages": '["LangA", "LangB"]'
        }
        
        print("    Fetching /movie-language/popular?languages=['LangA', 'LangB']")
        response = client.get('/movie-language/popular', query_string=params)
        
        if response.status_code != 200:
            print(f"[FAIL] Expected 200, got {response.status_code}")
            print(response.json)
            return

        data = response.json
        movies = data.get("movies", [])
        
        print(f"    Got {len(movies)} movies.")
        
        # Verify content and source_db injection
        found_a = False
        found_b = False
        for m in movies:
            print(f"      - {m.get('title')} from {m.get('source_db')}")
            if m.get('source_db') == "db_a": found_a = True
            if m.get('source_db') == "db_b": found_b = True
            
        if found_a and found_b:
            print("[PASS] Successfully fused movies from multiple language DBs.")
        else:
            print("[FAIL] Did not find movies from both DBs.")

if __name__ == "__main__":
    test_multi_language_logic()
