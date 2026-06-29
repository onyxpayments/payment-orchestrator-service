from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.application.commands import ProcessPaymentCommand
from app.domain.models import Customer


class MessageSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentRequestedCustomer(MessageSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    personal_id: str = Field(min_length=1, max_length=50)


class PaymentRequestedMessage(MessageSchema):
    event_id: UUID
    event_type: Literal["payment.requested"]
    schema_version: Literal[1]
    occurred_at: datetime
    correlation_id: UUID
    payment_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    notification_url: HttpUrl
    customer: PaymentRequestedCustomer

    @model_validator(mode="after")
    def correlation_matches_payment(self) -> "PaymentRequestedMessage":
        if self.correlation_id != self.payment_id:
            raise ValueError("correlation_id must match payment_id")
        return self

    def to_command(self) -> ProcessPaymentCommand:
        return ProcessPaymentCommand(
            event_id=self.event_id,
            payment_id=self.payment_id,
            amount=self.amount,
            currency=self.currency,
            notification_url=str(self.notification_url),
            customer=Customer(
                first_name=self.customer.first_name,
                last_name=self.customer.last_name,
                personal_id=self.customer.personal_id,
            ),
        )
