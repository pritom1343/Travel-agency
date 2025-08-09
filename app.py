from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, User, TourPackage
from forms import RegistrationForm, LoginForm, TourPackageForm , AdminLoginForm
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from forms import EditProfileForm
import os
from werkzeug.utils import secure_filename 



# --- App and Config ---
app = Flask(__name__)
app.config.from_object(Config)

# --- Extensions ---
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- User Loader for Login Manager ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =======================
# User-Facing Routes
# =======================

@app.route('/')
def home():
    return render_template('home.html')


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
        return redirect(url_for('user_dashboard'))  # Redirect if already logged in

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('user_dashboard'))  # Redirect to user dashboard
        else:
            flash("Invalid email or password.", "danger")

    return render_template('login.html', form=form)

@app.route('/user-dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        flash("Redirected to admin dashboard.", "info")
        return redirect(url_for('dashboard'))

    return render_template('user_dashboard.html', user=current_user)


@app.route('/admin/tour-packages')
@login_required
def admin_tour_packages():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))
    packages = TourPackage.query.all()
    return render_template('admin_tour_packages.html', packages=packages)

@app.route('/admin/tour-packages/add', methods=['GET', 'POST'])
@login_required
def add_tour_package():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    form = TourPackageForm()
    if form.validate_on_submit():
        filename = None
        if form.image_file.data:
            filename = secure_filename(form.image_file.data.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.image_file.data.save(filepath)

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
        flash("Tour package added successfully!", "success")
        return redirect(url_for('admin_tour_packages'))

    return render_template('add_tour_package.html', form=form)

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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


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
    print(users)
    return render_template('dashboard.html', users=users)

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

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.age = form.age.data
        current_user.gender = form.gender.data
        current_user.occupation = form.occupation.data
        current_user.education = form.education.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    # Pre-fill form with current user data
    form.full_name.data = current_user.full_name
    form.age.data = current_user.age
    form.gender.data = current_user.gender
    form.occupation.data = current_user.occupation
    form.education.data = current_user.education

    return render_template('edit_profile.html', form=form)


@app.route('/admin/tours')
@login_required
def manage_tours():
    if current_user.username != 'admin':
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    tours = TourPackage.query.all()
    return render_template('admin/manage_tours.html', tours=tours)


@app.route('/admin/tours/add', methods=['GET', 'POST'])
@login_required
def add_tour():
    if current_user.username != 'admin':
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    form = TourPackageForm()
    if form.validate_on_submit():
        tour = TourPackage(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            duration=form.duration.data,
            price=form.price.data
        )
        db.session.add(tour)
        db.session.commit()
        flash("Tour package added successfully!", "success")
        return redirect(url_for('manage_tours'))

    return render_template('admin/add_tour.html', form=form)


@app.route('/admin/tours/edit/<int:tour_id>', methods=['GET', 'POST'])
@login_required
def edit_tour(tour_id):
    if current_user.username != 'admin':
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    tour = TourPackage.query.get_or_404(tour_id)
    form = TourPackageForm(obj=tour)
    if form.validate_on_submit():
        form.populate_obj(tour)
        db.session.commit()
        flash("Tour package updated successfully.", "success")
        return redirect(url_for('manage_tours'))

    return render_template('admin/edit_tour.html', form=form)


@app.route('/admin/tours/delete/<int:tour_id>')
@login_required
def delete_tour(tour_id):
    if current_user.username != 'admin':
        flash("Access Denied: Admins only!", "danger")
        return redirect(url_for('home'))

    tour = TourPackage.query.get_or_404(tour_id)
    db.session.delete(tour)
    db.session.commit()
    flash("Tour package deleted successfully.", "success")
    return redirect(url_for('manage_tours'))


# =======================
# Run App
# =======================
if __name__ == '__main__':
    app.run(debug=True)
