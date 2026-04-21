# Handle all grades functionality
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from ....modals.branches_db import BranchClasses, db

import re


def sort_grade_list(rows, reverse=False):
    """
    Sort list of (id, grade_form) into hierarchy:
    PP1, PP2, Grade 1–12, Form 1–4, IGCSE.
    Removes duplicate grade names (case-insensitive).
    """

    CATEGORY_ORDER = {
        "PP": 1,
        "GRADE": 2,
        "FORM": 3,
        "IGCSE": 4,
    }

    def parse_class_name(name):
        raw = name.strip().upper()

        # IGCSE → always last
        if raw == "IGCSE":
            return CATEGORY_ORDER["IGCSE"], 999

        # PP1, PP2
        m = re.match(r"PP\s*([1-2])$", raw)
        if m:
            return CATEGORY_ORDER["PP"], int(m.group(1))

        # Grade 1–12
        m = re.match(r"GRADE\s*([1-9]|1[0-2])$", raw)
        if m:
            return CATEGORY_ORDER["GRADE"], int(m.group(1))

        # Form 1–4
        m = re.match(r"FORM\s*([1-4])$", raw)
        if m:
            return CATEGORY_ORDER["FORM"], int(m.group(1))

        # Unknown → push to bottom
        return 999, 999

    # -----------------------------------------
    # REMOVE DUPLICATES (case-insensitive)
    # -----------------------------------------
    seen = set()
    unique_rows = []
    for (id_, name) in rows:
        key = name.strip().upper()
        if key not in seen:
            seen.add(key)
            unique_rows.append((id_, name))

    # -----------------------------------------
    # SORT BASED ON CATEGORY + NUMBER
    # -----------------------------------------
    sorted_rows = sorted(unique_rows, key=lambda r: parse_class_name(r[1]))

    if reverse:
        sorted_rows.reverse()

    return sorted_rows


def load_grades(reverse=False):
    try:
        rows = BranchClasses.query.with_entities(
            BranchClasses.id,
            BranchClasses.grade_form
        ).order_by(BranchClasses.created_at.desc()).all()
        sorted_rows = sort_grade_list(rows, reverse=reverse)
        return [("", "--- Select a Grade / Form ---")] + [
            (r[1], r[1]) for r in sorted_rows
        ]    
    except Exception as e:
       return [("", "--- No loaded data yet ---")]

   

def create_class(form):
    # Create a new class + (streams) for a specific branch.
    try:
        # Prevent duplicates
        existing = BranchClasses.query.filter_by(
            branch_id=form.branches.data,
            class_year=form.class_year.data,
            grade_form=form.grade_form.data.strip(),
        ).first()
        
        if existing:
            return (
                None, 
                "A record for this Branch + Year + Grade/Form already exists!"
            )
        
        # Process streams safely
        streams_raw = form.streams.data or ""
        streams_list = [
            s.strip() for s in streams_raw.split(",") if s.strip()
        ] or None 
        
        # Save new record
        new_class = BranchClasses(
            branch_id=form.branches.data,
            class_year=form.class_year.data,
            grade_form=form.grade_form.data.strip(),
            streams=streams_list,
        )

        db.session.add(new_class)
        db.session.commit()

        return new_class, "Form/Grade record added successfully!"

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error saving BranchClasses: {e}", 
            exc_info=True
        )
        
        return (
            None, 
            "An unexpected error occurred while saving. Please try again."
        )
