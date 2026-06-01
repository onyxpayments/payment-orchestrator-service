from fastapi import APIRouter, Depends
from pydantic import BaseModel
import httpx
from . import schemas
from app.infraestructure.repositories.transaction_repository import (
    PostgresTransactionRepository,
)
from app.api.dependencies import get_create_transaction_use_case
from app.use_cases.create_transaction import CreateTransactionUseCase

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/provider-callbacks/mock-bank")
def receive_mock_bank_callback(
    request: schemas.ProviderCallbackRequest,
) -> dict[str, str]:
    return {
        "transaction_id": request.transaction_id,
        "status": "received",
    }


@router.post("/process-payment-test")
def process_payment_test(request: schemas.BankAuthorizationRequest) -> dict:
    payload = request.model_dump()

    response = httpx.post(
        "http://mock-bank-service:8000/authorize",
        json=payload,
        timeout=5,
    )
    response.raise_for_status()

    return response.json()


@router.post("/transactions")
def create_transaction(
    request: schemas.BankAuthorizationRequest,
    use_case: CreateTransactionUseCase = Depends(get_create_transaction_use_case),
):
    return use_case.execute(request)
