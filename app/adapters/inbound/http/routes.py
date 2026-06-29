from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, status

from app.adapters.inbound.http import schemas
from app.bootstrap import (
    get_process_payment_use_case,
    get_process_provider_callback_use_case,
)
from app.application.commands import (
    ProcessPaymentCommand,
    ProcessProviderCallbackCommand,
)
from app.application.use_cases.process_payment import ProcessPaymentUseCase
from app.application.use_cases.process_provider_callback import (
    ProcessProviderCallbackUseCase,
)
from app.domain.models import Customer

router = APIRouter()


@router.post(
    "/transactions",
    response_model=schemas.TransactionResponse,
    status_code=status.HTTP_200_OK,
)
def create_transaction(
    request: schemas.BankAuthorizationRequest,
    use_case: ProcessPaymentUseCase = Depends(get_process_payment_use_case),
):
    command = ProcessPaymentCommand(
        event_id=uuid4(),
        payment_id=request.transaction_id,
        amount=request.amount,
        currency=request.currency,
        notification_url=str(request.notification_url),
        customer=Customer(
            first_name=request.customer.first_name,
            last_name=request.customer.last_name,
            personal_id=request.customer.personal_id,
        ),
    )

    result = use_case.execute(command)

    return schemas.TransactionResponse(
        transaction_id=result.transaction_id,
        provider_transaction_id=result.provider_transaction_id,
        status=result.status.value,
    )


@router.post(
    "/provider-callbacks/mock-bank/{transaction_id}",
    response_model=schemas.CallbackResponse,
)
def receive_mock_bank_callback(
    transaction_id: UUID,
    callback: schemas.ProviderCallbackRequest,
    use_case: ProcessProviderCallbackUseCase = Depends(
        get_process_provider_callback_use_case
    ),
):
    command = ProcessProviderCallbackCommand(
        transaction_id=transaction_id,
        provider_transaction_id=callback.provider_transaction_id,
        status=callback.status,
        message=callback.message,
    )

    result = use_case.execute(command)

    return schemas.CallbackResponse(
        transaction_id=result.transaction_id,
        status=result.status.value,
    )
