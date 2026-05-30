from fastapi import APIRouter
from pydantic import BaseModel
import httpx

router = APIRouter()


class ProviderCallbackRequest(BaseModel):
    transaction_id: str
    provider_transaction_id: str
    status: str
    message: str


class PaymentRequest(BaseModel):
    transaction_id: str
    amount: float
    currency: str
    country: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/provider-callbacks/mock-bank")
def receive_mock_bank_callback(request: ProviderCallbackRequest) -> dict[str, str]:
    return {
        "transaction_id": request.transaction_id,
        "status": "received",
    }


@router.post("/process-payment-test")
def process_payment_test(request: PaymentRequest) -> dict:
    payload = request.model_dump()

    response = httpx.post(
        "http://mock-bank-service:8000/authorize",
        json=payload,
        timeout=5,
    )
    response.raise_for_status()

    return response.json()
