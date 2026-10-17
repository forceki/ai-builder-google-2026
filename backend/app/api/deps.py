from collections.abc import AsyncGenerator

from arq.connections import ArqRedis
from litestar.datastructures import State
from litestar.exceptions import NotFoundException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_scope
from app.models import Project


async def provide_db(state: State) -> AsyncGenerator[AsyncSession]:
    async for session in session_scope(state.sessionmaker):
        yield session


async def provide_queue(state: State) -> ArqRedis:
    return state.queue


async def get_project(db: AsyncSession, project_no: str) -> Project:
    project = await db.scalar(select(Project).where(Project.no == project_no))
    if project is None:
        raise NotFoundException(f"project {project_no} not found")
    return project
