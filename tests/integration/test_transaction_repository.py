import os
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from app.domain.models import Customer, PaymentStatus, Transaction
from app.infrastructure.repositories.transaction_repository import (
    PostgresTransactionRepository,
)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


def test_transaction_round_trip_preserves_the_aggregate():
    transaction = Transaction.create(
        transaction_id=uuid4(),
        amount=Decimal("12345.67"),
        currency="COP",
        customer=Customer(
            first_name="Integration",
            last_name="Test",
            personal_id=f"test-{uuid4()}",
        ),
    )

    with psycopg.connect(
        TEST_DATABASE_URL,
        row_factory=dict_row,
    ) as connection:
        repository = PostgresTransactionRepository(connection)

        repository.add(transaction)
        loaded = repository.get(transaction.id)

        assert loaded == transaction

        loaded.apply_authorization(
            provider_transaction_id=f"mock_{transaction.id}",
            new_status=PaymentStatus.PENDING,
        )
        repository.update(loaded)

        assert repository.get_for_update(transaction.id) == loaded

        connection.rollback()
