from flask import Flask, send_from_directory, render_template, flash, redirect, url_for, request, jsonify
import json
import os
from pathlib import Path
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
from flask_wtf import FlaskForm
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import re

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

@app.route('/update-prices', methods=['POST'])
@login_required
def update_prices():
    """Handle price updates from admin panel"""
    prices_data = request.form.get("prices")
    if prices_data:
      cols = ['date', '1 nigth', '2 nigth', '3 nigth', '4 nigth', '5 nigth', '6 nigth', '7 nigth', 'additional nigth']
      df = pd.read_csv(StringIO(prices_data) , sep=' ', names=cols, header=None)
    set_prices(df)
    return redirect("/admin_dashboard")

@app.route('/admin_dashboard')
@login_required
def admin():
    booked_dates = get_booked_dates()
    prices = get_prices().to_csv(sep=" ", index=False, header=None)

    return render_template('admin_panel.html', bookedDatesJson=booked_dates, pricesCsv=prices)

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
#--------------------------------------------------------------------------------
@app.route('/api/get-allowed-start-dates', methods=['GET'])
def get_allowed_start_dates():
  prices = get_prices()
  return jsonify(list(prices['date']))


@app.route('/api/get-forbidden-end-dates', methods=['GET'])
def get_forbidden_end_dates():
  try:
    if not 'start_date' in request.args:
      return jsonify({"error": "Missing start_date get argument"}), 400
    start_date        = request.args.get('start_date')
    prices            = get_prices()
    df                = prices.loc[prices["date"] == start_date]
    not_allowed       = [int(i.replace(' nigth', '')) for i in df.columns[df.eq(-1).any()]]
    start_datetime    = datetime.strptime(start_date, "%Y-%m-%d")
    not_allowed_dates = [(start_datetime + timedelta(days=i)).strftime("%Y-%m-%d") for i in not_allowed]
    return jsonify(not_allowed_dates)
  except Exception as e:
    return jsonify({"error": f"{e}"}), 500

@app.route('/api/get-price', methods=['POST'])
def get_price():
  try:
    args       = request.get_json()
    start_date = args["start_date"]
    end_date   = args["end_date"]
    duration = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
    prices = get_prices()
    try:
      price = int(prices.loc[prices["date"] == start_date][f"{duration} nigth"].iloc[0])
    except IndexError:
      return jsonify({
        "success": True, "total_price": "?", "details": "Les dates selectionées ne sont pas standard, veilliez contacter le propriétaie."}
      )
    else:
      return jsonify({
        "success": True, "total_price": price, "details": ""}
      )
  except Exception as e:
    return jsonify({
      "success": False, "total_price": "Unknown", "details": "Fail to process data"}
    ), 500

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

def set_prices(price_data):
    """Store price data in JSON file"""
    csv_file = "/app/prices.csv"
    price_data["date"] = price_data['date'].str.replace("/","-")
    price_data["date"] = price_data['date'].apply(lambda x: re.sub(r"(\d{2})-(\d{2})-(\d{4})", r"\3-\2-\1",x))
    price_data.to_csv(csv_file, index=False, sep=';')

def get_prices():
    """Retrieve price data from JSON file"""
    csv_file = "/app/prices.csv"
    if not Path(csv_file).exists():
      return pd.DataFrame()

    prices = pd.read_csv(csv_file, sep=';')
    return prices

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

