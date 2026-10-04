"""Explicit local provisioning: python -m app.staff LOGIN --role admin (prompts for password)."""

import argparse
import getpass
import hashlib
import hmac
import secrets
from uuid import uuid4

from app.config import Settings
from app.db import connect, migrate


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def check_password(password: str, encoded: str) -> bool:
    _, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(actual, expected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("login")
    parser.add_argument("--role", choices=["admin", "curator"], default="admin")
    args = parser.parse_args()
    password = getpass.getpass("New staff password (at least 12 characters): ")
    if len(password) < 12 or password != getpass.getpass("Confirm password: "):
        raise SystemExit("Password too short or confirmation differs")
    config = Settings()
    migrate(config)
    with connect(config) as db:
        db.execute(
            "INSERT INTO staff_user(id,login,password_hash,role) VALUES (%s,%s,%s,%s)",
            (uuid4(), args.login, hash_password(password), args.role),
        )
    print("Staff account created")
