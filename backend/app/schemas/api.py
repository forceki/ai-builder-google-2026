"""Request and response bodies for the HTTP API."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class GoogleLoginIn(BaseModel):
    credential: str = Field(min_length=20, max_length=4096, description="ID token from Google Identity Services")


class UserOut(Out):
    id: uuid.UUID
    email: str
    name: str
    role: str


class LoginOut(BaseModel):
    token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(description="Seconds until the token expires")
    user: UserOut


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scope: str = "NOT SCOPED"
    no: str | None = Field(default=None, description="Project number; generated (PRJ-<year>-<seq>) if omitted")


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    scope: str | None = Field(default=None, max_length=200)


class ProjectOut(Out):
    id: uuid.UUID
    no: str
    name: str
    scope: str
    stage: int = Field(description="1 UPLOAD, 2 EXTRACT, 3 MAP, 4 VERIFY")
    docs: int
    checks: dict[str, int] | None = Field(description="{pass, hold, reject} from the last completed run, or null")
    release: Literal["NO DOCUMENTS", "EXTRACTING", "NOT READY", "READY · SIGN-OFF", "RELEASED"]
    signoff: "SignoffOut | None" = None
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
    updated_at: datetime


class DocumentDetail(DocumentOut):
    extraction: dict[str, Any] | None


class DocumentLinkOut(BaseModel):
    url: str = Field(description="Temporary signed link to the original file; works without a token until it expires")
    expires_at: datetime


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


class AiLogOut(Out):
    id: uuid.UUID
    created_at: datetime
    purpose: str
    model: str
    project_id: uuid.UUID | None
    document_id: uuid.UUID | None
    item_key: str | None
    status: str
    error: str | None
    duration_ms: int
    input_tokens: int | None
    output_tokens: int | None
    thinking_tokens: int | None
    cached_tokens: int | None
    total_tokens: int | None


class AiUsageRow(BaseModel):
    model: str
    purpose: str
    calls: int
    errors: int
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    total_tokens: int
    avg_duration_ms: int


class AiUsageOut(BaseModel):
    calls: int
    total_tokens: int
    by_model: list[AiUsageRow] = Field(description="Totals per model and purpose")


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
    current: bool = Field(default=True, description="False once the documents changed after signing")


ProjectOut.model_rebuild()
