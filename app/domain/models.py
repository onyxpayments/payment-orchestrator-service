from dataclasses import dataclass


@dataclass
class Transaction:
    transaction_id: str
    amount: float
    currency: str
    country: str
    status: str
