from litestar import Controller, get
from litestar.params import Parameter
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_project
from app.models import AiLog
from app.schemas.api import AiLogOut, AiUsageOut, AiUsageRow


async def _scoped(db: AsyncSession, q: Select, project_no: str | None) -> Select:
    if project_no:
        q = q.where(AiLog.project_id == (await get_project(db, project_no)).id)
    return q


def _sum(col):
    return func.coalesce(func.sum(col), 0)


class AiLogController(Controller):
    path = "/api/ai-logs"

    @get("/")
    async def list_logs(
        self,
        db: AsyncSession,
        project: str | None = Parameter(default=None, description="Only calls for this project number"),
        limit: int = Parameter(default=100, ge=1, le=1000),
    ) -> list[AiLogOut]:
        q = await _scoped(db, select(AiLog).order_by(AiLog.created_at.desc()).limit(limit), project)
        return [AiLogOut.model_validate(r) for r in await db.scalars(q)]

    @get("/summary")
    async def summary(
        self,
        db: AsyncSession,
        project: str | None = Parameter(default=None, description="Only calls for this project number"),
    ) -> AiUsageOut:
        q = await _scoped(db, select(
            AiLog.model, AiLog.purpose, func.count(),
            func.count().filter(AiLog.status == "error"),
            _sum(AiLog.input_tokens), _sum(AiLog.output_tokens), _sum(AiLog.thinking_tokens), _sum(AiLog.total_tokens),
            func.coalesce(func.avg(AiLog.duration_ms), 0),
        ).group_by(AiLog.model, AiLog.purpose).order_by(AiLog.model, AiLog.purpose), project)
        rows = [
            AiUsageRow(model=m, purpose=p, calls=c, errors=e, input_tokens=i, output_tokens=o,
                       thinking_tokens=t, total_tokens=tot, avg_duration_ms=round(d))
            for m, p, c, e, i, o, t, tot, d in (await db.execute(q)).all()
        ]
        return AiUsageOut(calls=sum(r.calls for r in rows), total_tokens=sum(r.total_tokens for r in rows),
                          by_model=rows)
