from app.models import User
from app.provider import db


def test_alive_endpoint_reports_status(client):
    response = client.get("/api/alive", base_url="https://localhost")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["db"] == "reachable"
    assert data["version"] == "test"


def test_users_list_excludes_karma(client, app):
    with app.app_context():
        User.create(google_id="u1", name="User One")
        User.create(google_id="u2", name="User Two")

    response = client.get("/api/users", base_url="https://localhost")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert "karma" not in data[0]


def test_user_detail_and_patch(client, app):
    with app.app_context():
        user = User.create(google_id="u3", name="User Three")
        user_id = user.id
        db.session.commit()

    detail_response = client.get(f"/api/users/{user_id}", base_url="https://localhost")
    assert detail_response.status_code == 200
    detail_data = detail_response.get_json()
    assert detail_data["id"] == user_id

    patch_response = client.patch(
        f"/api/users/{user_id}",
        json={"display_name": "Updated Name"},
        base_url="https://localhost",
    )
    assert patch_response.status_code == 200
    patch_data = patch_response.get_json()
    assert patch_data["display_name"] == "Updated Name"
