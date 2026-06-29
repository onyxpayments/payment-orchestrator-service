from uuid import UUID


class PostgresInboxRepository:
    def __init__(self, connection):
        self.connection = connection

    def contains(self, event_id: UUID) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM processed_events WHERE event_id = %s;",
                (event_id,),
            )
            return cursor.fetchone() is not None

    def add(self, event_id: UUID, event_type: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO processed_events (event_id, event_type)
                VALUES (%s, %s)
                ON CONFLICT (event_id) DO NOTHING;
                """,
                (event_id, event_type),
            )
