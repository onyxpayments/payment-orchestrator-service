from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ProviderCallbackRequest(BaseModel):
    transaction_id: str
    provider_transaction_id: str
    status: str
    message: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/provider-callbacks/mock-bank")
def receive_mock_bank_callback(request: ProviderCallbackRequest) -> dict[str, str]:
    return {
        "transaction_id": request.transaction_id,
        "status": "received",
    }
