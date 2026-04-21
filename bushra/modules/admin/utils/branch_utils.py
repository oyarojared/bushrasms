from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from ....modals.branches_db import Branch
from flask_login import current_user


def load_branch_choices():
    try:
        query = Branch.query.with_entities(
            Branch.id, Branch.branch_name
        )

        # Apply ordering
        query = query.order_by(Branch.created_at.desc())

        # Role-based filtering
        if not current_user.is_super_admin and current_user.branch_id:
            query = query.filter(Branch.id == current_user.branch_id)

        rows = query.all()

        choices = [("", "--- Select a Branch ---")] + [
            (str(b.id), b.branch_name) for b in rows
        ]

        return choices

    except SQLAlchemyError as e:
        current_app.logger.error(f"[DB ERROR] load_branch_choices: {e}")
        return [("", "--- No Branches Available ---")]