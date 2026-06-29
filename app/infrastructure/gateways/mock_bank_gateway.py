import logging

import httpx

from app.application.ports import AuthorizationResult
from app.domain.models import PaymentStatus, Transaction
from config.settings import settings

logger = logging.getLogger(__name__)


class MockBankGateway:
    def authorize(
        self,
        transaction: Transaction,
        idempotency_key: str,
    ) -> AuthorizationResult:
        payload = {
            "transaction_id": str(transaction.id),
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "notification_url": transaction.notification_url,
            "customer": {
                "first_name": transaction.customer.first_name,
                "last_name": transaction.customer.last_name,
                "personal_id": transaction.customer.personal_id,
            },
        }

        response = httpx.post(
            f"{settings.bank_service_url}/authorize",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
            timeout=5,
        )

        response.raise_for_status()
        body = response.json()

        logger.info("Mock bank response: %s", body)

        return AuthorizationResult(
            provider_transaction_id=body["provider_transaction_id"],
            status=PaymentStatus(body["status"]),
        )
