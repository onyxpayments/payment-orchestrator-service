from fastapi import APIRouter, Depends
import httpx
from . import schemas
from app.api.dependencies import (
    get_process_transaction_use_case,
    get_process_provider_callback_use_case,
)
from app.use_cases.create_transaction import ProcessTransactionUseCase
from app.use_cases.receive_callback import ProcessProviderCallbackUseCase
from uuid import UUID

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/provider-callbacks/mock-bank/{transaction_id}")
def receive_mock_bank_callback(
    transaction_id: UUID,
    callback: schemas.ProviderCallbackRequest,
    use_case: ProcessProviderCallbackUseCase = Depends(
        get_process_provider_callback_use_case
    ),
):
    return use_case.execute(transaction_id, callback)


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
    use_case: ProcessTransactionUseCase = Depends(get_process_transaction_use_case),
):
    return use_case.execute(request)
