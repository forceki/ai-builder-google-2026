from collections.abc import AsyncGenerator
from typing import Any

from litestar import Request
from litestar.datastructures import State
from litestar.exceptions import NotFoundException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_scope
from app.models import Project, User
from app.queue import Queue


async def provide_db(state: State) -> AsyncGenerator[AsyncSession]:
    async for session in session_scope(state.sessionmaker):
        yield session


async def provide_queue(state: State) -> Queue:
    return state.queue


async def provide_user(request: Request[User, Any, Any]) -> User:
    return request.user


async def get_project(db: AsyncSession, project_no: str, user: User) -> Project:
    project = await db.scalar(select(Project).where(Project.no == project_no, Project.owner_id == user.id))
    if project is None:
        raise NotFoundException(f"project {project_no} not found")
    return project
