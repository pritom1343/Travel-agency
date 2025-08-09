from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    occupation = db.Column(db.String(100))
    education = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)

class TourPackage(db.Model):
    __tablename__ = 'tour_packages'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    members = db.Column(db.Integer, nullable=False)
    facilities = db.Column(db.Text)
    hotel_name = db.Column(db.String(100))
    room_type = db.Column(db.String(100))
    number_of_rooms = db.Column(db.Integer)
    transportation_details = db.Column(db.Text)
    tour_type = db.Column(db.String(50))
    image_filename = db.Column(db.String(255))  # store filename only

