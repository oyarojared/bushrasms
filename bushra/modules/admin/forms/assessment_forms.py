from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length


class ExamCreateForm(FlaskForm):
    branch_id = SelectField(
        "Branch",
        coerce=int,
        validators=[DataRequired(message="Branch is required")]
    )

    year = SelectField(
        "Academic Year",
        validators=[DataRequired(message="Academic year is required")]
    )

    term = SelectField(
        "Term",
        choices=[
            ("", "--- Select term ---"),
            ("I", "Term I"),
            ("II", "Term II"),
            ("III", "Term III")
        ],
        validators=[DataRequired(message="Term is required")]
    )

    name = StringField(
        "Exam Name",
        validators=[
            DataRequired(message="Exam name is required"),
            Length(min=3, max=100)
        ]
    )

    submit = SubmitField("Create Exam")
