"""Adopt and complete the transactions schema.

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260628_0001"
down_revision = None
branch_labels = None
depends_on = None

TABLE_NAME = "transactions"
PROVIDER_ID_CONSTRAINT = "uq_transactions_provider_transaction_id"


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE payment_status AS ENUM (
                'NEW',
                'PENDING',
                'APPROVED',
                'DECLINED',
                'ERROR',
                'EXPIRED'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """)

    if TABLE_NAME not in inspector.get_table_names():
        payment_status = postgresql.ENUM(
            "NEW",
            "PENDING",
            "APPROVED",
            "DECLINED",
            "ERROR",
            "EXPIRED",
            name="payment_status",
            create_type=False,
        )
        op.create_table(
            TABLE_NAME,
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("notification_url", sa.Text(), nullable=False),
            sa.Column(
                "status",
                payment_status,
                server_default=sa.text("'NEW'::payment_status"),
                nullable=False,
            ),
            sa.Column(
                "provider_transaction_id",
                sa.String(100),
                nullable=True,
            ),
            sa.Column("customer_first_name", sa.String(100), nullable=False),
            sa.Column("customer_last_name", sa.String(100), nullable=False),
            sa.Column("customer_personal_id", sa.String(50), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("NOW()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("NOW()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "provider_transaction_id",
                name=PROVIDER_ID_CONSTRAINT,
            ),
        )
        return

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}

    if "currency" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "currency",
                sa.String(3),
                server_default="COP",
                nullable=True,
            ),
        )
        sql = "UPDATE transactions SET currency='COP' WHERE currency IS NULL"
        op.execute(sql)
        op.alter_column(
            TABLE_NAME,
            "currency",
            existing_type=sa.String(3),
            server_default=None,
            nullable=False,
        )

    if "provider_transaction_id" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "provider_transaction_id",
                sa.String(100),
                nullable=True,
            ),
        )

    inspector = sa.inspect(connection)
    unique_constraints = inspector.get_unique_constraints(TABLE_NAME)
    provider_id_is_unique = any(
        constraint["column_names"] == ["provider_transaction_id"]
        for constraint in unique_constraints
    )
    if not provider_id_is_unique:
        op.create_unique_constraint(
            PROVIDER_ID_CONSTRAINT,
            TABLE_NAME,
            ["provider_transaction_id"],
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if TABLE_NAME not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    if PROVIDER_ID_CONSTRAINT in unique_constraints:
        op.drop_constraint(
            PROVIDER_ID_CONSTRAINT,
            TABLE_NAME,
            type_="unique",
        )

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if "provider_transaction_id" in columns:
        op.drop_column(TABLE_NAME, "provider_transaction_id")
    if "currency" in columns:
        op.drop_column(TABLE_NAME, "currency")
