import argparse
import asyncio
import base64
import getpass
import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Any

from litestar.connection import ASGIConnection
from litestar.security.jwt import JWTAuth, Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User

PUBLIC = ["^/api/health$", "^/api/auth/login$", "^/api/projects/[^/]+/events$", "^/schema"]

_N, _R, _P = 2**14, 8, 1


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(expected))
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.email == email.strip().lower()))
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    return user if user and ok else None


async def upsert_user(session: AsyncSession, email: str, name: str, password: str, role: str | None = None) -> User:
    email = email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=name, password_hash=hash_password(password))
        session.add(user)
    else:
        user.name = name
        user.password_hash = hash_password(password)
    if role:
        user.role = role
    await session.flush()
    return user


def create_token(user: User) -> str:
    return jwt_auth.create_token(identifier=str(user.id))


async def _retrieve_user(token: Token, connection: ASGIConnection[Any, Any, Any, Any]) -> User | None:
    try:
        user_id = uuid.UUID(token.sub)
    except ValueError:
        return None
    async with connection.app.state.sessionmaker() as session:
        return await session.get(User, user_id)


_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

jwt_auth = JWTAuth[User](
    retrieve_user_handler=_retrieve_user,
    token_secret=get_settings().jwt_secret.get_secret_value(),
    default_token_expiration=timedelta(hours=get_settings().jwt_ttl_hours),
    exclude=PUBLIC,
)


async def _add_user(email: str, name: str, role: str | None, password: str) -> None:
    from app.db import create_tables, make_engine, make_sessionmaker

    engine = make_engine()
    await create_tables(engine)
    async with make_sessionmaker(engine)() as session:
        user = await upsert_user(session, email, name, password, role)
        await session.commit()
        print(f"saved {user.email} ({user.name})")
    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description="Manage Heatmark sign-in accounts.")
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add-user", help="create a user, or reset an existing user's password")
    add.add_argument("email")
    add.add_argument("--name", required=True)
    add.add_argument("--role")
    a = p.parse_args()
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        p.error("password must be at least 8 characters")
    if getpass.getpass("Repeat: ") != password:
        p.error("passwords do not match")
    asyncio.run(_add_user(a.email, a.name, a.role, password))


if __name__ == "__main__":
    main()
