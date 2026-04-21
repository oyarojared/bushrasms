from flask import current_app, jsonify, request
from ....modals.branches_db import Branch, BranchClasses, db
from .. import admin_bp

from flask import request, jsonify, current_app
from sqlalchemy import func 
from ....modals.branches_db import BranchClasses
from ....modals.students_db import Student, StudentSubjectAllocation
from ....modals.subjects_db import Subject, SubjectEligibility, Lesson
from ....modals.staff_db import Teacher, ClassTeacher
from ..services.report import build_broadsheet_data
from ....modals.assessment_db import (StudentExamMark,ExamPaper, GradeGradingScheme, 
                                    GradingBoundary, GradingScheme, GradingSystem)

from ..utils import resolve_grade
from flask_login import login_required
from ..utils.route_protect import admin_required


# --------------------------------------
# API endpoint: Get all branches
# URL: /admin/api/branches
# Method: GET
# Returns a JSON list of branches with their id and name
# Example: [{"id": 1, "name": "Main Branch"}, ...]
# --------------------------------------
@admin_bp.route("/api/branches")
@login_required
def api_branches():
    try:
        if current_user.is_super_admin:
            branches = Branch.query.order_by(Branch.branch_name).all()
        else:
            branches = Branch.query.filter_by(id=current_user.branch_id).all()

        data = [{"id": b.id, "name": b.branch_name} for b in branches]
        return jsonify(data)

    except Exception as e:
        current_app.logger.error(f"Error fetching branches: {e}", exc_info=True)
        return jsonify([]), 500
# --------------------------------------
# API endpoint: Get grades/classes for a given branch
# URL: /admin/api/grades/<branch_id>
# Method: GET
# Returns a JSON list of classes with id, grade_form, and streams
# Example: [{"id": 1, "grade_form": "Form 1", "streams": ["A","B"]}, ...]
# --------------------------------------

from flask_login import current_user
from sqlalchemy import distinct

@admin_bp.route("/api/grades/<int:branch_id>")
@login_required
def api_grades(branch_id):
    try:
        # ADMIN → all classes in branch
        if current_user.is_admin:
            classes = (
                BranchClasses.query
                .filter_by(branch_id=branch_id)
                .all()
            )

            data = [
                {
                    "id": c.id,
                    "grade_form": c.grade_form,
                    "streams": c.streams or []
                }
                for c in classes
            ]

            return jsonify(data)

        # TEACHER → only classes they teach
        lessons = (
            Lesson.query
            .join(BranchClasses, Lesson.class_id == BranchClasses.id)
            .filter(
                Lesson.teacher_id == current_user.id,
                Lesson.branch_id == branch_id
            )
            .all()
        )

        # Group lessons by class
        class_map = {}

        for lesson in lessons:
            cls = lesson.class_

            if cls.id not in class_map:
                class_map[cls.id] = {
                    "id": cls.id,
                    "grade_form": cls.grade_form,
                    "streams": set()
                }

            if lesson.stream:
                class_map[cls.id]["streams"].add(lesson.stream)

        # Convert stream sets → lists
        data = []
        for item in class_map.values():
            item["streams"] = sorted(item["streams"])
            data.append(item)

        return jsonify(data)

    except Exception as e:
        current_app.logger.error(
            f"Error fetching grades for branch {branch_id}: {e}",
            exc_info=True
        )
        return jsonify([]), 500





