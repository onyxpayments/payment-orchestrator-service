from app.domain.models import Customer, Transaction, PaymentStatus


class CreateTransactionUseCase:
    def __init__(self, transaction_repository):
        self.transaction_repository = transaction_repository

    def execute(self, request):
        customer = Customer(
            first_name=request.customer.first_name,
            last_name=request.customer.last_name,
            personal_id=request.customer.personal_id,
            # email=request.customer.email,
            # country=request.customer.country,
            # ip=request.customer.ip,
        )

        transaction = Transaction(
            id=None,
            tracking_id=request.tracking_id,
            notification_url=request.notification_url,
            amount=request.amount,
            customer=customer,
            status=PaymentStatus.PENDING,
        )

        return self.transaction_repository.save(transaction)
