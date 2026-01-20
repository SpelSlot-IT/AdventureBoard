from pathlib import Path
import json
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app import provider
from app.provider import db
from app.models import User


@pytest.fixture()
def app(tmp_path, monkeypatch):
    try:
        provider.ap_scheduler.shutdown(wait=False)
    except Exception:
        pass

    monkeypatch.setattr(provider.ap_scheduler, "start", lambda *args, **kwargs: None)

    def fake_discovery_request(_url):
        class DummyResponse:
            def json(self):
                return {
                    "authorization_endpoint": "https://example.com/auth",
                    "token_endpoint": "https://example.com/token",
                    "userinfo_endpoint": "https://example.com/userinfo",
                }

        return DummyResponse()

    monkeypatch.setattr(provider.requests, "get", fake_discovery_request)

    config = {
        "VERSION": {"version": "test"},
        "APP": {
            "secret_key": "test-secret",
            "timeout_hours": 2,
            "content_security_policy": {"default-src": "'self'"},
            "behind_proxy": False,
            "log_level": "WARNING",
        },
        "EMAIL": {"active": False},
        "DB": {
            "flavor": "sqlite",
            "database": str(tmp_path / "test_db"),
        },
        "TIMING": {"assignment_day": "Sun@12", "release_day": "Mon@12"},
        "SCHEDULER_API_ENABLED": True,
        "GOOGLE": {
            "discovery_url": "https://example.com/.well-known/openid-configuration",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
        "API_TITLE": "Adventure Board API",
        "OPENAPI_URL_PREFIX": "/openapi",
        "OPENAPI_VERSION": "3.0.2",
        "OPENAPI_SWAGGER_UI_PATH": "/docs",
        "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
        "API_SPEC_OPTIONS": {"servers": [{"url": "http://localhost"}]},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))

    app = create_app(str(config_path))
    app.testing = True

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
    try:
        provider.ap_scheduler.shutdown(wait=False)
    except Exception:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, user_id: int):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


@pytest.fixture()
def admin_user_id(app):
    with app.app_context():
        user = User.create(google_id="admin-user", name="Admin", privilege_level=2)
        return user.id


@pytest.fixture()
def normal_user_id(app):
    with app.app_context():
        user = User.create(google_id="regular-user", name="Regular", privilege_level=0)
        return user.id
