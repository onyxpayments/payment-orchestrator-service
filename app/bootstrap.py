from app.application.use_cases.process_payment import ProcessPaymentUseCase
from app.application.use_cases.process_provider_callback import (
    ProcessProviderCallbackUseCase,
)
from app.infrastructure.db.unit_of_work import PostgresUnitOfWork
from app.infrastructure.gateways.mock_bank_gateway import MockBankGateway


def get_process_payment_use_case() -> ProcessPaymentUseCase:
    return ProcessPaymentUseCase(
        unit_of_work=PostgresUnitOfWork(),
        payment_provider=MockBankGateway(),
    )


def get_process_provider_callback_use_case() -> ProcessProviderCallbackUseCase:
    return ProcessProviderCallbackUseCase(
        unit_of_work=PostgresUnitOfWork(),
    )
