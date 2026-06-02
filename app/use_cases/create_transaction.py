from app.domain.models import Customer, Transaction, PaymentStatus


class ProcessTransactionUseCase:
    def __init__(self, transaction_repository, bank_gateway):
        self.transaction_repository = transaction_repository
        self.bank_gateway = bank_gateway

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
            # tracking_id=request.tracking_id,
            # notification_url=request.notification_url,
            amount=request.amount,
            customer=customer,
            status=PaymentStatus.PENDING,
        )
        saved_transaction = self.transaction_repository.save(transaction)

        bank_response = self.bank_gateway.authorize(request)

        self.transaction_repository.update_status(
            transaction_id=saved_transaction["id"],
            status=PaymentStatus(bank_response["status"]).value,
        )

        return {
            "transaction_id": str(saved_transaction["id"]),
            "status": bank_response["status"],
            "provider_transaction_id": bank_response["provider_transaction_id"],
        }
