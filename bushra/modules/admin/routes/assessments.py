from .. import admin_bp
from flask import render_template, flash, redirect, url_for, jsonify, request, current_app
from ..forms.assessment_forms import ExamCreateForm, ExamDeadlineForm
from ....modals.branches_db import Branch, BranchClasses 
from ....modals.assessment_db import GradingSystem, GradingScheme, GradeGradingScheme, GradingBoundary
from ....modals.assessment_db import Exam, ExamBranch, ExamPaper, db
from ....modals.students_db import Student
from ...admin.utils.exam_deadlines import (
    clear_deadline,
    deadline_payload,
    set_deadline,
)
from ...admin.services.report import get_report_card_data
from ...admin.services.assessment_services import (
    branch_has_locked_exams,
    get_exams_for_user,
)

from flask import Blueprint, request, make_response, render_template 
from flask import current_app, jsonify, send_file
from flask_login import login_required, current_user
from ...admin.utils.route_protect import admin_required

from ..services.grades import filter_active_classes, live_class_name
from ..services.grading_844 import generate_class_reports, normalize_form_name
from ..services.pdf_jobs import (
    advance_class_pdf_job,
    create_job,
    pdf_path,
    read_job,
)
from ..services.report_pdf import (
    build_report_bundle,
    pdf_http_headers,
    render_bundle_pdf,
)

from datetime import datetime
from urllib.parse import quote
import traceback
from sqlalchemy.orm import joinedload

from flask import render_template, make_response
import weasyprint

from ..utils import get_accessible_branches_query, user_can_access_branch

DEVELOPER_ID = 11


@admin_bp.route("assessments/dash", methods=["GET", "POST"])
@login_required
def assessment_dash():
    exam_form = ExamCreateForm()

    query = get_exams_for_user(current_user)
    exams_list = query.all()

    # Branch choices
    if current_user.is_super_admin:
        branches = (
            get_accessible_branches_query()
            .order_by(Branch.branch_name)
            .all()
        ) 
        exam_form.branch_id.choices = [(b.id, b.branch_name) for b in branches]
    else:
        branch = Branch.query.get(current_user.branch_id)
        if branch:
            exam_form.branch_id.choices = [(branch.id, branch.branch_name)]
        else:
            exam_form.branch_id.choices = []

    exam_form.year.choices = [
        (str(y), str(y)) for y in list(range(2026, 2036))
    ]

    if exam_form.validate_on_submit():

        # Selected branch
        selected_branch_id = exam_form.branch_id.data

        # --- DUPLICATE CHECK ---
        exists = (
            db.session.query(Exam.id)
            .join(ExamBranch)
            .filter(
                Exam.name == exam_form.name.data.strip(),
                Exam.year == int(exam_form.year.data),
                Exam.term == exam_form.term.data,
                ExamBranch.branch_id == selected_branch_id
            )
            .first()
        )

        if exists:
            flash(
                "An exam with the same name, year, term, and branch already exists.",
                "danger",
            )
            return redirect(url_for("admin.assessment_dash"))

        # --- CREATE EXAM ---
        exam = Exam(
            name=exam_form.name.data.strip(),
            year=int(exam_form.year.data),
            term=exam_form.term.data,
            is_locked=False,
        )
        db.session.add(exam)
        db.session.flush()  # get exam.id

        # Assign to selected branch
        db.session.add(
            ExamBranch(
                exam_id=exam.id,
                branch_id=selected_branch_id
            )
        )

        db.session.commit()
        if exam_form.marks_due_at.data:
            set_deadline(exam.id, exam_form.marks_due_at.data)
        flash("Exam created successfully.", "success")
        return redirect(url_for("admin.assessment_dash"))
    
    # Display grades based on the current user's branch
    if current_user.is_admin:
        if current_user.id == DEVELOPER_ID:
            grades = filter_active_classes(BranchClasses.query.all())
        else:
            grades = filter_active_classes(
                BranchClasses.query.filter_by(
                    branch_id=current_user.branch_id
                ).all()
            )
    else:
        grades = []
                
    exam_deadlines = {exam.id: deadline_payload(exam) for exam in exams_list}
    deadline_form = ExamDeadlineForm()
    has_locked_exams = (
        not current_user.is_admin
        and not exams_list
        and branch_has_locked_exams(current_user)
    )

    return render_template(
        "academics/assessment_dash.html",
        exam_form=exam_form,
        exams_list=exams_list,
        grades=grades,
        exam_deadlines=exam_deadlines,
        deadline_form=deadline_form,
        has_locked_exams=has_locked_exams,
    )


