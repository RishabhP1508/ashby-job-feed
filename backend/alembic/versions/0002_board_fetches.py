"""board_fetches: log of slugs people actually fetched

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "board_fetches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetch_count", sa.Integer(), nullable=False),
        sa.Column("last_job_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_fetches_slug", "board_fetches", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_board_fetches_slug", table_name="board_fetches")
    op.drop_table("board_fetches")
