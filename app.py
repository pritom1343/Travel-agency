from mailbox import Message
from flask import Flask, render_template, redirect, url_for, flash, request , jsonify 
from config import Config
from models import AgencyRating, AgencyStats, db, User, TourPackage, HomeImage , Booking 
from forms import RegistrationForm, LoginForm, TourPackageForm, AdminLoginForm, EditProfileForm
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from PIL import Image
import os
import secrets
from datetime import date
from forms import CustomTripForm, DeleteTripForm
from models import CustomTrip
from flask_socketio import SocketIO, emit, join_room, leave_room
# app.py (at the top with other imports)
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import ChatSession, Message  # Add this import
from datetime import datetime  # Make sure this is imported
# app.py (at the top with other imports)
from forms import RegistrationForm, LoginForm, TourPackageForm, AdminLoginForm, EditProfileForm, AgencyRatingForm, RatingReplyForm
from models import RatingReplyForm as RatingReplyModel 


# ----------------------------
# App Initialization
# ----------------------------
app = Flask(__name__)
app.config.from_object(Config)

socketio = SocketIO(app, cors_allowed_origins="*")

# Upload folder setup
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max

# Extensions
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =======================
# User-Facing Routes
# =======================

@app.route('/')
def home():
    home_image = HomeImage.query.first()
    return render_template('home.html', home_image=home_image)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid email or password.", "danger")
    return render_template('login.html', form=form)

# Admin: Add new tour package
@app.route('/admin/tour-packages/add', methods=['GET', 'POST'])
@login_required
def add_tour_package():
    form = TourPackageForm()
    if form.validate_on_submit():
        # Handle image upload
        image_file = form.image_file.data
        filename = None
        if image_file:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Create new tour package
        package = TourPackage(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            location=form.location.data,
            duration=form.duration.data,
            members=form.members.data,
            facilities=form.facilities.data,
            hotel_name=form.hotel_name.data,
            room_type=form.room_type.data,
            number_of_rooms=form.number_of_rooms.data,
            transportation_details=form.transportation_details.data,
            tour_type=form.tour_type.data,
            image_filename=filename
        )

        db.session.add(package)
        db.session.commit()
        flash('Tour package added successfully!', 'success')
        return redirect(url_for('admin_tour_packages'))

    return render_template('add_tour_package.html', form=form)

@app.route('/user-dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        flash("Redirected to admin dashboard.", "info")
        return redirect(url_for('dashboard'))
    return render_template('user_dashboard.html', user=current_user)

@app.route('/tour-packages')
def tour_packages():
    destination = request.args.get('destination')
    price_range = request.args.get('price')
    duration = request.args.get('duration')
    packages = TourPackage.query
    if destination:
        packages = packages.filter(TourPackage.location.ilike(f"%{destination}%"))
    if price_range:
        min_price, max_price = map(float, price_range.split('-'))
        packages = packages.filter(TourPackage.price.between(min_price, max_price))
    if duration:
        packages = packages.filter(TourPackage.duration.ilike(f"%{duration}%"))
    packages = packages.all()
    return render_template('tour_packages.html', packages=packages)

@app.route("/book_package/<int:package_id>", methods=["POST"])
@login_required
def book_package(package_id):
    data = request.get_json()
    members_requested = int(data.get("members", 0))

    package = TourPackage.query.get_or_404(package_id)

    if members_requested > package.available_slots:
        return jsonify({"success": False, "message": f"Not enough slots! Only {package.available_slots} left."}), 400

    # Add booking
    booking = Booking(user_id=current_user.id, package_id=package.id, members=members_requested)
    db.session.add(booking)

    # Update booked_members count
    package.booked_members += members_requested
    db.session.commit()

    return jsonify({"success": True, "remaining_slots": package.available_slots})



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# =======================
# Profile Editing
# =======================
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/uploads', picture_fn)
    output_size = (200, 200)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

# Admin: Manage tour packages
@app.route('/admin/tour-packages')
@login_required
def admin_tour_packages():
    packages = TourPackage.query.all()
    return render_template('admin_tour_packages.html', packages=packages)

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        if form.image_file.data and hasattr(form.image_file.data, 'filename'):
            if current_user.image_file != 'default.png':
                old_path = os.path.join(app.root_path, 'static/uploads', current_user.image_file)
                if os.path.exists(old_path):
                    os.remove(old_path)
            picture_file = save_picture(form.image_file.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.gender = form.gender.data
        current_user.age = form.age.data
        current_user.occupation = form.occupation.data
        current_user.address = form.address.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Your profile has been successfully updated!', 'success')
        return redirect(url_for('edit_profile'))
    return render_template('edit_profile.html', form=form)

# =======================
# Admin Panel Routes
# =======================
@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))
    users = User.query.filter_by(is_admin=False).all()
    return render_template('dashboard.html', users=users)

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    # Fetch all bookings (standard + custom)
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()

    return render_template('admin_bookings.html', bookings=bookings)

