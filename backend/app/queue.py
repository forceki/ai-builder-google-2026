"""Background job queue: in-process tasks locally, Google Cloud Tasks when deployed. Job functions live in app.jobs."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from app.config import get_settings

log = logging.getLogger(__name__)

PROCESS_DOCUMENT = "process_document"
SETTLE_CHECKS = "settle_checks"
RUN_CHECKS = "run_checks"
ASSESS_DOCUMENT = "assess_document"

Runner = Callable[[str, list[str]], Awaitable[None]]


class Queue:
    def __init__(self, run: Runner) -> None:
        self._run = run
        self._pending: set[asyncio.Task] = set()
        self._slots = asyncio.Semaphore(get_settings().tasks_inline_concurrency)
        self._client = None

    async def enqueue(self, job: str, *args: str, delay: int = 0) -> None:
        if get_settings().tasks_inline:
            task = asyncio.create_task(self._inline(job, list(args), delay))
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)
        else:
            await self._cloud_task(job, list(args), delay)

    async def close(self) -> None:
        for task in self._pending:
            task.cancel()
        if self._client is not None:
            await self._client.transport.close()

    async def _inline(self, job: str, args: list[str], delay: int) -> None:
        if delay:
            await asyncio.sleep(delay)
        async with self._slots:
            try:
                await self._run(job, args)
            except Exception:
                log.exception("job %s%s failed", job, args)

    async def _cloud_task(self, job: str, args: list[str], delay: int) -> None:
        from google.cloud import tasks_v2
        from google.protobuf import duration_pb2, timestamp_pb2

        s = get_settings()
        if not (s.gcp_project and s.tasks_service_url and s.tasks_service_account):
            raise RuntimeError("Cloud Tasks needs HIBANAKO_GCP_PROJECT, HIBANAKO_TASKS_SERVICE_URL and HIBANAKO_TASKS_SERVICE_ACCOUNT")
        if self._client is None:
            self._client = tasks_v2.CloudTasksAsyncClient()
        base = s.tasks_service_url.rstrip("/")
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{base}/tasks/{job}",
                headers={"Content-Type": "application/json"},
                body=json.dumps({"args": args}).encode(),
                oidc_token=tasks_v2.OidcToken(service_account_email=s.tasks_service_account, audience=base),
            ),
            dispatch_deadline=duration_pb2.Duration(seconds=s.tasks_deadline_seconds),
        )
        if delay:
            when = timestamp_pb2.Timestamp()
            when.FromDatetime(datetime.now(UTC) + timedelta(seconds=delay))
            task.schedule_time = when
        parent = self._client.queue_path(s.gcp_project, s.tasks_location, s.tasks_queue)
        await self._client.create_task(parent=parent, task=task)
