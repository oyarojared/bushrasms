from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (HiddenField, IntegerField, PasswordField, SelectField,
                     StringField, SubmitField)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class AddTeacherForm(FlaskForm):
    
    teacher_id = HiddenField()

    employer = SelectField(
        "Employer",
        choices=[("", "---Select---"), ("TSC", "TSC"), ("BOM", "BOM")],
        validators=[DataRequired(message="Employer is required.")],
    )

    branches = SelectField(
        "branches", choices=[], validators=[DataRequired(message="Select Branch!")]
    )

    fullname = StringField(
        "Full Name",
        validators=[
            Length(min=6, max=30),
            DataRequired(message="Full name is required.")
        ],
        render_kw={"placeholder": "Fullname"},
    )

    gender = SelectField(
        "Gender",
        choices=[("", "--- Select ---"), ("M", "Male"), ("F", "Female")],
        validators=[DataRequired(message="Please Select Gender!")],
    )

    staff_id = StringField(
        "Staff ID",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "Teacher Code"},
    )

    title = SelectField(
        "Title",
        choices=[
            ("Mr.", "Mr."),
            ("Mrs.", "Mrs."),
            ("M/s", "M/s"),
            ("Tr.", "Tr."),
            ("Mdm.", "Mdm."),
            ("Prof.", "Prof."),
            ("Dr.", "Dr."),
        ],
        validators=[DataRequired(message="Select a title.")],
    )

    id_no = IntegerField(
        "ID Number",
        validators=[Optional()],
        render_kw={"placeholder": "National ID Number"},
    )

    tsc_no = StringField(
        "TSC Number",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "TSC Number"},
    )

    phone = StringField(
        "Phone Number",
        validators=[
            DataRequired(),
            Length(
                min=10, max=13, message="Phone number must be 10-13 characters long"
            ),
        ],
        render_kw={"maxlength": 13, "placeholder": "0712345678 or +254712345678"},
    )

    email = StringField(
        "Email",
        validators=[Optional(), Email(message="Invalid email address.")],
        render_kw={"placeholder": "Email Address"},
    )

    submit = SubmitField("Add Teacher")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Enter your current password.")],
        render_kw={
            "autocomplete": "current-password",
            "placeholder": "Current password",
        },
    )
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(message="Enter a new password."),
            Length(
                min=6,
                max=64,
                message="Password must be 6 to 64 characters.",
            ),
        ],
        render_kw={
            "autocomplete": "new-password",
            "placeholder": "At least 6 characters",
        },
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(message="Confirm your new password."),
            EqualTo("new_password", message="New passwords must match."),
        ],
        render_kw={
            "autocomplete": "new-password",
            "placeholder": "Re-enter new password",
        },
    )
    submit = SubmitField("Update password")


class ResetPasswordForm(FlaskForm):
    submit = SubmitField("Reset password")


class TeacherPassportUploadForm(FlaskForm):
    passport = FileField(
        "Passport Photo",
        validators=[
            FileRequired(message="Please select your passport to upload!"),
            FileAllowed(["jpg", "jpeg", "png", "gif"], "Images only!"),
        ],
    )
