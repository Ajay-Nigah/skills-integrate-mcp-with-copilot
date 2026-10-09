"""Provision a teacher login in the local, git-ignored teachers.json file."""

import getpass
import hashlib
import json
import secrets
from pathlib import Path

PASSWORD_HASH_ITERATIONS = 600_000
TEACHERS_FILE = Path(__file__).with_name("teachers.json")


def main() -> None:
    username = input("Teacher username: ").strip()
    if not 3 <= len(username) <= 64:
        raise SystemExit("Username must be between 3 and 64 characters.")

    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    if TEACHERS_FILE.exists():
        try:
            data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"Cannot read {TEACHERS_FILE}: {error}") from error
    else:
        data = {"teachers": []}

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list):
        raise SystemExit("Teacher account file must contain a 'teachers' list.")
    if any(
        isinstance(teacher, dict)
        and isinstance(teacher.get("username"), str)
        and teacher["username"].casefold() == username.casefold()
        for teacher in teachers
    ):
        raise SystemExit("That username already exists.")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    teachers.append(
        {
            "username": username,
            "password_salt": salt.hex(),
            "password_hash": password_hash.hex(),
        }
    )

    TEACHERS_FILE.write_text(json.dumps({"teachers": teachers}, indent=2) + "\n", encoding="utf-8")
    TEACHERS_FILE.chmod(0o600)
    print(f"Teacher account '{username}' added to {TEACHERS_FILE}.")


if __name__ == "__main__":
    main()
