from flask import Blueprint

from ...modals import db
from ...modals.branches_db import Branch, BranchClasses
from ...modals.subjects_db import Subject, SubjectEligibility

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="templates",
    static_folder="static",
)


# Import routes so they attach to admin_bp
from . import utils
from .routes import (admin, api, branches, excel_files,
                     school_staff, students, subjects, assessments)
