"""Staff in-app messages.

Revision ID: b7e2a91c4d10
Revises: e8c4f1a92b70
Create Date: 2026-11-07 20:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7e2a91c4d10"
down_revision = "e8c4f1a92b70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "staff_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("audience_label", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["teachers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_messages_sender_id", "staff_messages", ["sender_id"])
    op.create_index("ix_staff_messages_branch_id", "staff_messages", ["branch_id"])

    op.create_table(
        "staff_message_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["message_id"], ["staff_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "teacher_id", name="uq_staff_message_recipient"
        ),
    )
    op.create_index(
        "ix_staff_message_recipients_message_id",
        "staff_message_recipients",
        ["message_id"],
    )
    op.create_index(
        "ix_staff_message_recipients_teacher_id",
        "staff_message_recipients",
        ["teacher_id"],
    )


def downgrade():
    op.drop_index(
        "ix_staff_message_recipients_teacher_id",
        table_name="staff_message_recipients",
    )
    op.drop_index(
        "ix_staff_message_recipients_message_id",
        table_name="staff_message_recipients",
    )
    op.drop_table("staff_message_recipients")
    op.drop_index("ix_staff_messages_branch_id", table_name="staff_messages")
    op.drop_index("ix_staff_messages_sender_id", table_name="staff_messages")
    op.drop_table("staff_messages")
