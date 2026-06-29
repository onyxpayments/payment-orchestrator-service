from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID


class InvalidStatusTransition(ValueError):
    pass


class ConflictingFinalStatus(InvalidStatusTransition):
    pass


class ProviderTransactionMismatch(ValueError):
    pass


class PaymentStatus(str, Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


TERMINAL_STATUSES = frozenset(
    {
        PaymentStatus.APPROVED,
        PaymentStatus.DECLINED,
        PaymentStatus.ERROR,
        PaymentStatus.EXPIRED,
    }
)


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
        self._validate_provider_transaction_id(provider_transaction_id)
        status_changed = self._transition_to(new_status)
        provider_id = provider_transaction_id
        provider_changed = self._set_provider_transaction_id(provider_id)
        return provider_changed or status_changed

    def apply_provider_callback(
        self,
        provider_transaction_id: str,
        new_status: PaymentStatus,
    ) -> bool:
        self._validate_provider_transaction_id(provider_transaction_id)
        status_changed = self._transition_to(new_status)
        provider_id = provider_transaction_id
        provider_changed = self._set_provider_transaction_id(provider_id)
        return provider_changed or status_changed

    def _validate_provider_transaction_id(
        self,
        provider_transaction_id: str,
    ) -> None:
        if (
            self.provider_transaction_id is not None
            and self.provider_transaction_id != provider_transaction_id
        ):
            message = "Provider transaction ID does not match"
            raise ProviderTransactionMismatch(message)

    def _set_provider_transaction_id(
        self,
        provider_transaction_id: str,
    ) -> bool:
        if self.provider_transaction_id == provider_transaction_id:
            return False

        self.provider_transaction_id = provider_transaction_id
        return True

    def _transition_to(self, new_status: PaymentStatus) -> bool:
        if self.status == new_status:
            return False

        if self.status in TERMINAL_STATUSES:
            if new_status in {PaymentStatus.NEW, PaymentStatus.PENDING}:
                return False

            raise ConflictingFinalStatus(
                f"Conflicting final statuses: {self.status} and {new_status}"
            )

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
