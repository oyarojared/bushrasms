from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ....modals.branches_db import Branch
from .. import admin_bp
from ..services.staff_messages import (
    ALL_USERS,
    MessageError,
    can_send_messages,
    class_choices,
    delete_sent_message,
    inbox_for,
    inbox_page,
    is_full_sender,
    open_inbox_item,
    resolve_branch_id,
    send_in_app,
    sent_detail,
    sent_for,
    sent_page,
    teacher_choices,
)
from ..utils.branch_utils import (
    is_system_admin,
    load_branch_choices,
    user_can_select_branch,
)


def _page_number():
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        return 1
    return page if page > 0 else 1


def _selected_branch_id():
    requested = request.values.get("branch_id")
    if str(requested or "") == ALL_USERS and is_system_admin():
        return ALL_USERS
    try:
        return resolve_branch_id(current_user, requested)
    except MessageError:
        return None


def _compose_context(branch_id, draft=None):
    draft = draft or {}
    everyone = branch_id == ALL_USERS
    classes = class_choices(current_user, branch_id) if branch_id and not everyone else []
    teachers = teacher_choices(current_user, branch_id) if branch_id and not everyone else []
    full = is_full_sender(current_user)
    audience = (draft.get("audience") or "").strip()
    if everyone:
        if audience not in ("all", "admins", "super_admins"):
            audience = "all"
    elif not audience:
        audience = "class" if not full else "school"
    branch = None if everyone or not branch_id else Branch.query.get(branch_id)
    return {
        "can_send": can_send_messages(current_user),
        "full_send": full,
        "can_message_everyone": is_system_admin(),
        "message_everyone": everyone,
        "can_select_branch": user_can_select_branch(),
        "branch_choices": load_branch_choices() if user_can_select_branch() else [],
        "selected_branch_id": branch_id,
        "branch_name": "All users, every school" if everyone else (branch.branch_name if branch else ""),
        "class_choices": classes,
        "teacher_choices": teachers,
        "draft": {
            "title": draft.get("title", ""),
            "body": draft.get("body", ""),
            "audience": audience,
            "class_value": draft.get("class_value", ""),
            "teacher_id": draft.get("teacher_id", ""),
        },
    }


@admin_bp.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    if request.method == "POST":
        draft = {
            "title": request.form.get("title", ""),
            "body": request.form.get("body", ""),
            "audience": request.form.get("audience", ""),
            "class_value": request.form.get("class_value", ""),
            "teacher_id": request.form.get("teacher_id", ""),
        }
        try:
            send_in_app(
                current_user,
                branch_id=request.form.get("branch_id"),
                audience=request.form.get("audience"),
                title=draft["title"],
                body=draft["body"],
                teacher_id=request.form.get("teacher_id"),
                class_value=request.form.get("class_value"),
                channel=request.form.get("channel") or "in_app",
            )
        except MessageError as error:
            flash(str(error), "danger")
            if not can_send_messages(current_user):
                return redirect(url_for("admin.messages", tab="inbox"))
            branch_id = _selected_branch_id()
            return render_template(
                "admin_templates/messages.html",
                tab="compose",
                inbox=inbox_for(current_user),
                sent=sent_for(current_user),
                **_compose_context(branch_id, draft),
            )
        flash("Message sent.", "success")
        return redirect(
            url_for(
                "admin.messages",
                tab="compose",
                branch_id=request.form.get("branch_id"),
            )
        )

    allowed = {"inbox"}
    can_send = can_send_messages(current_user)
    if can_send:
        allowed.update({"compose", "sent"})
    tab = request.args.get("tab")
    if not tab and can_send:
        return redirect(url_for("admin.messages", tab="compose"))
    if tab not in allowed:
        tab = "inbox"
    page = _page_number()
    branch_id = _selected_branch_id() if can_send else None
    inbox = inbox_page(current_user, page if tab == "inbox" else 1)
    sent = sent_page(current_user, page if tab == "sent" else 1)
    active = inbox if tab == "inbox" else sent if tab == "sent" else None
    if active is not None and active.pages and page > active.pages:
        return redirect(url_for("admin.messages", tab=tab, page=active.pages))
    return render_template(
        "admin_templates/messages.html",
        tab=tab,
        inbox=inbox,
        sent=sent,
        **_compose_context(branch_id),
    )


@admin_bp.route("/messages/inbox/<int:recipient_id>")
@login_required
def message_inbox_item(recipient_id):
    item = open_inbox_item(current_user, recipient_id)
    if item is None:
        flash("That message is not in your inbox.", "warning")
        return redirect(url_for("admin.messages", tab="inbox"))
    return render_template("admin_templates/message_detail.html", item=item)


@admin_bp.route("/messages/sent/<int:message_id>")
@login_required
def message_sent(message_id):
    message = sent_detail(current_user, message_id)
    if message is None:
        flash("That sent message was not found.", "warning")
        return redirect(url_for("admin.messages", tab="sent"))
    opened = sum(1 for row in message.recipients if row.opened_at)
    return render_template(
        "admin_templates/message_sent.html",
        message=message,
        sent_count=len(message.recipients),
        opened_count=opened,
    )


@admin_bp.route("/messages/sent/<int:message_id>/delete", methods=["POST"])
@login_required
def message_sent_delete(message_id):
    if delete_sent_message(current_user, message_id):
        flash("Message deleted.", "success")
    else:
        flash("That sent message was not found.", "warning")
    return redirect(url_for("admin.messages", tab="sent"))
