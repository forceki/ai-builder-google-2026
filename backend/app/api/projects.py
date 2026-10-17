from datetime import UTC, datetime

from litestar import Controller, get, post
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_project
from app.models import CheckRun, Document, Project, Signoff
from app.models.check import RunStatus
from app.models.document import DocStatus
from app.schemas.api import ProjectCreate, ProjectOut

_PROCESSING = (DocStatus.QUEUED, DocStatus.READING)


async def _project_out(db: AsyncSession, p: Project) -> ProjectOut:
    docs = (await db.scalars(select(Document).where(Document.project_id == p.id))).all()
    run = await db.scalar(
        select(CheckRun)
        .where(CheckRun.project_id == p.id, CheckRun.status == RunStatus.COMPLETE)
        .order_by(CheckRun.created_at.desc())
        .limit(1)
    )
    signoff = run and await db.scalar(
        select(Signoff).where(Signoff.run_id == run.id, Signoff.revoked_at.is_(None))
    )
    counts = run.summary["counts"] if run and run.summary else None

    processing = any(d.status in _PROCESSING for d in docs)
    if not docs:
        stage, release = 1, "NO DOCUMENTS"
    elif processing:
        stage, release = 2, "EXTRACTING"
    elif run is None:
        stage, release = 3, "NOT READY"
    else:
        stage = 4
        open_items = counts and (counts["hold"] or counts["reject"])
        if signoff and signoff.decision in ("release", "concession"):
            release = "RELEASED"
        else:
            release = "NOT READY" if open_items else "READY · SIGN-OFF"

    return ProjectOut(
        id=p.id, no=p.no, name=p.name, scope=p.scope, stage=stage, docs=len(docs),
        checks=counts, release=release, updated_at=p.updated_at,
    )


class ProjectController(Controller):
    path = "/api/projects"

    @get("/")
    async def list_projects(self, db: AsyncSession) -> list[ProjectOut]:
        projects = (await db.scalars(select(Project).order_by(Project.updated_at.desc()))).all()
        return [await _project_out(db, p) for p in projects]

    @post("/")
    async def create_project(self, db: AsyncSession, data: ProjectCreate) -> ProjectOut:
        no = data.no
        if not no:
            year = datetime.now(UTC).year
            count = await db.scalar(select(func.count()).select_from(Project).where(Project.no.like(f"PRJ-{year}-%")))
            no = f"PRJ-{year}-{count + 1:03d}"
        project = Project(no=no, name=data.name, scope=data.scope)
        db.add(project)
        await db.flush()
        return await _project_out(db, project)

    @get("/{project_no:str}")
    async def get_project(self, db: AsyncSession, project_no: str) -> ProjectOut:
        return await _project_out(db, await get_project(db, project_no))
