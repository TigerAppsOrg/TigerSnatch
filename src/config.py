# ----------------------------------------------------------------------
# config.py
# Contains various credentials for API and database access.
# ----------------------------------------------------------------------

from os import environ

# TigerSnatch host URL
TS_HOST = "localhost"
TS_DOMAIN = environ["TS_DOMAIN"]

# primary MongoDB server connection string
DB_CONNECTION_STR = environ["DB_CONNECTION_STR"]

# set of collections that are in a proper tigersnatch database
COLLECTIONS = {
    "mappings",
    "courses",
    "users",
    "waitlists",
    "enrollments",
    "admin",
    "logs",
    "system",
}

# MobileApp keys
CONSUMER_KEY = environ["CONSUMER_KEY"]
CONSUMER_SECRET = environ["CONSUMER_SECRET"]

# CAS key
APP_SECRET_KEY = b"N|\x193\\\xb8\xdaTc\x89\x15r\xb0-\xbb\x02"

# Heroku API key
HEROKU_API_KEY = environ["HEROKU_API_KEY"]

# Heroku app name
HEROKU_APP_NAME = environ["HEROKU_APP_NAME"]

# TigerSnatch email and password
TS_EMAIL = environ["TS_EMAIL"]
TS_PASSWORD = environ["TS_PASSWORD"]

# TigerSnatch SendGrid API key
SENDGRID_API_KEY = environ["SENDGRID_API_KEY"]

# minimum time interval on which new course data is fetched (triggered)
# on the front end web interface
COURSE_UPDATE_INTERVAL_MINS = float(environ["COURSE_UPDATE_INTERVAL_MINS"])

# minimum time interval on which new slots are checked and notifications
# are sent
NOTIFS_INTERVAL_SECS = int(environ["NOTIFS_INTERVAL_SECS"])

# maximum number of sections a user can be on waitlists for
MAX_WAITLIST_SIZE = int(environ["MAX_WAITLIST_SIZE"])

# maximum number of entries in custom user logs
MAX_LOG_LENGTH = MAX_WAITLIST_SIZE * 2

# maximum number of entries in admin panel logs
MAX_ADMIN_LOG_LENGTH = int(environ["MAX_ADMIN_LOG_LENGTH"])

# interval on which the notifications scheduling spreadsheet is polled
NOTIFS_SHEET_POLL_MINS = int(environ["NOTIFS_SHEET_POLL_MINS"])

# Twilio SMS
TWILIO_PHONE = environ["TWILIO_PHONE"]
TWILIO_SID = environ["TWILIO_SID"]
TWILIO_TOKEN = environ["TWILIO_TOKEN"]

# offset in minutes that is added to all provided notifications start times
# (this was an OIT request to alleviate load on endpoints during the first few minutes of enrollment)
OIT_NOTIFS_OFFSET_MINS = int(environ["OIT_NOTIFS_OFFSET_MINS"])

# Dead Man's Snitch URL (see heroku addons)
DMS_URL = environ["DMS_URL"]