@app.route('/admin/booking/<int:booking_id>')
@login_required
def admin_booking_details(booking_id):
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    booking = Booking.query.get_or_404(booking_id)
    return render_template('admin_booking_details.html', booking=booking)


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('dashboard'))
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, is_admin=True).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Admin login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid admin credentials.", "danger")
    return render_template('admin_login.html', form=form)

@app.route('/admin/custom-trips')
@login_required
def admin_custom_trips():
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    # Get filter from query params (default = show all except Confirmed)
    status_filter = request.args.get("status")

    query = CustomTrip.query

    # Only allow Pending, Approved, Rejected
    allowed_statuses = ["Pending", "Approved", "Rejected"]

    if status_filter in allowed_statuses:
        query = query.filter_by(status=status_filter)
    else:
        query = query.filter(CustomTrip.status.in_(allowed_statuses))

    # Sort by start date
    trips = query.order_by(CustomTrip.start_date.asc()).all()

    return render_template('admin_custom_trips.html', trips=trips, status_filter=status_filter)



@app.route('/admin/custom-trips/update/<int:trip_id>', methods=['POST'])
@login_required
def update_custom_trip(trip_id):
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    trip = CustomTrip.query.get_or_404(trip_id)
    action = request.form.get("action")

    if action == "approve":
        trip.price = float(request.form.get("price"))
        trip.status = "Approved"
        trip.admin_notes = request.form.get("admin_notes")
    elif action == "reject":
        trip.status = "Rejected"
        trip.admin_notes = request.form.get("admin_notes")

    db.session.commit()
    flash("Trip updated successfully!", "success")
    return redirect(url_for('admin_custom_trips'))


@app.route('/admin/user/<int:user_id>')
@login_required
def user_details(user_id):
    # Only admins can view user details
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)


    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('manage_users'))

    return render_template('user_details.html', user=user)


@app.route('/manage-users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))
    users = User.query.filter_by(is_admin=False).all()
    return render_template('manage_users.html', users=users)

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("You cannot delete another admin.", "danger")
        return redirect(url_for('dashboard'))
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} deleted successfully.", "success")
    return redirect(url_for('dashboard'))


# app.py (add with other routes)
@app.route('/admin/chat-manager')
@login_required
def admin_chat_manager():
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    # Get all active chat sessions with their users and unread counts
    chat_sessions = ChatSession.query.filter_by(is_active=True).order_by(ChatSession.updated_at.desc()).all()

    # Calculate total unread messages for the admin dashboard
    total_unread = 0
    selected_user = None
    selected_session = None
    messages = []

    for session in chat_sessions:
        session.unread_count = session.get_unread_count(for_admin=True)
        total_unread += session.unread_count

    # Check if a specific user chat is requested
    user_id = request.args.get('user_id', type=int)
    if user_id:
        selected_user = User.query.get_or_404(user_id)
        # Find or create a chat session for this user
        selected_session = ChatSession.query.filter_by(user_id=user_id, is_active=True).first()
        if not selected_session:
            selected_session = ChatSession(user_id=user_id)
            db.session.add(selected_session)
            db.session.commit()

        # Get messages for this session
        messages = Message.query.filter_by(session_id=selected_session.id).order_by(Message.timestamp.asc()).all()

        # Mark messages as read when admin opens the chat
        Message.query.filter_by(session_id=selected_session.id, is_admin_message=False, is_read=False).update({'is_read': True})
        db.session.commit()

    return render_template('admin_chat_manager.html', 
                         chat_sessions=chat_sessions, 
                         total_unread=total_unread,
                         selected_user=selected_user,
                         selected_session=selected_session,
                         messages=messages)
