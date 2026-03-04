# ViewFlix Backend (Flask)

This backend powers the ViewFlix platform, providing APIs for the User Interface, Admin Dashboard, and Recommendation Engine. It manages multi-language movie databases, user content, and admin configurations.


## Overview of Changes

- **Multi-Language Support**: New APIs to fetch aggregated movies based on user language preferences.
- **Admin Dashboard**: Flask-Admin integration for managing site content.
- **Admin Models**:
  - `SiteSetting` for key/value site configuration (supports types: text/html/json/url/int/bool).
  - `Banner` for homepage/hero banners with sort order and active toggle.
- Registered admin views for the above models.
- Added content API endpoints (read-only) to serve admin-managed content to the React app.
- Integrated Flask-Migrate for Alembic migrations.
- Pooled DB connections via SQLAlchemy engine options (configurable from `.env`).
- Isolated admin models in `app/models/admin/` so they do not mix with movie DB models.


## Directory Layout (Relevant Files)

- `app/__init__.py` – App factory; config, SQLAlchemy, Flask-Admin, Flask-Migrate, blueprints.
- `app/admin_views.py` – Admin index view (placeholder, ready for customization).
- `app/models/admin/site_content.py` – Admin models `SiteSetting`, `Banner`.
- `app/language_config.py` – Configuration mapping languages to database names.
- `route/content.py` – Public APIs to fetch settings and banners.
- `route/movie_language.py` – APIs for multi-language movie aggregation.
- `requirements.txt` – Includes Flask-Admin and Flask-Migrate.


## Requirements

Ensure you are using the included virtual environment or your own with Python 3.13. Then install:

```bash
pip install -r requirements.txt
```

Key packages:
- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- PyMySQL
- python-dotenv
- Flask-Admin
- Flask-Migrate


## Environment Configuration

Create or update `.env` in the project root. Example:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_DATABASE=viewflix_web

# Optional – connection pool configuration
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Optional – CORS frontends (comma-separated or single URL)
FE_URL=http://localhost:5173
```

Notes:
- App loads `.env` early via `python-dotenv`.
- All uppercase env vars are copied to `app.config` by the app factory.
- SQLAlchemy engine options read from the DB_POOL_* variables.


## Database Setup (MySQL)

Create the database if it doesn’t exist yet:

```bash
mysql -u root -p -e "CREATE DATABASE viewflix_web CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Ensure your `.env` has `DB_DATABASE=viewflix_web`.


## Migrations (Flask-Migrate/Alembic)

You can generate migrations for only admin models, only movie models, or both, by using environment variables:

- `MODEL_SCOPE` controls which models are loaded:
  - `admin`  → only admin models under `app/models/admin/`
  - `movies` → only movie DB models under `app/models/`
  - `all`    → both (default for running the app)
- `MIGRATIONS_DIR` controls where migration files are stored (default `migrations`).

Initialize and run migrations from the backend root.

Admin-only migrations (recommended separate history):

```bash
# 1) Point Flask to your entry file
export FLASK_APP=server.py

# 2) Initialize migrations in a separate directory for admin
export MODEL_SCOPE=admin
export MIGRATIONS_DIR=migrations_admin
flask db init

# 3) Autogenerate first migration from current models
flask db migrate -m "admin content initial"

# 4) Apply migration to the configured DB
flask db upgrade
```

Movie-only migrations (if needed later, separate history):

```bash
export FLASK_APP=server.py
export MODEL_SCOPE=movies
export MIGRATIONS_DIR=migrations_movies
flask db init
flask db migrate -m "movies initial"
flask db upgrade
```

Both sets together (single history; not recommended unless you want one timeline):

```bash
export FLASK_APP=server.py
export MODEL_SCOPE=all
export MIGRATIONS_DIR=migrations
flask db init
flask db migrate -m "full schema initial"
flask db upgrade
```

After step 2, you will have a `migrations/` folder at the backend root. After step 3, you’ll see a migration under `migrations/versions/` for the admin models.


## Admin Dashboard

- URL: `/admin`
- Models registered:
  - `SiteSetting` (key/value site configuration)
  - `Banner` (public banners with `is_active` and `sort_order`)

You can add/edit/delete entries here. These will be stored in `viewflix_web` and exposed by APIs below.


## Multi-Language Movie APIs

These APIs allow fetching movies based on a list of preferred languages, automatically aggregating results from the corresponding language-specific databases.

