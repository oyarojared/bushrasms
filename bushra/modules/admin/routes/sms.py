"""SMS messages for parents and teachers."""

from functools import wraps

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ....modals.branches_db import Branch, BranchClasses
from ....modals.sms_db import SmsMessage, SmsTemplate
from ....modals.students_db import Student
from .. import admin_bp
from ..services.grades import filter_active_classes, live_class_name, sort_grade_records
from ..services.sms import (
    PURPOSE_LABELS,
    add_credits,
    build_audience,
    can_access_sms,
    class_streams,
    display_phone,
    get_or_create_settings,
    MAX_SMS_PARTS,
    provider_configured,
    resend_failed,
    send_message,
    status_label,
)
from ..utils.branch_utils import locked_branch_id, user_can_access_branch
from ..utils.class_teacher import (
    get_assignment_for_teacher,
    list_class_teacher_assignments,
    teacher_owns_student,
)
from ..utils.route_protect import admin_required


def sms_user_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not can_access_sms(current_user):
            flash("SMS is for school admins and class teachers.", "warning")
            return redirect(url_for("admin.teacher_dash"))
        return view(*args, **kwargs)

    return wrapped


def _sms_branch_id(requested=None):
    locked = locked_branch_id()
    if locked:
        return locked
    if requested:
        try:
            branch_id = int(requested)
        except (TypeError, ValueError):
            return None
        if user_can_access_branch(branch_id):
            return branch_id
        return None
    if current_user.is_super_admin:
        return None
    return current_user.branch_id


def _teacher_may_send(settings):
    if current_user.is_admin:
        return True
    return bool(settings and settings.allow_class_teachers)


def _assignment_or_404(assignment_id):
    assignment = get_assignment_for_teacher(current_user, assignment_id)
    if not assignment:
        abort(404)
    return assignment


def _compose_context(branch_id, assignment=None):
    settings = get_or_create_settings(branch_id) if branch_id else None
    templates = []
    classes = []
    if branch_id:
        templates = (
            SmsTemplate.query.filter_by(branch_id=branch_id)
            .order_by(SmsTemplate.for_teachers.asc(), SmsTemplate.name.asc())
            .all()
        )
        class_rows = filter_active_classes(
            BranchClasses.query.filter_by(branch_id=branch_id).all()
        )
        classes = sort_grade_records(
            [
                {
                    "id": row.id,
                    "grade_form": live_class_name(row.grade_form),
                    "streams": class_streams(row),
                }
                for row in class_rows
            ]
        )
    assignments = []
    if not current_user.is_admin:
        assignments = [
            {
                "id": row.id,
                "label": f"{live_class_name(row.class_.grade_form) if row.class_ else 'Class'} {(row.stream or '').strip()}".strip(),
                "branch_id": row.branch_id,
                "class_id": row.class_id,
                "stream": (row.stream or "").strip(),
            }
            for row in list_class_teacher_assignments(current_user)
        ]
    return {
        "settings": settings,
        "templates": templates,
        "classes": classes,
        "assignments": assignments,
        "assignment": assignment,
        "purpose_labels": PURPOSE_LABELS,
        "provider_ready": provider_configured(),
        "max_parts": MAX_SMS_PARTS,
        "can_send": _teacher_may_send(settings) if settings else False,
        "can_manage": bool(current_user.is_admin),
        "is_admin": bool(current_user.is_admin),
    }


@admin_bp.route("/messages")
@login_required
@sms_user_required
def messages():
    branch_id = _sms_branch_id(request.args.get("branch_id"))
    if current_user.is_super_admin and not branch_id:
        from ..utils.branch_utils import get_accessible_branches_query

        schools = get_accessible_branches_query().order_by(Branch.branch_name.asc()).all()
        return render_template(
            "admin_templates/messages.html",
            messages=[],
            settings=None,
            provider_ready=provider_configured(),
            schools=schools,
            branch=None,
            can_manage=True,
            can_send=False,
            status_label=status_label,
        )

    if not branch_id or not user_can_access_branch(branch_id):
        flash("Choose a school first.", "warning")
        return redirect(url_for("admin.admin_dash" if current_user.is_admin else "admin.teacher_dash"))

    settings = get_or_create_settings(branch_id)
    query = SmsMessage.query.filter_by(branch_id=branch_id).order_by(
        SmsMessage.created_at.desc()
    )
    if not current_user.is_admin:
        query = query.filter_by(sender_id=current_user.id)
    rows = query.limit(80).all()
    return render_template(
        "admin_templates/messages.html",
        messages=rows,
        settings=settings,
        provider_ready=provider_configured(),
        schools=None,
        branch=Branch.query.get(branch_id),
        can_manage=bool(current_user.is_admin),
        can_send=_teacher_may_send(settings),
        status_label=status_label,
        display_phone=display_phone,
    )


