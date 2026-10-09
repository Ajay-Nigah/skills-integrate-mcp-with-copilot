# Mergington High School Activities API

A FastAPI application for browsing extracurricular activities. Activity details and participant lists are public; only authenticated teachers can add or remove student registrations.

## Setup

From the repository root:

1. Install dependencies: `pip install -r requirements.txt`.
2. Set a unique session secret in the root `.env` file. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and replace the `ADMIN_SESSION_SECRET` placeholder.
3. Provision the first teacher account: `python src/create_teacher.py`. The script prompts for a username and password and stores only a salted PBKDF2 password hash in `src/teachers.json`. That file is ignored by Git.
4. Start the application with `uvicorn src.app:app --reload`.
5. Open `http://localhost:8000`.

For HTTPS deployments, set `SESSION_COOKIE_SECURE=true`. The teacher session cookie is HttpOnly, SameSite=Strict, and expires after eight hours. Do not use the placeholder secret in a deployed environment.

## API endpoints

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/activities` | Public | List activities and participants |
| `GET` | `/auth/session` | Public | Check whether the current browser has a teacher session |
| `POST` | `/auth/login` | Public | Sign in with a provisioned teacher username and password |
| `POST` | `/auth/logout` | Public | Clear the teacher session cookie |
| `POST` | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher | Add a student to an activity |
| `DELETE` | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher | Remove a student from an activity |

Login accepts JSON with `username` and `password`. Invalid credentials receive the same generic error. Passwords are hashed with PBKDF2-HMAC-SHA256 and a unique random salt; signed session cookies use HMAC-SHA256.

Run tests by installing `requirements-dev.txt` and invoking `pytest`.

## Current limitations

Activity records and signups remain in memory and reset when the server restarts. Teacher account hashes are stored locally in `src/teachers.json`; provision accounts on each deployment and keep that file private. This change does not add persistent activity storage, account recovery, or external identity management.
