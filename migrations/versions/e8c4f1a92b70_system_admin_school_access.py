"""System admin flag and super-admin school assignments.

Revision ID: e8c4f1a92b70
Revises: c15c6fd83015
Create Date: 2026-09-08 12:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e8c4f1a92b70"
down_revision = "c15c6fd83015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "teachers",
        sa.Column(
            "is_system_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_table(
        "super_admin_branches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_id", "branch_id", name="uq_super_admin_branch"),
    )
    op.create_index(
        "ix_super_admin_branches_teacher_id",
        "super_admin_branches",
        ["teacher_id"],
    )
    op.create_index(
        "ix_super_admin_branches_branch_id",
        "super_admin_branches",
        ["branch_id"],
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE teachers
            SET is_system_admin = 1
            WHERE id = 11 OR username = 'omongare782'
            """
        )
    )
    # Keep current super admins working: they already saw schools 1-10.
    conn.execute(
        sa.text(
            """
            INSERT INTO super_admin_branches (teacher_id, branch_id)
            SELECT t.id, b.id
            FROM teachers t
            JOIN branches b ON b.id BETWEEN 1 AND 10
            WHERE t.is_super_admin = 1
              AND t.is_system_admin = 0
            """
        )
    )


def downgrade():
    op.drop_index("ix_super_admin_branches_branch_id", table_name="super_admin_branches")
    op.drop_index("ix_super_admin_branches_teacher_id", table_name="super_admin_branches")
    op.drop_table("super_admin_branches")
    op.drop_column("teachers", "is_system_admin")
