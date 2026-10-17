import uuid

import jwt

from app.auth import create_token, hash_password, verify_password
from app.config import get_settings
from app.models import User


def test_password_round_trip():
    stored = hash_password("correct horse")
    assert stored.startswith("scrypt$")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong horse", stored)


def test_same_password_gets_a_new_salt():
    assert hash_password("same") != hash_password("same")


def test_malformed_hash_is_rejected():
    assert not verify_password("x", "not-a-hash")
    assert not verify_password("x", "bcrypt$1$2$3$4$5")


def test_token_carries_the_user_id():
    user = User(id=uuid.uuid4(), email="a@b.c", name="A", password_hash="-")
    claims = jwt.decode(create_token(user), get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"])
    assert claims["sub"] == str(user.id)
    assert claims["exp"] > claims["iat"]
