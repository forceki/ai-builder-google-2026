from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.demo_requests import DemoRequestController, DemoRequestIn
from app.db import Base, make_sessionmaker
from app.models import DemoRequest


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as s:
        yield s
    await engine.dispose()


async def test_demo_request_is_stored_once_per_address_and_bots_are_dropped(session):
    api = DemoRequestController(owner=None)
    request = SimpleNamespace(headers={"user-agent": "test"})
    send = lambda **kw: DemoRequestController.request_demo.fn(api, db=session, request=request, data=DemoRequestIn(**kw))
    count = lambda: session.scalar(select(func.count()).select_from(DemoRequest))

    assert (await send(email=" QE@Plant.com ")).received
    await session.flush()
    await send(email="qe@plant.com")  # the same address the same day: still one request
    await session.flush()
    assert await count() == 1 and (await session.scalar(select(DemoRequest.email))) == "qe@plant.com"

    await send(email="bot@spam.io", website="http://spam.io")  # honeypot filled: accepted, not stored
    await session.flush()
    assert await count() == 1

    with pytest.raises(ValidationError):
        DemoRequestIn(email="not-an-email")
