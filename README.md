# ViewFlix Admin Backend Setup (Flask)

This document explains everything added to enable an Admin Dashboard using Flask-Admin, how to configure the environment, create the database, run migrations, and consume the new content APIs from your frontend.


## Overview of Changes

- Added Flask-Admin for a web dashboard at `/admin`.
- Added admin-only models:
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
- `route/content.py` – Public APIs to fetch settings and banners.
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


