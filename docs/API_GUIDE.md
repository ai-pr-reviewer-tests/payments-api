# API Guide

## Authentication

All endpoints except `/health` and `/api/v1/auth/login` require a valid JWT token
in the `Authorization` header:

```
Authorization: Bearer <token>
```

### Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'
```

Response:
```json
{"token": "eyJ...", "user_id": 1}
```

### Logout

```bash
curl -X POST http://localhost:5000/api/v1/auth/logout \
  -H "Authorization: Bearer <token>"
```

## Payments

### Create a Charge

```bash
curl -X POST http://localhost:5000/api/v1/payments/charge \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_cents": 2500,
    "currency": "usd",
    "source_token": "tok_visa",
    "description": "Order #1234"
  }'
```

### Get Payment Details

```bash
curl http://localhost:5000/api/v1/payments/42 \
  -H "Authorization: Bearer <token>"
```

### Refund a Payment

```bash
curl -X POST http://localhost:5000/api/v1/payments/42/refund \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount_cents": 1000}'
```

Omit `amount_cents` for a full refund.

## Error Handling

All errors return JSON with an `error` field:

```json
{"error": "Invalid credentials"}
```

Common HTTP status codes:
- `400` — Validation error
- `401` — Authentication required or failed
- `403` — Insufficient permissions
- `404` — Resource not found
