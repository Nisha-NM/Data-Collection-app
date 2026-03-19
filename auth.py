import logging
import re
from typing import Optional

import bcrypt

from database import create_user, get_user_by_email, update_user_password, User


logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
MIN_PASSWORD_LENGTH = 8


def validate_email(email: str) -> Optional[str]:
    if not email or not EMAIL_RE.match(email):
        return "Please enter a valid email address."
    return None


def validate_password(password: str) -> Optional[str]:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one digit."
    return None


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as exc:
        logger.exception("Password verification failed: %s", exc)
        return False


def register_user(email: str, password: str, role: str = "user") -> Optional[User]:
    try:
        password_hash = hash_password(password)
        return create_user(email=email, password_hash=password_hash, role=role)
    except Exception as exc:
        logger.exception("User registration failed: %s", exc)
        return None


def authenticate_user(email: str, password: str) -> Optional[User]:
    try:
        user = get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    except Exception as exc:
        logger.exception("Authentication failed: %s", exc)
        return None


def change_password(user_id: int, old_password: str, new_password: str) -> Optional[str]:
    from database import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        return "User not found."
    if not verify_password(old_password, user.password_hash):
        return "Current password is incorrect."
    error = validate_password(new_password)
    if error:
        return error
    new_hash = hash_password(new_password)
    update_user_password(user_id, new_hash)
    return None
