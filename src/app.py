"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

TEACHERS_FILE = Path(os.getenv("TEACHERS_FILE", str(BASE_DIR / "teachers.json")))
SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "")
SESSION_COOKIE_NAME = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000
SESSION_SECRET_PLACEHOLDER = "replace-with-a-random-secret-at-least-32-chars"


class LoginRequest(BaseModel):
    username: str
    password: str


def session_secret_is_configured() -> bool:
    return (
        len(SESSION_SECRET) >= 32
        and SESSION_SECRET != SESSION_SECRET_PLACEHOLDER
        and not SESSION_SECRET.startswith("replace-with-")
    )


def load_teachers() -> list[dict[str, Any]]:
    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Teacher account store is unavailable.") from error

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list):
        raise HTTPException(status_code=503, detail="Teacher account store is invalid.")
    return [
        teacher
        for teacher in teachers
        if isinstance(teacher, dict)
        and isinstance(teacher.get("username"), str)
        and isinstance(teacher.get("password_salt"), str)
        and isinstance(teacher.get("password_hash"), str)
    ]


def verify_teacher_password(teacher: dict[str, Any], password: str) -> bool:
    try:
        salt = bytes.fromhex(teacher["password_salt"])
        expected_hash = bytes.fromhex(teacher["password_hash"])
    except (KeyError, TypeError, ValueError):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_session_token(username: str) -> str:
    payload = json.dumps(
        {"username": username, "expires_at": int(time.time()) + SESSION_TTL_SECONDS},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = _base64url_encode(payload)
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded_payload}.{_base64url_encode(signature)}"


def get_authenticated_teacher(request: Request) -> str | None:
    if not session_secret_is_configured():
        return None

    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        supplied_signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected_signature = hmac.new(
            SESSION_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes)
        username = payload.get("username")
        if not isinstance(username, str) or payload.get("expires_at", 0) <= time.time():
            return None

        teacher_exists = any(
            teacher["username"].casefold() == username.casefold()
            for teacher in load_teachers()
        )
        return username if teacher_exists else None
    except (ValueError, TypeError, json.JSONDecodeError, HTTPException):
        return None


def require_teacher(request: Request) -> str:
    username = get_authenticated_teacher(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required.")
    return username

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def teacher_login(credentials: LoginRequest, response: Response):
    if not session_secret_is_configured():
        raise HTTPException(status_code=503, detail="Configure ADMIN_SESSION_SECRET before enabling teacher login.")

    username = credentials.username.strip()
    if not username or not credentials.password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    teachers = load_teachers()
    teacher = next(
        (item for item in teachers if item["username"].casefold() == username.casefold()),
        None,
    )
    if teacher is None or not verify_teacher_password(teacher, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(teacher["username"]),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.getenv("SESSION_COOKIE_SECURE", "false").casefold() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Teacher login successful.", "username": teacher["username"]}


@app.get("/auth/session")
def teacher_session(request: Request):
    username = get_authenticated_teacher(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/logout")
def teacher_logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=os.getenv("SESSION_COOKIE_SECURE", "false").casefold() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Teacher logged out."}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
