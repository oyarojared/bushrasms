import re

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from ....modals.staff_db import Teacher


def check_unique_teacher_fields(phone=None, email=None, tsc_no=None, id_no=None, exclude_id=None):
    filters = []

    # Normalize input to avoid format mismatches
    phone = phone.strip() if phone else None
    email = email.strip().lower() if email else None
    tsc_no = tsc_no.strip() if tsc_no else None
    id_no = str(id_no).strip() if id_no else None

    if phone:
        filters.append(Teacher.phone == phone)
    if email:
        filters.append(Teacher.email == email)
    if tsc_no:
        filters.append(Teacher.tsc_no == tsc_no)
    if id_no:
        filters.append(Teacher.id_no == id_no)

    if not filters:
        return None

    query = Teacher.query.filter(or_(*filters))

    # Make sure exclude_id is handled correctly
    if exclude_id is not None:
        query = query.filter(Teacher.id != int(exclude_id))

    existing = query.first()
    if not existing:
        return None

    # Check exact duplicate field
    if phone and existing.phone == phone:
        return {"field": "phone"}

    if email and existing.email == email:
        return {"field": "email"}

    if tsc_no and existing.tsc_no == tsc_no:
        return {"field": "tsc_no"}

    if id_no and existing.id_no == id_no:
        return {"field": "id_no"}

    return {"field": "unknown"}


def generate_username(fullname: str, phone: str):
    names = fullname.strip().split()
    first = names[0]
    last = names[-1] if len(names) > 1 else ""
    suffix = phone[-3:]
    if last:
        username = f"{first[0]}{last}{suffix}".lower()
    else:
        username = f"{first}{suffix}".lower()
    return re.sub(r"[^a-z0-9]", "", username)


def generate_initial_password(phone: str):
    if not isinstance(phone, str):
        raise TypeError(
            "Phone number must be converted to a string first!"
        )
    digits = re.sub(r"\D", "", phone)
    raw = digits[-4:]
    return generate_password_hash(raw, method="pbkdf2:sha256", salt_length=16)


def load_teacher_choices():
    """
    Returns a list of tuples suitable for WTForms SelectField choices:
    [(value, label), ...]
    """
    teachers_list = []
    try:
        teachers = Teacher.query.all()
        teachers_list = [("", "--- Select teacher ---")] + [
            (str(t.id), t.fullname or "Unknown") for t in teachers
        ]
    except Exception as e:
        current_app.logger.error(f"Can't fetch teachers: {e}")
    
    return teachers_list