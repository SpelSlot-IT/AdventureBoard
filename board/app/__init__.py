import site
# add path to installed packages to PATH:
site.addsitedir('/mnt/web105/e0/90/517590/htdocs/.local/lib/python3.11/site-packages')
import json, os
from flask import Flask
from flask_smorest import Api
from flask_talisman import Talisman
import logging

from .provider import db, ma, ap_scheduler, login_manager, google_oauth
from .models import *
from .util import *
from .api import *

def create_app(config_file=None):
    # --- Launch app --- 
    app = Flask(__name__)
    app.logger.info(f"App running in {os.getenv('FLASK_ENV')} mode")

    # load config
    if not config_file:
        config_file = os.getenv("APP_CONFIG", "config/config.json")
    app.config.from_file(config_file, load=json.load)
    config = app.config
    app.secret_key = config["APP"]["secret_key"]
    config["API_VERSION"] = f"v{config['VERSION']['version']}" if config["VERSION"]["version"] else "version-undefined"

    # configure logger
    level_name = config['APP']['log_level']
    app.logger.setLevel(getattr(logging, level_name.upper(), logging.WARNING))
    app.logger.info(f"App logging level set to: {level_name}")

    # configure WSGI middleware
    if config["APP"]["behind_proxy"]:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
        app.config['PREFERRED_URL_SCHEME'] = config["APP"]["behind_proxy"]
        app.logger.info(f"App running behind proxy: {config['APP']['behind_proxy']}")


    # --- Database setup ---
    # Dynamically construct the SQLALCHEMY_DATABASE_URI from app.config['DB']
    db_conf = config['DB']

    # Handle SQLite separately since it has a different format
    if db_conf["flavor"].startswith("sqlite"):
        uri = f"{db_conf['flavor']}:///{db_conf['database']}.db"
    else:
        uri = (
            f"{db_conf['flavor']}://{db_conf['user']}:{db_conf['password']}"
            f"@{db_conf['host']}/{db_conf['database']}"
        )

    config["SQLALCHEMY_DATABASE_URI"] = uri

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


    # --- Cronjobs ---   
    a_d, a_h = config['TIMING']['assignment_day'].split("@")
    r_d, r_h = config['TIMING']['release_day'].split("@")

    @ap_scheduler.task('cron', id='make_assignments', day_of_week=a_d, hour=a_h)
    def cron_make_assignments():
        with app.app_context():
            assign_players_to_adventures()

    @ap_scheduler.task('cron', id='release_assignment', day_of_week=r_d, hour=r_h)
    def cron_release_assignments():
        with app.app_context():
            release_assignments()

    return app