@admin_bp.route("/api/class-context", methods=["POST"])
@login_required
def api_class_context():
    data = request.get_json(silent=True) or {}

    branch_id = data.get("branch_id")
    class_id = data.get("class_id")
    stream = data.get("stream")  # optional

    if not branch_id or not class_id:
        return jsonify({"error": "branch_id and class_id are required"}), 400

    try:
        # ----------------------------
        # FETCH CLASS
        # ----------------------------
        class_obj = BranchClasses.query.filter_by(
            id=class_id,
            branch_id=branch_id
        ).first()

        if not class_obj:
            return jsonify({"error": "Class not found"}), 404

        # ----------------------------
        # FETCH SUBJECTS FOR THIS CLASS
        # ----------------------------
        from sqlalchemy import func

        subjects = (
            Subject.query
            .join(SubjectEligibility)
            .filter(
                func.lower(SubjectEligibility.grade_form)
                == func.lower(class_obj.grade_form)
            )
            .all()
        )


        # ----------------------------
        # FETCH TEACHERS FOR BRANCH
        # ----------------------------
        teachers = Teacher.query.filter_by(branch_id=branch_id).all()

        # ----------------------------
        # COUNT STUDENTS PER SUBJECT
        # ----------------------------
        student_query = Student.query.filter_by(
            branch_id=branch_id,
            class_id=class_id
        )

        if stream:
            student_query = student_query.filter_by(stream=stream)

        student_ids_subq = student_query.with_entities(Student.id)

        subject_counts = (
            db.session.query(
                StudentSubjectAllocation.subject_id,
                func.count(StudentSubjectAllocation.student_id).label("total")
            )
            .filter(StudentSubjectAllocation.student_id.in_(student_ids_subq))
            .group_by(StudentSubjectAllocation.subject_id)
            .all()
        )

        subject_count_map = {
            subject_id: total
            for subject_id, total in subject_counts
        }

        # ----------------------------
        # FETCH ASSIGNED TEACHERS
        # ----------------------------
        lesson_map = {}
        for lesson in Lesson.query.filter_by(branch_id=branch_id, class_id=class_id).all():
            if stream and lesson.stream != stream:
                continue
            lesson_map[lesson.subject_id] = lesson.teacher_id

        # ----------------------------
        # BUILD RESPONSE
        # ----------------------------
        subjects_data = []
        for subj in subjects:
            student_count = subject_count_map.get(subj.id, 0)
            
            # Skip subjects with 0 students
            if student_count == 0:
                continue

            assigned_teacher_id = lesson_map.get(subj.id)
            subjects_data.append({
                "id": subj.id,
                "name": subj.name,
                "code": subj.code,
                "category": subj.category,
                "is_examinable": subj.is_examinable,
                "is_compulsory": subj.is_compulsory,
                "student_count": student_count,
                "assigned_teacher_id": assigned_teacher_id
            })


        response = {
            "branch_id": branch_id,
            "class_id": class_obj.id,
            "class_name": class_obj.grade_form,
            "stream": stream,
            "subjects": subjects_data,
            "teachers": [
                {"id": t.id, "fullname": t.fullname, "title": t.title, "employer": t.employer}
                for t in teachers
            ]
        }

        return jsonify(response)

    except Exception as e:
        current_app.logger.exception("Error building class context API")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/api/class-teacher-context")
@login_required
def class_teacher_context():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", default=None, type=str)

    if not branch_id or not class_id:
        return jsonify({"error": "branch_id and class_id are required"}), 400

    # Get current class teacher
    current_assignment = ClassTeacher.query.filter_by(
        branch_id=branch_id,
        class_id=class_id,
        stream=stream
    ).first()

    current_teacher = None
    if current_assignment and current_assignment.teacher_id:
        teacher = Teacher.query.get(current_assignment.teacher_id)
        if teacher:
            current_teacher = {"id": teacher.id, "name": f"{teacher.title} {teacher.fullname}"}

    # Get all teachers in this branch
    teachers_query = Teacher.query.filter_by(branch_id=branch_id).all()
    teachers = [{"id": t.id, "name": f"{t.title} {t.fullname}"} for t in teachers_query]

    return jsonify({
        "current_teacher": current_teacher,
        "teachers": teachers
    })



@admin_bp.route("/api/subjects")
@login_required
def api_subjects():
    try:
        branch_id = request.args.get("branch_id", type=int)
        class_id = request.args.get("class_id", type=int)
        stream = request.args.get("stream")

        if not branch_id or not class_id:
            return jsonify([])

        # Normalize stream
        if stream in ("", "null", None):
            stream = None

        # Base query
        query = (
            Lesson.query
            .join(Subject)
            .filter(
                Lesson.branch_id == branch_id,
                Lesson.class_id == class_id,
                Subject.is_examinable.is_(True)
            )
        )

        # 🔐 Teacher restriction
        if not current_user.is_admin:
            query = query.filter(Lesson.teacher_id == current_user.id)

        # Stream filtering
        if stream:
            query = query.filter(Lesson.stream == stream)
        else:
            query = query.filter(Lesson.stream.is_(None))

        lessons = query.distinct(Lesson.subject_id).all()

        subjects = [
            {
                "id": lesson.subject.id,
                "name": lesson.subject.name,
                "code": lesson.subject.code
            }
            for lesson in lessons
        ]

        return jsonify(subjects)

    except Exception as e:
        current_app.logger.error(
            f"Error loading subjects: {e}", exc_info=True
        )
        return jsonify([]), 500


