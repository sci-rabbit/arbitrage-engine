"""add_updated_at_to_tables

Revision ID: a1c3e5f7d9b2
Revises: b3e7a92d1f04
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c3e5f7d9b2'
down_revision: Union[str, Sequence[str], None] = 'b3e7a92d1f04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = sa.text("now()")
    for table in ('markets', 'pairs', 'orderbooks', 'invalid_pair'):
        op.add_column(
            table,
            sa.Column(
                'updated_at',
                sa.DateTime(timezone=True),
                server_default=now,
                nullable=False,
            ),
        )


def downgrade() -> None:
    for table in ('markets', 'pairs', 'orderbooks', 'invalid_pair'):
        op.drop_column(table, 'updated_at')