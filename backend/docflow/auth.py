import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from .models import LoginSession, User, now

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("unavailable-account")
COOKIE_NAME = "docflow_session"
SESSION_SECONDS = 8 * 60 * 60


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def password_matches(password: str, stored: str) -> bool:
    try:
        return hasher.verify(stored, password)
    except VerificationError:
        return False


def authenticate(request: Request, db: Session) -> tuple[User, LoginSession]:
    token = request.cookies.get(COOKIE_NAME, "")
    session = db.get(LoginSession, digest(token))
    if session is None or session.expires_at <= now():
        raise HTTPException(401, "Sign in to continue")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "Account is unavailable")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf):
            raise HTTPException(403, "Invalid session request token; sign in again")
    return user, session
