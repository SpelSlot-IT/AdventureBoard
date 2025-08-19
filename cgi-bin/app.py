import site
# add path to installed packages to PATH:
site.addsitedir('/mnt/web105/e0/90/517590/htdocs/.local/lib/python3.11/site-packages')
import json
from flask import Flask, jsonify, send_from_directory, url_for, render_template, g
from flask_smorest import Api

from provider import db, ma, ap_scheduler, login_manager, google_oauth
from models import *
from util import *
from api import *

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

# --- Launch app --- 
app = Flask(__name__)
conf_file = "config.json"
if __name__ == '__main__':
    # will only be executed if run local
    conf_file = "config.local.json"
app.config.from_file(conf_file, load=json.load)
config = app.config
app.secret_key = config["APP"]["secret_key"]
config["API_VERSION"] = f"v{config['VERSION']['version']}" if config["VERSION"]["version"] else "version-undefined"

# --- Database setup ---
# Dynamically construct the SQLALCHEMY_DATABASE_URI from app.config['DB']
db_conf = config['DB']
config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_conf['user']}:{db_conf['password']}@{db_conf['host']}/{db_conf['database']}"

db.init_app(app)
with app.app_context():
    db.create_all()

# --- (De)Serialization setup ---
ma.init_app(app)
api = Api(app)
for blp in api_blueprints:
    api.register_blueprint(blp)

# --- APScheduler setup --- 
ap_scheduler.init_app(app)
ap_scheduler.start()

# --- Google OAuth setup ---
google_oauth.init_app(app)

# --- User session management setup --- 
# https://flask-login.readthedocs.io/en/latest
login_manager.init_app(app)
# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)
login_manager.anonymous_user = Anonymous


# --- Basic provider routs ---
@app.route('/')
def system_check():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('../static', path)

@app.route('/external/<path:path>')
def send_external(path):
    return send_from_directory('../external', path)

@app.route('/app')
def dashboard():
    return send_from_directory('../public', 'app.html')

@app.route('/help')
def send_help():
    return send_from_directory('../public', 'help.html')

# --- Cron ---   
a_d, a_h = config['TIMING']['assignment_day'].split("@")
r_d, r_h = config['TIMING']['release_day'].split("@")
re_d, re_h = config['TIMING']['reset_day'].split("@")

@ap_scheduler.task('cron', id='make_assignments', day_of_week=a_d, hour=a_h)
def cron_make_assignments():
    assign_players_to_adventures()

@ap_scheduler.task('cron', id='release_assignment', day_of_week=r_d, hour=r_h)
def cron_release_assignments():
    release_assignments()

@ap_scheduler.task('cron', id='reset_release', day_of_week=re_d, hour=re_h)
def cron_reset_release():
    reset_release()

# --- Local ---
if __name__ == '__main__':
    # will only be executed if run local
    import webbrowser
    import os
    app.secret_key = os.urandom(24)
    webbrowser.open("https://localhost:5000/")
    app.run(ssl_context='adhoc')


