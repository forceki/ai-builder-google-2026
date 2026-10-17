import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app import auth
from app.auth import GOOGLE_ONLY, GoogleSignInError, authenticate_google, verify_password
from app.config import get_settings
from app.db import Base, make_sessionmaker


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def google(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "google_client_id", "client-123")
    monkeypatch.setattr(settings, "google_allowed_domains", [])
    claims = {"iss": "https://accounts.google.com", "email": "Ana@Example.com", "email_verified": True, "name": "Ana"}
    monkeypatch.setattr(auth, "_verify_google_token", lambda credential, client_id: dict(claims))
    return claims


async def test_first_sign_in_registers_the_user(session, google):
    user = await authenticate_google(session, "token")
    assert (user.email, user.name, user.password_hash) == ("ana@example.com", "Ana", GOOGLE_ONLY)
    again = await authenticate_google(session, "token")
    assert again.id == user.id


async def test_google_only_account_has_no_password(session, google):
    user = await authenticate_google(session, "token")
    assert not verify_password("", user.password_hash)
    assert not verify_password(GOOGLE_ONLY, user.password_hash)


async def test_unverified_email_is_refused(session, google, monkeypatch):
    monkeypatch.setattr(auth, "_verify_google_token", lambda c, i: {**google, "email_verified": False})
    with pytest.raises(GoogleSignInError):
        await authenticate_google(session, "token")


async def test_domain_allow_list(session, google, monkeypatch):
    monkeypatch.setattr(get_settings(), "google_allowed_domains", ["company.com"])
    with pytest.raises(GoogleSignInError) as e:
        await authenticate_google(session, "token")
    assert e.value.forbidden


async def test_invalid_token_is_refused(session, google, monkeypatch):
    def bad(credential, client_id):
        raise ValueError("Token expired")

    monkeypatch.setattr(auth, "_verify_google_token", bad)
    with pytest.raises(GoogleSignInError):
        await authenticate_google(session, "token")
