from pydantic import BaseModel
from app.domain.models import Customer


class BankAuthorizationRequest(BaseModel):
    transaction_id: str
    amount: float
    currency: str

    customer: Customer


class CustomerRequest(BaseModel):
    first_name: str
    last_name: str
    personal_id: str
    email: str
    country: str
    # ip: str


class ProviderCallbackRequest(BaseModel):
    transaction_id: str
    provider_transaction_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str


class CallbackResponse(BaseModel):
    transaction_id: str
    status: str
