from flask import Flask, send_from_directory, render_template, flash, redirect, url_for, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from io import StringIO
import locale
import json
import os
import re
from email_validator import validate_email, EmailNotValidError

#---------------------------------------------------------------------------------
#-- MAIN APP
#---------------------------------------------------------------------------------
locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
C_STANDARD_DATE_FMT = "%Y-%m-%d"
C_PRETTY_DATE_FMT   = "%A %d %b %Y"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'fallback-super-secret'

C_SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
if C_SMTP_USERNAME is None:
  raise Exception("Please set SMTP_USERNAME env var")
C_SMTP_HOST = os.environ.get("SMTP_HOST")
if C_SMTP_HOST is None:
  raise Exception("Please set SMTP_HOST env var")
C_SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
if C_SMTP_PASSWORD is None:
  raise Exception("Please set SMTP_PASSWORD env var")
C_SMTP_PORT = os.environ.get("SMTP_PORT")
if C_SMTP_PORT is None:
  raise Exception("Please set SMTP_PORT env var")
if os.environ.get("DEFAULT_SENDER") is not None:
  C_DEFAULT_SENDER = os.environ.get("DEFAULT_SENDER")
elif os.environ.get("DEFAULT_SENDER") is None and "@" not in C_SMTP_USERNAME:
  raise Exception("Please set the DEFAULT_SENDER email address")
else:
  C_DEFAULT_SENDER = C_SMTP_USERNAME

#---------------------------------------------------------------------------------
#-- LIMITER
#---------------------------------------------------------------------------------
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # Limits by client IP
    default_limits=["200 per day", "50 per hour"]  # Default limits
)
#---------------------------------------------------------------------------------
#-- Configuration for Flask-Mail
#---------------------------------------------------------------------------------
app.config['MAIL_SERVER']         = C_SMTP_HOST
app.config['MAIL_PORT']           = C_SMTP_PORT
app.config['MAIL_USE_TLS']        = os.environ.get("SMTP_TLS", True)
app.config['MAIL_USE_SSL']        = os.environ.get("SMTP_SSL", False)
app.config['MAIL_USERNAME']       = C_SMTP_USERNAME
app.config['MAIL_PASSWORD']       = C_SMTP_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = C_DEFAULT_SENDER
mail = Mail(app)

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

@app.route('/update-website-config', methods=['POST'])
@login_required
def update_website_config():
    """Handle website configuration updates from admin panel"""
    website_title = request.form.get("website_title", "")
    icon_url = request.form.get("icon_url", "")

    config = {
        "website_title": website_title,
        "icon_url": icon_url
    }
    set_website_config(config)
    return redirect("/admin_dashboard")

@app.route('/update-prices', methods=['POST'])
@login_required
def update_prices():
    """Handle price updates from admin panel"""
    prices_data = request.form.get("prices")
    if prices_data:
      cols = ['date', '1 nigth', '2 nigth', '3 nigth', '4 nigth', '5 nigth', '6 nigth', '7 nigth', 'additional nigth']
      df = pd.read_csv(StringIO(prices_data) , sep=r'\s+', names=cols, header=None)
    set_prices(df)
    return redirect("/admin_dashboard")

@app.route('/admin_dashboard')
@login_required
def admin():
    booked_dates = get_booked_dates()
    prices = get_prices().to_csv(sep=" ", index=False, header=None)
    website_config = get_website_config()
    return render_template('admin_panel.html', bookedDatesJson=booked_dates, pricesCsv=prices, website_config=website_config)

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
#-- API Routes
#--------------------------------------------------------------------------------
@app.route('/api/get-allowed-start-dates', methods=['GET'])
def get_allowed_start_dates():
  allowed = get_allowed_start_dates()
  return jsonify(allowed)

@app.route('/api/get-forbidden-end-dates', methods=['GET'])
def get_forbidden_end_dates():
  try:
    if not 'start_date' in request.args:
      return jsonify({"error": "Missing start_date get argument"}), 400
    start_date        = request.args.get('start_date')
    prices            = get_prices()
    df                = prices.loc[prices["date"] == start_date]
    not_allowed       = [int(i.replace(' nigth', '')) for i in df.columns[df.eq(-1).any()]]
    start_datetime    = datetime.strptime(start_date, C_STANDARD_DATE_FMT)
    not_allowed_dates = [(start_datetime + timedelta(days=i)).strftime(C_STANDARD_DATE_FMT) for i in not_allowed]
    return jsonify(not_allowed_dates)
  except Exception as e:
    return jsonify({"error": f"{e}"}), 500

@app.route('/api/get-price', methods=['POST'])
def get_price():
  try:
    args       = request.get_json()
    start_date = args["start_date"]
    end_date   = args["end_date"]
    duration = (datetime.strptime(end_date, C_STANDARD_DATE_FMT) - datetime.strptime(start_date, C_STANDARD_DATE_FMT)).days
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

@app.route('/api/get-booked-dates', methods=['GET'])
def get_booked_dates_api():
    return jsonify(get_booked_dates())

#---------------------------------------------------------------------------------
#-- Routes
#--------------------------------------------------------------------------------
@app.route('/')
def serve_index():
  booked_dates_shown = []
  booked_dates = get_booked_dates()
  for i in booked_dates:
    if not (datetime.strptime(i, C_STANDARD_DATE_FMT) + timedelta(days=1)).strftime(C_STANDARD_DATE_FMT) in booked_dates:
      continue
    booked_dates_shown.append(i)
  return render_template('index.html', bookedDatesJson=booked_dates_shown)

