from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user

from ....modals.branches_db import Branch


def load_branch_choices():
    try:
        query = Branch.query.with_entities(
            Branch.id, Branch.branch_name
        )

        # Role-based filtering
        if current_user.is_super_admin:
            # Developer super admin sees all branches
            if current_user.id != 11:
                query = query.filter(Branch.id.between(1, 10))
        elif current_user.branch_id:
            # Regular users only see their own branch
            query = query.filter(Branch.id == current_user.branch_id)

        # Apply ordering
        query = query.order_by(Branch.created_at.desc())

        rows = query.all()

        choices = [("", "--- Select a Branch ---")] + [
            (str(b.id), b.branch_name) for b in rows
        ]

        return choices

    except SQLAlchemyError as e:
        current_app.logger.error(f"[DB ERROR] load_branch_choices: {e}")
        return [("", "--- No Branches Available ---")]

def get_accessible_branches_query():
    query = Branch.query

    if current_user.is_super_admin:
        if current_user.id != 11:
            query = query.filter(Branch.id.between(1, 10))
    elif current_user.branch_id:
        query = query.filter(Branch.id == current_user.branch_id)

    return query


# from flask import current_app
# from sqlalchemy.exc import SQLAlchemyError

# from ....modals.branches_db import Branch
# from flask_login import current_user


# def load_branch_choices():
#     try:
#         query = Branch.query.with_entities(
#             Branch.id, Branch.branch_name
#         )

#         # Apply ordering
#         query = query.order_by(Branch.created_at.desc())

#         # Role-based filtering
#         if not current_user.is_super_admin and current_user.branch_id:
#             query = query.filter(Branch.id == current_user.branch_id)

#         rows = query.all()

#         choices = [("", "--- Select a Branch ---")] + [
#             (str(b.id), b.branch_name) for b in rows
#         ]

#         return choices

#     except SQLAlchemyError as e:
#         current_app.logger.error(f"[DB ERROR] load_branch_choices: {e}")
#         return [("", "--- No Branches Available ---")]