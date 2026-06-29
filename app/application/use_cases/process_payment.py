import logging

from app.application.commands import ProcessPaymentCommand
from app.application.ports import PaymentProvider, UnitOfWork
from app.application.results import ProcessPaymentResult
from app.domain.models import Transaction

logger = logging.getLogger(__name__)


class ProcessPaymentUseCase:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_provider: PaymentProvider,
    ):
        self.uow = unit_of_work
        self.payment_provider = payment_provider

    def execute(self, command: ProcessPaymentCommand) -> ProcessPaymentResult:
        with self.uow:
            if self.uow.inbox.contains(command.event_id):
                transaction = self.uow.transactions.get(command.payment_id)
                if transaction is None:
                    raise RuntimeError("Processed event has no associated transaction")
                return self._result(transaction)

            transaction = self.uow.transactions.get(command.payment_id)

            if transaction is None:
                transaction = Transaction.create(
                    transaction_id=command.payment_id,
                    amount=command.amount,
                    currency=command.currency,
                    customer=command.customer,
                )

                self.uow.transactions.add(transaction)
                self.uow.commit()

        authorization = None
        if transaction.requires_authorization():
            authorization = self.payment_provider.authorize(
                transaction,
                idempotency_key=str(transaction.id),
            )

        with self.uow:
            transactions = self.uow.transactions
            transaction = transactions.get_for_update(command.payment_id)
            if transaction is None:
                raise RuntimeError("Transaction not found after creation")

            if authorization is not None:
                previous_status = transaction.status
                provider_id = authorization.provider_transaction_id
                changed = transaction.apply_authorization(
                    provider_transaction_id=provider_id,
                    new_status=authorization.status,
                )
                if changed:
                    transactions.update(transaction)
                elif previous_status != authorization.status:
                    logger.info(
                        "Ignored stale provider status %s for payment %s "
                        "already in %s",
                        authorization.status,
                        transaction.id,
                        previous_status,
                    )
            self.uow.inbox.add(
                event_id=command.event_id,
                event_type="payment.requested",
            )
            self.uow.commit()

        return self._result(transaction)

    @staticmethod
    def _result(transaction: Transaction) -> ProcessPaymentResult:
        return ProcessPaymentResult(
            transaction_id=transaction.id,
            provider_transaction_id=transaction.provider_transaction_id,
            status=transaction.status,
        )
