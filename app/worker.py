import logging

from app.adapters.inbound.messaging.payment_requested_consumer import (
    PaymentRequestedConsumer,
)
from app.bootstrap import get_process_payment_use_case
from config.settings import settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    consumer = PaymentRequestedConsumer(
        settings=settings,
        use_case_factory=get_process_payment_use_case,
    )
    consumer.run_forever()


if __name__ == "__main__":
    main()
