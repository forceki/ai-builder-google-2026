from typing import Any

from litestar import Controller, Request, get, post
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import Token
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate, create_token
from app.config import get_settings
from app.models import User
from app.schemas.api import LoginIn, LoginOut, UserOut


class AuthController(Controller):
    path = "/api/auth"

    @post("/login", status_code=HTTP_200_OK)
    async def login(self, db: AsyncSession, data: LoginIn) -> LoginOut:
        user = await authenticate(db, data.email, data.password)
        if user is None:
            raise NotAuthorizedException("wrong email or password")
        return LoginOut(
            token=create_token(user),
            expires_in=get_settings().jwt_ttl_hours * 3600,
            user=UserOut.model_validate(user),
        )

    @get("/me")
    async def me(self, request: Request[User, Token, Any]) -> UserOut:
        return UserOut.model_validate(request.user)
