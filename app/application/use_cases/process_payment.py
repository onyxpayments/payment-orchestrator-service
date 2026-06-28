from app.application.commands import ProcessPaymentCommand


class ProcessPaymentUseCase:
    def __init__(self, unit_of_work, payment_provider):
        self.uow = unit_of_work
        self.payment_provider = payment_provider

    def execute(
        self,
        command: ProcessPaymentCommand,
    ) -> ProcessPaymentResult:
        with self.uow:
            already_received = self.uow.inbox.exists(
                command.event_id
            )

            transaction = self.uow.transactions.get(
                command.payment_id
            )

            if not already_received:
                transaction = Transaction.create(
                    transaction_id=command.payment_id,
                    amount=command.amount,
                    currency=command.currency,
                    customer=command.customer,
                )

                self.uow.transactions.add(transaction)
                self.uow.inbox.add(
                    event_id=command.event_id,
                    event_type="payment.requested",
                )
                self.uow.commit()

        if transaction.requires_authorization():
            authorization = self.payment_provider.authorize(
                transaction,
                idempotency_key=str(transaction.id),
            )

            with self.uow:
                transaction = self.uow.transactions.get(
                    command.payment_id
                )

                transaction.apply_authorization(authorization)

                self.uow.transactions.update(transaction)
                self.uow.outbox.add(
                    PaymentStatusChanged.from_transaction(
                        transaction
                    )
                )
                self.uow.commit()

        return ProcessPaymentResult.from_transaction(transaction)