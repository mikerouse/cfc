# Council Finance Counters

This project migrates the legacy WordPress plugin into a Django application.

## Setup

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

## Importing legacy council data

Staff members can upload a JSON export from the legacy plugin directly in the
Django admin. Navigate to **Councils** in the admin and use the “Import JSON”
button at the top-right of the change list. After uploading the file you will be
prompted to map the plugin’s fields onto the new system. Large imports proceed
asynchronously with a progress readout. The file `councils-migration.json`
provides an example of the expected format.

Council types are editable via a dedicated model in the admin. Use the
**Council Types** section to add new entries which then appear as options in the
drop-down on each council form.

## Animated Counters

From July 2025 counters can be configured from the Django admin. Create a
`Counter Definition` with a slug, formula and explanation text. Counters sum the
specified figure fields using the `CounterAgent`. Each council can enable or
disable individual counters in the **Councils** admin. Managers can manage all
definitions via `/manage/counters/` using the management toolbar shown above the
header. The screen lists existing counters and provides an **Add counter**
button. Each form includes a small formula builder&mdash;click or drag available
fields into the formula input and choose operators. Formulas are validated
client-side using **math.js** so mistakes are surfaced immediately. Counters
also define precision, currency display and whether large values should appear
as friendly text like `£1m`.

### Proxy configuration

When `USE_X_FORWARDED_HOST` is enabled the application trusts the
`X-Forwarded-For` header to determine the client's IP address when handling
submissions. Deployments behind reverse proxies must ensure the proxy chain is
configured to pass a clean header from trusted sources only; otherwise the
recorded address can be spoofed.