# app.py (add with other routes)
@app.route('/user/chat')
@login_required
def user_chat():
    if current_user.is_admin:
        return redirect(url_for('admin_chat_manager'))

    # Find or create a chat session for the current user
    session = ChatSession.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not session:
        session = ChatSession(user_id=current_user.id)
        db.session.add(session)
        db.session.commit()

    messages = Message.query.filter_by(session_id=session.id).order_by(Message.timestamp.asc()).all()
    unread_count = session.get_unread_count(for_admin=False) # Messages user hasn't read

    return render_template('user_chat.html', session=session, messages=messages, unread_count=unread_count)


# Admin: Edit tour package
@app.route('/admin/tour-packages/edit/<int:package_id>', methods=['GET', 'POST'])
@login_required
def edit_tour_package(package_id):
    if not current_user.is_admin:
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))

    package = TourPackage.query.get_or_404(package_id)
    form = TourPackageForm(obj=package)

    if form.validate_on_submit():
        # Adjust booked_members if max members changed
        new_max = form.members.data
        package.adjust_booked_members_on_edit(new_max)

        # Update other fields
        package.title = form.title.data
        package.description = form.description.data
        package.price = form.price.data
        package.location = form.location.data
        package.duration = form.duration.data
        package.facilities = form.facilities.data
        package.hotel_name = form.hotel_name.data
        package.room_type = form.room_type.data
        package.number_of_rooms = form.number_of_rooms.data
        package.transportation_details = form.transportation_details.data
        package.tour_type = form.tour_type.data

        # Handle image upload
        if form.image_file.data:
            if package.image_filename:
                old_path = os.path.join(app.root_path, 'static/uploads', package.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(form.image_file.data.filename)
            form.image_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            package.image_filename = filename

        db.session.commit()
        flash("Tour package updated successfully!", "success")
        return redirect(url_for('admin_tour_packages'))

    return render_template('add_tour_package.html', form=form, package=package)

# Admin: Delete tour package
@app.route('/admin/tour-packages/delete/<int:package_id>', methods=['POST'])
@login_required
def delete_tour_package(package_id):
    package = TourPackage.query.get_or_404(package_id)
    # Delete image file if exists
    if package.image_filename:
        image_path = os.path.join(app.static_folder, 'uploads', package.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(package)
    db.session.commit()
    flash('Tour package deleted successfully!', 'success')
    return redirect(url_for('admin_tour_packages'))

# Admin: Tour package details
@app.route('/admin/tour-packages/details/<int:package_id>')
@login_required
def tour_package_details(package_id):
    if not current_user.is_admin:
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))

    package = TourPackage.query.get_or_404(package_id)
    return render_template('tour_package_details.html', package=package)


# app.py (replace the agency rating routes with these)

@app.route('/agency-feedback', methods=['GET', 'POST'])
@login_required
def agency_feedback():
    if current_user.is_admin:
        flash("Admins cannot submit feedback.", "info")
        return redirect(url_for('user_dashboard'))
    
    # Check if user has already rated
    existing_rating = AgencyRating.query.filter_by(user_id=current_user.id).first()
    
    form = AgencyRatingForm()
    reply_form = RatingReplyForm()  # Add this form for replies
    
    if form.validate_on_submit():
        if existing_rating:
            # Update existing rating
            existing_rating.rating = form.rating.data
            existing_rating.feedback = form.feedback.data
            flash('Your feedback has been updated!', 'success')
        else:
            # Create new rating
            rating = AgencyRating(
                user_id=current_user.id,
                rating=form.rating.data,
                feedback=form.feedback.data
            )
            db.session.add(rating)
            flash('Thank you for your feedback!', 'success')
        
        # Update agency stats
        update_agency_stats()
        db.session.commit()
        return redirect(url_for('agency_feedback'))
    
    # Pre-fill form if editing existing rating
    if existing_rating:
        form.rating.data = existing_rating.rating
        form.feedback.data = existing_rating.feedback
    
    return render_template('agency_feedback.html', 
                         form=form, 
                         reply_form=reply_form,  # Pass the reply form
                         existing_rating=existing_rating)