@admin_bp.route("/messages/compose")
@login_required
@sms_user_required
def sms_compose():
    assignment = None
    assignment_id = request.args.get("assignment", type=int)
    if assignment_id and not current_user.is_admin:
        assignment = _assignment_or_404(assignment_id)

    student_id = request.args.get("student_id", type=int)
    student = Student.query.get(student_id) if student_id else None
    if student and not current_user.is_admin and not teacher_owns_student(current_user, student):
        flash("That learner is not in your class.", "warning")
        return redirect(url_for("admin.my_class"))

    if not current_user.is_admin and not assignment and not student:
        rows = list_class_teacher_assignments(current_user)
        assignment = rows[0] if rows else None

    branch_id = None
    if assignment:
        branch_id = assignment.branch_id
    elif student:
        branch_id = student.branch_id
    else:
        branch_id = _sms_branch_id(request.args.get("branch_id"))

    if not branch_id or not user_can_access_branch(branch_id):
        flash("Choose a school first.", "warning")
        return redirect(url_for("admin.messages"))

    settings = get_or_create_settings(branch_id)
    if not _teacher_may_send(settings):
        flash("Your school admin has not allowed class teachers to send SMS yet.", "warning")
        return redirect(url_for("admin.messages"))

    audience = request.args.get("audience")
    if not audience:
        if student:
            audience = "parent_one"
        elif assignment or not current_user.is_admin:
            audience = "parents_class"
        else:
            audience = ""
    if audience in ("parents_school", "teachers") and not current_user.is_admin:
        audience = "parents_class"

    context = _compose_context(branch_id, assignment)
    default_class_id = request.args.get("class_id", type=int)
    default_stream = (request.args.get("stream") or "").strip()
    if assignment:
        default_class_id = assignment.class_id
        default_stream = (assignment.stream or "").strip()
    elif student:
        default_class_id = student.class_id
        default_stream = (student.stream or "").strip()

    return render_template(
        "admin_templates/sms_compose.html",
        branch=Branch.query.get(branch_id),
        audience=audience,
        purpose=request.args.get("purpose") or "",
        student=student,
        default_class_id=default_class_id,
        default_stream=default_stream,
        **context,
    )


@admin_bp.route("/messages/settings", methods=["GET", "POST"])
@login_required
@admin_required
def sms_settings():
    branch_id = _sms_branch_id(request.form.get("branch_id") or request.args.get("branch_id"))
    if not branch_id or not user_can_access_branch(branch_id):
        flash("Choose a school first.", "warning")
        return redirect(url_for("admin.messages"))

    settings = get_or_create_settings(branch_id)
    if request.method == "POST":
        action = request.form.get("action") or "save"
        if action == "credits":
            try:
                amount = int(request.form.get("credit_amount") or 0)
                add_credits(branch_id, amount)
                flash("SMS credit updated.", "success")
            except (TypeError, ValueError) as error:
                flash(str(error), "warning")
            return redirect(url_for("admin.sms_settings", branch_id=branch_id))

        sender = (request.form.get("sender_name") or "").strip().replace(" ", "")
        if sender and (len(sender) > 11 or not sender.isalnum()):
            flash("Sender name must be at most 11 letters or numbers, no spaces.", "warning")
            return redirect(url_for("admin.sms_settings", branch_id=branch_id))
        settings.sender_name = sender or None
        settings.allow_class_teachers = request.form.get("allow_class_teachers") == "1"
        settings.enabled = request.form.get("enabled") == "1"
        from ....modals import db

        db.session.commit()
        flash("SMS settings saved.", "success")
        return redirect(url_for("admin.sms_settings", branch_id=branch_id))

    return render_template(
        "admin_templates/sms_settings.html",
        settings=settings,
        branch=Branch.query.get(branch_id),
        provider_ready=provider_configured(),
    )


@admin_bp.route("/messages/<int:message_id>")
@login_required
@sms_user_required
def sms_detail(message_id):
    message = SmsMessage.query.get_or_404(message_id)
    if not user_can_access_branch(message.branch_id):
        abort(403)
    if not current_user.is_admin and message.sender_id != current_user.id:
        abort(403)
    return render_template(
        "admin_templates/sms_detail.html",
        message=message,
        status_label=status_label,
        display_phone=display_phone,
        purpose_labels=PURPOSE_LABELS,
        can_manage=bool(current_user.is_admin),
        provider_ready=provider_configured(),
    )


@admin_bp.route("/messages/<int:message_id>/resend", methods=["POST"])
@login_required
@sms_user_required
def sms_resend(message_id):
    message = SmsMessage.query.get_or_404(message_id)
    if not user_can_access_branch(message.branch_id):
        abort(403)
    if not current_user.is_admin and message.sender_id != current_user.id:
        abort(403)
    try:
        resend_failed(message, sender=current_user)
        flash("Failed numbers were retried.", "success")
    except ValueError as error:
        flash(str(error), "warning")
    return redirect(url_for("admin.sms_detail", message_id=message.id))


