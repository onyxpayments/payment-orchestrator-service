from app.infraestructure.repositories.transaction_repository import (
    PostgresTransactionRepository,
)
from app.use_cases.create_transaction import ProcessTransactionUseCase
from app.infraestructure.gateways.mock_bank_gateway import MockBankGateway


def get_process_transaction_use_case() -> ProcessTransactionUseCase:
    repository = PostgresTransactionRepository()
    return ProcessTransactionUseCase(repository, MockBankGateway())
