# Customer Feedback & Complaint Management System

FastAPI backend to collect customer feedback, manage complaints end to end, assign support agents, track SLAs, send in-app notifications and report on customer satisfaction.

**Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, JWT (access + rotating refresh tokens), bcrypt, MySQL / PostgreSQL (SQLite for local dev and tests), Pytest.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # edit DATABASE_URL and SECRET_KEY
alembic upgrade head            # create tables
uvicorn app.main:app --reload
```

* Swagger UI: http://localhost:8000/docs  ·  ReDoc: `/redoc`  ·  Health: `/health`
* On startup the app seeds the 3 SLA rules, the 5 default categories and (if `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` are set) the first admin. Run it manually with `python -m app.db.init_db`.
* `AUTO_CREATE_TABLES=true` creates tables without Alembic (dev convenience only).

### Docker

```bash
docker compose up --build       # API on :8000 + PostgreSQL, migrations run automatically
```

### MySQL / PostgreSQL

Set `DATABASE_URL` to `mysql+pymysql://user:pass@host:3306/feedback_db` or `postgresql+psycopg2://user:pass@host:5432/feedback_db`, then `alembic upgrade head`.

## Tests

```bash
pytest            # 111 tests, in-memory SQLite, no setup needed
```

Covers login/auth, role permissions, feedback, complaints, assignment, invalid status transitions, SLA calculations, dashboard metrics and reports.

## Roles

| Role | Can do |
|---|---|
| **admin** | Everything, incl. user management |
| **support_manager** | Customers, agents, categories, assign/reassign, SLA rules, dashboard, reports, audit logs |
| **support_agent** | See and work on complaints assigned to them (status, resolve, notes, comments) |
| **customer** | Own profile, own feedback, own complaints, comments, close/reopen own complaints |

## Complaint lifecycle

```
open ──assign──▶ assigned ──▶ in_progress ◀──▶ waiting_for_customer
                                  │                    │
                                  └──────▶ resolved ◀──┘
                                              │
                                  closed ◀────┤
                                     │        │
                                     └─▶ reopened ◀─┘ ──▶ assigned / in_progress
```

Invalid transitions return **409** `invalid_status_transition` with the allowed next statuses (e.g. a complaint cannot be closed without being resolved). Use the dedicated endpoints for `assign`, `resolve`, `close` and `reopen`; `POST /complaints/{id}/status` handles `in_progress` / `waiting_for_customer`. Closed complaints can be reopened within `REOPEN_WINDOW_DAYS` (default 7).

## SLA

* Hours per priority are stored in `sla_rules` (default **high 4h · medium 12h · low 24h**, editable via `PUT /sla/rules/{priority}`).
* `due_at = created_at + SLA hours`. Changing priority or reopening starts a new SLA cycle.
* Active complaint: `time_remaining = due_at − now`; **breached** if `now > due_at`; state `at_risk` when within `SLA_WARNING_MINUTES` (default 60).
* Resolved complaint: `resolution_duration = resolved_at − created_at`; **breached** if `resolved_at > due_at`, otherwise `met`.
* `POST /sla/check` creates `sla_approaching` / `sla_breached` notifications, once per complaint per SLA cycle. Call it from cron, or set `SLA_CHECK_INTERVAL_SECONDS` to run it inside the app.

### Timezone strategy

All timestamps are stored as **naive UTC**, created only via `utcnow()`, and returned as ISO-8601 with `+00:00`. Date filters (`date_from`, `date_to`, `created_from`, …) are calendar dates in UTC; `date_to` is inclusive of the whole day.

## Satisfaction metrics (formulas)

Also served by `GET /api/v1/reports/satisfaction/formulas`.

| Metric | Formula |
|---|---|
| Average rating | `AVG(rating)`, 2 decimals (null if no feedback) |
| Positive | count with rating ≥ 4 |
| Neutral | count with rating = 3 |
| Negative | count with rating ≤ 2 |
| Satisfaction % (CSAT) | `positive / total × 100` (0 if no feedback) |
| Trends | feedback grouped by UTC date: count and average rating |
| Resolved-complaint satisfaction | same metrics for feedback linked to resolved/closed complaints; response rate = resolved complaints with feedback ÷ resolved complaints × 100 |

## Dashboard & reports (manager/admin)

`/dashboard/summary` (customers, feedback, complaints, open, resolved, overdue, avg resolution hours, avg rating, by priority), `/dashboard/complaints-by-priority`, `/dashboard/agent-complaints`, `/reports/satisfaction[...]`, `/reports/complaints-by-category`, `/reports/agent-performance`. All accept `date_from` / `date_to`; list reports support `page`, `size`, `sort_by`, `sort_order`.

## API design notes

* **Pagination/sorting:** `page`, `size` (max 100), `sort_by` (validated against a whitelist), `sort_order`. Responses: `{items, total, page, size, pages}`.
* **Search & filtering:** `GET /complaints` combines status, priority, category, agent, customer, created range, resolved range, overdue and free text in one SQL query with `LIMIT/OFFSET` and composite indexes. Aggregates are computed in SQL, never in Python loops.
* **Errors:** one format everywhere: `{"error": {"code", "message", "details", "request_id"}}` with 400/401/403/404/409/422 used meaningfully; the `X-Request-ID` header matches.
* **Transactions:** each service call commits once; the audit row is written in the same transaction as the change, so both succeed or neither does.
* **Duplicates:** unique emails, case-insensitive category names, one feedback per complaint, short-window duplicate-feedback guard, unique complaint reference (`CMP-YYYYMMDD-XXXXXX`).
* **Audit logs:** `GET /audit-logs` records actor, action, entity, timestamp and a from/to diff for complaint creation, assignment/reassignment, status changes, resolution, reopening and feedback updates.
* **Security:** bcrypt hashing, refresh tokens stored hashed and rotated on every use, deactivation revokes tokens, customers can never see internal notes or other customers' data.

## Project layout

```
app/
  api/v1/endpoints/   HTTP layer (thin)        services/      business rules & workflow
  core/               security, jwt, RBAC       repositories/  SQL queries
  models/ schemas/    SQLAlchemy / Pydantic     middleware/    request id, error handling
  db/  utils/         session, seed, helpers
alembic/              migrations                tests/         unit + integration
postman/              ready-to-import collection
```

## Postman

Import `postman/customer_feedback_complaints.postman_collection.json`, run **Authentication → Login** (default `admin@example.com` / `Admin12345` from `.env`); the token is saved automatically. Creating a complaint stores `complaint_id` for the rest of the flow.
