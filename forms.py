from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired,NumberRange, Length, Email, EqualTo
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional
from flask_wtf.file import FileField, FileAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField
from wtforms import  DateField





class TourPackageForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    location = StringField('Location', validators=[DataRequired()])
    duration = StringField('Duration')
    members = IntegerField('Members')
    facilities = StringField('Facilities')
    hotel_name = StringField('Hotel Name')
    room_type = StringField('Room Type')
    number_of_rooms = IntegerField('Number of Rooms')
    transportation_details = StringField('Transportation Details')
    tour_type = SelectField('Tour Type', choices=[('Adventure','Adventure'),('Leisure','Leisure')])
    image_file = FileField('Upload Image')  # For file upload
    submit = SubmitField('Add Package')



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
    username = StringField('Username')
    email = StringField('Email')
    gender = SelectField('Gender', choices=[('Male','Male'), ('Female','Female'), ('Other','Other')])
    age = IntegerField('Age')
    occupation = StringField('Occupation')
    address = TextAreaField('Address')
    phone = StringField('Phone')
    image_file = FileField('Profile Picture', validators=[FileAllowed(['jpg','jpeg','png'])])
    submit = SubmitField('Save Changes')


class CustomTripForm(FlaskForm):
    destination = StringField('Destination', validators=[DataRequired(), Length(max=100)])
    transport = SelectField('Transport', validators=[DataRequired()],
                            choices=[('Plane','Plane'), ('Train','Train'), ('Bus','Bus'), ('Car','Car')])
    hotel = StringField('Hotel', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')
    people = IntegerField('Number of People', validators=[DataRequired(), NumberRange(min=1)])
    number_of_rooms = IntegerField('Number of Rooms', validators=[DataRequired(), NumberRange(min=1)])
    room_type = SelectField('Room Type', choices=[('Single', 'Single'), ('Double', 'Double'), ('Suite', 'Suite')])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Trip')

class DeleteTripForm(FlaskForm):
    submit = SubmitField('Delete')



