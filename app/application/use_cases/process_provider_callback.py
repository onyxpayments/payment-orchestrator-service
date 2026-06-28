from app.application.commands import ProcessProviderCallbackCommand
from app.application.ports import UnitOfWork
from app.application.results import ProcessProviderCallbackResult
from app.domain.models import PaymentStatus


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
            transaction = self.uow.transactions.get(command.transaction_id)
            if transaction is None:
                raise TransactionNotFound(str(command.transaction_id))

            changed = transaction.apply_provider_callback(
                provider_transaction_id=command.provider_transaction_id,
                new_status=PaymentStatus(command.status),
            )

            if changed:
                self.uow.transactions.update(transaction)

            self.uow.commit()

        return ProcessProviderCallbackResult(
            transaction_id=transaction.id,
            status=transaction.status,
        )