@admin_bp.route("/api/exam-students")
@login_required
def get_exam_students():
    """
    Returns students for a selected branch, class (grade), stream (optional),
    and subject, along with pre-existing marks if they exist.
    Used by marks entry UI.
    """

    # -------------------- 1. Read query parameters --------------------
    branch_id  = request.args.get("branch_id", type=int)
    class_id   = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    stream     = request.args.get("stream") or None
    exam_id    = request.args.get("exam_id", type=int) 

    # -------------------- 2. Validate required parameters --------------------
    if not all([branch_id, class_id, subject_id]):
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        # -------------------- 3. Load students for this class/stream/subject --------------------
        # Only students who are allocated to this subject
        students_query = (
            db.session.query(Student)
            .join(StudentSubjectAllocation, Student.id == StudentSubjectAllocation.student_id)
            .filter(
                Student.branch_id == branch_id,
                Student.class_id == class_id,
                StudentSubjectAllocation.subject_id == subject_id
            )
        )
        if stream:
            students_query = students_query.filter(Student.stream == stream)

        students = students_query.all()

        # -------------------- 4. Check if an ExamPaper exists --------------------
        paper = ExamPaper.query.filter_by(
            exam_id=exam_id,
            branch_id=branch_id,
            class_id=class_id,
            stream=stream,
            subject_id=subject_id
        ).first()

        # -------------------- 5. Load pre-existing marks --------------------
        marks_map = {} 
        if paper:
            marks_records = StudentExamMark.query.filter_by(exam_paper_id=paper.id).all()
            marks_map = {m.student_id: m.marks for m in marks_records}
            print(marks_map)
        # -------------------- 6. Build JSON response --------------------
        response = {
            "paper": {
                "id": paper.id if paper else None,
                "marks_out_of": paper.marks_out_of if paper else 100
            },
            "students": [
                {
                    "id": s.id,
                    "admission_number": s.admission_number,
                    "full_name": s.fullname,
                    "marks": marks_map.get(s.id)  # prefill if marks exist
                }
                for s in students
            ]
        }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Error fetching exam students: {e}", exc_info=True)
        return jsonify({"error": "Failed to load students"}), 500
    
    
    

@admin_bp.route("/api/save-exam-marks", methods=["POST"])
@login_required
def save_exam_marks():
    data = request.get_json()

    exam_id    = data.get("exam_id")
    branch_id  = data.get("branch_id")
    class_id   = data.get("class_id")
    stream     = data.get("stream")
    subject_id = data.get("subject_id")
    marks_out_of = data.get("marks_out_of")
    marks_list = data.get("marks")  # [{student_id, marks}]

    if not all([exam_id, branch_id, class_id, subject_id]):
        return jsonify({"error": "Missing required data"}), 400

    try:
        # 1. Get or create exam paper
        paper = ExamPaper.query.filter_by(
            exam_id=exam_id,
            branch_id=branch_id,
            class_id=class_id,
            stream=stream,
            subject_id=subject_id
        ).first()

        if not paper:
            paper = ExamPaper(
                exam_id=exam_id,
                branch_id=branch_id,
                class_id=class_id,
                stream=stream,
                subject_id=subject_id,
                marks_out_of=marks_out_of
            )
            db.session.add(paper)
            db.session.flush()  # get paper.id

        # if paper.is_locked:
        #     return jsonify({"error": "Paper is locked"}), 403

        # 2. Save marks
        for item in marks_list:
            student_id = item["student_id"]
            marks = item["marks"]

            record = StudentExamMark.query.filter_by(
                exam_paper_id=paper.id,
                student_id=student_id
            ).first()

            if record:
                record.marks = marks
            else:
                db.session.add(
                    StudentExamMark(
                        exam_paper_id=paper.id,
                        student_id=student_id,
                        marks=marks
                    )
                )

        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Saving marks failed: {e}", exc_info=True)
        return jsonify({"error": "Failed to save marks"}), 500

