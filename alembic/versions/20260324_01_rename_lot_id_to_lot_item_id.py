"""rename lot_id to lot_item_id in lwin_matching

Revision ID: 20260324_01
Revises: 20260315_01
Create Date: 2026-03-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260324_01"
down_revision = "20260315_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing data references lots.external_id (incompatible with lot_item FK).
    # Clear before applying new constraints.
    op.execute("TRUNCATE TABLE lwin_matching RESTART IDENTITY")
    op.alter_column("lwin_matching", "lot_id", new_column_name="lot_item_id")
    op.create_unique_constraint("uq_lwin_matching_lot_item_id", "lwin_matching", ["lot_item_id"])
    op.create_foreign_key(
        "fk_lwin_matching_lot_item_id",
        "lwin_matching",
        "lot_items",
        ["lot_item_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_lwin_matching_lot_item_id", "lwin_matching", type_="foreignkey")
    op.drop_constraint("uq_lwin_matching_lot_item_id", "lwin_matching", type_="unique")
    op.alter_column("lwin_matching", "lot_item_id", new_column_name="lot_id")
