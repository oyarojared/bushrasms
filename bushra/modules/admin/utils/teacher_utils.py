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


def _phone_digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def build_username_stem(fullname: str, phone: str) -> str:
    """Build the preferred username for a new account. Does not check uniqueness."""
    names = (fullname or "").strip().split()
    first = names[0] if names else "user"
    last = names[-1] if len(names) > 1 else ""
    digits = _phone_digits(phone)
    suffix = digits[-4:] if digits else ""

    if last:
        raw = f"{first[0]}{last}{suffix}"
    else:
        raw = f"{first}{suffix}"

    stem = re.sub(r"[^a-z0-9]", "", raw.lower())
    if len(stem) < 6:
        stem = (stem + "user00")[:6]
    return stem[:50]


def next_available_username(stem: str, taken) -> str:
    """Return stem, or stem2 / stem3 / ... if those names are already used."""
    taken_lower = {str(name).lower() for name in taken if name}
    candidate = stem
    n = 2
    while candidate in taken_lower:
        suffix = str(n)
        candidate = f"{stem[:50 - len(suffix)]}{suffix}"
        n += 1
        if n > 9999:
            raise ValueError("Could not allocate a unique username")
    return candidate


def _usernames_starting_with(stem: str):
    rows = Teacher.query.filter(Teacher.username.ilike(f"{stem}%")).all()
    return [teacher.username for teacher in rows if teacher.username]


def generate_username(fullname: str, phone: str, existing_usernames=None):
    """
    Username for a newly created teacher.

    Existing accounts are never rewritten. This only allocates a name that
    is not already in use, including older generated usernames.
    """
    stem = build_username_stem(fullname, phone)
    if existing_usernames is None:
        existing_usernames = _usernames_starting_with(stem)
    return next_available_username(stem, existing_usernames)


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