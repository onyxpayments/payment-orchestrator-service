from app.infraestructure.repositories.transaction_repository import (
    PostgresTransactionRepository,
)
from app.application.use_cases.create_transaction import ProcessTransactionUseCase
from app.application.use_cases.receive_callback import ProcessProviderCallbackUseCase
from app.infraestructure.gateways.mock_bank_gateway import MockBankGateway


def get_process_transaction_use_case() -> ProcessTransactionUseCase:
    repository = PostgresTransactionRepository()
    return ProcessTransactionUseCase(repository, MockBankGateway())


def get_process_provider_callback_use_case() -> ProcessProviderCallbackUseCase:
    repository = PostgresTransactionRepository()
    return ProcessProviderCallbackUseCase(repository)
