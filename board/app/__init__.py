import site
# add path to installed packages to PATH:
site.addsitedir('/mnt/web105/e0/90/517590/htdocs/.local/lib/python3.11/site-packages')
import json, os
from flask import Flask, jsonify, send_from_directory, url_for, render_template, g
from flask_smorest import Api
from flask_talisman import Talisman
from apispec.ext.marshmallow import MarshmallowPlugin

from .provider import db, ma, ap_scheduler, login_manager, google_oauth
from .models import *
from .util import *
from .api import *

def create_app(config_file=None):
    # --- Launch app --- 
    app = Flask(__name__)
    app.logger.info(f"App running in {os.getenv('FLASK_ENV')} mode")

    if not config_file:
        config_file = os.getenv("APP_CONFIG", "config/config.json")

    app.config.from_file(config_file, load=json.load)
    config = app.config
    app.secret_key = config["APP"]["secret_key"]
    config["API_VERSION"] = f"v{config['VERSION']['version']}" if config["VERSION"]["version"] else "version-undefined"

    if config["APP"]["behind_proxy"]:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
        app.config['PREFERRED_URL_SCHEME'] = config["APP"]["behind_proxy"]
        app.logger.warning(f"App running behind proxy: {config['APP']['behind_proxy']}")

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

    # --- Security headers ---
    talisman = Talisman(app)
    talisman.content_security_policy = config['APP']['content_security_policy']

    # --- Basic provider routs ---
    @app.route('/')
    def system_check():
        return send_from_directory('.', 'index.html')

    @app.route('/app')
    def dashboard():
        return render_template('app.html')

    @app.route('/help')
    def send_help():
        return render_template('help.html')

    @app.route('/profile/me')
    def view_own_profile():
        return render_template('profile.html', user_id="me")

    @app.route('/profile/<int:user_id>')
    def view_profile(user_id):
        return render_template('profile.html', user_id=user_id)

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

    return app