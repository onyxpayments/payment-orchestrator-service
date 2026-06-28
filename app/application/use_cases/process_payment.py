from app.application.commands import ProcessPaymentCommand
from app.application.ports import PaymentProvider, UnitOfWork
from app.application.results import ProcessPaymentResult
from app.domain.models import Transaction


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

        if transaction.requires_authorization():
            authorization = self.payment_provider.authorize(
                transaction,
                idempotency_key=str(transaction.id),
            )

            with self.uow:
                transaction = self.uow.transactions.get(command.payment_id)
                if transaction is None:
                    raise RuntimeError("Transaction not found after creation")

                provider_id = authorization.provider_transaction_id
                transaction.apply_authorization(
                    provider_transaction_id=provider_id,
                    new_status=authorization.status,
                )
                self.uow.transactions.update(transaction)
                self.uow.commit()

        return ProcessPaymentResult(
            transaction_id=transaction.id,
            provider_transaction_id=transaction.provider_transaction_id,
            status=transaction.status,
        )
