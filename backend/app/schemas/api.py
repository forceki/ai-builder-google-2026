"""Request and response bodies for the HTTP API."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scope: str = "NOT SCOPED"
    no: str | None = Field(default=None, description="Project number; generated (PRJ-<year>-<seq>) if omitted")


class ProjectOut(Out):
    id: uuid.UUID
    no: str
    name: str
    scope: str
    stage: int = Field(description="1 UPLOAD, 2 EXTRACT, 3 MAP, 4 VERIFY")
    docs: int
    checks: dict[str, int] | None = Field(description="{pass, hold, reject} from the last completed run, or null")
    release: Literal["NO DOCUMENTS", "EXTRACTING", "NOT READY", "READY · SIGN-OFF", "RELEASED"]
    updated_at: datetime


class DocumentOut(Out):
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    pages: int
    doc_type: str | None
    suggested_type: str | None
    evidence_for: str | None
    status: str
    error: str | None
    created_at: datetime


class DocumentDetail(DocumentOut):
    extraction: dict[str, Any] | None


class DocumentTypeUpdate(BaseModel):
    doc_type: Literal["mtc", "weld", "ndt", "insp", "prod"]


class FindingOut(Out):
    id: uuid.UUID
    check_id: str
    rule_id: str
    item_key: str
    status: str
    message: str
    sources: list[dict[str, Any]]
    explanation: str | None
    next_step: str | None


class CheckRunOut(Out):
    id: uuid.UUID
    rule_set: str
    status: str
    created_at: datetime
    finished_at: datetime | None
    summary: dict[str, Any] | None
    error: str | None
    findings: list[FindingOut] = []


class TraceItemOut(Out):
    id: uuid.UUID
    kind: str
    key: str
    label: str
    attributes: dict[str, Any]
    sources: list[dict[str, Any]]


class TraceLinkOut(Out):
    from_item_id: uuid.UUID
    to_item_id: uuid.UUID
    kind: str


class TraceMapOut(BaseModel):
    items: list[TraceItemOut]
    links: list[TraceLinkOut]


class SignoffIn(BaseModel):
    decision: Literal["hold", "concession", "release"]
    name: str = Field(min_length=1, max_length=120)
    comment: str = ""
    reviewed: bool = Field(description="The engineer confirms they reviewed the findings and sources")


class SignoffOut(Out):
    id: uuid.UUID
    run_id: uuid.UUID
    decision: str
    name: str
    comment: str
    signed_at: datetime
    revoked_at: datetime | None
