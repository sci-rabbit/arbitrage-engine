"""add_invalid_pair_and_pair_a_index

Revision ID: b3e7a92d1f04
Revises: fc901c6f5651
Create Date: 2026-04-24 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b3e7a92d1f04'
down_revision: str | Sequence[str] | None = 'fc901c6f5651'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'invalid_pair',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('a_market_id', sa.Text(), nullable=False),
        sa.Column('b_market_id', sa.Text(), nullable=False),
    )

    op.create_table(
        'pair_a_index',
        sa.Column('pair_id', sa.BigInteger(), sa.ForeignKey('pairs.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('a_market_id', sa.Text(), nullable=False),
        sa.Column('final_score', sa.Double(), nullable=False),
    )

    op.create_index(
        'idx_pair_a_index_a_score',
        'pair_a_index',
        ['a_market_id', sa.text('final_score DESC')],
    )


def downgrade() -> None:
    op.drop_index('idx_pair_a_index_a_score', table_name='pair_a_index')
    op.drop_table('pair_a_index')
    op.drop_table('invalid_pair')
