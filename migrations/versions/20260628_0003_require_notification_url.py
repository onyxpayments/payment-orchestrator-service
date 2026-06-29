"""Require a webhook notification URL for every new transaction.

Revision ID: 20260628_0003
Revises: 20260628_0002
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260628_0003"
down_revision = "20260628_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {
        column["name"]: column for column in inspector.get_columns("transactions")
    }

    if "notification_url" not in columns:
        op.add_column(
            "transactions",
            sa.Column("notification_url", sa.Text(), nullable=True),
        )

    null_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM transactions "
            "WHERE notification_url IS NULL OR BTRIM(notification_url) = ''"
        )
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot require notification_url while legacy transactions have no URL"
        )

    op.alter_column(
        "transactions",
        "notification_url",
        existing_type=sa.Text(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "transactions",
        "notification_url",
        existing_type=sa.Text(),
        nullable=True,
    )
