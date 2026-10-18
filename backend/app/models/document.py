import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._common import IdMixin, TimestampMixin


class DocType(StrEnum):
    MTC = "mtc"  # material certificates
    WELD = "weld"  # weld logs, WPS / PQR, welder qualifications
    NDT = "ndt"  # UT / RT / MT / PT / VT reports and registers
    INSPECTION = "insp"  # ITP, dimensional, hydro test
    PRODUCTION = "prod"  # travelers, fabrication records, PWHT records


class DocStatus(StrEnum):
    QUEUED = "queued"
    READING = "reading"
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"  # extracted, but some fields are low confidence
    FAILED = "failed"


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(255))
    pages: Mapped[int] = mapped_column(Integer, default=1)

    # Type confirmed by the uploader; suggested_type is what the classifier thought.
    doc_type: Mapped[DocType | None] = mapped_column(String(16), default=None)
    suggested_type: Mapped[DocType | None] = mapped_column(String(16), default=None)
    # Open finding item key this file is meant to clear (e.g. "W-14").
    evidence_for: Mapped[str | None] = mapped_column(String(64), default=None)

    status: Mapped[DocStatus] = mapped_column(String(16), default=DocStatus.QUEUED)
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    # Welding assessment intake (app.assessment): the slot the file was sorted into, and why.
    for_assessment: Mapped[bool] = mapped_column(Boolean, default=False)
    slot: Mapped[str | None] = mapped_column(String(16), default=None)  # mtc, wps, wpq, drawing, asbuilt, other; None = rejected
    slot_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    slot_reason: Mapped[str | None] = mapped_column(Text, default=None)
    slot_manual: Mapped[bool] = mapped_column(Boolean, default=False)  # assigned or confirmed by the user

    project: Mapped["Project"] = relationship(back_populates="documents")  # noqa: F821
