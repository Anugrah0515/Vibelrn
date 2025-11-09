Vibelrn
======

Lightweight FastAPI + Celery + SQLAlchemy demo application.

Overview
--------
This project demonstrates:
- FastAPI HTTP endpoints
- SQLAlchemy Core (table definitions + simple queries)
- Celery background tasks with Redis broker
- Optional OpenAI integration to enrich review tone/sentiment

Repository layout
-----------------
app/
- main.py            FastAPI app and route definitions (delegates to helpers in tasks.py)
- tasks.py           Celery task(s) and synchronous helper implementations used by endpoints
- database.py        SQLAlchemy engine, metadata and table definitions
- celery_app.py      Celery app configuration (broker/backend)
- celery_worker.py   Worker entrypoint used when starting Celery

Quickstart (Windows PowerShell)
-------------------------------
Prereqs
- Python 3.9+ installed and on PATH
- Redis server running locally (or update broker URL in `app/celery_app.py`)

1) Create and activate virtualenv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install fastapi uvicorn sqlalchemy celery redis openai
```

3) (Optional) Set OpenAI API key for tone/sentiment enrichment

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

4) Start Redis (if not already running)
- On Windows if you installed Redis, run the redis-server executable (or use WSL / Docker). The app expects Redis at redis://localhost:6379/0 by default.

5) Start the Celery worker (from project root)

```powershell
celery -A app.celery_worker worker --loglevel=info
```

This worker imports `app.tasks` so Celery tasks are registered. If you previously started a worker without the module import setup you may hit KeyError for tasks.

6) Run the FastAPI app

```powershell
uvicorn app.main:app --reload
```

7) Open interactive docs

Visit http://127.0.0.1:8000/docs to try endpoints through Swagger UI.

Notes about the database
------------------------
- By default the project creates an in-memory SQLite DB (configured in `app/database.py`). That means data is ephemeral and disappears when the process exits.
- To persist data across restarts, change the engine URL in `app/database.py`:

```py
# change this
engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
# to a file-based sqlite database
engine = create_engine("sqlite:///./app.db", echo=True)
```

- After changing the engine, restart the FastAPI server so tables are created on startup (the module runs `metadata_obj.create_all(engine)`).

Endpoints (examples)
--------------------
- GET /
  - Returns: {"message": "FastAPI + Celery + SQLAlchemy demo"}

- POST /add-category/
  - Query params: name (required), description (optional)
  - Example: POST http://localhost:8000/add-category/?name=Electronics&description=Gadgets
  - Returns message and created category (including generated id)

- GET /categories/
  - Lists all categories

- POST /review/add-review/
  - Params: text, stars, review_id, tone (opt), sentiment (opt), category_id (opt)
  - Adds a review history entry (multiple entries per `review_id` represent versions)

- GET /reviews/
  - Lists raw review_history rows

- GET /reviews/by-category/?category_id=<id>
  - Returns up to 15 most-recent reviews for a category; uses the latest review_history entry per review_id
  - If a review's tone or sentiment is null, and `OPENAI_API_KEY` is configured, the server will call OpenAI synchronously to enrich and persist those values

- GET /reviews/trends
  - Returns top 5 categories by descending average stars (average uses latest review per review_id)
  - Access is logged asynchronously using Celery

Access logging and Celery
-------------------------
- All endpoints invoke `log_access_task.delay(...)` to enqueue an access log entry.
- The Celery worker must be started with `celery -A app.celery_worker worker --loglevel=info` so that `app.tasks` is imported and tasks are registered with the Celery app.
- The Celery broker and backend are configured in `app/celery_app.py` (default: Redis at `redis://localhost:6379/0`).

OpenAI enrichment
-----------------
- `app/tasks.py` contains code that uses the OpenAI ChatCompletion API (gpt-3.5-turbo) to compute `tone` and `sentiment` for reviews that are missing those fields.
- The key must be set in the `OPENAI_API_KEY` environment variable before starting the FastAPI server.
- Current behavior: enrichment occurs synchronously as part of `GET /reviews/by-category/` (this will add latency when missing values exist). If you prefer async enrichment, move the enrichment call into a Celery task and call it with `.delay()`.

Troubleshooting
---------------
- sqlite3.OperationalError: no such table: category
  - Ensure you imported/started the server after `app.database` was created. The `database.py` module calls `metadata_obj.create_all(engine)`; restart the FastAPI app to create tables.

- KeyError: 'app.tasks.log_access_task' when running the worker
  - Start the worker using the `app.celery_worker` module (created in this project) which imports `app.tasks` so tasks get registered:

```powershell
celery -A app.celery_worker worker --loglevel=info
```

- OpenAI failures or missing enrichment
  - Ensure `OPENAI_API_KEY` is set. Check network access and API quota.

Next steps / Improvements
------------------------
- Make OpenAI enrichment asynchronous (move into a Celery task) to avoid request latency.
- Switch to a persistent DB (SQLite file, PostgreSQL) for production and for sharing data with Celery workers.
- Add unit tests around the SQL logic and endpoint responses.
- Add a `requirements.txt` for reproducible installs.

If you'd like I can (pick one):
- Add a `requirements.txt` with pinned versions
- Switch the DB to a file-based SQLite by updating `app/database.py` and restarting the server
- Move LLM enrichment into a background Celery task