from datetime import datetime

@admin_bp.route("/api/exams")
@login_required
def api_exams():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", default=None, type=str)

    if not branch_id or not class_id:
        return jsonify([])

    try:
        query = ExamPaper.query.filter(
            ExamPaper.branch_id == branch_id,
            ExamPaper.class_id == class_id
        )

        # ✅ Handle stream correctly
        # if stream in ("null", "", None):
        #     stream = None

        # if stream:
        #     query = query.filter(ExamPaper.stream == stream)
        # else:
        #     query = query.filter(ExamPaper.stream.is_(None))

        papers = query.all()
        
        exams = {}
        for paper in papers:
            exams[paper.exam.id] = {
                "id": paper.exam.id,
                "name": paper.exam.name
            }

        return jsonify(list(exams.values()))

    except Exception as e:
        print(e)
        current_app.logger.error(f"Error loading exams: {e}", exc_info=True)
        return jsonify([]), 500


# # -------------------- API: Get exam students with resolved grades --------------------
@admin_bp.route("/api/exam-students-with-grades")
@login_required
def api_exam_students_with_grades():
    branch_id  = request.args.get("branch_id", type=int)
    class_id   = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    exam_id    = request.args.get("exam_id", type=int)
    stream     = request.args.get("stream", default=None, type=str)

    if not all([branch_id, class_id, subject_id, exam_id]): 
        print(f'BRANCH ID: {branch_id}, CLASS ID: {class_id}, SUBJECT ID: {subject_id}, EXAM ID: {exam_id}')
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        # -------------------- Normalize stream --------------------
        if stream in ("null", "", None):
            stream = None

        # -------------------- Fetch students allocated to subject --------------------
        students_query = (
            Student.query
            .join(
                StudentSubjectAllocation,
                Student.id == StudentSubjectAllocation.student_id
            )
            .filter(
                Student.branch_id == branch_id,
                Student.class_id == class_id,
                StudentSubjectAllocation.subject_id == subject_id
            )
        )

        if stream:
            students_query = students_query.filter(Student.stream == stream)

        students = students_query.all()

        # -------------------- Fetch exam paper (STREAM-SAFE) --------------------
        paper_query = ExamPaper.query.filter_by(
            exam_id=exam_id,
            branch_id=branch_id,
            class_id=class_id,
            subject_id=subject_id
        )

        if stream:
            paper_query = paper_query.filter(ExamPaper.stream == stream)
        else:
            paper_query = paper_query.filter(ExamPaper.stream.is_(None))

        paper = paper_query.first()

        # -------------------- Fetch marks --------------------
        marks_map = {}
        if paper:
            marks_records = StudentExamMark.query.filter_by(
                exam_paper_id=paper.id
            ).all()
            marks_map = {m.student_id: m.marks for m in marks_records}

        # -------------------- Resolve grades --------------------
        students_data = []

        for s in students:
            marks = marks_map.get(s.id)

            if marks is not None and paper:
                grade_info = resolve_grade(class_id, marks)
                if grade_info is None:
                    grade_info = {
                        "performance_level": None,
                        "points": None,
                        "descriptor": None
                    }
            else:
                grade_info = {
                    "performance_level": None,
                    "points": None,
                    "descriptor": None
                }

            students_data.append({
                "id": s.id,
                "admission_number": s.admission_number,
                "pathway": s.pathway,
                "full_name": s.fullname,
                "marks": marks,
                **grade_info
            })

        # -------------------- Response --------------------
        return jsonify({
            "paper": {
                "id": paper.id if paper else None,
                "marks_out_of": paper.marks_out_of if paper else 100
            },
            "students": students_data
        })

    except Exception:
        current_app.logger.exception("Error fetching students with grades")
        return jsonify({"error": "Failed to load students"}), 500



