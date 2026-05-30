from app.infraestructure.db.connection import get_connection


class PostgresTransactionRepository:
    def save(self, transaction):
        query = """
            INSERT INTO transactions (
                tracking_id,
                notification_url,
                amount,
                status,
                customer_first_name,
                customer_last_name,
                customer_personal_id,
                customer_email,
                customer_country,
                customer_ip
            )
            VALUES (
                %(tracking_id)s,
                %(notification_url)s,
                %(amount)s,
                %(status)s,
                %(customer_first_name)s,
                %(customer_last_name)s,
                %(customer_personal_id)s,
                %(customer_email)s,
                %(customer_country)s,
                %(customer_ip)s
            )
            RETURNING id, tracking_id, amount, status;
        """

        params = {
            "tracking_id": transaction.tracking_id,
            "notification_url": transaction.notification_url,
            "amount": transaction.amount,
            "status": transaction.status.value,
            "customer_first_name": transaction.customer.first_name,
            "customer_last_name": transaction.customer.last_name,
            "customer_personal_id": transaction.customer.personal_id,
            "customer_email": transaction.customer.email,
            "customer_country": transaction.customer.country,
            "customer_ip": transaction.customer.ip,
        }

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                conn.commit()

        return result