# Payments API

A Flask-based REST API for processing payments, managing user accounts, and handling subscriptions.

## Architecture

```
src/
  api/        — REST endpoints and request validation
  auth/       — JWT authentication, session management, RBAC
  payments/   — Payment gateway integration, charge processing
  db/         — Database models, queries, migrations
  cache/      — Redis caching layer
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens |
| `STRIPE_SECRET_KEY` | Stripe API secret key |

## Running

```bash
# Development
flask --app src.api.app run --debug

# Production
gunicorn src.api.app:create_app()
```

## Testing

```bash
pytest --cov=src
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Authenticate and receive JWT |
| POST | `/api/v1/auth/logout` | Invalidate session |
| GET | `/api/v1/users/me` | Get current user profile |
| POST | `/api/v1/payments/charge` | Create a new charge |
| GET | `/api/v1/payments/:id` | Get payment details |
| POST | `/api/v1/payments/:id/refund` | Refund a payment |
