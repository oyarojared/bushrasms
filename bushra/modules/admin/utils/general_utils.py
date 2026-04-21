import re
from ....modals.assessment_db import GradeGradingScheme, GradingBoundary, GradingScheme, GradingSystem


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_date(d):
    if not d:
        return "---"
    try:
        return d.strftime("%Y-%m-%d")
    except AttributeError:
        return d


def is_phone_correct_format(phone):
    # ---------------------------------------
    # PHONE NORMALIZATION & VALIDATION
    # ---------------------------------------
    pattern = r"^(?:0\d{9}|\+254\d{9})$"
    if phone:
        phone_clean = phone.replace(" ", "")
    else:
        return
    return re.match(pattern, phone_clean)



def validate_fullname(name: str) -> bool:
    if not name:
        return False

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name.strip())

    if len(name) < 2:
        return False

    # Allow letters (including Unicode), spaces, hyphens, apostrophes
    pattern = r"^[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[ '\-][A-Za-zÀ-ÖØ-öø-ÿ]+)*$"
    return bool(re.fullmatch(pattern, name))



def resolve_grade(grade_id, score):
    """
    Given a grade (BranchClasses.id) and a score, return the grading outcome.
    ALWAYS returns a dictionary with performance_level, points, descriptor.
    """

    # Default empty result (CRITICAL)
    empty_result = {
        "performance_level": None,
        "points": None,
        "descriptor": None
    }

    # Defensive: no score
    if score is None:
        return empty_result

    # 1️⃣ Find the active grading scheme for this grade
    mapping = (
        GradeGradingScheme.query
        .join(GradeGradingScheme.scheme)
        .filter(GradeGradingScheme.grade_id == grade_id)
        .order_by(
            GradingScheme.is_active.desc(),  # active first
            GradingScheme.created_at.desc()   # newest first
        )
        .first()
    )


    if not mapping:
        return empty_result  # No grading scheme assigned

    scheme = mapping.scheme

    # 2️⃣ Fetch all boundaries for this scheme
    boundaries = GradingBoundary.query.filter_by(scheme_id=scheme.id).all()

    if not boundaries:
        return empty_result

    # 3️⃣ Find the boundary that contains the score
    for b in boundaries:
        if b.min_score <= score <= b.max_score:
            return {
                "performance_level": b.performance_level,
                "points": b.points,
                "descriptor": b.descriptor
            }

    # 4️⃣ Score outside all boundaries
    return empty_result



