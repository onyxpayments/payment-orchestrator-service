from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

from app.application.events import PaymentNotificationRequested
from app.domain.models import Customer, PaymentStatus, Transaction
from app.infrastructure.messaging.notification_publisher import (
    RabbitMQNotificationPublisher,
)
from config.settings import Settings


def create_settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://test",
        bank_service_url="http://bank",
    )


@patch("app.infrastructure.messaging.notification_publisher.pika.BlockingConnection")
def test_notification_publisher_routes_persistent_event(mock_connection):
    connection = Mock()
    connection.is_open = True
    channel = connection.channel.return_value
    channel.basic_publish.return_value = True
    mock_connection.return_value = connection
    transaction_id = uuid4()
    event = PaymentNotificationRequested.from_transaction(
        Transaction(
            id=transaction_id,
            amount=Decimal("10000"),
            currency="COP",
            notification_url="https://merchant.example/webhooks/payments",
            status=PaymentStatus.APPROVED,
            customer=Customer("Juan", "Bello", "123456789"),
            provider_transaction_id=f"mock_{transaction_id}",
        ),
        "Approved",
    )

    RabbitMQNotificationPublisher(create_settings()).publish_payment_notification(event)

    channel.queue_declare.assert_called_once_with(
        queue="webhook.payment-notifications.q",
        durable=True,
    )
    published = channel.basic_publish.call_args.kwargs
    assert published["exchange"] == "payment.events"
    assert published["routing_key"] == "payment.notification.requested.v1"
    assert published["properties"].delivery_mode == 2
    assert published["mandatory"] is True