@admin_bp.route("/api/exam-students-with-grades-all-subjects")
@login_required
def api_exam_students_with_grades_all_subjects():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    exam_id = request.args.get("exam_id", type=int)
    stream = request.args.get("stream", default=None, type=str)

    if not all([branch_id, class_id, exam_id]):
        return jsonify({"error": "Missing required parameters"}), 400

    if stream in ("", "null"):
        stream = None

    try:
        # -------------------- Branch --------------------
        branch = Branch.query.get(branch_id)
        branch_name = branch.branch_name if branch else ""

        # -------------------- Students --------------------
        students_query = Student.query.filter_by(
            branch_id=branch_id,
            class_id=class_id
        )
        if stream:
            students_query = students_query.filter_by(stream=stream)

        students = students_query.all()
        student_ids = [s.id for s in students]

        if not students:
            return jsonify({"students": [], "branch_name": branch_name})

        # -------------------- Subject Allocations --------------------
        allocations = StudentSubjectAllocation.query.filter(
            StudentSubjectAllocation.student_id.in_(student_ids)
        ).all()

        allocations_by_student = {}
        subject_ids = set()

        for a in allocations:
            allocations_by_student.setdefault(a.student_id, []).append(a)
            subject_ids.add(a.subject_id)

        # -------------------- Subjects --------------------
        subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
        subject_map = {s.id: s for s in subjects}

        # -------------------- Exam Papers --------------------
        papers_query = ExamPaper.query.filter_by(
            exam_id=exam_id,
            branch_id=branch_id,
            class_id=class_id
        ).filter(ExamPaper.subject_id.in_(subject_ids))

        if stream:
            papers_query = papers_query.filter_by(stream=stream)
        else:
            papers_query = papers_query.filter(ExamPaper.stream.is_(None))

        papers = papers_query.all()
        paper_map = {(p.subject_id): p for p in papers}

        # -------------------- Marks --------------------
        paper_ids = [p.id for p in papers]

        marks = StudentExamMark.query.filter(
            StudentExamMark.exam_paper_id.in_(paper_ids),
            StudentExamMark.student_id.in_(student_ids)
        ).all()

        marks_map = {(m.student_id, m.exam_paper_id): m for m in marks}

        # -------------------- Lessons & Teachers --------------------
        lessons_query = Lesson.query.filter_by(
            branch_id=branch_id,
            class_id=class_id
        ).filter(Lesson.subject_id.in_(subject_ids))

        if stream:
            lessons_query = lessons_query.filter_by(stream=stream)

        lessons = lessons_query.all()
        lesson_map = {l.subject_id: l for l in lessons}

        teacher_ids = [l.teacher_id for l in lessons if l.teacher_id]
        teachers = Teacher.query.filter(Teacher.id.in_(teacher_ids)).all()
        teacher_map = {t.id: t for t in teachers}

        # -------------------- Build Response --------------------
        students_data = []

        for s in students:
            subjects_data = []

            for alloc in allocations_by_student.get(s.id, []):
                subject = subject_map.get(alloc.subject_id)
                paper = paper_map.get(alloc.subject_id)

                marks_value = None
                grade_info = {
                    "performance_level": None,
                    "points": None,
                    "descriptor": None
                }

                if paper:
                    mark_obj = marks_map.get((s.id, paper.id))

                    if mark_obj is not None:
                        marks_value = mark_obj.marks  # may be 0, and that's OK 

                        resolved = resolve_grade(class_id, marks_value)
                        if resolved:
                            grade_info = resolved


                teacher_initials = ""
                lesson = lesson_map.get(alloc.subject_id)
                if lesson:
                    teacher = teacher_map.get(lesson.teacher_id)
                    if teacher:
                        initials = [n[0] for n in teacher.fullname.split()]
                        teacher_initials = ". ".join(initials).upper() + "."

                subjects_data.append({
                    "teacher": teacher_initials,
                    "code": subject.code if subject else None,
                    "id": alloc.subject_id,
                    "name": subject.name if subject else "",
                    "marks": marks_value,
                    **grade_info
                })

            students_data.append({
                "id": s.id,
                "admission_number": s.admission_number,
                "pathway": s.pathway,
                "assessment_no": s.knec_assessment_no,
                "full_name": s.fullname,
                "subjects": subjects_data,
                "passport": s.passport or "default.JPG"
            })
        return jsonify({
            "students": students_data,
            "branch_name": branch_name, 
        })
    except Exception as e:
        current_app.logger.exception("Error fetching students with all subjects")
        return jsonify({"error": "Failed to load students"}), 500


