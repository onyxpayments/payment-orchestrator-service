import json

import pika

from app.application.events import PaymentNotificationRequested
from config.settings import Settings
from app.infrastructure.messaging.rabbitmq_connection import connection_parameters


class RabbitMQNotificationPublisher:
    def __init__(self, settings: Settings):
        self.settings = settings

    def publish_payment_notification(
        self,
        event: PaymentNotificationRequested,
    ) -> None:
        connection = pika.BlockingConnection(connection_parameters(self.settings))
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=self.settings.rabbitmq_exchange,
                exchange_type="topic",
                durable=True,
            )
            channel.queue_declare(
                queue=self.settings.rabbitmq_notification_queue,
                durable=True,
            )
            channel.queue_bind(
                exchange=self.settings.rabbitmq_exchange,
                queue=self.settings.rabbitmq_notification_queue,
                routing_key=self.settings.rabbitmq_notification_routing_key,
            )
            channel.confirm_delivery()
            published = channel.basic_publish(
                exchange=self.settings.rabbitmq_exchange,
                routing_key=self.settings.rabbitmq_notification_routing_key,
                body=json.dumps(event.to_dict()).encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    message_id=str(event.event_id),
                    correlation_id=str(event.transaction_id),
                    type=event.event_type,
                ),
                mandatory=True,
            )
            if published is False:
                raise RuntimeError("RabbitMQ did not confirm notification event")
        finally:
            if connection.is_open:
                connection.close()
