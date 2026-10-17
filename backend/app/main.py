"""Heatmark API.  Run with:  uvicorn app.main:app --reload"""

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.di import Provide

from app import queue
from app.api import CheckController, DocumentController, ProjectController
from app.api.deps import provide_db, provide_queue
from app.config import get_settings
from app.db import create_tables, make_engine, make_sessionmaker


async def on_startup(app: Litestar) -> None:
    engine = make_engine()
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    if get_settings().auto_create_tables:
        await create_tables(engine)
    app.state.queue = await queue.connect()


async def on_shutdown(app: Litestar) -> None:
    await app.state.queue.aclose()
    await app.state.engine.dispose()


@get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app = Litestar(
    route_handlers=[health, ProjectController, DocumentController, CheckController],
    dependencies={"db": Provide(provide_db), "queue": Provide(provide_queue)},
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    cors_config=CORSConfig(allow_origins=get_settings().cors_origins),
    request_max_body_size=get_settings().max_upload_mb * 1024 * 1024 + 1024 * 1024,
)
