from flask import Flask, send_from_directory, render_template, flash, redirect, url_for, request
import json
import os
from pathlib import Path
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
from flask_wtf import FlaskForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'fallback-super-secret'
#---------------------------------------------------------------------------------
#-- CLASSES FOR FLASK LOGIN
#---------------------------------------------------------------------------------
class AdminUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id  # Flask-Login requires 'id' attribute

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":  # only one valid user
        return AdminUser(user_id)
    return None
#---------------------------------------------------------------------------------
#-- Admin routes
#---------------------------------------------------------------------------------
@app.route('/update-dates', methods=['POST'])
@login_required
def update_dates():
    new_dates = request.form.get("booked_dates").replace(" ","").split(",")
    set_booked_dates(new_dates)
    return redirect("/admin_dashboard")

@app.route('/admin_dashboard')
@login_required
def admin():
    booked_dates = get_booked_dates()
    print(booked_dates, flush=True)
    return render_template('admin_panel.html', bookedDatesJson=booked_dates)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect('/admin_dashboard')

    form = LoginForm()
    if form.validate_on_submit():
        if (form.username.data == "admin" and
            check_password_hash(get_hashed_password(), form.password.data)):
            user = AdminUser("admin")
            login_user(user)
            return redirect('/admin_dashboard')
        else:
            flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        # Verify current password
        if not check_password_hash(get_hashed_password(), current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('change_password'))

        # Update password
        set_hashed_password(new_password)
        flash('Password changed successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('change_password.html', form=form)

@app.route('/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

#---------------------------------------------------------------------------------
#-- Routes
#---------------------------------------------------------------------------------
@app.route('/')
def serve_index():
    booked_dates = get_booked_dates()
    return render_template('index.html', bookedDatesJson=booked_dates)
#---------------------------------------------------------------------------------
#-- FUNCTIONS
#---------------------------------------------------------------------------------
def set_booked_dates(dates):
    json_file = "/app/booked_dates.json"
    with open(json_file, "w") as f:
        json.dump(dates, f)

def get_booked_dates():
    json_file = "/app/booked_dates.json"
    if not Path(json_file).exists():
        with open(json_file, "w") as f:
            json.dump([], f)

    with open(json_file, "r") as f:
        return json.load(f)

def get_hashed_password():
    json_file = "/app/password_config.json"
    if not Path(json_file).exists():
        # Create default password file if it doesn't exist
        default_password = os.environ.get('DEFAULT_PASSWORD', 'toto')
        set_hashed_password(default_password)

    with open(json_file, "r") as f:
        config = json.load(f)
        return config.get("hashed_password", "")

def set_hashed_password(password):
    json_file = "/app/password_config.json"
    hashed_password = generate_password_hash(password)
    config = {"hashed_password": hashed_password}
    with open(json_file, "w") as f:
        json.dump(config, f)
#---------------------------------------------------------------------------------
#-- MAIN
#---------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

