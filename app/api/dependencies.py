from app.infraestructure.repositories.transaction_repository import (
    PostgresTransactionRepository,
)
from app.use_cases.create_transaction import CreateTransactionUseCase


def get_create_transaction_use_case() -> CreateTransactionUseCase:
    repository = PostgresTransactionRepository()
    return CreateTransactionUseCase(repository)
