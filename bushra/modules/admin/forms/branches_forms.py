# forms.py
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp
from wtforms.validators import ValidationError
from ....modals.branches_db import Branch
from flask_wtf.file import FileField, FileAllowed

class BranchesList(FlaskForm):
    branches = SelectField(
        "Branch",
        validators=[DataRequired(message="Please select branch to continue!")],
        coerce=str,
        choices=[],  # will be filled dynamically 
    )


class ExtendedBranchForm(BranchesList):
    # Add extra form fields
    grade_form = StringField(
        "Grade/Form", validators=[DataRequired(message="Please type grade/form!")]
    )

    streams = StringField(
        "Streams: N/B Names separated by a comma",
        validators=[
            Regexp(
                r"^[A-Za-z,\s]*$",
                message="Streams may only contain letters and commas.",
            )
        ],
    )

    # Calendar input with 2025 selected by default
    class_year = SelectField(
        "Class Year",
        choices=[(str(y), str(y)) for y in range(2035, 2024, -1)],
        default="2025",
        validators=[DataRequired()],
    )



class BranchGradeStreamForm(FlaskForm):
    branch = SelectField(
        "Branch",
        choices=[],
        validators=[DataRequired(message="Select branch to continue!")],
    )

    grade_form = SelectField(
        "Grade/Form",
        choices=[],
        validators=[DataRequired(message="Select grade/form to continue!")],
    )

    stream = SelectField(
        # optional
        "Stream",
        choices=[],
        validators=[Optional()],
    )


class AddBranchForm(FlaskForm):
    # Basic branch details
    branch_name = StringField(
        "Branch Name",
        validators=[
            DataRequired(message="Branch name is required!"),
            Length(max=150, message="Name too long."),
        ],
    )

    school_code = IntegerField(
        "School Code",
        validators=[ 
            Optional()
        ],
    )

    branch_manager = StringField(
        "Branch Manager",
        validators=[
            DataRequired(message="Branch manager name is required!"),
            Length(max=100),
        ],
    )

    # Primary / Secondary / Mixed
    branch_level = SelectField(
        "Branch Level",
        choices=[
            ("", "--- Select school level ---"),
            ("Primary", "Primary"),
            ("Secondary", "Secondary"),
            ("Mixed", "Mixed (Primary + Secondary)"),
        ],
        validators=[DataRequired(message="You must select school level!")],
    )

    # This will be populated dynamically inside your route
    branch_head = SelectField(
        "Branch Head",
        coerce=str,   
    )

    # Added fields
    school_gender = SelectField(
        "School Gender",
        choices=[
            ("", "--- Select school gender ---"),
            ("Boys", "Boys"),
            ("Girls", "Girls"),
            ("Mixed", "Mixed"),
        ],
        validators=[DataRequired(message="Please select school gender!")],
    )

    school_type = SelectField(
        "School Type",
        choices=[
            ("", "--- Select school type ---"),
            ("Boarding", "Boarding"),
            ("Day School", "Day School"),
            ("Both", "Both"),
        ],
        validators=[DataRequired(message="Please select school type!")],
    )

    # Optional but very useful fields
    email = StringField(
        "Branch Email",
        validators=[
            Optional(),
            Email(message="Enter a valid email address."), 
            Length(max=120)
        ]
    )
    
    logo = FileField(
        "School Logo",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Images only!")]
    )

    motto = StringField(
        "School Motto",
        validators=[Optional(), Length(max=250)]
    )
    
    def validate_school_code(self, field):
        if field.data is None:
            return  # optional field, skip if empty

        # Check if branch_id is passed in form (for update scenario)
        branch_id = getattr(self, "branch_id", None)

        # Query for another branch with same code
        existing = Branch.query.filter_by(school_code=field.data).first()

        # If updating, ignore current branch
        if existing and (branch_id is None or existing.id != branch_id):
            raise ValidationError("The school code you entered is already in use by another branch.")
        
    def validate_branch_name(self, field):
        if not field.data:
            return   
        branch_id = getattr(self, "branch_id", None)
        existing = Branch.query.filter_by(branch_name=field.data.strip()).first()
        if existing and (branch_id is None or existing.id != branch_id):
            raise ValidationError("The branch name you entered is already in use by another branch.")

    submit = SubmitField("Save Branch")


class GradeSelectForm(FlaskForm):
    grade_select = SelectField(
        "Select Grade / Form to view subjects offered.",
        validators=[
            DataRequired(message="Please select a Grade / Form to view subjects offered.")
        ],
        choices=[]
    )
    