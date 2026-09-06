"""SMS tables for parent and teacher messages.

Revision ID: b7e4a91c2d08
Revises: c15c6fd83015
Create Date: 2026-09-05 06:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7e4a91c2d08"
down_revision = "c15c6fd83015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sms_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("sender_name", sa.String(length=11), nullable=True),
        sa.Column("allow_class_teachers", sa.Boolean(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id"),
    )
    op.create_table(
        "sms_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("for_teachers", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sms_templates_branch_id", "sms_templates", ["branch_id"])
    op.create_table(
        "sms_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("audience_type", sa.String(length=30), nullable=False),
        sa.Column("audience_label", sa.String(length=180), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=True),
        sa.Column("stream", sa.String(length=50), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("credits_used", sa.Integer(), nullable=False),
        sa.Column("ready_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("sent_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["branch_classes.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["teachers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sms_messages_branch_id", "sms_messages", ["branch_id"])
    op.create_index("ix_sms_messages_sender_id", "sms_messages", ["sender_id"])
    op.create_index("ix_sms_messages_created_at", "sms_messages", ["created_at"])
    op.create_table(
        "sms_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("recipient_type", sa.String(length=20), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("detail", sa.String(length=180), nullable=True),
        sa.Column("phone_raw", sa.String(length=30), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("skip_reason", sa.String(length=80), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("parts", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=250), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["sms_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sms_recipients_message_id", "sms_recipients", ["message_id"])


def downgrade():
    op.drop_table("sms_recipients")
    op.drop_table("sms_messages")
    op.drop_table("sms_templates")
    op.drop_table("sms_settings")
