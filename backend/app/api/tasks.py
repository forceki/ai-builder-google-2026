import asyncio

import google.auth.transport.requests
from google.oauth2 import id_token
from litestar import Request, post
from litestar.exceptions import NotFoundException, PermissionDeniedException
from pydantic import BaseModel

from app.config import get_settings
from app.jobs import JOBS, run_job


class TaskIn(BaseModel):
    args: list[str]


def _claims(token: str, audience: str) -> dict:
    return id_token.verify_oauth2_token(token, google.auth.transport.requests.Request(), audience=audience)


async def verify_task_request(authorization: str | None) -> None:
    s = get_settings()
    if s.tasks_inline or not (s.tasks_service_url and s.tasks_service_account):
        raise PermissionDeniedException("background jobs run in-process here")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise PermissionDeniedException("missing task token")
    try:
        claims = await asyncio.to_thread(_claims, token, s.tasks_service_url.rstrip("/"))
    except ValueError as e:
        raise PermissionDeniedException("invalid task token") from e
    if claims.get("email") != s.tasks_service_account or not claims.get("email_verified"):
        raise PermissionDeniedException("task token is not from the tasks service account")


@post("/tasks/{job:str}", status_code=200)
async def run_task(request: Request, job: str, data: TaskIn) -> dict[str, bool]:
    if job not in JOBS:
        raise NotFoundException(f"unknown job {job}")
    await verify_task_request(request.headers.get("authorization"))
    await run_job(request.app.state.sessionmaker, request.app.state.queue, job, data.args)
    return {"ok": True}
