import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pika

from app.adapters.inbound.messaging.payment_requested_consumer import (
    PaymentRequestedConsumer,
)
from config.settings import Settings


class RecordingUseCase:
    def __init__(self, error=None):
        self.commands = []
        self.error = error

    def execute(self, command):
        self.commands.append(command)
        if self.error is not None:
            raise self.error


def create_settings(**overrides):
    values = {
        "database_url": "postgresql://test",
        "bank_service_url": "http://bank",
        "rabbitmq_max_retries": 3,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def create_body():
    payment_id = uuid4()
    event_id = uuid4()
    return (
        json.dumps(
            {
                "event_id": str(event_id),
                "event_type": "payment.requested",
                "schema_version": 1,
                "occurred_at": "2026-06-28T12:00:00Z",
                "correlation_id": str(payment_id),
                "payment_id": str(payment_id),
                "amount": "10000.00",
                "currency": "COP",
                "customer": {
                    "first_name": "Juan",
                    "last_name": "Bello",
                    "personal_id": "123456789",
                },
            }
        ).encode(),
        event_id,
        payment_id,
    )


def create_delivery(headers=None):
    channel = Mock()
    channel.basic_publish.return_value = True
    method = SimpleNamespace(delivery_tag=7)
    properties = pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,
        message_id=str(uuid4()),
        headers=headers or {},
    )
    return channel, method, properties


def test_valid_message_executes_use_case_before_ack():
    body, event_id, payment_id = create_body()
    channel, method, properties = create_delivery()
    use_case = RecordingUseCase()
    consumer = PaymentRequestedConsumer(
        create_settings(),
        use_case_factory=lambda: use_case,
    )

    consumer.handle_message(channel, method, properties, body)

    assert len(use_case.commands) == 1
    assert use_case.commands[0].event_id == event_id
    assert use_case.commands[0].payment_id == payment_id
    channel.basic_ack.assert_called_once_with(delivery_tag=7)
    channel.basic_nack.assert_not_called()


def test_invalid_message_is_moved_to_dead_letter_queue():
    channel, method, properties = create_delivery()
    use_case = RecordingUseCase()
    consumer = PaymentRequestedConsumer(
        create_settings(),
        use_case_factory=lambda: use_case,
    )

    consumer.handle_message(channel, method, properties, b"not-json")

    assert use_case.commands == []
    publish = channel.basic_publish.call_args.kwargs
    assert publish["exchange"] == "payment.dead-letter"
    assert publish["routing_key"] == "payment.requested.failed"
    channel.basic_ack.assert_called_once_with(delivery_tag=7)


def test_processing_failure_is_scheduled_for_retry():
    body, _event_id, _payment_id = create_body()
    channel, method, properties = create_delivery()
    use_case = RecordingUseCase(error=RuntimeError("database unavailable"))
    consumer = PaymentRequestedConsumer(
        create_settings(),
        use_case_factory=lambda: use_case,
    )

    consumer.handle_message(channel, method, properties, body)

    publish = channel.basic_publish.call_args.kwargs
    assert publish["exchange"] == "payment.retry"
    assert publish["properties"].headers["x-retry-count"] == 1
    channel.basic_ack.assert_called_once_with(delivery_tag=7)


def test_none_publish_confirmation_is_successful():
    body, _event_id, _payment_id = create_body()
    channel, method, properties = create_delivery()
    channel.basic_publish.return_value = None
    use_case = RecordingUseCase(error=RuntimeError("database unavailable"))
    consumer = PaymentRequestedConsumer(
        create_settings(),
        use_case_factory=lambda: use_case,
    )

    consumer.handle_message(channel, method, properties, body)

    channel.basic_ack.assert_called_once_with(delivery_tag=7)
    channel.basic_nack.assert_not_called()


def test_exhausted_message_is_moved_to_dead_letter_queue():
    body, _event_id, _payment_id = create_body()
    channel, method, properties = create_delivery(headers={"x-retry-count": 3})
    use_case = RecordingUseCase(error=RuntimeError("database unavailable"))
    consumer = PaymentRequestedConsumer(
        create_settings(rabbitmq_max_retries=3),
        use_case_factory=lambda: use_case,
    )

    consumer.handle_message(channel, method, properties, body)

    publish = channel.basic_publish.call_args.kwargs
    assert publish["exchange"] == "payment.dead-letter"
    assert publish["properties"].headers["x-failure-reason"] == "RuntimeError"
    channel.basic_ack.assert_called_once_with(delivery_tag=7)