- **Base URL**: `/movie-language`
- **Query Parameter**: `languages` (Required). Must be a JSON list, e.g., `["Bengali", "Marathi"]`.


### API Endpoints & Examples

Here are the full example URLs for testing (assuming server runs on port 5001):

1. **Upcoming Movies**
   - `http://localhost:5001/movie-language/?languages=["Bengali","Marathi","European"]`

2. **Popular Movies**
   - `http://localhost:5001/movie-language/popular?languages=["Bengali","Marathi","European"]`

3. **Recently Added Movies**
   - `http://localhost:5001/movie-language/recent?languages=["Bengali","Marathi","European"]`

4. **Top Rated Movies**
   - `http://localhost:5001/movie-language/recent-movies?languages=["Bengali","Marathi","European"]`

5. **Classical Movies**
   - `http://localhost:5001/movie-language/classical?languages=["Bengali","Marathi","European"]`

### Response Format
The response is a JSON list of movies. Each movie object includes a `source_db` field indicating its origin.

```json
{
  "movies": [
    {
      "id": 101,
      "title": "Movie Title",
      "source_db": "bengali_movies",
      "poster_path": "...",
      ...
    }
  ]
}
```


## Content APIs (Read-only)

Base path: `/content`

1) Get settings
   - `GET /content/settings`
   - Optional query param: `?key=YOUR_KEY` to fetch a single setting
   - Response example:
     ```json
     [
       { "id": 1, "key": "site_title", "value": "ViewFlix", "value_type": "text", "updated_at": "2025-11-11T12:34:56" }
     ]
     ```

2) Get banners
   - `GET /content/banners`
   - Returns only active banners, ordered by `sort_order` ASC then `created_at` DESC
   - Response example:
     ```json
     [
       {
         "id": 10,
         "title": "Holiday Sale",
         "image_url": "https://cdn.example.com/banner.jpg",
         "link_url": "https://example.com/offer",
         "is_active": true,
         "sort_order": 1,
         "created_at": "2025-11-11T12:34:56",
         "updated_at": "2025-11-11T12:35:56"
       }
     ]
     ```


## React Usage (Example)

```javascript
// Get all banners
const res = await fetch(`${API_BASE}/content/banners`);
const banners = await res.json();

// Get one setting by key
const res2 = await fetch(`${API_BASE}/content/settings?key=site_title`);
const siteTitle = await res2.json();
```


## Model Isolation

- Admin models live under: `app/models/admin/` and are imported only where needed:
  - Registered in Admin UI inside `app/__init__.py`.
  - Used by content API in `route/content.py`.
- Movie-related models remain in `app/models/` and are not imported by the app factory for admin/migration scope. This keeps migrations focused only on admin content tables unless you opt-in to import movies models explicitly.


## CORS

Set `FE_URL` in `.env` to your frontend origin(s). The app reads it and configures CORS accordingly.


## Connection Pool (Optional)

The app uses pooled MySQL connections with defaults that can be overridden via `.env`:

```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```


## Troubleshooting

- Access denied (1045): Ensure `DB_USER`/`DB_PASSWORD` in `.env` match MySQL credentials.
- QueuePool timeouts: Increase `DB_POOL_SIZE` / `DB_MAX_OVERFLOW`; verify long-running queries/transactions.
- Migrations not detected: Ensure admin models are importable at app init and re-run `flask db migrate`.
- CORS blocked: Set `FE_URL` correctly in `.env` and restart the server.


## Run The Server

```bash
python server.py
# or
FLASK_APP=server.py flask run --host 0.0.0.0 --port 5000
```

Open:
- Admin: `/admin`
- APIs: `/content/settings`, `/content/banners`
 

## Content-Based Recommendation System (Phase 1)

This backend also includes a **metadata-only, content-based movie recommendation model** built with **Linear Regression** (scikit-learn).  
It uses only movie metadata (genres, popularity, release date) and synthetic user genre profiles (no behavior data yet).


### High-Level Overview

- **Goal**: Rank movies for:
  - **Recommended for You**
  - **Trending in Your Genres**
  - **New Releases in &lt;Genre&gt;** (e.g. Action)
- **Inputs**:
  - Movie metadata from MySQL:
    - `id`
    - `title`
    - `genre_text` – e.g. `"Action|Drama|Thriller"`
    - `popularity`
    - `release_date`
  - User-selected genres (e.g. `["Action", "Drama"]`)
