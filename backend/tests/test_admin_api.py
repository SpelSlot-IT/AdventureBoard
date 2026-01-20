import pytest

from tests.conftest import login


@pytest.mark.parametrize("action", ["assign", "reassign", "release", "reset"])
def test_admin_actions_execute_for_admin(client, admin_user_id, action):
    login(client, admin_user_id)

    response = client.put(
        "/api/player-assignments",
        json={"action": action},
        base_url="https://localhost",
    )

    assert response.status_code == 200


def test_update_karma_executes_for_admin(client, admin_user_id):
    login(client, admin_user_id)

    response = client.post("/api/update-karma", json={}, base_url="https://localhost")

    assert response.status_code == 200


@pytest.mark.parametrize("action", ["assign", "reassign", "release", "reset"])
def test_admin_actions_reject_non_admin(client, normal_user_id, action):
    login(client, normal_user_id)

    response = client.put(
        "/api/player-assignments",
        json={"action": action},
        base_url="https://localhost",
    )

    assert response.status_code == 401


def test_update_karma_rejects_non_admin(client, normal_user_id):
    login(client, normal_user_id)

    response = client.post("/api/update-karma", json={}, base_url="https://localhost")

    assert response.status_code == 401