@admin_bp.route("/api/students-by-subject")
@login_required
def api_students_by_subject():
    """
    Returns students of a selected branch and class who are doing the selected subject,
    including the subject teacher.
    Query params:
        branch_id (int) - required
        class_id (int) - required
        subject_id (int) - required
        stream (str) - optional
    """
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    stream = request.args.get("stream", default=None, type=str)

    if not all([branch_id, class_id, subject_id]):
        return jsonify({"error": "branch_id, class_id, and subject_id are required"}), 400

    try:
        # -------------------- 1. Get students for this class/stream who take the subject --------------------
        students_query = (
            db.session.query(Student)
            .join(StudentSubjectAllocation, Student.id == StudentSubjectAllocation.student_id)
            .filter(
                Student.branch_id == branch_id,
                Student.class_id == class_id,
                StudentSubjectAllocation.subject_id == subject_id
            )
            .order_by(Student.fullname)  # <-- sort alphabetically by fullname
        )

        if stream:
            students_query = students_query.filter(Student.stream == stream)

        students = students_query.all()

        if not students:
            return jsonify({"students": []})

        # Start base query
        lesson_query = Lesson.query.filter_by(
            branch_id=branch_id,
            class_id=class_id,
            subject_id=subject_id
        )

        # Only filter by stream if stream is provided
        if stream:
            lesson_query = lesson_query.filter_by(stream=stream)
        else:
            # Ensure we get rows where stream IS NULL
            lesson_query = lesson_query.filter(Lesson.stream.is_(None))

        lesson = lesson_query.first()
        subject_name = Subject.query.get(subject_id).name if Subject.query.get(subject_id) else "N/A"
        class_name = BranchClasses.query.get(class_id).grade_form if BranchClasses.query.get(class_id) else "N/A"
        branch_name = Branch.query.get(branch_id).branch_name if Branch.query.get(branch_id) else "N/A"
    
        teacher_name = None 
        if lesson and lesson.teacher_id:
            teacher = Teacher.query.get(lesson.teacher_id)
            if teacher:
                teacher_name = f"{teacher.title} {teacher.fullname}" 


        # -------------------- 3. Build response --------------------
        students_data = []
        for s in students:
            students_data.append({
                "admission_number": s.admission_number,
                "full_name": s.fullname.upper(),
                "subject_name": lesson.subject.name if lesson and lesson.subject else "N/A",
                "subject_teacher": teacher_name or "Not assigned",
                "class_name": class_name,
                "stream": stream if stream else "",
                "branch_name": branch_name
            }) 
        return jsonify({"students": students_data})

    except Exception:
        current_app.logger.exception("Error fetching students by subject")
        return jsonify({"error": "Failed to load students"}), 500


