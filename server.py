from app import create_app, db
from flask import render_template
from flask_cors import CORS
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

app = create_app()

frontend_urls = os.getenv("FE_URL", "").split(",")
frontend_urls = [u.strip() for u in frontend_urls if u.strip()]

CORS(app, resources={r"/*": {"origins": frontend_urls}})

# ----------------------------------------------------------------------------
# Register blueprints ONCE
# ----------------------------------------------------------------------------
from route.movie import movie_bp
from route.movie_language import movie_language_bp
from route.profile import profile_bp
from route.recommendations import reco_bp

# app.register_blueprint(movie_bp, url_prefix="/movie")
app.register_blueprint(movie_language_bp, url_prefix="/movie-language")
app.register_blueprint(profile_bp, url_prefix="/profile")
app.register_blueprint(reco_bp)   # already has /api/recommendations

print("[INFO] ✓ Recommendation API ready at /api/recommendations")
print("[INFO] ✓ Recommendation UI at /recommendations")

# ----------------------------------------------------------------------------

@app.route("/db-test")
def db_test():
    try:
        result = db.session.execute(text("SELECT 1")).scalar()
        return f"DB OK: {result}"
    except Exception as e:
        return str(e), 500


@app.route("/recommendations")
def recommendations_ui():
    """Serve the Bootstrap recommendation frontend."""
    return render_template("recommendations.html")


@app.route("/")
def index():
    return {
        "status": "online",
        "services": [
            "/movie",
            "/profile",
            "/recommendations",
            "/api/recommendations",
            "/api/recommendations/top-ten"
        ]
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

