from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.models import PaymentStatus, Transaction


@dataclass(frozen=True)
class AuthorizationResult:
    provider_transaction_id: str
    status: PaymentStatus


class TransactionRepository(Protocol):
    def get(self, transaction_id: UUID) -> Transaction | None: ...

    def get_for_update(
        self,
        transaction_id: UUID,
    ) -> Transaction | None: ...

    def add(self, transaction: Transaction) -> None: ...

    def update(self, transaction: Transaction) -> None: ...


class UnitOfWork(Protocol):
    transactions: TransactionRepository

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, exc_type, exc_value, traceback) -> None: ...

    def commit(self) -> None: ...


class PaymentProvider(Protocol):
    def authorize(
        self,
        transaction: Transaction,
        idempotency_key: str,
    ) -> AuthorizationResult: ...
