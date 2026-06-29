from uuid import UUID

from app.domain.models import Customer, PaymentStatus, Transaction


class PostgresTransactionRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, transaction_id: UUID) -> Transaction | None:
        return self._get(transaction_id, for_update=False)

    def get_for_update(
        self,
        transaction_id: UUID,
    ) -> Transaction | None:
        return self._get(transaction_id, for_update=True)

    def _get(
        self,
        transaction_id: UUID,
        *,
        for_update: bool,
    ) -> Transaction | None:
        lock_clause = " FOR UPDATE" if for_update else ""
        query = """
            SELECT
                id,
                amount,
                currency,
                status,
                provider_transaction_id,
                customer_first_name,
                customer_last_name,
                customer_personal_id
            FROM transactions
            WHERE id = %s
            """ + lock_clause + ";"

        with self.connection.cursor() as cursor:
            cursor.execute(query, (transaction_id,))
            row = cursor.fetchone()

        if row is None:
            return None

        return Transaction(
            id=row["id"],
            amount=row["amount"],
            currency=row["currency"],
            status=PaymentStatus(row["status"]),
            provider_transaction_id=row["provider_transaction_id"],
            customer=Customer(
                first_name=row["customer_first_name"],
                last_name=row["customer_last_name"],
                personal_id=row["customer_personal_id"],
            ),
        )

    def add(self, transaction: Transaction) -> None:
        query = """
            INSERT INTO transactions (
                id,
                amount,
                currency,
                status,
                provider_transaction_id,
                customer_first_name,
                customer_last_name,
                customer_personal_id
            )
            VALUES (
                %(id)s,
                %(amount)s,
                %(currency)s,
                %(status)s,
                %(provider_transaction_id)s,
                %(customer_first_name)s,
                %(customer_last_name)s,
                %(customer_personal_id)s
            );
        """

        params = {
            "id": transaction.id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status.value,
            "provider_transaction_id": transaction.provider_transaction_id,
            "customer_first_name": transaction.customer.first_name,
            "customer_last_name": transaction.customer.last_name,
            "customer_personal_id": transaction.customer.personal_id,
        }

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)

    def update(self, transaction: Transaction) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE transactions
                SET status = %s,
                    provider_transaction_id = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (
                    transaction.status.value,
                    transaction.provider_transaction_id,
                    transaction.id,
                ),
            )
