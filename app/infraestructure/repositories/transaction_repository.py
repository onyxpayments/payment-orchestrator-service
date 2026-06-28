from uuid import UUID

from app.domain.models import Customer, PaymentStatus, Transaction


class PostgresTransactionRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, transaction_id: UUID) -> Transaction | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    amount,
                    status,
                    customer_first_name,
                    customer_last_name,
                    customer_personal_id
                FROM transactions
                WHERE id = %s;
                """,
                (transaction_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return Transaction(
            id=row["id"],
            amount=row["amount"],
            currency=None,
            status=PaymentStatus(row["status"]),
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
                status,
                customer_first_name,
                customer_last_name,
                customer_personal_id
            )
            VALUES (
                %(id)s,
                %(amount)s,
                %(status)s,
                %(customer_first_name)s,
                %(customer_last_name)s,
                %(customer_personal_id)s
            );
        """

        params = {
            "id": transaction.id,
            "amount": transaction.amount,
            "status": transaction.status.value,
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
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (transaction.status.value, transaction.id),
            )
