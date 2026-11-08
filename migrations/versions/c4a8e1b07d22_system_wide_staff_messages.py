"""Allow a system-wide staff message with no single school.

Revision ID: c4a8e1b07d22
Revises: b7e2a91c4d10
Create Date: 2026-11-08 08:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c4a8e1b07d22"
down_revision = "b7e2a91c4d10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("staff_messages") as batch:
        batch.alter_column(
            "branch_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("staff_messages") as batch:
        batch.alter_column(
            "branch_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
