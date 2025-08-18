from flask import Flask, render_template, redirect, url_for, flash, request , jsonify 
from config import Config
from models import db, User, TourPackage, HomeImage , Booking 
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



# ----------------------------
# App Initialization
# ----------------------------
app = Flask(__name__)
app.config.from_object(Config)

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
# =======================
# Run App
# =======================
if __name__ == '__main__':
    app.run(debug=True)
