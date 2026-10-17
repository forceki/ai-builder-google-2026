from datetime import UTC, datetime

from litestar import Controller, delete, get, patch, post
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_project
from app.models import CheckRun, Document, Project
from app.models.check import RunStatus
from app.models.document import DocStatus
from app.schemas.api import ProjectCreate, ProjectOut, ProjectUpdate, SignoffOut
from app.signoffs import active_signoff

_PROCESSING = (DocStatus.QUEUED, DocStatus.READING)


async def _project_out(db: AsyncSession, p: Project) -> ProjectOut:
    docs = (await db.scalars(select(Document).where(Document.project_id == p.id))).all()
    run = await db.scalar(
        select(CheckRun)
        .where(CheckRun.project_id == p.id, CheckRun.status == RunStatus.COMPLETE)
        .order_by(CheckRun.created_at.desc())
        .limit(1)
    )
    signoff, current = await active_signoff(db, p.id)
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
        if signoff and current and signoff.decision in ("release", "concession"):
            release = "RELEASED"
        else:
            release = "NOT READY" if open_items else "READY · SIGN-OFF"

    return ProjectOut(
        id=p.id, no=p.no, name=p.name, scope=p.scope, stage=stage, docs=len(docs),
        checks=counts, release=release, updated_at=p.updated_at,
        signoff=SignoffOut.model_validate(signoff).model_copy(update={"current": current}) if signoff else None,
    )


async def _list_projects(db: AsyncSession) -> list[ProjectOut]:
    projects = (await db.scalars(select(Project).order_by(Project.updated_at.desc()))).all()
    return [await _project_out(db, p) for p in projects]


class ProjectController(Controller):
    path = "/api/projects"

    @get("/")
    async def list_projects(self, db: AsyncSession) -> list[ProjectOut]:
        return await _list_projects(db)

    @post("/")
    async def create_project(self, db: AsyncSession, data: ProjectCreate) -> ProjectOut:
        no = data.no
        if not no:
            prefix = f"PRJ-{datetime.now(UTC).year}-"
            taken = (await db.scalars(select(Project.no).where(Project.no.like(f"{prefix}%")))).all()
            last = max((int(n.removeprefix(prefix)) for n in taken if n.removeprefix(prefix).isdigit()), default=0)
            no = f"{prefix}{last + 1:03d}"
        project = Project(no=no, name=data.name, scope=data.scope)
        db.add(project)
        await db.flush()
        return await _project_out(db, project)

    @get("/{project_no:str}")
    async def get_project(self, db: AsyncSession, project_no: str) -> ProjectOut:
        return await _project_out(db, await get_project(db, project_no))

    @delete("/{project_no:str}")
    async def delete_project(self, db: AsyncSession, project_no: str) -> None:
        project = await get_project(db, project_no)
        await db.execute(sa_delete(Project).where(Project.id == project.id))
        await db.commit()

    @patch("/{project_no:str}")
    async def update_project(self, db: AsyncSession, project_no: str, data: ProjectUpdate) -> ProjectOut:
        project = await get_project(db, project_no)
        if data.name is not None:
            project.name = data.name.strip()
        if data.scope is not None:
            project.scope = data.scope.strip() or "NOT SCOPED"
        await db.flush()
        return await _project_out(db, project)
