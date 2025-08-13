from flask_marshmallow import Marshmallow
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

import requests
from oauthlib.oauth2 import WebApplicationClient

ap_scheduler = APScheduler()
ma = Marshmallow()
db = SQLAlchemy()
login_manager = LoginManager()

class GoogleOAuth:
    def __init__(self, app=None):
        self.client = None
        self.provider_cfg = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.client = WebApplicationClient(app.config["GOOGLE"]["client_id"])
        self.provider_cfg = requests.get(app.config["GOOGLE"]["discovery_url"]).json()
        app.extensions = getattr(app, "extensions", {})
        app.extensions["google_oauth"] = self
google_oauth = GoogleOAuth()

