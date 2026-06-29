from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID


class InvalidStatusTransition(ValueError):
    pass


class PaymentStatus(str, Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


@dataclass
class Customer:
    first_name: str
    last_name: str
    personal_id: str


@dataclass
class Transaction:
    id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    customer: Customer
    provider_transaction_id: str | None = None

    @classmethod
    def create(
        cls,
        transaction_id: UUID,
        amount: Decimal,
        currency: str,
        customer: Customer,
    ) -> "Transaction":
        return cls(
            id=transaction_id,
            amount=amount,
            currency=currency,
            customer=customer,
            status=PaymentStatus.NEW,
        )

    def requires_authorization(self) -> bool:
        return self.status == PaymentStatus.NEW

    def apply_authorization(
        self,
        provider_transaction_id: str,
        new_status: PaymentStatus,
    ) -> bool:
        self.provider_transaction_id = provider_transaction_id
        return self._transition_to(new_status)

    def apply_provider_callback(
        self,
        provider_transaction_id: str,
        new_status: PaymentStatus,
    ) -> bool:
        if (
            self.provider_transaction_id is not None
            and self.provider_transaction_id != provider_transaction_id
        ):
            raise ValueError("Provider transaction ID does not match")

        self.provider_transaction_id = provider_transaction_id
        return self._transition_to(new_status)

    def _transition_to(self, new_status: PaymentStatus) -> bool:
        if self.status == new_status:
            return False

        allowed_transitions = {
            PaymentStatus.NEW: {
                PaymentStatus.PENDING,
                PaymentStatus.APPROVED,
                PaymentStatus.DECLINED,
                PaymentStatus.ERROR,
            },
            PaymentStatus.PENDING: {
                PaymentStatus.APPROVED,
                PaymentStatus.DECLINED,
                PaymentStatus.ERROR,
                PaymentStatus.EXPIRED,
            },
        }

        if new_status not in allowed_transitions.get(self.status, set()):
            raise InvalidStatusTransition(
                f"Cannot transition payment from {self.status} to {new_status}"
            )

        self.status = new_status
        return True
