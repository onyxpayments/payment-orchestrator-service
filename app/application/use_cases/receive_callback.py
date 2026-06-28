from app.domain.models import PaymentStatus


class ProcessProviderCallbackUseCase:

    def __init__(self, transaction_repository):
        self.transaction_repository = transaction_repository

    def execute(self, transaction_id, callback):

        self.transaction_repository.update_status(
            transaction_id=transaction_id,
            status=PaymentStatus(callback.status),
        )

        return {"message": "Callback received"}
