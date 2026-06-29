import logging

from app.application.commands import ProcessProviderCallbackCommand
from app.application.ports import UnitOfWork
from app.application.results import ProcessProviderCallbackResult
from app.domain.models import PaymentStatus

logger = logging.getLogger(__name__)


class TransactionNotFound(LookupError):
    pass


class ProcessProviderCallbackUseCase:
    def __init__(self, unit_of_work: UnitOfWork):
        self.uow = unit_of_work

    def execute(
        self,
        command: ProcessProviderCallbackCommand,
    ) -> ProcessProviderCallbackResult:
        with self.uow:
            transactions = self.uow.transactions
            transaction = transactions.get_for_update(command.transaction_id)
            if transaction is None:
                raise TransactionNotFound(str(command.transaction_id))

            new_status = PaymentStatus(command.status)
            previous_status = transaction.status
            changed = transaction.apply_provider_callback(
                provider_transaction_id=command.provider_transaction_id,
                new_status=new_status,
            )

            if changed:
                transactions.update(transaction)
            elif previous_status != new_status:
                logger.info(
                    "Ignored stale callback %s for %s (current=%s)",
                    new_status,
                    transaction.id,
                    previous_status,
                )

            self.uow.commit()

        return ProcessProviderCallbackResult(
            transaction_id=transaction.id,
            status=transaction.status,
        )
