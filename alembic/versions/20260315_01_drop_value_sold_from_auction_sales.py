"""drop value_sold from auction_sales

Revision ID: 20260315_01
Revises:
Create Date: 2026-03-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("auction_sales", "value_sold")


def downgrade() -> None:
    op.add_column("auction_sales", sa.Column("value_sold", sa.Float(), nullable=True))
