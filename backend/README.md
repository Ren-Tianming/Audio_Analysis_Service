# Audio_Analysis_System Backend

FastAPI + MySQL + Redis backend for `Audio_Analysis_System`.

## Run

```bash
pip install -r requirements-dev.txt
cp ../.env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

Create or promote the first administrator after migrations:

```bash
export AUDIO_ADMIN_EMAIL=admin@example.com
export AUDIO_ADMIN_USERNAME=Administrator
export AUDIO_ADMIN_PASSWORD=replace-with-a-strong-password
PYTHONPATH=. python scripts/create_admin.py
```

## Key Endpoints

| Area | Endpoint | Purpose |
| --- | --- | --- |
| Auth | `POST /api/v1/auth/register` | Register, issue JWT and hashed refresh token |
| Auth | `POST /api/v1/auth/login` | Login and daily bonus |
| Auth | `POST /api/v1/auth/refresh` | Refresh token rotation |
| Auth | `POST /api/v1/auth/logout-all` | Revoke all user refresh tokens |
| Points | `GET /api/v1/points/transactions` | Point ledger |
| Analysis | `POST /api/v1/songs/analyze` | Analyze audio and charge points on success |
| Analysis | `GET /api/v1/songs/history/{id}/report` | PDF report |
| API Key | `POST /api/v1/api-keys` | Issue API key, plaintext shown once |
| Admin | `/api/v1/admin/*` | User, role, points, orders, settings, audit |
| Ops | `/health`, `/ready`, `/metrics` | Health, dependency readiness, Prometheus metrics |

## Configuration

Environment variables use the `AUDIO_` prefix.

| Variable | Purpose |
| --- | --- |
| `AUDIO_DATABASE_URL` | SQLAlchemy MySQL URL |
| `AUDIO_REDIS_URL` | Redis URL for rate limiting |
| `AUDIO_JWT_SECRET_KEY` | JWT signing secret |
| `AUDIO_CORS_ORIGINS` | Comma-separated frontend origins |
| `AUDIO_UPLOAD_DIR` | Temporary upload directory |
| `AUDIO_RATE_LIMIT_REQUESTS` | Global requests per window |
| `AUDIO_AUTH_RATE_LIMIT_REQUESTS` | Auth requests per window |
| `AUDIO_AUTO_CREATE_TABLES` | Test/local-only schema creation |

## Quality

```bash
ruff check .
mypy app scripts
bandit -r app scripts -x tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=60
```
