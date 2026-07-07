from flask import Blueprint

from ...modals import db
from ...modals.branches_db import Branch, BranchClasses
from ...modals.subjects_db import Subject, SubjectEligibility

from flask import send_from_directory
from pathlib import Path
from flask import current_app, send_from_directory

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="templates",
    static_folder="static",
)


@admin_bp.route('/media/passports/<filename>')
def serve_passport(filename):
    base = Path(current_app.root_path).parent.parent.parent
    folder = base / "uploads" / "passports"

    return send_from_directory(folder, filename)

# Import routes so they attach to admin_bp
from . import utils
from .routes import (admin, api, branches, excel_files,
                     school_staff, students, subjects, assessments)
