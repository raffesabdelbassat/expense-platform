# ExpenseIQ

ExpenseIQ is a FastAPI application for importing bank CSV transactions, assigning categories with a scikit-learn model, and viewing per-user spending in a browser dashboard.

## Run locally

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Set a private JWT signing key before starting the server:

   ```powershell
   $env:JWT_SECRET_KEY = "replace-with-a-long-random-secret"
   ```

   The app uses `sqlite:///./expense_platform.db` when `DATABASE_URL` is unset. Set `DATABASE_URL` to a SQLAlchemy-compatible PostgreSQL URL to use PostgreSQL.

3. Start the app:

   ```powershell
   uvicorn main:app --reload
   ```

   Open <http://127.0.0.1:8000>.

## API

- `POST /register?email=...&password=...` creates an account (passwords must contain at least 8 characters).
- `POST /login` accepts OAuth2 form fields `username` (email) and `password`, and returns a bearer token.
- `GET /me` returns the authenticated account.
- `POST /upload` accepts a CSV file with a description (`description`, `merchant`, `name`, or `details`) and amount (`amount`, `value`, or `sum`) column. An optional date column can be named `date`, `transaction date`, or `time`. Imports are limited to 5 MB and 5,000 rows.
- `GET /transactions` returns the authenticated user's transactions.

## Deployment

Configure `DATABASE_URL` and a unique `JWT_SECRET_KEY` in the hosting provider's environment settings. Do not commit secrets or production database credentials.

## Connect a bank (Salt Edge)

Bank linking is server-side and disabled until Salt Edge Partner API credentials are configured. Salt Edge's Partners API currently requires an invitation; partner accounts begin with fake/sandbox providers, and real-bank access requires Salt Edge approval. See the [Salt Edge Partners API quick start](https://docs.saltedge.com/partners/v1/).

Set these environment variables on the server (never in browser JavaScript or a committed file):

- `SALTEDGE_APP_ID`
- `SALTEDGE_SECRET`
- `APP_BASE_URL` (the public HTTPS URL in production, such as `https://your-app.example.com`)

For local development, set them in the PowerShell session before launching Uvicorn. The dashboard sends the signed-in user's email to Salt Edge to create a lead, then sends the user to Salt Edge and their bank to approve account and transaction access. The app never asks for or stores bank login credentials.

Before enabling real banks, complete Salt Edge's partner approval and configure its required terms, privacy policy, callback, consent-revocation, and live-mode requirements. Until then, only Salt Edge fake/sandbox providers may be available.
