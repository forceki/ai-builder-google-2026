import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._common import IdMixin, TimestampMixin, utcnow


class Assessment(IdMixin, TimestampMixin, Base):
    """One welding assessment per project: the chosen conditions, the files sorted into document slots and waivers."""

    __tablename__ = "assessments"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    # {profile, governing, edition, supplementary[], design_pressure_mpa, design_temp_c, mdmt_c, upload_mode}
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON)
    # [{name, slot (null = rejected), reason, manual}]
    files: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # {finding key "X-06:W-22": {by, reason, at}}; a waiver follows its finding across re-runs.
    waivers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AssessmentRun(IdMixin, Base):
    """One run of the rules. Immutable except for waivers, which are re-applied to the stored findings."""

    __tablename__ = "assessment_runs"

    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    condition_hash: Mapped[str] = mapped_column(String(32))
    documents_hash: Mapped[str] = mapped_column(String(32))
    rule_pack: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(16))
    conclusion: Mapped[str] = mapped_column(String(32))
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON)
    documents: Mapped[dict[str, Any]] = mapped_column(JSON)  # files per slot at run time
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    run_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # The reviewer's notes on this run's conclusion: {text, by, at}; printed on the report.
    notes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)
