# Battle Chess Arena API

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run `python manage.py migrate` to create the local SQLite database.
4. Start the API with `python manage.py runserver 127.0.0.1:8000`.

The health check is available at `http://127.0.0.1:8000/api/health/`.

The local development database is SQLite and is stored in `db.sqlite3`.