@admin_bp.route("/api/sms/audience")
@login_required
@sms_user_required
def sms_audience_api():
    payload, error, status = _audience_payload()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@admin_bp.route("/api/sms/send", methods=["POST"])
@login_required
@sms_user_required
def sms_send_api():
    data = request.get_json() or {}
    branch_id = _sms_branch_id(data.get("branch_id"))
    if not branch_id or not user_can_access_branch(branch_id):
        return jsonify({"error": "Choose a school first."}), 400
    settings = get_or_create_settings(branch_id)
    if not _teacher_may_send(settings):
        return jsonify({"error": "Class teachers cannot send SMS at this school."}), 403

    audience_type = (data.get("audience_type") or "").strip()
    class_id = data.get("class_id")
    stream = data.get("stream")
    student_id = data.get("student_id")
    assignment_id = data.get("assignment_id")

    if not current_user.is_admin:
        if audience_type in ("parents_school", "teachers"):
            return jsonify({"error": "You can only message parents in your class."}), 403
        assignment = get_assignment_for_teacher(current_user, assignment_id) if assignment_id else None
        if audience_type == "parents_class":
            if not assignment:
                return jsonify({"error": "Choose your class."}), 400
            class_id = assignment.class_id
            stream = assignment.stream
            branch_id = assignment.branch_id
        if audience_type == "parent_one":
            student = Student.query.get(student_id)
            if not student or not teacher_owns_student(current_user, student):
                return jsonify({"error": "That learner is not in your class."}), 403
            branch_id = student.branch_id

    try:
        class_id = int(class_id) if class_id else None
        student_id = int(student_id) if student_id else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid class or learner."}), 400

    try:
        message = send_message(
            branch_id=branch_id,
            sender=current_user,
            audience_type=audience_type,
            body=data.get("body") or "",
            purpose=data.get("purpose") or "custom",
            class_id=class_id,
            stream=stream,
            student_id=student_id,
            exclude_keys=data.get("exclude_keys") or [],
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "ok": True,
            "message_id": message.id,
            "status": message.status,
            "redirect": url_for("admin.sms_detail", message_id=message.id),
        }
    )


def _audience_payload(data=None):
    data = data or request.args
    assignment_id = data.get("assignment_id")
    assignment = None
    if assignment_id and not current_user.is_admin:
        try:
            assignment_id = int(assignment_id)
        except (TypeError, ValueError):
            assignment_id = None
        assignment = get_assignment_for_teacher(current_user, assignment_id)
        if not assignment:
            return None, "Choose your class.", 400

    student_id = data.get("student_id")
    audience_type = (data.get("audience_type") or data.get("audience") or "").strip()
    branch_id = _sms_branch_id(data.get("branch_id"))
    class_id = data.get("class_id")
    stream = data.get("stream")

    if assignment:
        branch_id = assignment.branch_id
        class_id = assignment.class_id
        stream = assignment.stream
        if audience_type in ("parents_school", "teachers"):
            return None, "You can only message parents in your class.", 403

    if student_id and audience_type == "parent_one":
        try:
            student = Student.query.get(int(student_id))
        except (TypeError, ValueError):
            student = None
        if not student:
            return None, "Learner not found.", 404
        if not current_user.is_admin and not teacher_owns_student(current_user, student):
            return None, "That learner is not in your class.", 403
        branch_id = student.branch_id

    if not branch_id or not user_can_access_branch(branch_id):
        return None, "Choose a school first.", 400
    if not current_user.is_admin and audience_type in ("parents_school", "teachers"):
        return None, "You can only message parents in your class.", 403

    try:
        class_id = int(class_id) if class_id else None
        student_id = int(student_id) if student_id else None
    except (TypeError, ValueError):
        return None, "Invalid class or learner.", 400

    try:
        audience = build_audience(
            branch_id,
            audience_type,
            class_id=class_id,
            stream=stream,
            student_id=student_id,
        )
    except ValueError as error:
        return None, str(error), 400

    public = []
    for row in audience["recipients"]:
        public.append(
            {
                "key": row["key"],
                "display_name": row["display_name"],
                "detail": row.get("detail"),
                "phone": display_phone(row.get("phone")),
                "phone_raw": row.get("phone_raw"),
                "status": row["status"],
                "skip_reason": row.get("skip_reason"),
                "fields": row.get("fields") or {},
            }
        )
    ready = sum(1 for row in public if row["status"] == "ready")
    skipped = len(public) - ready
    return (
        {
            "label": audience["label"],
            "branch_id": branch_id,
            "ready": ready,
            "skipped": skipped,
            "total": len(public),
            "recipients": public,
        },
        None,
        200,
    )
