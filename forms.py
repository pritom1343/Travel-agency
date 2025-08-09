from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional
from flask_wtf.file import FileField, FileAllowed




class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class TourPackageForm(FlaskForm):
    title = StringField("Package Title", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[DataRequired()])
    price = FloatField("Price", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired()])
    duration = StringField("Duration", validators=[DataRequired()])
    members = IntegerField("Number of Members", validators=[DataRequired()])
    facilities = TextAreaField("Facilities")
    hotel_name = StringField("Hotel/Resort Name")
    room_type = StringField("Room Type")
    number_of_rooms = IntegerField("Number of Rooms")
    transportation_details = TextAreaField("Transportation Details")
    tour_type = SelectField("Tour Type", choices=[("Family", "Family"), ("Friends", "Friends"), ("Mixed", "Mixed")])
    image_file = FileField("Package Image", validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField("Save Package")

class AdminLoginForm(FlaskForm):
    email = StringField('Admin Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login as Admin')


class EditProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[Optional()])
    age = IntegerField("Age", validators=[Optional()])
    gender = StringField("Gender", validators=[Optional()])
    occupation = StringField("Occupation", validators=[Optional()])
    education = StringField("Education", validators=[Optional()])
    submit = SubmitField("Save Changes")

