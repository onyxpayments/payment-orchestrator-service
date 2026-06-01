from dataclasses import dataclass
from uuid import UUID
from enum import Enum


class PaymentStatus(str, Enum):
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
    # email: str
    # country: str
    # ip: str


@dataclass
class Transaction:
    id: UUID | None
    amount: float
    status: PaymentStatus
    customer: Customer

    tracking_id: str | None = None
    notification_url: str | None = None
