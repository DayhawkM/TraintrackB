from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message="Passwords must match")]
    )
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Login')

class AlgorithmForm(FlaskForm):
    goals = SelectField(
        'Fitness Goal',
        choices=[('fat_loss', 'Fat Loss'), ('muscle_building', 'Muscle Building')],
        validators=[DataRequired()]
    )
    experience_level = SelectField(
        'Experience Level',
        choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('expert', 'Expert')],
        validators=[DataRequired()]
    )
    submit = SubmitField('Get Workout Plan')