@app.route('/admin/agency-feedback')
@login_required
def admin_agency_feedback():
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))
    
    # Get all ratings with their users and replies
    all_ratings = AgencyRating.query.order_by(AgencyRating.created_at.desc()).all()
    
    return render_template('admin_agency_feedback.html', all_ratings=all_ratings)

@app.route('/admin/feedback/reply/<int:rating_id>', methods=['GET', 'POST'])
@login_required
def reply_to_feedback(rating_id):
    if not current_user.is_admin:
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))
    
    rating = AgencyRating.query.get_or_404(rating_id)
    form = RatingReplyForm()  # This is the FORM
    
    if form.validate_on_submit():
        # Use the MODEL class (not the form class)
        reply = RatingReplyModel(  # ✅ Use the model class
            rating_id=rating_id,
            user_id=current_user.id,
            is_admin_reply=True,
            reply_text=form.reply_text.data
        )
        db.session.add(reply)
        db.session.commit()
        flash('Your reply has been posted!', 'success')
        return redirect(url_for('admin_agency_feedback'))
    
    return render_template('reply_to_feedback.html', form=form, rating=rating)

@app.route('/feedback/reply/<int:rating_id>', methods=['GET', 'POST'])
@login_required
def user_reply_to_feedback(rating_id):
    rating = AgencyRating.query.get_or_404(rating_id)
    
    # Check if the current user owns this rating
    if rating.user_id != current_user.id:
        flash("You can only reply to your own feedback.", "danger")
        return redirect(url_for('user_dashboard'))
    
    form = RatingReplyForm()  # This is the FORM
    
    if form.validate_on_submit():
        # Use the MODEL class (not the form class)
        reply = RatingReplyModel(  # ✅ Use the model class
            rating_id=rating_id,
            user_id=current_user.id,
            is_admin_reply=False,
            reply_text=form.reply_text.data
        )
        db.session.add(reply)
        db.session.commit()
        flash('Your reply has been posted!', 'success')
        return redirect(url_for('agency_feedback'))
    
    return render_template('user_reply_to_feedback.html', form=form, rating=rating)

# Helper function to update agency stats
def update_agency_stats():
    all_ratings = AgencyRating.query.all()
    
    if all_ratings:
        total_ratings = len(all_ratings)
        average_rating = sum(r.rating for r in all_ratings) / total_ratings
        
        # Get or create agency stats
        stats = AgencyStats.query.first()
        if not stats:
            stats = AgencyStats()
            db.session.add(stats)
        
        stats.total_ratings = total_ratings
        stats.average_rating = round(average_rating, 1)
    else:
        # No ratings yet
        stats = AgencyStats.query.first()
        if stats:
            stats.total_ratings = 0
            stats.average_rating = 0.0
    
    db.session.commit()
    return stats

# Function to get current agency stats (for templates)
@app.context_processor
def utility_processor():
    def get_agency_stats():
        stats = AgencyStats.query.first()
        if not stats:
            stats = AgencyStats()
            db.session.add(stats)
            db.session.commit()
        return stats
    return dict(get_agency_stats=get_agency_stats)


def get_agency_stats():
    stats = AgencyStats.query.first()
    if not stats:
        stats = AgencyStats()
        db.session.add(stats)
        db.session.commit()
    return stats



@app.context_processor
def utility_processor():
    def get_agency_stats():
        stats = AgencyStats.query.first()
        if not stats:
            stats = AgencyStats()
            db.session.add(stats)
            db.session.commit()
        return stats
    return dict(get_agency_stats=get_agency_stats)


with app.app_context():
    try:
        stats = AgencyStats.query.first()
        if not stats:
            stats = AgencyStats()
            db.session.add(stats)
            db.session.commit()
            print("Agency stats initialized")
    except:
        print("Could not initialize agency stats (tables might not exist yet)")


