from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.models import Customer


@dataclass(frozen=True)
class ProcessPaymentCommand:
    event_id: UUID
    payment_id: UUID
    amount: Decimal
    currency: str
    customer: Customer


@dataclass(frozen=True)
class ProcessProviderCallbackCommand:
    transaction_id: UUID
    provider_transaction_id: str
    status: str
    message: str | None = None
