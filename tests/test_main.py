from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_process_transaction_use_case

client = TestClient(app)


class FakeProcessTransactionUseCase:
    def execute(self, request):
        return {
            "transaction_id": "fake-uuid-123",
            "status": "APPROVED",
            "provider_transaction_id": "mock_trx_123",
        }


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
    }

    app.dependency_overrides.clear()


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mock_bank_callback_returns_received():
    payload = {
        "transaction_id": "trx_123",
        "provider_transaction_id": "mock_trx_123",
        "status": "APPROVED",
        "message": "Payment approved by mock bank",
    }

    response = client.post("/provider-callbacks/mock-bank", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "transaction_id": "trx_123",
        "status": "received",
    }


def test_mock_bank_callback_rejects_missing_required_field():
    payload = {
        "transaction_id": "trx_123",
        "status": "APPROVED",
        "message": "Payment approved by mock bank",
    }

    response = client.post("/provider-callbacks/mock-bank", json=payload)

    assert response.status_code == 422
