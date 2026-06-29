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
        self.inbox = self
        self.saved = {}
        self.processed_events = set()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get(self, transaction_id):
        return self.saved.get(transaction_id)

    def get_for_update(self, transaction_id):
        return self.get(transaction_id)

    def update(self, transaction):
        self.saved[transaction.id] = transaction

    def contains(self, event_id):
        return event_id in self.processed_events

    def add(self, item=None, event_type=None, event_id=None):
        if event_id is not None:
            self.processed_events.add(event_id)
            return
        if isinstance(item, Transaction):
            self.saved[item.id] = item
            return
        self.processed_events.add(item)

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


class CallbackBeforePendingProvider:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def authorize(self, transaction, idempotency_key):
        stored = self.unit_of_work.saved[transaction.id]
        stored.apply_provider_callback(
            provider_transaction_id=f"mock_{transaction.id}",
            new_status=PaymentStatus.APPROVED,
        )
        return AuthorizationResult(
            provider_transaction_id=f"mock_{transaction.id}",
            status=PaymentStatus.PENDING,
        )


class RecordingNotificationPublisher:
    def __init__(self):
        self.events = []

    def publish_payment_notification(self, event):
        self.events.append(event)


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
            notification_url="https://merchant.example/webhooks/payments",
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


def test_process_payment_does_not_repeat_processed_event():
    unit_of_work = FakeUnitOfWork()
    provider = FakePaymentProvider()
    use_case = ProcessPaymentUseCase(unit_of_work, provider)
    event_id = uuid4()
    payment_id = uuid4()
    command = ProcessPaymentCommand(
        event_id=event_id,
        payment_id=payment_id,
        amount=Decimal("10000"),
        currency="COP",
        notification_url="https://merchant.example/webhooks/payments",
        customer=Customer(
            first_name="Juan",
            last_name="Bello",
            personal_id="123456789",
        ),
    )

    first_result = use_case.execute(command)
    second_result = use_case.execute(command)

    assert first_result == second_result
    assert len(provider.calls) == 1
    assert event_id in unit_of_work.processed_events


def test_process_payment_does_not_regress_after_early_callback():
    unit_of_work = FakeUnitOfWork()
    provider = CallbackBeforePendingProvider(unit_of_work)
    use_case = ProcessPaymentUseCase(unit_of_work, provider)
    payment_id = uuid4()

    result = use_case.execute(
        ProcessPaymentCommand(
            event_id=uuid4(),
            payment_id=payment_id,
            amount=Decimal("10000"),
            currency="COP",
            notification_url="https://merchant.example/webhooks/payments",
            customer=Customer(
                first_name="Juan",
                last_name="Bello",
                personal_id="123456789",
            ),
        )
    )

    assert result.status == PaymentStatus.APPROVED
    assert unit_of_work.saved[payment_id].status == PaymentStatus.APPROVED


def test_provider_callback_updates_pending_transaction():
    unit_of_work = FakeUnitOfWork()
    payment_id = uuid4()
    unit_of_work.saved[payment_id] = Transaction(
        id=payment_id,
        amount=Decimal("10000"),
        currency="COP",
        notification_url="https://merchant.example/webhooks/payments",
        customer=Customer(
            first_name="Juan",
            last_name="Bello",
            personal_id="123456789",
        ),
        status=PaymentStatus.PENDING,
        provider_transaction_id=f"mock_{payment_id}",
    )
    publisher = RecordingNotificationPublisher()
    use_case = ProcessProviderCallbackUseCase(unit_of_work, publisher)

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
    assert len(publisher.events) == 1
    assert publisher.events[0].notification_url == (
        "https://merchant.example/webhooks/payments"
    )