@app.route('/reservation-form')
def reservation_form():
    email      = request.args.get('email', '')
    people     = request.args.get('people', 2)
    firstname  = request.args.get('firstname', '')
    lastname   = request.args.get('lastname', '')
    comment    = request.args.get('comment', '')
    start_date = request.args.get('start_date', '')
    end_date   = request.args.get('end_date', '')
    phone      = request.args.get('phone', '')
    address    = request.args.get('address', '')
    duration   = (datetime.strptime(end_date, C_STANDARD_DATE_FMT) - datetime.strptime(start_date, C_STANDARD_DATE_FMT)).days
    prices     = get_prices()
    try:
      price = int(prices.loc[prices["date"] == start_date][f"{duration} nigth"].iloc[0])
    except IndexError:
        price  = "Inconnu"
    return render_template('reservation-form.html',
                         start_date=datetime.strptime(start_date, C_STANDARD_DATE_FMT).strftime(C_PRETTY_DATE_FMT),
                         end_date=datetime.strptime(end_date, C_STANDARD_DATE_FMT).strftime(C_PRETTY_DATE_FMT),
                         people=people,
                         firstname=firstname,
                         lastname=lastname,
                         comment=comment,
                         phone=phone,
                         address=address,
                         email=email,
                         price=price)

@app.route('/submit-reservation', methods=['POST'])
@limiter.limit("10 per day")
def submit_reservation():
    start_date = request.form.get('start_date')
    end_date   = request.form.get('end_date')
    price      = request.form.get('price')
    people     = request.form.get('people')
    firstname  = request.form.get('firstname')
    lastname   = request.form.get('lastname')
    email      = request.form.get('email')
    phone      = request.form.get('phone', '')
    address    = request.form.get('address', '')
    comment    = request.form.get('comment', '')

    # Validate email format using email-validator
    try:
        emailinfo = validate_email(email, check_deliverability=True)
        email     = emailinfo.normalized  # Use normalized email
    except EmailNotValidError as e:
        start_date = datetime.strptime(start_date, C_PRETTY_DATE_FMT).strftime(C_STANDARD_DATE_FMT),
        end_date   = datetime.strptime(end_date, C_PRETTY_DATE_FMT).strftime(C_STANDARD_DATE_FMT),
        flash('Veuillez entrer une adresse email valide.', 'error')
        return redirect(url_for('reservation_form',
                               start_date=start_date,
                               end_date=end_date,
                               people=people,
                               firstname=firstname,
                               lastname=lastname,
                               comment=comment,
                               phone=phone,
                               address=address,
                               email=email,
                        ))

    # Get website configuration for email template
    website_config = get_website_config()

    # Send confirmation email to customer
    subject = f"Demande de réservation - {start_date} au {end_date}"
    website_title = website_config.get('website_title', '')
    if website_title:
        subject = f"[{website_title}] " + subject
    body = render_template('reservation-email.html',
                       start_date=start_date,
                       end_date=end_date,
                       price=price,
                       people=people,
                       email=email,
                       firstname=firstname,
                       lastname=lastname,
                       phone=phone,
                       address=address,
                       comment=comment,
                       to_customer=True,
                       website_title=website_title,
                       icon_url=website_config.get('icon_url', ''),
                    )

    # Send confirmation email to owner
    subject_owner = f"Demande de réservation - {start_date} au {end_date}"
    body_owner = render_template('reservation-email.html',
                       start_date=start_date,
                       end_date=end_date,
                       price=price,
                       people=people,
                       email=email,
                       firstname=firstname,
                       lastname=lastname,
                       phone=phone,
                       address=address,
                       comment=comment,
                       to_customer=False,
                       website_title=website_title,
                       icon_url=website_config.get('icon_url', ''),
                    )
    try:
      msg = Message(subject, recipients=[email])
      msg.html = body
      mail.send(msg)

      msg = Message(subject_owner, recipients=[C_DEFAULT_SENDER])
      msg.html = body_owner
      mail.send(msg)
    except Exception as e:
      return render_template('error.html', error=f'{e}', error_message=f'Rééssayez plus tard ou contactez directement {os.environ.get("GMAIL_EMAIL")}', error_title="Une erreur est survenue pendant la reservation")
    else:
      return render_template('reservation-success.html', message="Demande de réservation envoyé ! Vous allez recevoir prochainement un email de comfimation.")
#---------------------------------------------------------------------------------
#-- FUNCTIONS
#---------------------------------------------------------------------------------
def get_allowed_start_dates():
  prices_dates = [datetime.strptime(i, C_STANDARD_DATE_FMT) for i in list(get_prices()['date'])]
  booked_dates = [datetime.strptime(i, C_STANDARD_DATE_FMT) for i in get_booked_dates()]
  allowed = []
  for date in prices_dates:
    if date in booked_dates:
      if not date + timedelta(days=1) in booked_dates: # is the next day free
        allowed.append(date.strftime(C_STANDARD_DATE_FMT))
        continue
      continue
    allowed.append(date.strftime(C_STANDARD_DATE_FMT))
  return allowed

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
    price_data.sort_values("date", inplace=True)
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

def get_website_config():
    """Retrieve website configuration from JSON file"""
    json_file = "/app/website_config.json"
    if not Path(json_file).exists():
        # Create default config file if it doesn't exist
        default_config = {"website_title": "", "icon_url": ""}
        set_website_config(default_config)

    with open(json_file, "r") as f:
        return json.load(f)

def set_website_config(config):
    """Store website configuration in JSON file"""
    json_file = "/app/website_config.json"
    with open(json_file, "w") as f:
        json.dump(config, f)

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