@admin_bp.route("/api/students-by-class")
@login_required
def api_students_by_class():
    """
    Returns ALL students of a selected branch and class,
    optionally filtered by stream, including the class teacher.

    Query params:
        branch_id (int) - required
        class_id (int) - required
        stream (str) - optional
    """

    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", default=None, type=str)

    # -------------------- Normalize stream --------------------
    # Handles "", None, "All"
    if not stream or stream == "All":
        stream = None

    if not branch_id or not class_id:
        return jsonify({"error": "branch_id and class_id are required"}), 400

    try:
        # -------------------- 1. Fetch students --------------------
        students_query = (
            db.session.query(Student)
            .filter(
                Student.branch_id == branch_id,
                Student.class_id == class_id
            )
            .order_by(Student.fullname)
        )

        if stream is not None:
            students_query = students_query.filter(Student.stream == stream)

        students = students_query.all()

        if not students:
            return jsonify({"students": []})

        # -------------------- 2. Fetch class teacher --------------------
        class_teacher_query = ClassTeacher.query.filter(
            ClassTeacher.branch_id == branch_id,
            ClassTeacher.class_id == class_id
        )

        if stream is not None:
            # Stream-specific class
            class_teacher_query = class_teacher_query.filter(ClassTeacher.stream == stream)
        else:
            # Non-stream class → handle both NULL and ""
            class_teacher_query = class_teacher_query.filter(
                db.or_(
                    ClassTeacher.stream.is_(None),
                    ClassTeacher.stream == ""
                )
            )

        class_teacher_record = class_teacher_query.first()

        teacher_name = "Not assigned"
        if class_teacher_record and class_teacher_record.teacher:
            teacher = class_teacher_record.teacher
            teacher_name = f"{teacher.title} {teacher.fullname}"

        # -------------------- 3. Fetch metadata --------------------
        class_obj = db.session.get(BranchClasses, class_id)
        branch_obj = db.session.get(Branch, branch_id)

        class_name = class_obj.grade_form if class_obj else "N/A"
        branch_name = branch_obj.branch_name if branch_obj else "N/A"

        # -------------------- 4. Build response --------------------
        students_data = [
            {
                "admission_number": s.admission_number,
                "full_name": s.fullname.upper(),
                "class_teacher": teacher_name,
                "class_name": class_name,
                "stream": stream if stream else "",
                "branch_name": branch_name
            }
            for s in students
        ]

        return jsonify({"students": students_data})

    except Exception:
        current_app.logger.exception("Error fetching students by class")
        return jsonify({"error": "Failed to load students"}), 500



@admin_bp.route("/api/broadsheet")
@login_required
def api_broadsheet():

    branch_id = request.args.get("branch_id", type=int)
    class_id  = request.args.get("class_id", type=int)
    exam_id   = request.args.get("exam_id", type=int)
    stream    = request.args.get("stream", default=None, type=str)

    try:
        data = build_broadsheet_data(branch_id, class_id, exam_id, stream)
        return jsonify(data)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception:
        current_app.logger.exception("Error building broadsheet")
        return jsonify({"error": "Failed to load broadsheet"}), 500
    

from flask import render_template, make_response
from weasyprint import HTML, CSS

@admin_bp.route("/api/broadsheet/pdf")
@login_required
def broadsheet_pdf():

    branch_id = request.args.get("branch_id", type=int)
    class_id  = request.args.get("class_id", type=int)
    exam_id   = request.args.get("exam_id", type=int)
    stream    = request.args.get("stream", default=None, type=str)

    try:
        data = build_broadsheet_data(branch_id, class_id, exam_id, stream)

        # Render HTML template
        html = render_template("academics/full_analysis_broadsheet.html", data=data)

        # Generate PDF
        pdf = HTML(string=html).write_pdf(
            stylesheets=[
                CSS(string="""
                    @page {
                        size: A4 landscape;
                        margin: 10mm;
                    }
                    body {
                        font-family: Arial, sans-serif;
                        font-size: 11px;
                    }
                """)
            ]
        )

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f"inline; filename=broadsheet_{data['class_name']}_{data['exam_name']}.pdf"
        )

        return response

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception:
        current_app.logger.exception("Error generating broadsheet PDF")
        return jsonify({"error": "Failed to generate PDF"}), 500
    



@admin_bp.route("/api/broadsheet/missing-pdf")
@login_required
def broadsheet_missing_pdf():

    branch_id = request.args.get("branch_id", type=int)
    class_id  = request.args.get("class_id", type=int)
    exam_id   = request.args.get("exam_id", type=int)
    stream    = request.args.get("stream", default=None, type=str)

    try:
        data = build_broadsheet_data(branch_id, class_id, exam_id, stream)

        # Extract only missing marks
        missing = data.get("missing_marks", [])

        # Optional: early exit
        if not missing:
            return jsonify({"error": "No missing marks found"}), 404

        html = render_template(
            "academics/missing_marks.html",
            data=data,
            missing=missing
        )

        pdf = HTML(string=html).write_pdf(
            stylesheets=[CSS(string="""
                @page {
                    size: A4 portrait;
                    margin: 12mm;
                }
            """)]
        )

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f"inline; filename=missing_marks_{data['class_name']}.pdf"
        )

        return response

    except Exception:
        current_app.logger.exception("Missing marks PDF error")
        return jsonify({"error": "Failed to generate missing marks PDF"}), 500