import pytest
from litestar.exceptions import NotFoundException
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.deps import get_project
from app.db import Base, make_sessionmaker
from app.models import Project, User


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as s:
        yield s
    await engine.dispose()


async def test_projects_are_visible_to_their_owner_only(session):
    ana = User(email="ana@a.com", name="Ana", password_hash="-")
    bo = User(email="bo@b.com", name="Bo", password_hash="-")
    session.add_all([ana, bo])
    await session.flush()
    session.add(Project(no="PRJ-1", name="Ana's", owner_id=ana.id))
    await session.flush()

    assert (await get_project(session, "PRJ-1", ana)).name == "Ana's"
    with pytest.raises(NotFoundException):
        await get_project(session, "PRJ-1", bo)
