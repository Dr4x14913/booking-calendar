from flask import Flask, send_from_directory, render_template, flash, redirect, url_for, request
import json
import os
from pathlib import Path
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'fallback-super-secret'

HASHED_PASSWORD = 'scrypt:32768:8:1$xxnzWKJVYVZb9gAx$7ac30bebe582b4c63879304eb80dcbfb91f00a25996b454558045ce4b29254ce9265379a00eff1ba4b8d63134f3029c520c05c64882bc5dece0507810050e61d' # hash for 'toto'
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
            check_password_hash(HASHED_PASSWORD, form.password.data)):
            user = AdminUser("admin")
            login_user(user)
            return redirect('/admin_dashboard')
        else:
            flash('Invalid username or password')
    return render_template('login.html', form=form)

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
#---------------------------------------------------------------------------------
#-- MAIN
#---------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

