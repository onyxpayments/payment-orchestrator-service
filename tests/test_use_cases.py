from decimal import Decimal
from uuid import uuid4

from app.application.commands import (
    ProcessPaymentCommand,
    ProcessProviderCallbackCommand,
)
from app.application.ports import AuthorizationResult
from app.application.use_cases.process_payment import ProcessPaymentUseCase
from app.application.use_cases.process_provider_callback import (
    ProcessProviderCallbackUseCase,
)
from app.domain.models import Customer, PaymentStatus, Transaction


class FakeUnitOfWork:
    def __init__(self):
        self.transactions = self
        self.saved = {}
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get(self, transaction_id):
        return self.saved.get(transaction_id)

    def add(self, transaction):
        self.saved[transaction.id] = transaction

    def update(self, transaction):
        self.saved[transaction.id] = transaction

    def commit(self):
        self.commits += 1


class FakePaymentProvider:
    def __init__(self):
        self.calls = []

    def authorize(self, transaction, idempotency_key):
        self.calls.append((transaction, idempotency_key))
        return AuthorizationResult(
            provider_transaction_id=f"mock_{transaction.id}",
            status=PaymentStatus.PENDING,
        )


def test_process_payment_creates_and_authorizes_transaction():
    unit_of_work = FakeUnitOfWork()
    provider = FakePaymentProvider()
    use_case = ProcessPaymentUseCase(unit_of_work, provider)
    payment_id = uuid4()

    result = use_case.execute(
        ProcessPaymentCommand(
            event_id=uuid4(),
            payment_id=payment_id,
            amount=Decimal("10000"),
            currency="COP",
            customer=Customer(
                first_name="Juan",
                last_name="Bello",
                personal_id="123456789",
            ),
        )
    )

    assert result.transaction_id == payment_id
    assert result.status == PaymentStatus.PENDING
    assert result.provider_transaction_id == f"mock_{payment_id}"
    assert provider.calls[0][1] == str(payment_id)
    assert unit_of_work.commits == 2


def test_provider_callback_updates_pending_transaction():
    unit_of_work = FakeUnitOfWork()
    payment_id = uuid4()
    unit_of_work.saved[payment_id] = Transaction(
        id=payment_id,
        amount=Decimal("10000"),
        currency="COP",
        customer=Customer(
            first_name="Juan",
            last_name="Bello",
            personal_id="123456789",
        ),
        status=PaymentStatus.PENDING,
        provider_transaction_id=f"mock_{payment_id}",
    )
    use_case = ProcessProviderCallbackUseCase(unit_of_work)

    result = use_case.execute(
        ProcessProviderCallbackCommand(
            transaction_id=payment_id,
            provider_transaction_id=f"mock_{payment_id}",
            status="APPROVED",
            message="Approved",
        )
    )

    assert result.status == PaymentStatus.APPROVED
    assert unit_of_work.saved[payment_id].status == PaymentStatus.APPROVED
    assert unit_of_work.commits == 1
