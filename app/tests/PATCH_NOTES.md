# Test suite for savings-automation

Generated: 2025-09-03T20:02:18.254832 UTC

## What’s included
- `tests/` with end-to-end integration tests (HTTP) and a couple of optional unit tests.
- `requirements.additions.txt` with the extra dev dependencies needed to run tests.

## How to install test deps (minimal change)
Append these lines to your existing `requirements.txt` (or install them only for dev):

```
pytest==8.3.2
pytest-asyncio==0.23.8
httpx==0.27.0
anyio==4.4.0
pillow==10.4.0
python-dateutil==2.9.0.post0
```

> `pillow` is already in your app requirements for OCR; keep whichever single version you prefer.

Then rebuild and bring the stack up:

```bash
docker compose build --no-cache
docker compose up -d
```

## Run the tests (integration, hitting the live API)

From your repo root (where `docker-compose.yml` lives):

```bash
# Run against the running API on localhost:8000
docker compose exec savings_api pytest -q

# or, to see logs
docker compose exec savings_api pytest -vv
```

### Environment variables the tests understand

- `TEST_BASE_URL` (default: `http://localhost:8000`)
- `TEST_DATABASE_URL` (optional, used for DB seeding when needed).
  If omitted, the tests will try sensible defaults:
    - Inside the compose network: `postgresql://savings:savings@savings_db:5432/savings`
    - On host: `postgresql://savings:savings@localhost:5432/savings`

## What the tests do (happy path)
1. Healthcheck.
2. Signup with a random email and login to get a JWT.
3. Setup a (simulated) payment method and authorization.
4. Seed a `provider` and `service` directly in Postgres (no admin HTTP endpoints required).
5. Upload a dummy image as bill to `/bills?service_id=...`.
6. Start a negotiation `/services/{service_id}/negotiate` (strategy `retention`) with rate-limit guard.
7. Confirm the negotiation via `/negotiations/{id}/confirm` by introspecting the OpenAPI schema to build a minimal valid body. If the schema cannot be parsed, the test will be *skipped* gracefully instead of failing spuriously.
8. Read `/dashboard/me` and assert the structure and numeric fields.

There are also tests for JWT protection and rate-limiting behavior.

## Notes
- The suite is written to be robust across small implementation differences. If your `confirm` endpoint requires specific fields, the test will infer them from OpenAPI. If it can’t, it will skip that part with a clear reason.
- If your rate-limit is very strict, the negotiation test uses unique provider accounts to avoid flapping.
