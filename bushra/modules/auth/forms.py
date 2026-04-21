from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username can't be empty!"),
            Length(
                min=6,
                max=50,
                message="Username must be between 6 and 50 characters long!",
            ),
        ],
    )

    password = PasswordField(
        "Password", validators=[DataRequired(message="Password can't be empty!")]
    )

    remember_me = BooleanField("Remember Me")

    submit = SubmitField("Login")
