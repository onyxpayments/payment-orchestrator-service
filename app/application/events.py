from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.models import PaymentStatus, Transaction


@dataclass(frozen=True)
class PaymentNotificationRequested:
    event_id: UUID
    occurred_at: datetime
    transaction_id: UUID
    provider_transaction_id: str
    status: PaymentStatus
    message: str | None
    notification_url: str
    event_type: str = "payment.notification_requested"
    schema_version: int = 1

    @classmethod
    def from_transaction(
        cls,
        transaction: Transaction,
        message: str | None,
    ) -> "PaymentNotificationRequested":
        if transaction.provider_transaction_id is None:
            raise ValueError("Provider transaction ID is required for notification")
        return cls(
            event_id=uuid5(
                NAMESPACE_URL,
                f"onyxpay:{transaction.id}:{transaction.status.value}",
            ),
            occurred_at=datetime.now(timezone.utc),
            transaction_id=transaction.id,
            provider_transaction_id=transaction.provider_transaction_id,
            status=transaction.status,
            message=message,
            notification_url=transaction.notification_url,
        )

    def to_dict(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.transaction_id),
            "transaction_id": str(self.transaction_id),
            "provider_transaction_id": self.provider_transaction_id,
            "status": self.status.value,
            "message": self.message,
            "notification_url": self.notification_url,
        }
