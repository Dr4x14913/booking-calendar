# Booking Calendar

A Flask-based reservation system for vacation rentals with automated email confirmations and admin management.

## Features

- **Public Booking Interface**: Users can browse available dates and submit reservations
- **Admin Dashboard**: Manage booked dates, pricing, and website configuration
- **Email Notifications**: Automatic confirmation emails to both customers and owners
- **Date Validation**: API endpoints for allowed start dates and forbidden end dates
- **Rate Limiting**: Protection against abuse with configurable limits

## Tech Stack

- Python 3.13
- Flask framework
- Docker & Docker Compose
- Pandas (pricing data)
- Flask-Login, Flask-Mail, Flask-Limiter

## Setup

### Environment Variables

Required `.env` file:

```bash
SMTP_USERNAME=your_email@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_PASSWORD=your_app_password
DEFAULT_SENDER=admin@email.com
SECRET_KEY=your-secret-key
```

### Run with Docker

```bash
docker-compose up --build
```

Access the app at `http://localhost:5000`

## Default Admin Credentials

- Username: `admin`
- Password: `toto` (change immediately after first login)

## Admin Routes

- `/admin` - Login page
- `/admin_dashboard` - Manage bookings, prices, and settings
- `/change-password` - Update admin password

## API Endpoints

- `GET /api/get-allowed-start-dates` - Available booking start dates
- `GET /api/get-forbidden-end-dates?start_date=YYYY-MM-DD` - Forbidden end dates
- `POST /api/get-price` - Calculate total price (body: `{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}`)
- `GET /api/get-booked-dates` - All booked dates

## Data Storage

All persistent data stored in `/app_data` volume:

- `booked_dates.json` - Reserved dates
- `prices.csv` - Pricing calendar (per night, per duration)
- `config.json` - Admin password & website settings

## Disclaimer

The front end is all vibe coded but i mostly coded the back
