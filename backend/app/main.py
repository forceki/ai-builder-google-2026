"""Hibanako API.  Run with:  uvicorn app.main:app --reload"""

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.di import Provide
from litestar.logging.config import LoggingConfig

from app.api import (
    AiLogController,
    AssessmentController,
    AuthController,
    CheckController,
    DemoRequestController,
    DocumentController,
    ProjectController,
)
from app.api.deps import provide_db, provide_queue, provide_user
from app.api.events import project_events
from app.api.tasks import run_task
from app.auth import jwt_auth
from app.config import get_settings
from app.db import create_tables, make_engine, make_sessionmaker
from app.jobs import resume_pending, run_job
from app.queue import Queue


async def on_startup(app: Litestar) -> None:
    engine = make_engine()
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    if get_settings().auto_create_tables:
        await create_tables(engine)
    app.state.queue = Queue(lambda job, args: run_job(app.state.sessionmaker, app.state.queue, job, args))
    if get_settings().tasks_inline:
        await resume_pending(app.state.sessionmaker, app.state.queue)


async def on_shutdown(app: Litestar) -> None:
    await app.state.queue.close()
    await app.state.engine.dispose()


@get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app = Litestar(
    route_handlers=[
        health, AuthController, ProjectController, DocumentController, CheckController, AiLogController,
        AssessmentController, DemoRequestController,
        project_events, run_task,
    ],
    on_app_init=[jwt_auth.on_app_init],
    dependencies={"db": Provide(provide_db), "queue": Provide(provide_queue), "user": Provide(provide_user)},
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    cors_config=CORSConfig(allow_origins=get_settings().cors_origins),
    logging_config=LoggingConfig(log_exceptions="always", disable_stack_trace={400, 401, 403, 404, 405, 409, 413, 422}),
    request_max_body_size=get_settings().max_upload_mb * 1024 * 1024 + 1024 * 1024,
)
