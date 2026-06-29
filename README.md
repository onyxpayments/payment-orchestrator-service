# OnyxPay Payment Orchestrator

Core transaction coordination service for the OnyxPay payment platform.

The orchestrator owns transaction persistence and coordinates communication
with payment providers. In the current development flow, it stores a pending
transaction in PostgreSQL, requests authorization from the Mock Bank, and
updates the transaction again when the provider sends an asynchronous callback.

## Responsibilities

- Create and persist payment transactions.
- Generate the platform transaction identifier.
- Send authorization requests to the configured bank provider.
- Store the provider's immediate payment status.
- Receive asynchronous provider callbacks.
- Update the final transaction status.
- Keep HTTP, application, domain, and infrastructure concerns separated.

## Payment Flow

```text
API Gateway
    │
    │ POST /transactions
    ▼
Payment Orchestrator ──────► PostgreSQL
    │
    │ POST /authorize
    ▼
Mock Bank
    │
    │ PENDING immediately
    │ APPROVED callback after 5 seconds
    ▼
Payment Orchestrator ──────► PostgreSQL
```

## API

When the full platform is running through Docker Compose, the orchestrator is
available at `http://localhost:8002`.

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Create Transaction

```http
POST /transactions
Content-Type: application/json
```

Request:

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount": 10000,
  "currency": "COP",
  "customer": {
    "first_name": "Juan",
    "last_name": "Bello",
    "personal_id": "123456789"
  }
}
```

Example:

```bash
curl -X POST http://localhost:8002/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": 10000,
    "currency": "COP",
    "customer": {
      "first_name": "Juan",
      "last_name": "Bello",
      "personal_id": "123456789"
    }
  }'
```

Immediate response:

```json
{
  "transaction_id": "9d03c06f-66b6-4495-82a7-e2fa41d740e4",
  "provider_transaction_id": "mock_9d03c06f-66b6-4495-82a7-e2fa41d740e4",
  "status": "PENDING"
}
```

The service creates a PostgreSQL UUID and uses it for all provider
communication. The request's `transaction_id` field is currently replaced by
the persisted identifier.

### Receive Mock Bank Callback

```http
POST /provider-callbacks/mock-bank/{transaction_id}
Content-Type: application/json
```

Request:

```json
{
  "transaction_id": "9d03c06f-66b6-4495-82a7-e2fa41d740e4",
  "provider_transaction_id": "mock_9d03c06f-66b6-4495-82a7-e2fa41d740e4",
  "status": "APPROVED",
  "message": "Mock bank payment approved asynchronously"
}
```

Response:

```json
{
  "message": "Callback received"
}
```

### Provider Connectivity Test

`POST /process-payment-test` forwards the supplied authorization payload
directly to the Mock Bank. It is a development-only endpoint and does not
persist a transaction.

Interactive API documentation:

```text
http://localhost:8002/docs
```

## Configuration

The service requires the following environment variables:

| Variable | Description | Compose example |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@orchestrator-db:5432/orchestrator_db` |
| `BANK_SERVICE_URL` | Payment provider base URL | `http://mock-bank-service:8000` |

For local development, create a `.env` file:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/orchestrator_db
BANK_SERVICE_URL=http://localhost:8001
```

The infrastructure repository bootstraps PostgreSQL for local development.
Alembic migrations in this service are the source of truth for schema changes.

## Database migrations

The orchestrator owns its PostgreSQL schema through Alembic. Apply pending
migrations before starting a new application version:

```bash
make migrate
```

The first migration adopts databases created by the legacy infrastructure SQL
script and also supports an empty database. Existing rows without a currency
are migrated to `COP`, because the previous schema did not persist that value.

Run the repository round-trip integration test against a migrated test
database:

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/orchestrator_db \
  make test-integration
```

## Running the Full Platform

```bash
cd ../infra
docker compose pull
docker compose up -d
```

## Local Development

Requirements:

- Python 3.13
- PostgreSQL with the OnyxPay transaction schema
- A reachable bank provider
- Make

Install dependencies:

```bash
make install
```

Run the service:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Run quality checks:

```bash
make format
make lint
make test
```

## Docker

Build the image:

```bash
make docker-build
```

Run it inside a network that can resolve PostgreSQL and the Mock Bank:

```bash
docker run --rm -p 8002:8001 \
  -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5433/orchestrator_db" \
  -e BANK_SERVICE_URL="http://host.docker.internal:8001" \
  payment-orchestrator-service
```

Published image:

```text
ghcr.io/onyxpayments/payment-orchestrator-service:latest
```

## Architecture

```text
.
├── app
│   ├── api
│   │   ├── dependencies.py          # Dependency wiring
│   │   ├── routes.py                # HTTP endpoints
│   │   └── schemas.py               # Request and response schemas
│   ├── domain
│   │   ├── models.py                # Transaction and payment status models
│   │   └── ports.py                 # Domain port placeholder
│   ├── use_cases
│   │   ├── create_transaction.py    # Transaction authorization flow
│   │   └── receive_callback.py      # Provider callback flow
│   ├── infraestructure
│   │   ├── db                       # PostgreSQL connection
│   │   ├── gateways                 # Mock Bank adapter
│   │   └── repositories             # PostgreSQL transaction repository
│   └── main.py
├── config                            # Environment-based settings
└── tests
```

## Payment Statuses

The domain currently supports:

- `PENDING`
- `APPROVED`
- `DECLINED`
- `ERROR`
- `EXPIRED`

The database schema additionally defines `NEW`.

## CI/CD

GitHub Actions installs dependencies, checks formatting, runs tests, builds the
Docker image, and publishes the following tags on pushes to `main`:

```text
ghcr.io/onyxpayments/payment-orchestrator-service:latest
ghcr.io/onyxpayments/payment-orchestrator-service:<commit-sha>
```

## Current Limitations

- Only the Mock Bank provider is integrated.
- Provider requests are synchronous; only the final callback is asynchronous.
- The RabbitMQ adapter is not implemented yet.
- Callback authentication, idempotency, and retry handling are not implemented.

## Health probes

- `GET /health/live` checks that the API process can respond.
- `GET /health/startup` confirms application startup completed.
- `GET /health/ready` runs `SELECT 1` against PostgreSQL.
- `GET /health` remains available for backward compatibility.
