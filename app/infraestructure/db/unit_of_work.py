from app.infraestructure.db.connection import get_connection
from app.infraestructure.repositories.transaction_repository import (
    PostgresTransactionRepository,
)


class PostgresUnitOfWork:
    def __init__(self):
        self.connection = None
        self.transactions = None

    def __enter__(self):
        self.connection = get_connection()
        self.transactions = PostgresTransactionRepository(self.connection)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection is None:
            return

        if exc_type is not None:
            self.connection.rollback()

        self.connection.close()
        self.connection = None
        self.transactions = None

    def commit(self) -> None:
        if self.connection is None:
            raise RuntimeError("Unit of work is not active")
        self.connection.commit()