# =======================
# Admin Home Image Management
# =======================
@app.route('/admin-home-image', methods=['GET', 'POST'])
@login_required
def admin_home_image():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    home_image = HomeImage.query.first()

    if request.method == 'POST':
        file = request.files.get('image_file')
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.root_path, 'static/uploads', filename))

            if home_image:
                old_path = os.path.join(app.root_path, 'static/uploads', home_image.filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
                home_image.filename = filename
            else:
                home_image = HomeImage(filename=filename)
                db.session.add(home_image)
            
            db.session.commit()
            flash("Home image updated successfully!", "success")
        return redirect(url_for('admin_home_image'))

    return render_template('admin_home_image.html', home_image=home_image)

@app.route('/update-home-image', methods=['POST'])
@login_required
def update_home_image():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    file = request.files.get('image_file')
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path, 'static/uploads', filename))

        home_image = HomeImage.query.first()
        if home_image:
            old_path = os.path.join(app.root_path, 'static/uploads', home_image.filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            home_image.filename = filename
        else:
            home_image = HomeImage(filename=filename)
            db.session.add(home_image)

        db.session.commit()
        flash("Homepage wallpaper updated!", "success")

    return redirect(url_for('home'))

# Create Custom Trip
@app.route('/custom-trip', methods=['GET', 'POST'])
@login_required
def custom_trip():
    if request.method == 'POST':
        destination = request.form.get('destination', '')
        transport = request.form.get('transport', '')
        hotel = request.form.get('hotel', '')
        number_of_rooms = request.form.get('number_of_rooms')
        room_type = request.form.get('room_type', '')  # default empty string
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        people = request.form.get('people', 1)
        other_preferences = request.form.get('other_preferences', '')
        notes = request.form.get('notes', '')

        try:
            people = int(people)
        except ValueError:
            people = 1
        # Convert number_of_rooms to int if provided
        try:
            number_of_rooms = int(number_of_rooms) if number_of_rooms else None
        except ValueError:
            number_of_rooms = None

        new_trip = CustomTrip(
            user_id=current_user.id,
            destination=destination,
            transport=transport,
            hotel=hotel,
            number_of_rooms=number_of_rooms,
            room_type=room_type,
            start_date=start_date,
            end_date=end_date,
            people=people,
            other_preferences=other_preferences,
            notes=notes
        )
        db.session.add(new_trip)
        db.session.commit()
        flash("Your custom trip has been created!", "success")
        return redirect(url_for('my_custom_trips'))

    return render_template('custom_trip_form.html', trip=None)


# View Trips
@app.route('/my-custom-trips')
@login_required
def my_custom_trips():
    trips = CustomTrip.query.filter_by(user_id=current_user.id).all()
    return render_template('my_custom_trips.html', trips=trips)


# Edit Trip
@app.route('/edit-custom-trip/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def edit_custom_trip(trip_id):
    trip = CustomTrip.query.get_or_404(trip_id)

    # Only allow the owner to edit
    if trip.user_id != current_user.id:
        flash("You are not allowed to edit this trip.", "danger")
        return redirect(url_for('my_custom_trips'))

    if request.method == 'POST':
        # Update fields
        trip.destination = request.form.get('destination', trip.destination)
        trip.transport = request.form.get('transport', trip.transport)
        trip.hotel = request.form.get('hotel', trip.hotel)
        trip.number_of_rooms = int(request.form.get('number_of_rooms', trip.number_of_rooms))
        trip.room_type = request.form.get('room_type', trip.room_type)
        trip.start_date = request.form.get('start_date', trip.start_date)
        trip.end_date = request.form.get('end_date', trip.end_date)
        trip.people = int(request.form.get('people', trip.people))
        trip.other_preferences = request.form.get('other_preferences', trip.other_preferences)
        trip.notes = request.form.get('notes', trip.notes)

        # Reset status → Pending (so admin can recheck)
        trip.status = "Pending"
        trip.resubmit_flag = True   # Optional: admin can see that it was modified

        db.session.commit()
        flash("Trip updated and sent for review again!", "success")
        return redirect(url_for('my_custom_trips'))

    return render_template('custom_trip_form.html', trip=trip)

@app.route('/confirm-custom-trip/<int:trip_id>', methods=['POST'])
@login_required
def confirm_custom_trip(trip_id):
    trip = CustomTrip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id or trip.status != "Approved":
        flash("You cannot confirm this trip.", "danger")
        return redirect(url_for('my_custom_trips'))

    # Create booking with custom_trip_id
    booking = Booking(
        user_id=current_user.id,
        package_id=None,   # Not a standard package
        custom_trip_id=trip.id,  # Link to custom trip
        members=trip.people
    )
    db.session.add(booking)

    # Optionally mark trip as "Confirmed"
    trip.status = "Confirmed"

    db.session.commit()

    flash("Your custom trip has been confirmed and booked!", "success")
    return redirect(url_for('my_custom_trips'))


# Delete Trip
@app.route('/delete-custom-trip/<int:trip_id>')
@login_required
def delete_custom_trip(trip_id):
    trip = CustomTrip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        flash("You are not allowed to delete this trip.", "danger")
        return redirect(url_for('my_custom_trips'))

    db.session.delete(trip)
    db.session.commit()
    flash("Trip deleted successfully!", "success")
    return redirect(url_for('my_custom_trips'))

# app.py (Socket.IO Handlers)

# Handle user connecting
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        print(f"User {current_user.id} connected")
        # Join a room unique to this user for private messaging
        join_room(f'user_{current_user.id}')
        if current_user.is_admin:
            # Admins join a general admin room for broadcasts
            join_room('admin_room')
    else:
        # Reject connection if not authenticated
        return False

# Handle user disconnecting
@socketio.on('disconnect')
def handle_disconnect():
    print(f"User {current_user.id} disconnected")

# Handle sending a new message
@socketio.on('send_message')
def handle_send_message(data):
    """Handles sending a message from either user or admin."""
    if not current_user.is_authenticated:
        return

    user_id = data.get('user_id') # For admin, this is the target user's ID
    content = data.get('content', '').strip()

    if not content:
        return

    # Find or create a chat session
    if current_user.is_admin:
        # Admin is sending to a specific user
        target_user_id = user_id
        session = ChatSession.query.filter_by(user_id=target_user_id, is_active=True).first()
        if not session:
            # Create a new session if none exists
            session = ChatSession(user_id=target_user_id)
            db.session.add(session)
            db.session.commit()
        is_admin_msg = True
        sender_room = f'user_{target_user_id}' # Send to the specific user's room
        receiver_room = 'admin_room' # Also send to all admins for their live view
    else:
        # User is sending to admin
        session = ChatSession.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not session:
            session = ChatSession(user_id=current_user.id)
            db.session.add(session)
            db.session.commit()
        target_user_id = current_user.id
        is_admin_msg = False
        sender_room = 'admin_room' # Send to all admins
        receiver_room = f'user_{target_user_id}' # Also send back to the user for their live view

    # Create and save the new message
    new_message = Message(
        session_id=session.id,
        is_admin_message=is_admin_msg,
        content=content
    )
    db.session.add(new_message)
    session.updated_at = datetime.utcnow() # Update the session's last activity
    db.session.commit()

    # Prepare data to send back to clients
    message_data = {
        'message_id': new_message.id,
        'session_id': session.id,
        'sender_name': current_user.username,
        'is_admin': is_admin_msg,
        'content': content,
        'timestamp': new_message.timestamp.strftime("%Y-%m-%d %H:%M"),
        'is_read': new_message.is_read
    }

    # Emit the new message to the relevant rooms
    emit('receive_message', message_data, room=sender_room)
    if sender_room != receiver_room: # Avoid duplicate sends if admin is messaging themselves
        emit('receive_message', message_data, room=receiver_room)

# Handle marking messages as read (for admin)
@socketio.on('mark_messages_read')
def handle_mark_read(data):
    """Marks all messages from a user in a session as read."""
    if not current_user.is_authenticated or not current_user.is_admin:
        return

    session_id = data.get('session_id')
    user_id = data.get('user_id')

    # Find the session and mark all user messages as read
    if session_id:
        session = ChatSession.query.get(session_id)
    elif user_id:
        session = ChatSession.query.filter_by(user_id=user_id, is_active=True).first()
    else:
        return

    if session:
        # Mark all unread messages from the user (not admin) as read
        Message.query.filter_by(session_id=session.id, is_admin_message=False, is_read=False).update({'is_read': True})
        db.session.commit()

        # Notify the user that their messages have been read (optional)
        emit('messages_read', {'session_id': session.id}, room=f'user_{session.user_id}')
        print(f"Marked messages read for session {session.id}")


# =======================
# Run App
# =======================
# app.py (at the very bottom)
if __name__ == '__main__':
    socketio.run(app, debug=True)