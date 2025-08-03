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
