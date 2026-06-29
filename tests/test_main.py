from fastapi.testclient import TestClient
from unittest.mock import patch

from app.application.results import (
    ProcessPaymentResult,
    ProcessProviderCallbackResult,
)
from app.bootstrap import (
    get_process_payment_use_case,
    get_process_provider_callback_use_case,
)
from app.domain.models import PaymentStatus
from app.main import app

client = TestClient(app)


class FakeProcessPaymentUseCase:
    def execute(self, command):
        return ProcessPaymentResult(
            transaction_id=command.payment_id,
            status=PaymentStatus.APPROVED,
            provider_transaction_id=f"mock_{command.payment_id}",
        )


class FakeProcessProviderCallbackUseCase:
    def execute(self, command):
        return ProcessProviderCallbackResult(
            transaction_id=command.transaction_id,
            status=PaymentStatus(command.status),
        )


def test_create_transaction_returns_approved():
    app.dependency_overrides[get_process_payment_use_case] = (
        lambda: FakeProcessPaymentUseCase()
    )

    transaction_id = "123e4567-e89b-12d3-a456-426614174000"
    payload = {
        "transaction_id": transaction_id,
        "amount": 10000,
        "currency": "COP",
        "customer": {
            "first_name": "Juan",
            "last_name": "Bello",
            "personal_id": "123456789",
        },
    }

    response = client.post("/transactions", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "transaction_id": transaction_id,
        "status": "APPROVED",
        "provider_transaction_id": f"mock_{transaction_id}",
    }

    app.dependency_overrides.clear()


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_returns_alive():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_startup_returns_started():
    response = client.get("/health/startup")

    assert response.status_code == 200
    assert response.json() == {"status": "started"}


@patch(
    "adapters.inbound.http.health.database_is_ready",
    return_value=True,
)
def test_readiness_returns_ready_when_database_is_ready(_mock_ready):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "up"},
    }


@patch(
    "adapters.inbound.http.health.database_is_ready",
    return_value=False,
)
def test_readiness_returns_503_when_database_is_unavailable(_mock_ready):
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "down"},
    }


def test_mock_bank_callback_returns_received():
    app.dependency_overrides[get_process_provider_callback_use_case] = (
        lambda: FakeProcessProviderCallbackUseCase()
    )

    transaction_id = "123e4567-e89b-12d3-a456-426614174000"

    payload = {
        "provider_transaction_id": f"mock_{transaction_id}",
        "status": "APPROVED",
        "message": "Payment approved by mock bank",
    }

    response = client.post(
        f"/provider-callbacks/mock-bank/{transaction_id}",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "transaction_id": transaction_id,
        "status": "APPROVED",
    }

    app.dependency_overrides.clear()


def test_mock_bank_callback_rejects_missing_required_field():
    transaction_id = "123e4567-e89b-12d3-a456-426614174000"
    payload = {
        "status": "APPROVED",
        "message": "Payment approved by mock bank",
    }

    response = client.post(
        f"/provider-callbacks/mock-bank/{transaction_id}",
        json=payload,
    )

    assert response.status_code == 422