@admin_bp.route("/exams/<int:exam_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_exam(exam_id):
    exam = Exam.query.get(exam_id)

    if not exam:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.assessment_dash"))
    
    if not current_user.is_admin:
        flash("You have no admin rights to delete exams!", "warning")
        return redirect(url_for("admin.assessment_dash"))

    # 🔒 FUTURE-SAFE CHECK: Prevent deletion if marks exist
    if hasattr(exam, "marks") and exam.marks:
         flash(
            "This exam already has marks and cannot be deleted.",
            "warning"
        )
         return redirect(url_for("admin.assessment_dash"))
    
    if exam.is_locked:
        flash(
            "Locked exams cannot be deleted. Unlock the exam first.",
            "warning"
        )
        return redirect(url_for("admin.assessment_dash"))

    try:
        # Soft delete i.e make exam inactive
        exam.is_inactive = True
        db.session.commit()
        clear_deadline(exam_id)

        flash("Exam deleted successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(
            "An error occurred while deleting the exam.",
            "danger"
        )

    return redirect(url_for("admin.assessment_dash"))


@admin_bp.route("/exams/<int:exam_id>/lock", methods=["POST"])
@admin_required
@login_required
def lock_exam(exam_id):
    exam = Exam.query.get(exam_id)

    if not exam:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.exams"))

    if exam.is_locked:
        flash("This exam is already locked.", "info")
        return redirect(url_for("admin.exams"))

    try:
        exam.is_locked = True
        db.session.commit()

        flash("Exam locked successfully. Marks entry is now closed.", "success")

    except Exception:
        db.session.rollback()
        flash("Failed to lock the exam. Please try again.", "danger")

    return redirect(url_for("admin.assessment_dash"))


@admin_bp.route("/exams/<int:exam_id>/unlock", methods=["POST"]) 
@admin_required
@login_required
def unlock_exam(exam_id):
    exam = Exam.query.get(exam_id)

    if not exam:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.assessment_dash"))

    if not exam.is_locked:
        flash("This exam is already open.", "info")
        return redirect(url_for("admin.assessment_dash"))

    # 🔮 Future-proof rule (no results published)
    if hasattr(exam, "results_published") and exam.results_published:
        flash(
            "Published exams cannot be unlocked.",
            "warning"
        )
        return redirect(url_for("admin.assessment_dash"))

    try:
        exam.is_locked = False
        db.session.commit()

        flash("Exam unlocked. Marks entry is now open.", "success")

    except Exception:
        db.session.rollback()
        flash("Failed to unlock the exam. Please try again.", "danger")

    return redirect(url_for("admin.assessment_dash"))


def _admin_can_manage_exam(exam):
    if not exam or not current_user.is_authenticated or not current_user.is_admin:
        return False
    if current_user.is_super_admin:
        return True
    return any(user_can_access_branch(eb.branch_id) for eb in exam.exam_branches)


@admin_bp.route("/exams/<int:exam_id>/deadline", methods=["POST"])
@login_required
@admin_required
def set_exam_deadline(exam_id):
    exam = Exam.query.get(exam_id)
    if not exam or exam.is_inactive:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.assessment_dash"))
    if not _admin_can_manage_exam(exam):
        flash("You cannot set a marks entry deadline for this exam.", "warning")
        return redirect(url_for("admin.assessment_dash"))

    form = ExamDeadlineForm()
    if not (form.exam_id.data or "").strip():
        form.exam_id.data = str(exam_id)

    clearing = bool(form.clear.data)
    if not form.validate():
        other_errors = {
            name: messages
            for name, messages in form.errors.items()
            if not (clearing and name == "marks_due_at")
        }
        if other_errors:
            flash("Could not save the marks entry deadline. Check the date and time.", "danger")
            return redirect(url_for("admin.assessment_dash"))

    if str(form.exam_id.data) != str(exam_id):
        flash("That deadline did not match the exam.", "danger")
        return redirect(url_for("admin.assessment_dash"))

    if clearing or not form.marks_due_at.data:
        clear_deadline(exam_id)
        flash("Teachers' marks entry deadline removed.", "success")
    else:
        set_deadline(exam_id, form.marks_due_at.data)
        flash("Teachers' marks entry deadline saved.", "success")

    return redirect(url_for("admin.assessment_dash"))


@admin_bp.route("/exams/<int:exam_id>/marks", methods=["GET"])
@login_required
def marks_entry(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if exam.is_locked:
        flash(
            "This exam is locked. Marks entry is not allowed.",
            "warning"
        )
        return redirect(url_for("admin.assessment_dash"))

    marks_deadline = deadline_payload(exam)
    return render_template(
        "academics/marks_entry.html",
        exam=exam,
        marks_deadline=marks_deadline,
        marks_entry_closed=marks_deadline["is_closed"],
    )


def _as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    if value is None:
        return default
    return bool(value)


def _cbe_report_print_options(payload, is_844):
    """CBE-only print switches. 8-4-4 always prints ranking and never an opening date."""
    if is_844:
        return True, None

    include_ranking = _as_bool(payload.get("include_ranking"), default=True)
    opening_date = None
    if _as_bool(payload.get("include_opening_date"), default=False):
        raw = payload.get("opening_date")
        raw = raw.strip() if isinstance(raw, str) else ""
        if raw:
            try:
                opening_date = datetime.strptime(raw, "%Y-%m-%d").strftime("%d %B %Y")
            except ValueError:
                opening_date = None
    return include_ranking, opening_date


@admin_bp.route("/generate-reportcards-pdf", methods=["POST"])
@login_required
@admin_required
def generate_reportcards_pdf():
    data = request.get_json() or {}

    branch_id = data.get("branch_id")
    class_id = data.get("class_id")
    exam_id = data.get("exam_id")
    stream = data.get("stream", None)
    student_id = data.get("student_id", None)

    if not branch_id or not class_id or not exam_id:
        return {"error": "branch_id, class_id, and exam_id are required"}, 400

    try:
        branch_id = int(branch_id)
        class_id = int(class_id)
        exam_id = int(exam_id)
        if student_id:
            student_id = int(student_id)
    except (TypeError, ValueError):
        return {"error": "Invalid report request."}, 400

    if not user_can_access_branch(branch_id):
        return {"error": "You cannot generate reports for that school."}, 403

    try:
        if student_id:
            class_obj = BranchClasses.query.get_or_404(class_id)
            normalized_form = normalize_form_name(live_class_name(class_obj.grade_form))
            is_844 = normalized_form in ("Form 3", "Form 4", "IGCSE")
            include_ranking, opening_date = _cbe_report_print_options(data, is_844)
            bundle = build_report_bundle(
                branch_id=branch_id,
                class_id=class_id,
                exam_id=exam_id,
                stream=stream,
                student_id=student_id,
                include_ranking=include_ranking,
                opening_date=opening_date,
            )
            pdf = render_bundle_pdf(bundle, lite=False)
            response = make_response(pdf)
            for header, value in pdf_http_headers(bundle["filename"]).items():
                response.headers[header] = value
            response.headers["Content-Length"] = str(len(pdf))
            return response

        class_obj = BranchClasses.query.get_or_404(class_id)
        normalized_form = normalize_form_name(live_class_name(class_obj.grade_form))
        is_844 = normalized_form in ("Form 3", "Form 4", "IGCSE")
        include_ranking, opening_date = _cbe_report_print_options(data, is_844)
        filename = (
            f"{class_obj.grade_form} {stream}_Assessment_Reports.pdf"
            if stream
            else f"{class_obj.grade_form}_Assessment_Reports.pdf"
        )
        job_id = create_job(
            current_user.id,
            filename,
            {
                "branch_id": branch_id,
                "class_id": class_id,
                "exam_id": exam_id,
                "stream": stream,
                "student_id": None,
                "include_ranking": include_ranking,
                "opening_date": opening_date,
            },
        )
        return jsonify({"job_id": job_id, "status": "queued"}), 202
    except Exception as e:
        current_app.logger.exception("Failed to start report-card PDF")
        traceback.print_exc()
        return {
            "error": "Failed to generate PDF! Make sure you have configured grading first!",
            "details": str(e),
        }, 500


@admin_bp.route("/reportcards-pdf-status/<job_id>")
@login_required
@admin_required
def reportcards_pdf_status(job_id):
    meta = read_job(job_id)
    if not meta or meta.get("user_id") != current_user.id:
        return jsonify({"error": "Report job not found."}), 404
    if meta.get("status") not in ("ready", "error"):
        meta = advance_class_pdf_job(job_id) or meta
    return jsonify(
        {
            "status": meta.get("status"),
            "done": meta.get("done") or 0,
            "total": meta.get("total") or 0,
            "message": meta.get("message") or "",
            "error": meta.get("error"),
            "filename": meta.get("filename"),
        }
    )


@admin_bp.route("/reportcards-pdf-download/<job_id>")
@login_required
@admin_required
def reportcards_pdf_download(job_id):
    meta = read_job(job_id)
    if not meta or meta.get("user_id") != current_user.id:
        return jsonify({"error": "Report job not found."}), 404
    if meta.get("status") != "ready":
        return jsonify({"error": "The PDF is not ready yet."}), 409
    path = pdf_path(job_id)
    if not path.exists():
        return jsonify({"error": "The PDF file is missing. Please generate it again."}), 404
    filename = meta.get("filename") or "Assessment_Reports.pdf"
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )



@admin_bp.route("/save_grading_config", methods=["POST"])
@login_required
@admin_required
def save_grading_config():
    data = request.get_json()

    system_name = data.get("system")
    boundaries = data.get("boundaries")
    selected_classes = data.get("selected_classes")  # still class IDs

    if not all([system_name, boundaries, selected_classes]):
        return jsonify({"error": "Missing required data"}), 400

    valid_boundaries = []
    for boundary in boundaries:
        performance_level = (boundary.get("performance_level") or "").strip()
        min_score = boundary.get("min_score")
        max_score = boundary.get("max_score")

        if performance_level == "" or min_score is None or max_score is None:
            continue

        try:
            min_score = int(min_score)
            max_score = int(max_score)
        except (TypeError, ValueError):
            continue

        valid_boundaries.append({
            **boundary,
            "min_score": min_score,
            "max_score": max_score,
            "performance_level": performance_level,
        })

    if not valid_boundaries:
        return jsonify({
            "error": "At least one complete grading boundary is required."
        }), 400

    boundaries = valid_boundaries

    try:
        # 1️⃣ Resolve or create grading system
        system = GradingSystem.query.filter_by(name=system_name).first()
        if not system:
            system = GradingSystem(
                name=system_name,
                created_at=datetime.utcnow()
            )
            db.session.add(system)
            db.session.flush()

        # 2️⃣ Determine grade_form names from selected class IDs
        grade_forms = (
            BranchClasses.query
            .filter(BranchClasses.id.in_(selected_classes))
            .with_entities(BranchClasses.grade_form)
            .distinct()
            .all()
        )
        # Extract grade_form strings from tuples
        grade_forms = [gf[0] for gf in grade_forms]

        # 3️⃣ Apply boundaries to matching classes
        for grade_form in grade_forms:

            query = BranchClasses.query.filter_by(grade_form=grade_form)

            # Branch 11 can manage all branches
            if current_user.id != DEVELOPER_ID:
                query = query.filter_by(branch_id=current_user.branch_id)

            classes = query.all()

            for cls in classes:
                grade_id = cls.id

                # Delete old mappings and boundaries for this class
                old_mappings = GradeGradingScheme.query.filter_by(
                    grade_id=grade_id
                ).all()

                for m in old_mappings:
                    GradingBoundary.query.filter_by(
                        scheme_id=m.scheme_id
                    ).delete()
                    db.session.delete(m)

                db.session.flush()

                # Create new scheme
                scheme = GradingScheme(
                    system_id=system.id,
                    name=f"{system_name} Scheme {datetime.utcnow().year}",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(scheme)
                db.session.flush()

                # Link scheme to class
                mapping = GradeGradingScheme(
                    grade_id=grade_id,
                    scheme_id=scheme.id
                )
                db.session.add(mapping)
                db.session.flush()

                # Insert new boundaries
                for b in boundaries:
                    try:
                        boundary = GradingBoundary(
                            scheme_id=scheme.id,
                            min_score=int(b.get("min_score", 0)),
                            max_score=int(b.get("max_score", 100)),
                            performance_level=b.get("performance_level"),
                            points=int(b["points"]) if b.get("points") else None,
                            descriptor=b.get("descriptor")
                        )
                        db.session.add(boundary)
                    except (ValueError, TypeError):
                        continue

        # 4️⃣ Commit all changes
        db.session.commit()
        return jsonify({"success": True})

    except Exception:
        db.session.rollback()
        current_app.logger.error("Saving grading config failed", exc_info=True)
        return jsonify({"error": "Failed to save grading configuration"}), 500





@admin_bp.route("/api/class-reports", methods=["GET"])
def class_reports_api():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", type=str)
    exam_id = request.args.get("exam_id", type=int)

    if not all([branch_id, class_id, exam_id]):
        return jsonify({"error": "Missing required parameters"}), 400

    # Generate reports
    reports = generate_class_reports(branch_id, class_id, stream, exam_id)

    # Only send essential info for PDF
    for r in reports:
        r.pop("subjects")  # remove subject-level details if unnecessary

    return jsonify(reports)

@admin_bp.route("/api/class-reports/pdf", methods=["GET"])
def class_reports_pdf():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", type=str)
    exam_id = request.args.get("exam_id", type=int)

    if not all([branch_id, class_id, exam_id]):
        return "Missing parameters", 400

    # Generate reports
    reports = generate_class_reports(branch_id, class_id, stream, exam_id)

    # Only keep essential info
    for r in reports:
        r.pop("subjects", None)
 
    # Render HTML template
    html = render_template("academics/class_ranking.html", reports=reports)
    pdf = weasyprint.HTML(string=html).write_pdf()

    # Send PDF response
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=Class_Ranking_{class_id}_{exam_id}.pdf"
    return response

