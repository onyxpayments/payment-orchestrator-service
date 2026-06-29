from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerRequest(ApiSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    personal_id: str = Field(min_length=1, max_length=50)


class BankAuthorizationRequest(ApiSchema):
    transaction_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    customer: CustomerRequest

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ProviderCallbackRequest(ApiSchema):
    provider_transaction_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    message: str | None = None


class TransactionResponse(ApiSchema):
    transaction_id: UUID
    provider_transaction_id: str | None = None
    status: str


class CallbackResponse(ApiSchema):
    transaction_id: UUID
    status: str


class HealthResponse(ApiSchema):
    status: str
