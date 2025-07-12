# Council Finance Counters

This project migrates the legacy WordPress plugin into a Django application.

## Setup

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Whenever `requirements.txt` changes (for example, after pulling a new version of
the code) run the install command again so new packages like **Django Channels**
are available.

2. Apply database migrations whenever pulling new code:

```bash
python manage.py migrate
```
The notification system introduced in July 2025 adds a new table, so be sure to
run migrations after updating.

3. **Create the first admin account** so you can log in to the Django admin. Run:

```bash
python manage.py createsuperuser
```

Follow the prompts to set a username, email and password.

4. Start the development server:

```bash
python manage.py runserver
```

You can then access the admin at `http://localhost:8000/admin/` using the credentials created above.

When using SQLite with the real-time features enabled, you might see
`database is locked` errors if multiple connections try to write at the same
time. The default configuration now increases the SQLite timeout to 20 seconds
to mitigate this. If the problem persists, stop any background processes that
may be accessing the database.

## Adding councils and figures

Create councils and financial years directly in the Django admin backend. Otherwise use the front-end to create things like new fields, characteristics, etc.

## Animated Counters

Counters can be configured with a formula and explanation text. Each council can enable or disable individual counters in the **Councils** admin (so you can remove counters that don't apply - for instance, not all councils collect council tax). 