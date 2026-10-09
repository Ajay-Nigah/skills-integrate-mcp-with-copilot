import copy
import hashlib
import json
import secrets
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import src.app as app_module


@pytest.fixture

def client(tmp_path, monkeypatch):
    salt = secrets.token_bytes(16)
    password = "Correct-Horse-123"
    teacher_file = tmp_path / "teachers.json"
    teacher_file.write_text(
        json.dumps(
            {
                "teachers": [
                    {
                        "username": "teacher",
                        "password_salt": salt.hex(),
                        "password_hash": hashlib.pbkdf2_hmac(
                            "sha256", password.encode(), salt, app_module.PASSWORD_HASH_ITERATIONS
                        ).hex(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(app_module, "TEACHERS_FILE", teacher_file)
    monkeypatch.setattr(app_module, "SESSION_SECRET", "test-session-secret-with-at-least-32-bytes")
    original_activities = copy.deepcopy(app_module.activities)

    with TestClient(app_module.app) as test_client:
        yield test_client

    app_module.activities.clear()
    app_module.activities.update(original_activities)


def test_activities_and_participants_are_public(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()
    assert "michael@mergington.edu" in response.json()["Chess Club"]["participants"]
    assert client.get("/auth/session").json() == {"authenticated": False, "username": None}


def test_unauthenticated_users_cannot_change_signups(client):
    before = client.get("/activities").json()["Chess Club"]["participants"]

    signup = client.post(
        "/activities/Chess Club/signup", params={"email": "new@mergington.edu"}
    )
    unregister = client.delete(
        "/activities/Chess Club/unregister", params={"email": "michael@mergington.edu"}
    )

    assert signup.status_code == 401
    assert unregister.status_code == 401
    assert client.get("/activities").json()["Chess Club"]["participants"] == before


def test_teacher_can_sign_in_and_manage_signups(client):
    login = client.post(
        "/auth/login", json={"username": "teacher", "password": "Correct-Horse-123"}
    )

    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=strict" in login.headers["set-cookie"].lower()
    assert client.get("/auth/session").json() == {"authenticated": True, "username": "teacher"}

    signup = client.post(
        "/activities/Chess Club/signup", params={"email": "new@mergington.edu"}
    )
    assert signup.status_code == 200
    assert "new@mergington.edu" in client.get("/activities").json()["Chess Club"]["participants"]

    unregister = client.delete(
        "/activities/Chess Club/unregister", params={"email": "new@mergington.edu"}
    )
    assert unregister.status_code == 200
    assert "new@mergington.edu" not in client.get("/activities").json()["Chess Club"]["participants"]


def test_invalid_credentials_do_not_create_a_session(client):
    response = client.post(
        "/auth/login", json={"username": "teacher", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert client.get("/auth/session").json()["authenticated"] is False


def test_login_fails_closed_with_placeholder_secret(client, monkeypatch):
    monkeypatch.setattr(
        app_module, "SESSION_SECRET", app_module.SESSION_SECRET_PLACEHOLDER
    )

    response = client.post(
        "/auth/login", json={"username": "teacher", "password": "Correct-Horse-123"}
    )

    assert response.status_code == 503
    assert client.get("/auth/session").json()["authenticated"] is False


def test_logout_clears_teacher_session(client):
    client.post("/auth/login", json={"username": "teacher", "password": "Correct-Horse-123"})
    logout = client.post("/auth/logout")

    assert logout.status_code == 200
    assert client.get("/auth/session").json()["authenticated"] is False


def test_tampered_session_is_rejected(client):
    client.post("/auth/login", json={"username": "teacher", "password": "Correct-Horse-123"})
    valid_cookie = client.cookies.get(app_module.SESSION_COOKIE_NAME)
    client.cookies.clear()
    client.cookies.set(
        app_module.SESSION_COOKIE_NAME,
        valid_cookie + "tampered",
        domain="testserver.local",
        path="/",
    )

    rejected = client.post(
        "/activities/Chess Club/signup", params={"email": "new@mergington.edu"}
    )
    assert rejected.status_code == 401
