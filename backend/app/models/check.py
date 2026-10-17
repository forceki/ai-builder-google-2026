import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._common import IdMixin, utcnow


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class CheckRun(IdMixin, Base):
    __tablename__ = "check_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    rule_set: Mapped[str] = mapped_column(String(32))
    status: Mapped[RunStatus] = mapped_column(String(16), default=RunStatus.QUEUED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Per-check results: [{check, name, status, issues}], plus overall counts.
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    findings: Mapped[list["Finding"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Finding(IdMixin, Base):
    __tablename__ = "findings"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("check_runs.id", ondelete="CASCADE"), index=True)
    check_id: Mapped[str] = mapped_column(String(8))  # C-01 … C-04
    rule_id: Mapped[str] = mapped_column(String(16))  # e.g. R-NDT-03
    item_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(8))  # HOLD | REJECT (PASS is the absence of findings)
    message: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # Generated for review; never changes the status.
    explanation: Mapped[str | None] = mapped_column(Text, default=None)
    next_step: Mapped[str | None] = mapped_column(Text, default=None)

    run: Mapped[CheckRun] = relationship(back_populates="findings")


class Signoff(IdMixin, Base):
    __tablename__ = "signoffs"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("check_runs.id", ondelete="CASCADE"))
    decision: Mapped[str] = mapped_column(String(16))  # hold | concession | release
    name: Mapped[str] = mapped_column(String(120))
    comment: Mapped[str] = mapped_column(Text, default="")
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
