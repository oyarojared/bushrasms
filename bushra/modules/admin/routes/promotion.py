from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from .. import admin_bp
from ..forms.students_forms import PromotionForm
from ..services.promotion import (
    PromotionError,
    apply_promotion,
    build_plan,
    describe_promotion,
)
from ..utils import (
    accessible_branch_ids,
    apply_locked_branch,
    load_branch_choices,
    user_can_access_branch,
    user_can_select_branch,
)
from ..utils.route_protect import admin_required


def _repeat_ids():
    chosen = []
    for raw in request.form.getlist("repeat_ids"):
        try:
            chosen.append(int(raw))
        except (TypeError, ValueError):
            continue
    return chosen


def _continue_to():
    chosen = {}
    prefix = "continue_branch_"
    for key, value in request.form.items():
        if not key.startswith(prefix) or value in ("", None):
            continue
        try:
            chosen[int(key[len(prefix):])] = int(value)
        except (TypeError, ValueError):
            continue
    return chosen


def _promotion_form():
    form = PromotionForm()
    choices = []
    for value, label in load_branch_choices():
        if value in ("", None):
            choices.append(("", label))
        else:
            choices.append((int(value), label))
    form.branch_id.choices = choices
    locked = None
    for value, _label in choices:
        if value != "":
            locked = value
            break
    apply_locked_branch(form.branch_id)
    if form.branch_id.data not in ("", None):
        form.branch_id.data = int(form.branch_id.data)
    elif locked is not None and len(choices) == 1:
        form.branch_id.data = locked
    return form


@admin_bp.route("/promote", methods=["GET", "POST"])
@login_required
@admin_required
def promote_students():
    form = _promotion_form()
    plan = None

    if form.validate_on_submit():
        branch_id = form.branch_id.data
        if not user_can_access_branch(branch_id):
            flash("You cannot promote learners in that school.", "warning")
            return render_template(
                "student_templates/promotion.html",
                promotion_form=form,
                plan=None,
                can_select_branch=user_can_select_branch(),
            )

        action = request.form.get("action") or "preview"
        continue_to = _continue_to()
        allowed_branch_ids = accessible_branch_ids()
        try:
            if action == "apply":
                plan = apply_promotion(
                    branch_id,
                    form.from_year.data,
                    int(form.from_year.data) + 1,
                    repeat_ids=_repeat_ids(),
                    continue_to=continue_to,
                    allowed_branch_ids=allowed_branch_ids,
                )
                flash(describe_promotion(plan), "success")
                return redirect(url_for("admin.promote_students"))

            plan = build_plan(
                branch_id,
                form.from_year.data,
                int(form.from_year.data) + 1,
                repeat_ids=_repeat_ids(),
                continue_to=continue_to,
                allowed_branch_ids=allowed_branch_ids,
            )
        except PromotionError as error:
            flash(str(error), "warning")

    return render_template(
        "student_templates/promotion.html",
        promotion_form=form,
        plan=plan,
        can_select_branch=user_can_select_branch(),
    )
