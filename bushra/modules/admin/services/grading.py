from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from ....modals.assessment_db import *

def get_max_points_for_class(grade_id):
    """
    Returns the highest points value for a given class (BranchClasses.id)
    based on the active/latest grading scheme.
    """

    mapping = (
        GradeGradingScheme.query
        .join(GradeGradingScheme.scheme)
        .filter(GradeGradingScheme.grade_id == grade_id)
        .order_by(
            GradingScheme.is_active.desc(),
            GradingScheme.created_at.desc()
        )
        .first()
    )

    if not mapping:
        return None

    return (
        db.session.query(db.func.max(GradingBoundary.points))
        .filter(GradingBoundary.scheme_id == mapping.scheme_id)
        .scalar()
    )


