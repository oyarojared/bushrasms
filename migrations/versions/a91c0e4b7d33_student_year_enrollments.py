"""Record the class a student belonged to in each school year.

Revision ID: a91c0e4b7d33
Revises: c4a8e1b07d22
Create Date: 2026-11-23 05:40:00.000000
"""

from datetime import date

from alembic import op
import sqlalchemy as sa


revision = "a91c0e4b7d33"
down_revision = "c4a8e1b07d22"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    student_columns = {col["name"] for col in inspector.get_columns("students")}

    if "enrollment_status" not in student_columns:
        op.add_column(
            "students",
            sa.Column(
                "enrollment_status",
                sa.String(length=20),
                nullable=False,
                server_default="active",
            ),
        )
    if "current_year" not in student_columns:
        op.add_column(
            "students",
            sa.Column("current_year", sa.Integer(), nullable=True),
        )

    # Learners already on the register are in the school year that is
    # open when this change is applied.
    op.execute(
        sa.text(
            "UPDATE students SET current_year = :year WHERE current_year IS NULL"
        ).bindparams(year=date.today().year)
    )

    if "student_enrollments" not in inspector.get_table_names():
        _create_enrollment_table()

    indexes = {idx["name"] for idx in inspector.get_indexes("student_enrollments")}
    if "ix_student_enrollments_class_year" not in indexes:
        op.create_index(
            "ix_student_enrollments_class_year",
            "student_enrollments",
            ["class_id", "year"],
        )
    if "ix_student_enrollments_student_id" not in indexes:
        op.create_index(
            "ix_student_enrollments_student_id",
            "student_enrollments",
            ["student_id"],
        )


def _create_enrollment_table():
    op.create_table(
        "student_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("stream", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["branch_classes.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "year", name="uq_student_enrollment_year"
        ),
    )
    op.create_index(
        "ix_student_enrollments_class_year",
        "student_enrollments",
        ["class_id", "year"],
    )
    op.create_index(
        "ix_student_enrollments_student_id",
        "student_enrollments",
        ["student_id"],
    )


def downgrade():
    op.drop_index(
        "ix_student_enrollments_student_id", table_name="student_enrollments"
    )
    op.drop_index(
        "ix_student_enrollments_class_year", table_name="student_enrollments"
    )
    op.drop_table("student_enrollments")
    op.drop_column("students", "current_year")
    op.drop_column("students", "enrollment_status")
