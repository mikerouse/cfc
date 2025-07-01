# Council Finance Counters

This project migrates the legacy WordPress plugin into a Django application.

## Setup

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Apply database migrations:

```bash
python manage.py migrate
```

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
