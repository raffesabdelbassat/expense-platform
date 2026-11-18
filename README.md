# ExpenseIQ

**A clear, personal view of your spending.** ExpenseIQ is a web app for importing transactions, automatically categorizing purchases, and exploring cash flow in a clean dashboard.

## Overview

ExpenseIQ gives each user a private workspace for their financial activity. Create an account, import a bank statement as CSV, and review your transactions and spending patterns from the dashboard. The app can also connect to banks through Salt Edge when partner credentials are configured.

### Features

- Email and password accounts with hashed passwords and bearer-token authentication
- Per-user transaction storage
- CSV import with automatic transaction categorization
- Dashboard summaries for outflow, inflow, transaction count, and average outflow
- Cash-flow and spending-by-category charts
- Transaction search, category filtering, and date-range selection
- Optional Salt Edge bank connection and transaction sync
- SQLite by default, with PostgreSQL support through `DATABASE_URL`

## Get started

### Requirements

- Python 3.10 or newer
- `pip`

### Windows PowerShell

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set a private JWT signing key and start the development server:

```powershell
$env:JWT_SECRET_KEY = "replace-with-a-long-random-secret"
python -m uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Create an account, sign in, and import a CSV from the dashboard.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export JWT_SECRET_KEY="replace-with-a-long-random-secret"
python -m uvicorn main:app --reload
```

Then visit [http://127.0.0.1:8000](http://127.0.0.1:8000).

> Keep the server terminal open while using the local app. Stop it with `Ctrl+C`.

## Importing transactions

Upload a UTF-8 CSV file up to **5 MB** and **5,000 transactions**. The importer detects common comma, semicolon, tab, and pipe separators. A date column is optional.

The file must include:

| Field | Accepted column names |
| --- | --- |
| Description | `description`, `merchant`, `merchant name`, `name`, `details`, `transaction`, `memo`, `payee`, and related bank-export names |
| Amount | `amount`, `transaction amount`, `value`, `sum`, or supported Polish equivalents such as `kwota operacji` |
| Date (optional) | `date`, `transaction date`, `posting date`, `booking date`, `time`, or supported Polish equivalents |
| Currency (optional) | `currency`, `currency code`, or supported Polish equivalents |

Example:

```csv
date,description,amount,currency
2026-01-15,Coffee shop,-18.50,PLN
2026-01-31,Salary,6200.00,PLN
```

Expenses are typically negative and incoming payments positive. The included model predicts a category from each transaction description; review categories as estimates rather than financial advice.

## Bank connections (optional)

Direct bank linking uses the Salt Edge Partners API and is disabled until credentials are configured. Partner access may require an invitation or approval; sandbox providers may be the only available option before approval.

Configure these variables in the server environment:

| Variable | Purpose |
| --- | --- |
| `SALTEDGE_APP_ID` | Salt Edge application ID |
| `SALTEDGE_SECRET` | Salt Edge application secret |
| `APP_BASE_URL` | Public base URL used for the authorization return route; use HTTPS in production |

For local PowerShell development, set them in the same terminal before starting Uvicorn:

```powershell
$env:SALTEDGE_APP_ID = "your-app-id"
$env:SALTEDGE_SECRET = "your-app-secret"
$env:APP_BASE_URL = "http://127.0.0.1:8000"
```

Users authorize access with Salt Edge and their bank. ExpenseIQ does not ask for or store bank login credentials. Keep provider secrets out of source control and browser code. Before enabling real-bank access, complete Salt Edge's partner requirements for consent, terms, privacy, callbacks, and production mode. See the [Salt Edge Partners API documentation](https://docs.saltedge.com/partners/v1/).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `JWT_SECRET_KEY` | Local development fallback | Signing key for access tokens. Set a unique, long random value for every deployed environment. |
| `DATABASE_URL` | `sqlite:///./expense_platform.db` | SQLAlchemy database URL. PostgreSQL is supported. |
| `SALTEDGE_APP_ID` | Unset | Enables Salt Edge bank connection when paired with the secret. |
| `SALTEDGE_SECRET` | Unset | Salt Edge API secret. |
| `APP_BASE_URL` | Request host | Public app URL for Salt Edge's authorization return route. |

Set secrets through your shell or hosting provider's environment settings. The repository ignores `.env` files and local database files; do not commit credentials or production data.

## API

FastAPI serves interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) while the app is running.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/register` | Create an account with `email` and `password` query parameters; password must be at least 8 characters. |
| `POST` | `/login` | Sign in with OAuth2 form fields `username` (email) and `password`; returns a bearer token. |
| `GET` | `/me` | Return the signed-in account. |
| `POST` | `/upload` | Import a CSV file; requires bearer authentication. |
| `GET` | `/transactions` | List the signed-in user's transactions. |
| `GET` | `/bank/connections` | List the signed-in user's bank connections. |
| `POST` | `/bank/connect` | Start a Salt Edge authorization flow. |
| `POST` | `/bank/complete` | Complete the authorization callback. |
| `POST` | `/bank/sync` | Sync transactions from connected banks. |

## Deployment

The repository includes a Render service definition in `render.yaml`. Configure a persistent database URL and a unique `JWT_SECRET_KEY` in the hosting provider's environment settings. For Salt Edge, also configure the credentials and public HTTPS `APP_BASE_URL`. Review the provider's storage and database requirements before using SQLite for a deployed service.

## Tech stack

- **Backend:** FastAPI, SQLAlchemy, SQLite or PostgreSQL
- **Authentication:** OAuth2 password flow, JWT, bcrypt password hashing
- **Categorization:** scikit-learn text-classification pipeline
- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **Bank data:** Salt Edge Partners API (optional)

## License

No license file is currently included. Contact the repository owner for permission to reuse or distribute this project.
