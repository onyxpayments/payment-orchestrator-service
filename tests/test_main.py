from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import (
    get_process_transaction_use_case,
    get_process_provider_callback_use_case,
)

client = TestClient(app)


class FakeProcessTransactionUseCase:
    def execute(self, request):
        return {
            "message": "Transaction processed",
            "transaction_id": "fake-uuid-123",
            "status": "APPROVED",
            "provider_transaction_id": "mock_trx_123",
        }


class FakeProcessProviderCallbackUseCase:
    def execute(self, transaction_id, callback):
        return {"message": "Callback received"}


def test_create_transaction_returns_approved():
    app.dependency_overrides[get_process_transaction_use_case] = (
        lambda: FakeProcessTransactionUseCase()
    )

    payload = {
        "transaction_id": "trx_123",
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
        "transaction_id": "fake-uuid-123",
        "status": "APPROVED",
        "provider_transaction_id": "mock_trx_123",
        "message": "Transaction processed",
    }

    app.dependency_overrides.clear()


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mock_bank_callback_returns_received():
    app.dependency_overrides[get_process_provider_callback_use_case] = (
        lambda: FakeProcessProviderCallbackUseCase()
    )

    transaction_id = "123e4567-e89b-12d3-a456-426614174000"

    payload = {
        "transaction_id": transaction_id,
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
        "message": "Callback received",
    }

    app.dependency_overrides.clear()


def test_mock_bank_callback_rejects_missing_required_field():
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

    assert response.status_code == 422
