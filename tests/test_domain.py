from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.models import (
    ConflictingFinalStatus,
    Customer,
    PaymentStatus,
    ProviderTransactionMismatch,
    Transaction,
)


def transaction_with_status(status: PaymentStatus) -> Transaction:
    transaction_id = uuid4()
    return Transaction(
        id=transaction_id,
        amount=Decimal("10000"),
        currency="COP",
        notification_url="https://merchant.example/webhooks/payments",
        status=status,
        customer=Customer(
            first_name="Juan",
            last_name="Bello",
            personal_id="123456789",
        ),
        provider_transaction_id=f"mock_{transaction_id}",
    )


def test_terminal_status_ignores_stale_pending_status():
    transaction = transaction_with_status(PaymentStatus.APPROVED)

    changed = transaction.apply_authorization(
        provider_transaction_id=transaction.provider_transaction_id,
        new_status=PaymentStatus.PENDING,
    )

    assert changed is False
    assert transaction.status == PaymentStatus.APPROVED


def test_duplicate_final_status_is_a_no_op():
    transaction = transaction_with_status(PaymentStatus.APPROVED)

    changed = transaction.apply_provider_callback(
        provider_transaction_id=transaction.provider_transaction_id,
        new_status=PaymentStatus.APPROVED,
    )

    assert changed is False


def test_conflicting_final_status_is_rejected():
    transaction = transaction_with_status(PaymentStatus.APPROVED)

    with pytest.raises(ConflictingFinalStatus):
        transaction.apply_provider_callback(
            provider_transaction_id=transaction.provider_transaction_id,
            new_status=PaymentStatus.DECLINED,
        )

    assert transaction.status == PaymentStatus.APPROVED


def test_provider_transaction_mismatch_is_rejected_without_mutation():
    transaction = transaction_with_status(PaymentStatus.PENDING)

    with pytest.raises(ProviderTransactionMismatch):
        transaction.apply_provider_callback(
            provider_transaction_id="different-provider-id",
            new_status=PaymentStatus.APPROVED,
        )

    assert transaction.status == PaymentStatus.PENDING
