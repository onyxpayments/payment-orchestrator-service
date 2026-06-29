import logging
import signal
import threading
import time
from collections.abc import Callable

import pika
from pydantic import ValidationError

from app.adapters.inbound.messaging.schemas import PaymentRequestedMessage
from app.application.use_cases.process_payment import ProcessPaymentUseCase
from app.infrastructure.messaging.rabbitmq_connection import (
    connection_parameters,
)
from config.settings import Settings

logger = logging.getLogger(__name__)


class PaymentRequestedConsumer:
    def __init__(
        self,
        settings: Settings,
        use_case_factory: Callable[[], ProcessPaymentUseCase],
    ):
        self.settings = settings
        self.use_case_factory = use_case_factory
        self._stop_requested = threading.Event()
        self._connection = None
        self._channel = None

    def run_forever(self) -> None:
        self._install_signal_handlers()
        while not self._stop_requested.is_set():
            try:
                self._consume()
            except pika.exceptions.AMQPError:
                logger.exception("RabbitMQ consumer connection failed")
            except Exception:
                logger.exception("PaymentRequested consumer stopped unexpectedly")
            finally:
                self._close_connection()

            if not self._stop_requested.is_set():
                time.sleep(self.settings.rabbitmq_reconnect_delay_seconds)

    def request_stop(self, *_args) -> None:
        self._stop_requested.set()
        connection = self._connection
        if connection is not None and connection.is_open:
            connection.add_callback_threadsafe(self._stop_consuming)

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)

    def _consume(self) -> None:
        self._connection = pika.BlockingConnection(connection_parameters(self.settings))
        self._channel = self._connection.channel()
        self._declare_topology(self._channel)
        self._channel.confirm_delivery()
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(
            queue=self.settings.rabbitmq_payment_requested_queue,
            on_message_callback=self.handle_message,
            auto_ack=False,
        )
        logger.info(
            "Consuming PaymentRequested messages from %s",
            self.settings.rabbitmq_payment_requested_queue,
        )
        self._channel.start_consuming()

    def _declare_topology(self, channel) -> None:
        channel.exchange_declare(
            exchange=self.settings.rabbitmq_exchange,
            exchange_type="topic",
            durable=True,
        )
        channel.queue_declare(
            queue=self.settings.rabbitmq_payment_requested_queue,
            durable=True,
        )
        channel.queue_bind(
            exchange=self.settings.rabbitmq_exchange,
            queue=self.settings.rabbitmq_payment_requested_queue,
            routing_key=(self.settings.rabbitmq_payment_requested_routing_key),
        )

        channel.exchange_declare(
            exchange=self.settings.rabbitmq_retry_exchange,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(
            queue=self.settings.rabbitmq_payment_requested_retry_queue,
            durable=True,
            arguments={
                "x-message-ttl": self.settings.rabbitmq_retry_delay_ms,
                "x-dead-letter-exchange": self.settings.rabbitmq_exchange,
                "x-dead-letter-routing-key": (
                    self.settings.rabbitmq_payment_requested_routing_key
                ),
            },
        )
        channel.queue_bind(
            exchange=self.settings.rabbitmq_retry_exchange,
            queue=self.settings.rabbitmq_payment_requested_retry_queue,
            routing_key=(self.settings.rabbitmq_payment_requested_retry_routing_key),
        )

        channel.exchange_declare(
            exchange=self.settings.rabbitmq_dead_letter_exchange,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(
            queue=(self.settings.rabbitmq_payment_requested_dead_letter_queue),
            durable=True,
        )
        channel.queue_bind(
            exchange=self.settings.rabbitmq_dead_letter_exchange,
            queue=(self.settings.rabbitmq_payment_requested_dead_letter_queue),
            routing_key=(
                self.settings.rabbitmq_payment_requested_dead_letter_routing_key
            ),
        )

    def handle_message(self, channel, method, properties, body: bytes) -> None:
        delivery_tag = method.delivery_tag
        try:
            message = PaymentRequestedMessage.model_validate_json(body)
        except (ValidationError, ValueError, UnicodeDecodeError) as error:
            logger.warning("Invalid PaymentRequested message: %s", error)
            self._dead_letter_or_requeue(
                channel,
                delivery_tag,
                properties,
                body,
                reason="invalid_message",
            )
            return

        try:
            self.use_case_factory().execute(message.to_command())
        except Exception as error:
            logger.exception(
                "PaymentRequested processing failed for event %s",
                message.event_id,
            )
            self._retry_or_dead_letter(
                channel,
                delivery_tag,
                properties,
                body,
                error,
            )
            return

        channel.basic_ack(delivery_tag=delivery_tag)
        logger.info(
            "PaymentRequested event %s acknowledged for payment %s",
            message.event_id,
            message.payment_id,
        )

    def _retry_or_dead_letter(
        self,
        channel,
        delivery_tag,
        properties,
        body: bytes,
        error: Exception,
    ) -> None:
        headers = dict(properties.headers or {})
        retry_count = int(headers.get("x-retry-count", 0))
        if retry_count >= self.settings.rabbitmq_max_retries:
            self._dead_letter_or_requeue(
                channel,
                delivery_tag,
                properties,
                body,
                reason=type(error).__name__,
            )
            return

        headers["x-retry-count"] = retry_count + 1
        published = self._publish(
            channel=channel,
            exchange=self.settings.rabbitmq_retry_exchange,
            routing_key=(self.settings.rabbitmq_payment_requested_retry_routing_key),
            properties=properties,
            body=body,
            headers=headers,
        )
        if published:
            channel.basic_ack(delivery_tag=delivery_tag)
            logger.warning(
                "PaymentRequested scheduled for retry %s/%s",
                retry_count + 1,
                self.settings.rabbitmq_max_retries,
            )
        else:
            channel.basic_nack(delivery_tag=delivery_tag, requeue=True)

    def _dead_letter_or_requeue(
        self,
        channel,
        delivery_tag,
        properties,
        body: bytes,
        reason: str,
    ) -> None:
        headers = dict(properties.headers or {})
        headers["x-failure-reason"] = reason
        published = self._publish(
            channel=channel,
            exchange=self.settings.rabbitmq_dead_letter_exchange,
            routing_key=(
                self.settings.rabbitmq_payment_requested_dead_letter_routing_key
            ),
            properties=properties,
            body=body,
            headers=headers,
        )
        if published:
            channel.basic_ack(delivery_tag=delivery_tag)
            logger.error("PaymentRequested moved to dead-letter queue: %s", reason)
        else:
            channel.basic_nack(delivery_tag=delivery_tag, requeue=True)

    @staticmethod
    def _publish(
        channel,
        exchange: str,
        routing_key: str,
        properties,
        body: bytes,
        headers: dict,
    ) -> bool:
        published = channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type=properties.content_type or "application/json",
                content_encoding=properties.content_encoding or "utf-8",
                delivery_mode=2,
                message_id=properties.message_id,
                correlation_id=properties.correlation_id,
                type=properties.type,
                headers=headers,
            ),
            mandatory=True,
        )
        return published is not False

    def _stop_consuming(self) -> None:
        if self._channel is not None and self._channel.is_open:
            self._channel.stop_consuming()

    def _close_connection(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
        self._connection = None
        self._channel = None
