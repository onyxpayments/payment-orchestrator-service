import logging

import pika

from app.adapters.inbound.http.health import database_is_ready
from app.infrastructure.messaging.rabbitmq_connection import (
    connection_parameters,
)
from config.settings import settings

logger = logging.getLogger(__name__)


def rabbitmq_is_ready() -> bool:
    connection = None
    try:
        connection = pika.BlockingConnection(connection_parameters(settings))
        return connection.is_open
    except pika.exceptions.AMQPError as error:
        logger.warning("RabbitMQ readiness check failed: %s", error)
        return False
    finally:
        if connection is not None and connection.is_open:
            connection.close()


def main() -> None:
    if not database_is_ready() or not rabbitmq_is_ready():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
