import logging
from typing import Optional

import bcrypt

from database import create_user, get_user_by_email, User, init_db


logger = logging.getLogger(__name__)


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
        init_db()
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

