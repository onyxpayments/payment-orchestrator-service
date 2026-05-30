from pydantic import BaseModel


class PaymentRequest(BaseModel):
    tracking_id: str
    amount: float
    currency: str
    country: str


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

class BankAuthorizationRequest(BaseModel):
    transaction_id: str
    amount: float
    currency: str

    customer_name: str
    customer_document: str