- **Outputs**:
  - Ranked movie lists per section, using a trained Linear Regression model.


### Data Sources & Mapping (Multi-DB)

The recommender is designed to train **one global model** over movies coming from **multiple MySQL databases** (languages/genres).

- Each DB has a common movie table schema (logical):
  - `id` – movie id
  - `title` – movie title
  - `genre_text` – pipe/comma separated genres, e.g. `"Action|Drama|Thriller"`
  - `popularity` – numeric popularity score (stored as float or string)
  - `release_date` – `DATE` or string `YYYY-MM-DD`
  - `poster_path` – optional poster relative path or URL
- All **free movie** data lives in a table named `free_movies` in each DB.
- The mapping is centralized via `MovieTableConfig`:
  - File: `app/reco/data_loader.py`
  - Example:
    - `MovieTableConfig(table_name="free_movies", id_column="id", title_column="title", genre_text_column="genre_text", popularity_column="popularity", release_date_column="release_date", poster_path_column="poster_path")`


### Modules & Responsibilities

- **`app/reco/db_connections.py`**
  - Reads base MySQL connection details from env:
    - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`
  - Discovers which movie databases to use:
    - `RECO_MOVIE_DATABASES` – comma-separated list (recommended), e.g.  
      `tamil_movies,telugu_movies,kanada_movies,malayalam_movies,action_movies,comedy_movies,romantic_movies,animated_movies,horror_movies,thriller_movies,mixgenres_movies`
    - If not set, falls back to values from `app.genre_config.DB_BY_GENRE`.
  - Provides:
    - `get_reco_database_names()` → `List[str]` of DB names.
    - `connect_to_database(database_name)` → raw MySQL connection using shared creds.

- **`app/reco/data_loader.py`**
  - Defines:
    - `MovieRecord` – container for movie metadata:
      - `id`, `title`, `genre_text`, `popularity_raw`, `release_date`
      - `poster_path` (optional)
      - `source_db` (optional, filled by multi-DB loader)
    - `MovieTableConfig` – describes which table/columns to read.

- **`app/reco/multi_db_loader.py`**
  - Uses `MovieTableConfig` + `connect_to_database` to read from **multiple** DBs.
  - Functions:
    - `load_movies_from_database(db_name, cfg)` – load `List[MovieRecord]` from a single DB.
    - `load_movies_multi_db(db_names, cfg)` – load from all DBs, combine into one list; each record is tagged with `source_db`.

- **`app/reco/preprocessing.py`**
  - Genre utilities:
    - `parse_genres(genre_text)` – supports `"Action|Drama"` or comma-separated.
    - `build_genre_vocab(movies)` – global vocab `genre -> index`.
    - `encode_genres_multi_hot(genres, vocab)` – multi-hot numpy vectors.
  - Popularity:
    - `PopularityNormalizer` – min–max scaling, built from all movie popularities.
  - Recency:
    - `compute_recency_score(release_date, half_life_days=180)` implementing  
      \( \text{recency} = \exp(-\text{days\_since\_release} / 180) \).
  - Feature containers:
    - `EngineeredFeatures` – holds:
      - `movie_ids`, `titles`
      - `movie_genre_vectors` (N × G)
      - `popularity_norm` (N × 1)
      - `recency_scores` (N × 1)
      - `genre_vocab`, `popularity_normalizer`
  - User-aware features:
    - `compute_genre_match_score(movie_genres, user_genres)` = matched / total user genres.
    - `build_full_feature_matrix_for_user(engineered, movies, user_genres)` combines:
      - movie genre multi-hot
      - normalized popularity
      - recency score
      - user genre multi-hot
      - `genre_match_score`

- **`app/reco/model.py`**
  - Relevance function (used to synthesize labels for supervised training):
    - \( \text{relevance} = 0.5 \cdot \text{genre\_match} + 0.3 \cdot \text{popularity\_norm} + 0.2 \cdot \text{recency} \)
  - Model:
    - `LinearRegression` from `sklearn.linear_model`.
    - `train_recommender(movies, default_user_genres, test_size=0.2)`:
      - Builds `EngineeredFeatures` from movies.
      - Builds a user-specific feature matrix for a **synthetic user genre profile**.
      - Trains the Linear Regression model.
      - Computes and returns **MSE** and **R²**.
  - Artifact wrapper:
    - `TrainedRecommender` stores:
      - `model` (LinearRegression)
      - `engineered` (EngineeredFeatures)
    - Methods:
      - `predict_for_user(movies, user_genres)` → predicted relevance + `genre_match_scores`.
      - `save(path)` / `load(path)` using `joblib`.
    - Default path: `RECO_MODEL_PATH` or `app/reco_artifacts/content_recommender.joblib`.

- **`app/reco/inference.py`**
  - `ScoredMovie` – holds:
    - `movie` (`MovieRecord`)
    - `model_score`
    - `popularity_norm`
    - `recency_score`
    - `genre_match_score`
  - `score_movies_for_user(recommender, movies, user_genres)`:
    - Uses `TrainedRecommender` to produce `List[ScoredMovie]` for a user.

  - **Section helpers (homepage logic)**:
    - **A. `recommended_for_you(scored_movies, user_genres, limit=25)`**
      - Filters to movies whose genres overlap with `user_genres`.
      - Sorts by `model_score` (predicted relevance).
      - Returns top 20–30 (configurable).
    - **B. `trending_in_your_genres(scored_movies, user_genres, limit=12)`**
      - Filters to movies overlapping `user_genres`.
      - Ranks by:
        - \( 0.7 \cdot \text{popularity\_norm} + 0.3 \cdot \text{model\_score} \)
      - Returns top 10–15 (configurable).
    - **C. `new_releases_in_genre(scored_movies, target_genre, days_window=60, limit=20)`**
      - Filters to movies where `genre_text` includes `target_genre` (case-insensitive).
      - Only keeps movies with `release_date` in the last `days_window` days.
      - Ranks by `model_score + recency_score`.
      - Reusable for any genre (e.g. `"Action"` → **“New Releases in Action”**).


### Dependencies for the Recommender

Additional packages (already listed in `requirements.txt`):

- `numpy`
- `scikit-learn`
- `joblib`

Install everything in your (activated) virtual environment:

```bash
pip install -r requirements.txt
```


### Training the Global Multi-DB Model

1. **Ensure base DB env vars are set** (same as for the main app, but note we do NOT use `DB_DATABASE` here):

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=your_mysql_user_with_access_to_all_movie_dbs
export DB_PASSWORD=your_password
```

