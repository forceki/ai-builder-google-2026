"""Public "Request a demo" endpoint behind the landing page form."""

import logging
import re
from datetime import timedelta

from litestar import Controller, Request, post
from litestar.exceptions import ClientException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models._common import utcnow
from app.models.demo_request import DemoRequest

log = logging.getLogger(__name__)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class DemoRequestIn(BaseModel):
    email: str = Field(max_length=320)
    # Hidden from people; a bot that fills every field gives itself away. The request is then dropped silently.
    website: str = Field(default="", max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL.match(v):
            raise ValueError("enter a valid email address")
        return v


class DemoRequestOut(BaseModel):
    received: bool = True


class DemoRequestController(Controller):
    path = "/api/demo-requests"

    @post("/")
    async def request_demo(self, db: AsyncSession, request: Request, data: DemoRequestIn) -> DemoRequestOut:
        """Store a demo request. The same address within a day is one request."""
        if data.website:
            log.info("demo request dropped: honeypot filled")
            return DemoRequestOut()
        recent = await db.scalar(select(DemoRequest.id).where(
            DemoRequest.email == data.email, DemoRequest.created_at > utcnow() - timedelta(days=1)))
        if recent is None:
            count = await db.scalar(select(DemoRequest.id).where(DemoRequest.created_at > utcnow() - timedelta(minutes=1))
                                    .limit(1).offset(20))
            if count is not None:  # more than 20 a minute from anywhere: a flood, not people
                raise ClientException("too many requests; try again in a minute", status_code=429)
            db.add(DemoRequest(email=data.email, user_agent=(request.headers.get("user-agent") or "")[:300]))
            log.info("demo request from %s", data.email)
        return DemoRequestOut()
