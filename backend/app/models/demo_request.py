from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._common import IdMixin, utcnow


class DemoRequest(IdMixin, Base):
    """A "Request a demo" submission from the landing page. Listed with `python -m app.demo_requests`."""

    __tablename__ = "demo_requests"

    email: Mapped[str] = mapped_column(String(320), index=True)
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
