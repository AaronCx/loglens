# LogLens

A real-time error logging and monitoring platform.

**Live:** [Dashboard](https://loglens-app.vercel.app) | [API](https://loglens-api.vercel.app/docs) | [Health](https://loglens-api.vercel.app/health)

- **Backend** — FastAPI + SQLAlchemy + Postgres/Supabase, deployed as Vercel Serverless Functions
- **Frontend** — Next.js 16, Tailwind CSS, Recharts, auto-refreshing dashboard
- **SDK** — `loglens-sdk` Python package with a `capture()` API

```
loglens/
├── backend/       # FastAPI API (Vercel Serverless)
├── frontend/      # Next.js dashboard
└── sdk/           # loglens-sdk Python package
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | >= 3.11 |
| Node.js | >= 18 |
| PostgreSQL | >= 14 (or Supabase project) |
| Vercel CLI | `npm i -g vercel` |

---

## 1 — Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit .env
```

### Environment variables (`backend/.env`)

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy async URL | `postgresql+asyncpg://user:pass@localhost/loglens` |
| `API_KEY` | Secret key clients must send | `super-secret-key` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3000` |
| `RATE_LIMIT` | Default rate limit | `100/minute` |
| `INGEST_RATE_LIMIT` | Event ingestion limit | `200/minute` |
| `RETENTION_DAYS` | Auto-delete events older than N days | `30` |
| `CRON_SECRET` | Secures the `/cron/cleanup` endpoint | (random string) |

#### Using Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Go to **Project Settings -> Database -> Connection string -> URI**.
3. Replace `postgresql://` with `postgresql+asyncpg://` and set it as `DATABASE_URL`.

### Start the backend (local)

```bash
uvicorn main:app --reload --port 8000
```

Tables are auto-created on first run. API docs at <http://localhost:8000/docs>.

---

## 2 — Frontend setup

```bash
cd frontend
cp .env.example .env.local   # edit if backend isn't on :8000
npm install
npm run dev
```

Open <http://localhost:3000>.

### Environment variables (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |

---

## 3 — SDK

### Install

```bash
pip install ./sdk          # local
# or
pip install loglens-sdk    # once published to PyPI
```

### Usage

```python
from loglens_sdk import LogLens

ll = LogLens(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    service="payment-service",
    environment="production",
)

# Severity shortcuts
ll.info("Server started")
ll.warning("Disk usage above 80%", metadata={"percent": 82})
ll.error("Failed to process order", metadata={"order_id": "ord_99"})
ll.critical("Database connection lost!")

# Capture exceptions automatically
try:
    risky_operation()
except Exception:
    ll.capture_exception()

# Global singleton
import loglens_sdk
loglens_sdk.init(api_url="...", api_key="...", service="my-app")
loglens_sdk.capture("Something went wrong", severity="error")
```

---

## API Reference

### `POST /events` — Ingest an event

**Header:** `X-API-Key: <your-key>`

```json
{
  "severity": "error",
  "service": "payment-service",
  "message": "Stripe webhook failed",
  "stack_trace": "Traceback (most recent call last):\n...",
  "metadata": { "order_id": "ord_42", "amount": 99.99 },
  "environment": "production"
}
```

Returns `201` with the created event object.

### `GET /events` — List events

Query params: `severity` (repeatable), `service`, `environment`, `search`, `page`, `page_size`

### `GET /events/{id}` — Get a single event

### `GET /stats` — Aggregate counts by severity and service

### `GET /stats/timeseries?hours=24` — Hourly buckets for the time-series chart

### `DELETE /events/{id}` — Delete a single event (requires API key)

### `DELETE /events` — Clear all events (requires API key)

### `DELETE /events/expired` — Remove events past retention period

### Projects & API Keys

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/projects` | Create a project |
| `GET` | `/projects` | List all projects |
| `GET` | `/projects/{id}` | Get project details |
| `POST` | `/projects/{id}/keys` | Create project-scoped API key |
| `GET` | `/projects/{id}/keys` | List API keys for a project |
| `DELETE` | `/projects/{id}/keys/{key_id}` | Revoke API key |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks` | Create webhook with severity/service filters |
| `GET` | `/webhooks` | List all webhooks |
| `PATCH` | `/webhooks/{id}` | Update webhook configuration |
| `DELETE` | `/webhooks/{id}` | Delete webhook |

Webhooks fire on event creation with HMAC-SHA256 signature verification (`X-LogLens-Signature` header) and support severity/service filtering.

---

## Dashboard features

| Feature | Detail |
|---|---|
| Auto-refresh | Dashboard polls for new events every 5 seconds |
| Severity filter | Toggle info / warning / error / critical |
| Environment filter | Filter by production, staging, development, testing |
| Full-text search | Filter by message content |
| Event deletion | Delete individual events from the detail drawer |
| Toast notifications | User-facing feedback for errors and actions |
| Events over time | Stacked area chart, 24 h window, auto-refreshes |
| Events by service | Horizontal bar chart, top 8 services |
| Stack trace viewer | Slide-in drawer with syntax highlight, one-click copy |
| Pagination | 50 events per page |
| Stats cards | Total, critical, error, warning counts |

---

## Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend  | Vercel   | https://loglens-app.vercel.app |
| Backend   | Vercel Serverless Functions | https://loglens-api.vercel.app |
| Database  | Supabase | Postgres 17 (us-west-2) |

Previously hosted on Render. Migrated to Vercel serverless functions for unified deployment.

### Backend (Vercel)

Root directory: `backend/`. Deployed as a Python serverless function via `@vercel/python`.

Set these env vars in the Vercel dashboard:
- `DATABASE_URL` — Supabase connection string
- `API_KEY` — global API key
- `ALLOWED_ORIGINS` — frontend URL(s)
- `CRON_SECRET` — secures the scheduled cleanup endpoint

Retention cleanup runs automatically via Vercel Cron (every 6 hours).

### Frontend (Vercel)

Root directory: `frontend/`. Set `NEXT_PUBLIC_API_URL` to the backend URL.

---

## License

MIT
