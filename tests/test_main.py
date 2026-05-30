from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
