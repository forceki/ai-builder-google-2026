import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._common import IdMixin, TimestampMixin


class Project(IdMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    no: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. PRJ-2026-041
    name: Mapped[str] = mapped_column(String(200))
    scope: Mapped[str] = mapped_column(String(200), default="NOT SCOPED")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, default=None
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="project", cascade="all, delete-orphan")  # noqa: F821
