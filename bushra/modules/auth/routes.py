from flask import Blueprint, flash, redirect, render_template, session, url_for, request
from werkzeug.security import check_password_hash

from ...modals.staff_db import Teacher
from ..admin.forms.students_forms import PassportUploadForm
from .forms import LoginForm
from flask_login import current_user, login_user, logout_user, login_required

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    template_folder="templates",
    static_folder="static",
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Prevent logged-in users from seeing login page again
    if current_user.is_authenticated:
        return redirect(url_for("admin.assessment_dash"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data.strip()

        user = Teacher.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password", "danger")
        else:
            # Replace manual session handling with Flask-Login
            login_user(user, remember=form.remember_me.data)

            # Redirect to the page user wanted or dashboard
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin.admin_dash"))

    return render_template("login.html", form=form)



@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))