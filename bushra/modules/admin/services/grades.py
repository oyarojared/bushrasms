# Handle all grades functionality
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from ....modals.branches_db import BranchClasses, db

import re


def format_grade_form(name):
    if not name:
        return ""
    return re.sub(r"\s+", " ", str(name).strip()).upper()


def sort_grade_list(rows, reverse=False, dedupe=True):
    """
    Sort list of (id, grade_form) into hierarchy:
    Play Group, PP1, PP2, Grade 1–12, Form 1–4, IGCSE.
    Optionally removes duplicate grade names (case-insensitive).
    """

    CATEGORY_ORDER = {
        "PLAYGROUP": 0,
        "PP": 1,
        "GRADE": 2,
        "FORM": 3,
        "IGCSE": 4,
    }

    def parse_class_name(name):
        raw = format_grade_form(name)

        if raw in {"PLAY GROUP", "PLAYGROUP", "PLAY-GROUP"}:
            return CATEGORY_ORDER["PLAYGROUP"], 0

        if raw == "IGCSE":
            return CATEGORY_ORDER["IGCSE"], 999

        compact = raw.replace(" ", "")

        m = re.match(r"PP([12])$", compact)
        if m:
            return CATEGORY_ORDER["PP"], int(m.group(1))

        m = re.match(r"GRADE([1-9]|1[0-2])$", compact)
        if m:
            return CATEGORY_ORDER["GRADE"], int(m.group(1))

        m = re.match(r"FORM([1-4])$", compact)
        if m:
            return CATEGORY_ORDER["FORM"], int(m.group(1))

        return 999, 999

    if dedupe:
        seen = set()
        unique_rows = []
        for id_, name in rows:
            key = format_grade_form(name)
            if key and key not in seen:
                seen.add(key)
                unique_rows.append((id_, name))
        rows = unique_rows

    sorted_rows = sorted(rows, key=lambda r: parse_class_name(r[1]))

    if reverse:
        sorted_rows.reverse()

    return sorted_rows


def sort_grade_records(records):
    """Sort grade API records and normalize grade_form to uppercase."""
    if not records:
        return []

    rows = [(record["id"], record.get("grade_form", "")) for record in records]
    sorted_rows = sort_grade_list(rows, dedupe=False)
    record_map = {record["id"]: record for record in records}

    result = []
    for record_id, _ in sorted_rows:
        item = dict(record_map[record_id])
        item["grade_form"] = format_grade_form(item.get("grade_form", ""))
        result.append(item)

    return result


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
