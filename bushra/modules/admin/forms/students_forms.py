from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (DateField, IntegerField, SearchField, SelectField,
                     StringField, SubmitField, TextAreaField)
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp
from wtforms.validators import ValidationError
import re

from ..services.leaving_certificate import (
    REPORT_MAX_WORDS,
    headteacher_report_fits,
)


class StudentSearchForm(FlaskForm):
    query = SearchField(
        "Search",
        validators=[
            DataRequired(message="Enter Name, Adm no or Ass. no and try to search!")
        ],
    )


class AddStudentForm(FlaskForm):
    branches = SelectField(
        "Branch",
        validators=[DataRequired(message="You must select branch!")],
        choices=[],
        render_kw={"placeholder": "Select branch"}
    )

    admission_number = IntegerField(
            "Auto-generated admission number",
            render_kw={"readonly": True}
    )

    fullname = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=50)],
        render_kw={"placeholder": "Full name"}
    )

    knec_assessment_no = StringField(
        "KNEC Assessment Number",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "KNEC no (opt)"}
    )

    nemis_number = StringField(
        "NEMIS Number",
        validators=[Optional()],
        render_kw={"placeholder": "NEMIS no (opt)"}
    )

    birth_cert_no = StringField(
        "Birth Certificate Entry Number",
        validators=[Optional(), Length(max=30)],
        render_kw={"placeholder": "Birth cert no (opt)"}
    )

    gender = SelectField(
        "Gender",
        choices=[
            ("", "--- Select ---"),
            ("M", "Male"),
            ("F", "Female")
        ],
        render_kw={"placeholder": "Gender"}
    )

    dob = DateField(
        "Date of Birth",
        validators=[Optional()],
        render_kw={"placeholder": "DOB"}
    )

    boarding_status = SelectField(
        "Boarding Status",
        choices=[
            ("", "--- Select ---"),
            ("Boarding", "Boarding"),
            ("Day Scholar", "Day Scholar")
        ],
        validators=[Optional()],
        render_kw={"placeholder": "Boarding"}
    )

    pathway = SelectField(
        "Pathway",
        choices=[
            ("", "--- Select ---"),
            ("STEM", "STEM"),
            ("Social Science", "Social Science"),
            ("Arts & Sports", "Arts & Sports")
        ],
        validators=[Optional()],
        render_kw={"placeholder": "Pathway"}
    )

    kcpe_marks = IntegerField(
        "KCPE Marks",
        validators=[Optional()],
        render_kw={"placeholder": "KCPE marks"}
    )

    kcpe_index_no = StringField(
        "KCPE Index Number",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "KCPE index"}
    )

    kcpe_year = IntegerField(
        "KCPE Year",
        validators=[Optional()],
        render_kw={"placeholder": "KCPE year"}
    )

    date_of_admission = DateField(
        "Date of Admission",
        default=date.today,
        validators=[DataRequired()],
        render_kw={"placeholder": "Admission date"}
    )

    parent_fullname = StringField(
        "Parent/Guardian Full Name",
        validators=[Optional(), Length(min=2, max=100)],
        render_kw={"placeholder": "Parent name"}
    )

    parent_phone = StringField(
        "Parent/Guardian Phone",
        validators=[
            Optional(),
            Regexp(r"^\d{10,15}$", message="Enter a valid phone number (digits only)."),
        ],
        render_kw={"placeholder": "Parent phone"}
    )

    def validate_fullname(self, field):
        name = field.data.strip()

        # Normalize smart apostrophes
        name = name.replace("’", "'")

        # Collapse weird spaces
        name = " ".join(name.split())

        pattern = r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$"

        if not re.fullmatch(pattern, name):
            raise ValidationError(
                "Name may only contain letters, spaces, hyphens, and apostrophes."
            )

        field.data = name



    submit = SubmitField("Save Student")


class TransferLetterForm(FlaskForm):
    knec_assessment_no = StringField(
        "Assessment number",
        validators=[
            DataRequired(message="Enter the assessment number before generating the letter."),
            Length(max=50),
        ],
    )
    reason = TextAreaField(
        "Reason for transfer",
        validators=[Optional(), Length(max=600)],
        render_kw={
            "rows": 3,
            "placeholder": "Optional",
        },
    )


class LeavingCertificateForm(FlaskForm):
    school_name = StringField(
        "School",
        validators=[DataRequired(), Length(max=150)],
        render_kw={"aria-describedby": "lcSchoolHint"},
    )
    school_address = StringField(
        "School address",
        validators=[Optional(), Length(max=250)],
    )
    student_name = StringField(
        "Full name",
        validators=[DataRequired(), Length(min=2, max=80)],
    )
    admission_number = StringField(
        "Admission/Serial No",
        validators=[DataRequired(), Length(max=20)],
    )
    date_of_birth = DateField(
        "Date of birth (in admission register, optional)",
        validators=[Optional()],
        render_kw={"type": "date"},
    )
    date_of_admission = DateField(
        "Entered this school on",
        validators=[DataRequired()],
        render_kw={"type": "date"},
    )
    form_enrolled = StringField(
        "Enrolled in Form",
        validators=[DataRequired(), Length(max=20)],
    )
    date_of_leaving = DateField(
        "Left on",
        validators=[
            DataRequired(message="Enter the date the pupil left school."),
        ],
        render_kw={"type": "date"},
    )
    issue_date = DateField(
        "Date of issue",
        validators=[DataRequired()],
        render_kw={"type": "date"},
    )
    headteacher_report = TextAreaField(
        "Headteacher's report",
        validators=[DataRequired(), Length(max=400)],
        render_kw={
            "rows": 4,
            "data-max-words": REPORT_MAX_WORDS,
        },
    )

    def validate_date_of_leaving(self, field):
        admitted = self.date_of_admission.data
        if admitted and field.data and field.data < admitted:
            raise ValidationError("Date of leaving cannot be before admission.")

    def validate_date_of_birth(self, field):
        admitted = self.date_of_admission.data
        if admitted and field.data and field.data >= admitted:
            raise ValidationError("Date of birth must be before admission.")

    def validate_headteacher_report(self, field):
        if not headteacher_report_fits(field.data):
            raise ValidationError(
                f"Keep the comment to {REPORT_MAX_WORDS} words so it fits "
                "the three lines on the certificate."
            )


class PassportUploadForm(FlaskForm):
    passport = FileField(
        "Passport Photo",
        validators=[
            FileRequired(message="Please select student's passport to upload!"),
            FileAllowed(["jpg", "jpeg", "png", "gif"], "Images only!"),
        ],
        render_kw={"placeholder": "Choose photo"}
    )

    submit = SubmitField("Upload")



class MuiltapleStudentsUploadForm(FlaskForm):
    branches = SelectField(
        "Branch", validators=[DataRequired(message="Please select branch!")], choices=[]
    )

    excel_file = FileField(
        "Choose Excel File",
        validators=[FileRequired(), FileAllowed(["xls", "xlsx"], "Excel files only!")],
    )
