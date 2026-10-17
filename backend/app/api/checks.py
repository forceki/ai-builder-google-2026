from arq.connections import ArqRedis
from litestar import Controller, delete, get, post
from litestar.exceptions import ClientException, NotFoundException
from litestar.status_codes import HTTP_202_ACCEPTED
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_project
from app.config import get_settings
from app.models import CheckRun, Signoff, TraceItem, TraceLink
from app.models._common import utcnow
from app.models.check import RunStatus
from app.queue import RUN_CHECKS
from app.schemas.api import CheckRunOut, SignoffIn, SignoffOut, TraceItemOut, TraceLinkOut, TraceMapOut


async def _latest_run(db: AsyncSession, project_id, *, complete_only: bool = False) -> CheckRun | None:
    q = select(CheckRun).where(CheckRun.project_id == project_id)
    if complete_only:
        q = q.where(CheckRun.status == RunStatus.COMPLETE)
    return await db.scalar(
        q.options(selectinload(CheckRun.findings)).order_by(CheckRun.created_at.desc()).limit(1)
    )


async def _active_signoff(db: AsyncSession, project_id) -> Signoff | None:
    return await db.scalar(
        select(Signoff)
        .where(Signoff.project_id == project_id, Signoff.revoked_at.is_(None))
        .order_by(Signoff.signed_at.desc())
        .limit(1)
    )


class CheckController(Controller):
    path = "/api/projects/{project_no:str}"

    @post("/checks", status_code=HTTP_202_ACCEPTED)
    async def run_checks(self, db: AsyncSession, queue: ArqRedis, project_no: str) -> CheckRunOut:
        project = await get_project(db, project_no)
        run = CheckRun(project_id=project.id, rule_set=get_settings().rule_set, findings=[])
        db.add(run)
        await db.commit()
        await queue.enqueue_job(RUN_CHECKS, str(run.id))
        return CheckRunOut.model_validate(run)

    @get("/checks/latest")
    async def latest(self, db: AsyncSession, project_no: str, complete: bool = False) -> CheckRunOut:
        """Latest run; with ?complete=true, the latest run that finished successfully."""
        project = await get_project(db, project_no)
        run = await _latest_run(db, project.id, complete_only=complete)
        if run is None:
            raise NotFoundException("checks have not been run for this project")
        return CheckRunOut.model_validate(run)

    @get("/trace")
    async def trace_map(self, db: AsyncSession, project_no: str) -> TraceMapOut:
        project = await get_project(db, project_no)
        items = await db.scalars(select(TraceItem).where(TraceItem.project_id == project.id))
        links = await db.scalars(select(TraceLink).where(TraceLink.project_id == project.id))
        return TraceMapOut(
            items=[TraceItemOut.model_validate(i) for i in items],
            links=[TraceLinkOut.model_validate(link) for link in links],
        )

    @get("/signoff")
    async def get_signoff(self, db: AsyncSession, project_no: str) -> SignoffOut | None:
        project = await get_project(db, project_no)
        signoff = await _active_signoff(db, project.id)
        return SignoffOut.model_validate(signoff) if signoff else None

    @post("/signoff")
    async def sign(self, db: AsyncSession, project_no: str, data: SignoffIn) -> SignoffOut:
        project = await get_project(db, project_no)
        if not data.reviewed:
            raise ClientException("confirm that the findings and their sources were reviewed")
        run = await _latest_run(db, project.id, complete_only=True)
        if run is None:
            raise ClientException("run the checks before signing off")
        if data.decision == "release" and run.findings:
            raise ClientException(f"release is blocked: {len(run.findings)} findings are open on the last run")
        if await _active_signoff(db, project.id):
            raise ClientException("the report is already signed; revoke the signature first")

        signoff = Signoff(project_id=project.id, run_id=run.id, decision=data.decision,
                          name=data.name.strip(), comment=data.comment.strip())
        db.add(signoff)
        await db.flush()
        return SignoffOut.model_validate(signoff)

    @delete("/signoff")
    async def revoke(self, db: AsyncSession, project_no: str) -> None:
        project = await get_project(db, project_no)
        signoff = await _active_signoff(db, project.id)
        if signoff is None:
            raise NotFoundException("no active signature")
        signoff.revoked_at = utcnow()