2. **Specify which databases to include** in training (recommended):

```bash
export RECO_MOVIE_DATABASES="tamil_movies,telugu_movies,kanada_movies,malayalam_movies,action_movies,comedy_movies,romantic_movies,animated_movies,horror_movies,thriller_movies,mixgenres_movies"
```

If `RECO_MOVIE_DATABASES` is not set, the system will fall back to using all database names from `app.genre_config.DB_BY_GENRE`.

3. **Run the multi-DB training script** from the backend root:

```bash
python train.py
```

This will:

- Connect to each configured database.
- Load movies from the `free_movies` table in every DB.
- Build a unified dataset and engineer features (genres, popularity, recency).
- Train a global Linear Regression model using a synthetic user genre profile.
- Print **MSE** and **R²** to the console.
- Save the trained model artifact to `app/reco_artifacts/content_recommender.joblib` (or `RECO_MODEL_PATH` if set).


### Running Inference (CLI Demo, Multi-DB)

You can test the multi-DB recommender from the command line before wiring it into Flask routes:

```bash
python run_recommender_demo.py
```

What it does:

- Resolves the list of movie databases using `RECO_MOVIE_DATABASES` (or `DB_BY_GENRE` fallback).
- Loads movies from the `free_movies` table across all those DBs.
- Loads `TrainedRecommender` from disk.
- Uses a sample user genre profile (e.g. `["Action", "Drama"]`).
- Scores all movies (from every DB) and prints:
  - **“Recommended for You”**
  - **“Trending in Your Genres”**
  - **“New Releases in Action”**


### Integrating with Flask Routes (Future Phase)

For production integration, the typical pattern is:

- Load `TrainedRecommender` once at app startup (or lazily, then cache it).
- For each request:
  - Resolve user’s selected genres (e.g. from `users.free_genres` or onboarding data).
  - Load candidate movies (e.g. from `movie_tamil_en`, `popularmovies`, etc.).
  - Use:
    - `score_movies_for_user(...)`
    - `recommended_for_you(...)`
    - `trending_in_your_genres(...)`
    - `new_releases_in_genre(...)`
  - Return ranked lists as JSON to your frontend.

This phase-1 system is **content-based only** (no collaborative filtering, no deep learning) and is designed so you can later plug in behavior-based or hybrid models without changing the database schema.

