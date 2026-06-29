# OnyxPay Payment Orchestrator Service

Transaction owner and payment coordination service for OnyxPay.

The service consumes `payment.requested` events, persists transactions in
PostgreSQL, calls the Mock Bank, receives asynchronous provider callbacks, and
publishes webhook delivery events to RabbitMQ.

## Responsibilities

- Consume and validate versioned payment request events.
- Persist the transaction and its required `notification_url`.
- Authorize new transactions with the Mock Bank.
- Handle immediate and out-of-order provider statuses safely.
- Receive and persist asynchronous Mock Bank callbacks.
- Publish `payment.notification_requested` events for the Webhook Service.
- Deduplicate redelivered payment requests through a PostgreSQL inbox.
- Retry transient consumer failures and dead-letter exhausted messages.

## End-to-end flow

```text
Payment Request Service
    │ payment.requested.v1
    ▼
RabbitMQ: orchestrator.payment-requested.q
    │
    ▼
Orchestrator Worker ───────────────► PostgreSQL
    │ POST /authorize
    ▼
Mock Bank
    │ PENDING response
    │ asynchronous callback
    ▼
Orchestrator API ──────────────────► PostgreSQL
    │ payment.notification.requested.v1
    ▼
RabbitMQ: webhook.payment-notifications.q
    │
    ▼
Webhook Service
```

The API and RabbitMQ worker run as separate processes from the same image.
Alembic migrations run as a third one-shot Compose service.

## HTTP API

With the full stack running, the API is available at
`http://localhost:8002`; the container listens on port `8001`.

### Create a transaction directly

This endpoint is useful for development. Normal platform traffic reaches the
same use case through RabbitMQ.

```http
POST /transactions
Content-Type: application/json
```

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount": "10000.50",
  "currency": "COP",
  "notification_url": "https://merchant.example/webhooks/payments",
  "customer": {
    "first_name": "Juan",
    "last_name": "Bello",
    "personal_id": "123456789"
  }
}
```

`notification_url` is required and must be a valid HTTP or HTTPS URL.
Currency values are normalized to uppercase.

Response:

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "provider_transaction_id": "mock_123e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING"
}
```

The client-provided transaction identifier remains the identifier used across
the platform.

### Receive a Mock Bank callback

```http
POST /provider-callbacks/mock-bank/{transaction_id}
Content-Type: application/json
```

```json
{
  "provider_transaction_id": "mock_123e4567-e89b-12d3-a456-426614174000",
  "status": "APPROVED",
  "message": "Mock bank payment approved asynchronously"
}
```

Response:

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "APPROVED"
}
```

After committing the status, the API publishes a persistent notification event
with publisher confirms enabled. Its deterministic event ID is derived from
the transaction ID and status, giving duplicate callbacks the same
idempotency key.

Interactive OpenAPI documentation is available at
`http://localhost:8002/docs`.

## RabbitMQ contracts

### Consumed event

| Property | Value |
| --- | --- |
| Exchange | `payment.events` |
| Routing key | `payment.requested.v1` |
| Queue | `orchestrator.payment-requested.q` |
| Event type | `payment.requested` |
| Schema version | `1` |

The event includes `event_id`, timestamps, correlation and payment IDs,
amount, currency, required `notification_url`, and customer identity.

The worker uses manual acknowledgements and `prefetch_count=1`. It acknowledges
only after processing succeeds and the database transaction commits.

### Published notification event

| Property | Value |
| --- | --- |
| Exchange | `payment.events` |
| Routing key | `payment.notification.requested.v1` |
| Queue | `webhook.payment-notifications.q` |
| Event type | `payment.notification_requested` |
| Schema version | `1` |

The event contains the destination URL, transaction and provider IDs, final
status, provider message, timestamp, correlation ID, and deterministic event
ID.

### Payment request retries

| Purpose | Exchange | Queue / routing key |
| --- | --- | --- |
| Retry | `payment.retry` | `orchestrator.payment-requested.retry.q` / `payment.requested.retry` |
| Dead letter | `payment.dead-letter` | `orchestrator.payment-requested.dlq` / `payment.requested.failed` |

Retry messages wait for `RABBITMQ_RETRY_DELAY_MS` and are attempted up to
`RABBITMQ_MAX_RETRIES`. Invalid messages go directly to the dead-letter queue.

## Persistence and migrations

The orchestrator owns the `transactions` and `processed_events` tables.
`notification_url` is non-nullable in the current schema.

Apply migrations before starting either process:

```bash
make migrate
```

Migration `20260628_0003` refuses to make the column non-nullable when legacy
transactions still have an empty or null URL. Clean those rows before
deployment.

Run the PostgreSQL repository integration test against a migrated database:

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/transactions_db \
  make test-integration
```

## Configuration

`DATABASE_URL`, `BANK_SERVICE_URL`, and `RABBITMQ_PASSWORD` are required.
Database and broker passwords are represented as Pydantic secret values so
they are masked in settings representations and logs.

Copy `.env.example` to `.env` for local development and replace every
`change-me` value. Never commit the resulting `.env` file.

| Variable | Default |
| --- | --- |
| `RABBITMQ_HOST` | `rabbitmq` |
| `RABBITMQ_PORT` | `5672` |
| `RABBITMQ_USER` | `guest` |
| `RABBITMQ_PASSWORD` | required secret |
| `RABBITMQ_VHOST` | `/` |
| `RABBITMQ_EXCHANGE` | `payment.events` |
| `RABBITMQ_PAYMENT_REQUESTED_QUEUE` | `orchestrator.payment-requested.q` |
| `RABBITMQ_PAYMENT_REQUESTED_ROUTING_KEY` | `payment.requested.v1` |
| `RABBITMQ_NOTIFICATION_QUEUE` | `webhook.payment-notifications.q` |
| `RABBITMQ_NOTIFICATION_ROUTING_KEY` | `payment.notification.requested.v1` |
| `RABBITMQ_RETRY_EXCHANGE` | `payment.retry` |
| `RABBITMQ_PAYMENT_REQUESTED_RETRY_QUEUE` | `orchestrator.payment-requested.retry.q` |
| `RABBITMQ_PAYMENT_REQUESTED_RETRY_ROUTING_KEY` | `payment.requested.retry` |
| `RABBITMQ_DEAD_LETTER_EXCHANGE` | `payment.dead-letter` |
| `RABBITMQ_PAYMENT_REQUESTED_DEAD_LETTER_QUEUE` | `orchestrator.payment-requested.dlq` |
| `RABBITMQ_PAYMENT_REQUESTED_DEAD_LETTER_ROUTING_KEY` | `payment.requested.failed` |
| `RABBITMQ_RETRY_DELAY_MS` | `5000` |
| `RABBITMQ_MAX_RETRIES` | `3` |
| `RABBITMQ_RECONNECT_DELAY_SECONDS` | `2` |

## Local development

Requirements: Python 3.13, PostgreSQL, RabbitMQ, and a reachable Mock Bank.

```bash
make install
make migrate
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Run the worker separately:

```bash
.venv/bin/python -m app.worker
```

Quality checks:

```bash
make format
make lint
make test
```

## Docker and Compose

```bash
make docker-build
```

The published image is:

```text
ghcr.io/onyxpayments/payment-orchestrator-service:latest
```

For the complete API, worker, migration, PostgreSQL, RabbitMQ, Mock Bank, and
Webhook Service setup, use:

```bash
cd ../infra
docker compose pull
docker compose up -d
```

## Health checks

- `GET /health/live`: API process liveness.
- `GET /health/startup`: application startup.
- `GET /health/ready`: PostgreSQL connectivity through `SELECT 1`.
- `GET /health`: backward-compatible basic health check.
- `python -m app.worker_health`: PostgreSQL and RabbitMQ worker readiness.

## Project structure

```text
.
├── app
│   ├── adapters/inbound
│   │   ├── http                 # API routes, schemas, and health checks
│   │   └── messaging            # PaymentRequested consumer
│   ├── application
│   │   ├── use_cases            # Payment and callback workflows
│   │   ├── commands.py
│   │   ├── events.py
│   │   ├── ports.py
│   │   └── results.py
│   ├── domain                   # Transaction aggregate and status rules
│   ├── infrastructure
│   │   ├── db                   # PostgreSQL connection and unit of work
│   │   ├── gateways             # Mock Bank adapter
│   │   ├── messaging            # RabbitMQ connection and publisher
│   │   └── repositories         # Transaction and inbox repositories
│   ├── main.py                  # FastAPI process
│   ├── worker.py                # RabbitMQ worker process
│   └── worker_health.py
├── config/settings.py
├── migrations
└── tests
```

## Current limitations

- Only the Mock Bank provider is integrated.
- Provider authorization calls are synchronous.
- Provider callbacks are not authenticated.
- Notification publishing is direct rather than transactional-outbox based.
