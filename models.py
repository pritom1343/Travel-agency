from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()
class HomeImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200))          # Optional
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    occupation = db.Column(db.String(100))
    address = db.Column(db.String(250))
    phone = db.Column(db.String(20))
    education = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
  #  profile_image = db.Column(db.String(150), nullable=True, default="default_profile.png")
   # profile_image = db.Column(db.String(200))
    image_file = db.Column(db.String(100), nullable=False, default='default.png')


class TourPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50))
    members = db.Column(db.Integer)               # Max members
    booked_members = db.Column(db.Integer, default=0)  # Members already booked
    facilities = db.Column(db.String(200))
    hotel_name = db.Column(db.String(100))
    room_type = db.Column(db.String(50))
    number_of_rooms = db.Column(db.Integer)
    transportation_details = db.Column(db.String(200))
    tour_type = db.Column(db.String(50))
    image_filename = db.Column(db.String(200))

    @property
    def available_slots(self):
        """Calculate remaining slots dynamically."""
        if self.members is None:
            return 0
        return max(self.members - self.booked_members, 0)

    def adjust_booked_members_on_edit(self, new_max_members):
        """If max members reduced below booked_members, adjust booked_members."""
        if new_max_members < self.booked_members:
            self.booked_members = new_max_members
        self.members = new_max_members

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('tour_package.id'), nullable=True)   # Standard tour package
    custom_trip_id = db.Column(db.Integer, db.ForeignKey('custom_trips.id'), nullable=True)  # Custom trip booking
    members = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', backref='bookings', lazy=True)
    package = db.relationship('TourPackage', backref='bookings', lazy=True)
    custom_trip = db.relationship('CustomTrip', backref='bookings', lazy=True)


class CustomTrip(db.Model):
    __tablename__ = 'custom_trips'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('custom_trips', lazy=True, cascade='all, delete-orphan'))

    destination = db.Column(db.String(100), nullable=False)
    transport = db.Column(db.String(50), nullable=False)
    hotel = db.Column(db.String(100), nullable=False)
    number_of_rooms = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    people = db.Column(db.Integer, nullable=False)
    other_preferences = db.Column(db.String(200)) 
    notes = db.Column(db.Text)  # optional
    price = db.Column(db.Float, nullable=True)   # Admin sets this
    status = db.Column(db.String(20), nullable=False, default="Pending")
    admin_notes = db.Column(db.Text, nullable=True)
    resubmit_flag = db.Column(db.Boolean, default=False)


class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('chat_sessions', lazy=True))
    messages = db.relationship('Message', backref='chat_session', lazy='dynamic', cascade='all, delete-orphan')

    def get_unread_count(self, for_admin=True):
        """Count unread messages. for_admin=True counts user's unread messages for admin."""
        return self.messages.filter_by(is_read=False, is_admin_message=not for_admin).count()

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    is_admin_message = db.Column(db.Boolean, default=False) # True if sender is admin
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# models.py (update AgencyRating model and add Reply model)

class AgencyRating(db.Model):
    __tablename__ = 'agency_ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Removed is_approved field
    
    # Relationship
    user = db.relationship('User', backref=db.backref('agency_ratings', lazy=True))
    replies = db.relationship('RatingReplyForm', backref='rating', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AgencyRating {self.rating} stars by {self.user.username}>'

class RatingReplyForm(db.Model):
    __tablename__ = 'rating_replies'
    id = db.Column(db.Integer, primary_key=True)
    rating_id = db.Column(db.Integer, db.ForeignKey('agency_ratings.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_admin_reply = db.Column(db.Boolean, default=False)
    reply_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('rating_replies', lazy=True))

class AgencyStats(db.Model):
    __tablename__ = 'agency_stats'
    id = db.Column(db.Integer, primary_key=True)
    total_ratings = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)    