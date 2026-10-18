import asyncio

import pytest
from litestar.exceptions import PermissionDeniedException
from sqlalchemy.ext.asyncio import create_async_engine

from app import events, jobs
from app.api import tasks
from app.config import get_settings
from app.db import Base, make_sessionmaker
from app.models import CheckRun, Document, Project
from app.models.check import RunStatus
from app.models.document import DocStatus
from app.queue import RUN_CHECKS, Queue


class RecordingQueue:
    def __init__(self):
        self.jobs = []

    async def enqueue(self, job, *args, delay=0):
        self.jobs.append((job, args, delay))


@pytest.fixture
async def sessions():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield make_sessionmaker(engine)
    await engine.dispose()


@pytest.fixture
def cloud_tasks(monkeypatch):
    monkeypatch.setenv("HIBANAKO_TASKS_INLINE", "false")
    monkeypatch.setenv("HIBANAKO_TASKS_SERVICE_URL", "https://api.example.run.app")
    monkeypatch.setenv("HIBANAKO_TASKS_SERVICE_ACCOUNT", "tasks@example.iam.gserviceaccount.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _project(sessions):
    async with sessions() as s:
        project = Project(no="PRJ-1", name="P")
        s.add(project)
        await s.commit()
        return project.id


async def test_a_document_already_read_is_not_read_again(sessions, monkeypatch):
    async def no_download(*_):
        raise AssertionError("document was downloaded again")

    monkeypatch.setattr(jobs.storage, "get", no_download)
    pid = await _project(sessions)
    async with sessions() as s:
        doc = Document(project_id=pid, filename="a.pdf", content_type="application/pdf", size=1,
                       storage_key="k", status=DocStatus.EXTRACTED, extraction={"x": 1})
        s.add(doc)
        await s.commit()

    queue = RecordingQueue()
    await jobs.process_document(sessions, queue, str(doc.id))

    async with sessions() as s:
        assert (await s.get(Document, doc.id)).status == DocStatus.EXTRACTED
    assert queue.jobs == []


async def test_a_document_that_takes_too_long_fails_instead_of_hanging(sessions, monkeypatch):
    monkeypatch.setenv("HIBANAKO_EXTRACT_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()

    async def download(*_):
        return b"%PDF"

    async def hangs(*_):
        await asyncio.sleep(30)

    monkeypatch.setattr(jobs.storage, "get", download)
    monkeypatch.setattr(jobs, "document_parts", lambda *_: [])
    monkeypatch.setattr(jobs, "extract", hangs)
    pid = await _project(sessions)
    async with sessions() as s:
        doc = Document(project_id=pid, filename="a.pdf", content_type="application/pdf", size=1,
                       storage_key="k", doc_type="mtc")
        s.add(doc)
        await s.commit()

    queue = RecordingQueue()
    try:
        await asyncio.wait_for(jobs.process_document(sessions, queue, str(doc.id)), 5)
    finally:
        get_settings.cache_clear()

    async with sessions() as s:
        failed = await s.get(Document, doc.id)
        assert failed.status == DocStatus.FAILED
        assert "took longer" in failed.error
    assert [job for job, *_ in queue.jobs] == ["settle_checks"]


async def test_inline_queue_runs_at_most_the_configured_number_of_jobs_at_once():
    running = 0
    peak = 0
    release = asyncio.Event()

    async def run(job, args):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await release.wait()
        running -= 1

    queue = Queue(run)
    for i in range(10):
        await queue.enqueue(RUN_CHECKS, str(i))
    await asyncio.sleep(0.05)
    assert peak == get_settings().tasks_inline_concurrency
    release.set()
    await asyncio.sleep(0.05)
    await queue.close()


async def test_a_finished_check_run_is_not_run_again(sessions, monkeypatch):
    async def no_rerun(*_, **__):
        raise AssertionError("run executed again")

    monkeypatch.setattr(jobs, "execute_run", no_rerun)
    pid = await _project(sessions)
    async with sessions() as s:
        run = CheckRun(project_id=pid, rule_set="RS", status=RunStatus.COMPLETE)
        s.add(run)
        await s.commit()

    await jobs.run_checks(sessions, RecordingQueue(), str(run.id))


async def test_unfinished_work_is_resumed_after_a_restart(sessions):
    pid = await _project(sessions)
    async with sessions() as s:
        doc = Document(project_id=pid, filename="a.pdf", content_type="application/pdf", size=1,
                       storage_key="k", status=DocStatus.READING)
        run = CheckRun(project_id=pid, rule_set="RS", status=RunStatus.RUNNING)
        s.add_all([doc, run])
        await s.commit()

    queue = RecordingQueue()
    await jobs.resume_pending(sessions, queue)

    assert ("process_document", (str(doc.id),), 0) in queue.jobs
    assert (RUN_CHECKS, (str(run.id),), 0) in queue.jobs
    async with sessions() as s:
        assert (await s.get(CheckRun, run.id)).status == RunStatus.QUEUED


async def test_inline_queue_runs_the_job_in_the_background():
    done = asyncio.Event()
    seen = []

    async def run(job, args):
        seen.append((job, args))
        done.set()

    queue = Queue(run)
    await queue.enqueue(RUN_CHECKS, "run-1")
    await asyncio.wait_for(done.wait(), 1)
    assert seen == [(RUN_CHECKS, ["run-1"])]
    await queue.close()


async def test_task_endpoint_is_closed_when_jobs_run_in_process():
    with pytest.raises(PermissionDeniedException):
        await tasks.verify_task_request("Bearer anything")


async def test_task_endpoint_needs_a_token(cloud_tasks):
    with pytest.raises(PermissionDeniedException):
        await tasks.verify_task_request(None)


async def test_task_endpoint_rejects_tokens_from_other_accounts(cloud_tasks, monkeypatch):
    monkeypatch.setattr(tasks, "_claims", lambda token, audience: {"email": "someone@else.com", "email_verified": True})
    with pytest.raises(PermissionDeniedException):
        await tasks.verify_task_request("Bearer token")


async def test_task_endpoint_accepts_the_tasks_service_account(cloud_tasks, monkeypatch):
    audiences = []

    def claims(token, audience):
        audiences.append(audience)
        return {"email": "tasks@example.iam.gserviceaccount.com", "email_verified": True}

    monkeypatch.setattr(tasks, "_claims", claims)
    await tasks.verify_task_request("Bearer token")
    assert audiences == ["https://api.example.run.app"]


async def test_events_reach_subscribers_of_that_project_only():
    with events.subscribe("p1") as inbox, events.subscribe("p2") as other:
        await events.publish("p1", "document", id="d1", status="reading")
        assert '"status": "reading"' in await asyncio.wait_for(inbox.get(), 1)
        assert other.empty()
