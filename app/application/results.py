from dataclasses import dataclass
from uuid import UUID

from app.domain.models import PaymentStatus


@dataclass(frozen=True)
class ProcessPaymentResult:
    transaction_id: UUID
    provider_transaction_id: str | None
    status: PaymentStatus


@dataclass(frozen=True)
class ProcessProviderCallbackResult:
    transaction_id: UUID
    status: PaymentStatus
