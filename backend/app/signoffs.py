import hashlib
import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckRun, Document, Signoff
from app.models.check import RunStatus


def fingerprint(docs: Iterable[Document]) -> str:
    raw = "|".join(sorted(f"{d.id}:{d.updated_at.isoformat()}" for d in docs))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def current_fingerprint(db: AsyncSession, project_id: uuid.UUID) -> str:
    return fingerprint((await db.scalars(select(Document).where(Document.project_id == project_id))).all())


async def latest_complete_run(db: AsyncSession, project_id: uuid.UUID) -> CheckRun | None:
    return await db.scalar(
        select(CheckRun)
        .where(CheckRun.project_id == project_id, CheckRun.status == RunStatus.COMPLETE)
        .order_by(CheckRun.created_at.desc())
        .limit(1)
    )


async def active_signoff(db: AsyncSession, project_id: uuid.UUID) -> tuple[Signoff | None, bool]:
    signoff = await db.scalar(
        select(Signoff)
        .where(Signoff.project_id == project_id, Signoff.revoked_at.is_(None))
        .order_by(Signoff.signed_at.desc())
        .limit(1)
    )
    if signoff is None:
        return None, False
    signed_run = await db.get(CheckRun, signoff.run_id)
    inputs = (signed_run.summary or {}).get("inputs") if signed_run else None
    if inputs:
        return signoff, inputs == await current_fingerprint(db, project_id)
    latest = await latest_complete_run(db, project_id)
    return signoff, latest is not None and latest.id == signoff.run_id
