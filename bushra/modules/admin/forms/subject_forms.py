from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired, Length, Optional


_choices = [
   "Languages", 
   "Mathematics",
   "Science & Technology",
   "Arts & Humanities", 
   "Physical & Applied" 
]


class DeleteSubjectForm(FlaskForm):
    pass


class SubjectForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[
            DataRequired(
                message="Please Enter the name of the subject."
            ),
            Length(min=4, max=35)
        ],
    )
    
    code = IntegerField(
        "Code",
        validators=[
            DataRequired(
                message="Please enter subject code."
            )
        ]
    )
    
    is_examinable = BooleanField(
        "Examinable",
    )
    
    is_compulsory = BooleanField(
        "Compulsory",
    )
    
    category = SelectField(
        "Category",
        validators = [
            DataRequired(
                message="Please select subject category."
            )
        ],
        choices=_choices
    )
    

class BranchGradeSelectionForm(FlaskForm):
    branches = SelectField(
        "Branch",
        validators=[
            DataRequired(
                message="Please select branch to assign subjects."
            )
        ],
        choices=[],
    )
    
    grades = SelectField(
        "Grade / Form",
        validators=[
            DataRequired(
                message="Please select grade/form to assign subjects."
            )
        ],
        choices=[],
    )