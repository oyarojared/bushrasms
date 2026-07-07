"""
Service functions to handle branch related operations.
"""
from flask import current_app

from ....modals.branches_db import Branch, BranchClasses, db
from ....modals.staff_db import Teacher, ClassTeacher
from ....modals.students_db import Student
from collections import defaultdict
from sqlalchemy import func

from collections import defaultdict
from ..utils.file_utils import preprocess_image


def get_first_branch_id():   
    first_branch = Branch.query.first()
    return first_branch.id if first_branch else None


def count_gender_distribution(data):
    male = 0
    female = 0

    for v in data:
        if v.gender:
            g = v.gender.lower()
            if g.startswith("m"):
                male += 1
            elif g.startswith("f"):
                female += 1

    return [male, female]


def get_branch_data(branch_id):
    """
    Return general branch data:
        branch name
        Total teachers per branch and their gender
        Total Students per class per branch and their gender
    """

    branch = Branch.query.get(branch_id)
    if not branch:
        return None, "Branch does not exist."
    
    # Fetch students + teachers 
    students = Student.query.filter_by(branch_id=branch_id).all()
    teachers = Teacher.query.filter_by(branch_id=branch_id).all()

    student_gender_counts = count_gender_distribution(students)
    teacher_gender_counts = count_gender_distribution(teachers)

    students_per_class = {}
    for s in students:
        class_name = "Unknown"
        if s.class_info and hasattr(s.class_info, "grade_form"):
            class_name = s.class_info.grade_form

        students_per_class[class_name] = students_per_class.get(class_name, 0) + 1

    # Package data
    data = {
        "branch": branch.to_dict(),
        "total_students": len(students),
        "total_teachers": len(teachers),
        "gender_counts": student_gender_counts,
        "teacher_gender_counts": teacher_gender_counts,
        "students_per_class": students_per_class,
    }

    return data, None


def get_branch_classes():
    records = BranchClasses.query.order_by(
        BranchClasses.branch_id,
        BranchClasses.class_year.desc()
    ).all()

    branch_data = {}
    for r in records: 
        # Skip if branch is None (orphaned)
        if not r.branch:
            continue

        branch_name = r.branch.branch_name
        if branch_name not in branch_data:
            branch_data[branch_name] = []

        branch_data[branch_name].append({
            "grade_form": r.grade_form,
            "streams": r.streams or []
        })

    return branch_data


def delete_branch_service(branch_id):
    branch = db.session.get(Branch, branch_id)

    if not branch:
        return False, "Invalid Branch"

    has_students = db.session.query(Student.id).filter_by(branch_id=branch_id).first()

    if has_students:
        return False, (
            "Can't delete a branch that has students! "
            "Please move them to another branch first."
        )

    try:
        db.session.delete(branch)
        db.session.commit()

        return True, f"Branch {branch.branch_name.upper()} was deleted successfully."

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to delete branch {branch.branch_name.upper()}: {e}"
        )
        return False, "Error occurred while deleting branch."


def update_branch_service(form, branch_id):  
    branch = Branch.query.get(branch_id)
    if not branch:
        return None, "Invalid branch selected."
    
    # Process logo if uploaded
    logo_filename = None
    if form.logo.data:
        logo_filename = preprocess_image(form.logo.data, size=(200, 200))

    try:
        # Update text fields
        branch.branch_name = form.branch_name.data.strip()
        branch.school_code = form.school_code.data  
        branch.branch_manager = form.branch_manager.data.strip()
        branch.branch_level = form.branch_level.data      
        branch.school_gender = form.school_gender.data
        branch.school_type = form.school_type.data
        branch.logo = logo_filename if logo_filename else branch.logo
        branch.motto = form.motto.data.strip() if form.motto.data else None

        # optional field
        branch.email = form.email.data.strip() if form.email.data else None

        if form.branch_head.data:
            branch.branch_head = form.branch_head.data  
        else:
            branch.branch_head = branch.branch_head
 
        db.session.commit()
        return branch, "Branch updated successfully!"

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            "Update branch failed | id=%s | %s: %s",
            branch_id,
            type(e).__name__,
            e
        )

        return None, "An error occurred while updating the branch. Try again."


def get_branch_academic_population(branch_id: int):
    """
    Returns academic population structure for a branch:
    - Grades / Forms
    - Total students per grade
    - Boys / Girls per grade
    - Stream-level breakdown where applicable
    - Class teacher if assigned (at class and stream level)
    """

    branch = Branch.query.get(branch_id)
    if not branch:
        return None, "Branch does not exist."

    # Fetch all classes for the branch
    classes = BranchClasses.query.filter_by(branch_id=branch_id).all()
    if not classes:
        return {
            "branch_id": branch_id,
            "branch_name": branch.branch_name,
            "grades": []
        }, None

    # Fetch all students for the branch
    students = Student.query.filter_by(branch_id=branch_id).all()

    # Fetch all class teachers for this branch
    class_teachers = ClassTeacher.query.filter_by(branch_id=branch_id).all()

    # Map teachers by (class_id, stream) for quick lookup
    # stream can be None for a whole-class teacher
    class_teacher_map = {
        (ct.class_id, ct.stream or None): ct.teacher
        for ct in class_teachers if ct.teacher
    }

    # Index students by class_id
    students_by_class = defaultdict(list)
    for s in students:
        students_by_class[s.class_id].append(s)

    grades_data = []

    for cls in classes:
        cls_students = students_by_class.get(cls.id, [])

        # Grade-level gender counts
        boys = sum(1 for s in cls_students if s.gender and s.gender.lower().startswith("m"))
        girls = sum(1 for s in cls_students if s.gender and s.gender.lower().startswith("f"))

        # Class-level teacher (for stream=None)
        class_teacher = class_teacher_map.get((cls.id, None))
        class_teacher_info = {
            "id": class_teacher.id,
            "name": f"{class_teacher.title} {class_teacher.fullname}"
        } if class_teacher else None

        grade_entry = {
            "class_id": cls.id,
            "grade_form": cls.grade_form,
            "class_year": cls.class_year,
            "teacher": class_teacher_info,  # Class-level teacher
            "totals": {
                "total": len(cls_students),
                "boys": boys,
                "girls": girls,
            },
            "streams": []
        }

        # Stream-level breakdown (if streams exist)
        if cls.streams:
            stream_map = defaultdict(list)
            for s in cls_students:
                stream_name = s.stream or "Unassigned"
                stream_map[stream_name].append(s)

            for stream_name, stream_students in stream_map.items():
                stream_boys = sum(1 for s in stream_students if s.gender and s.gender.lower().startswith("m"))
                stream_girls = sum(1 for s in stream_students if s.gender and s.gender.lower().startswith("f"))

                # Stream-level teacher, fallback to class teacher if none
                teacher = class_teacher_map.get((cls.id, stream_name)) or class_teacher
                teacher_info = {
                    "id": teacher.id,
                    "name": f"{teacher.title} {teacher.fullname}"
                } if teacher else None

                grade_entry["streams"].append({
                    "name": stream_name,
                    "total": len(stream_students),
                    "boys": stream_boys,
                    "girls": stream_girls,
                    "teacher": teacher_info
                })

        grades_data.append(grade_entry)

    return {
        "branch_id": branch.id,
        "branch_name": branch.branch_name,
        "grades": grades_data
    }, None
