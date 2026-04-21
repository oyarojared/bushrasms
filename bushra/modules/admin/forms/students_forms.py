from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (DateField, IntegerField, SearchField, SelectField,
                     StringField, SubmitField)
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp
from wtforms.validators import ValidationError
import re


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
        "Admission Number",
        validators=[DataRequired(message="Please provide an adm no!")],
        render_kw={"placeholder": "Adm no"}
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
    
    import re
    from wtforms.validators import ValidationError

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
