from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional


class OptionalDateTimeLocalField(DateTimeLocalField):
    """Treat a blank datetime-local input as unset instead of invalid."""

    def process_formdata(self, valuelist):
        if not valuelist or not str(valuelist[0]).strip():
            self.data = None
            return
        raw = str(valuelist[0]).strip().replace("Z", "")
        if "." in raw:
            raw = raw.split(".", 1)[0]
        super().process_formdata([raw])


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

    marks_due_at = OptionalDateTimeLocalField(
        "Teachers' marks entry deadline",
        format=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
        validators=[Optional()],
    )

    submit = SubmitField("Create Exam")


class ExamDeadlineForm(FlaskForm):
    exam_id = HiddenField(validators=[DataRequired()])
    marks_due_at = OptionalDateTimeLocalField(
        "Teachers' marks entry deadline",
        format=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
        validators=[Optional()],
    )
    submit = SubmitField("Save deadline")
    clear = SubmitField("Remove deadline")
