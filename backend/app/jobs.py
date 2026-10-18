"""Background jobs: read documents, then build the map and run the rules."""

import asyncio
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import storage
from app.ai.classify import classify
from app.ai.extract import extract, needs_review
from app.ai.inputs import document_parts
from app.ai.usage import ai_context
from app.config import get_settings
from app.events import publish
from app.models import CheckRun, Document
from app.models._common import utcnow
from app.models.check import RunStatus
from app.models.document import DocStatus, DocType
from app.pipeline.run import execute_run
from app.queue import PROCESS_DOCUMENT, RUN_CHECKS, SETTLE_CHECKS, Queue

log = logging.getLogger(__name__)

Sessions = async_sessionmaker[AsyncSession]
PENDING = (DocStatus.QUEUED, DocStatus.READING)


async def process_document(sessions: Sessions, queue: Queue, document_id: str) -> None:
    async with sessions() as session:
        doc = await session.get(Document, uuid.UUID(document_id))
        if doc is None or doc.status not in PENDING:
            return
        doc.status = DocStatus.READING
        doc.error = None
        await session.commit()
        await publish(doc.project_id, "document", id=doc.id, status=doc.status)

        limit = get_settings().extract_timeout_seconds
        try:
            async with asyncio.timeout(limit):
                data = await storage.get(get_settings().documents_bucket, doc.storage_key)
                parts = document_parts(doc.filename, data)
                with ai_context(project_id=doc.project_id, document_id=doc.id):
                    if doc.doc_type is None:
                        suggestion = await classify(parts)
                        doc.suggested_type = DocType(suggestion.doc_type)
                        doc.doc_type = doc.suggested_type
                    result = await extract(DocType(doc.doc_type), parts)
            doc.extraction = result.model_dump(mode="json")
            doc.status = DocStatus.NEEDS_REVIEW if needs_review(result) else DocStatus.EXTRACTED
        except TimeoutError:
            log.warning("extraction of %s took longer than %ss", doc.filename, limit)
            doc.status = DocStatus.FAILED
            doc.error = f"Reading took longer than {limit // 60} minutes. Change the document type to read it again."
        except Exception as e:
            log.exception("extraction failed for %s", doc.filename)
            doc.status = DocStatus.FAILED
            doc.error = str(e)[:2000]
        await session.commit()
        await publish(doc.project_id, "document", id=doc.id, status=doc.status)

        # Once the last pending document of the project is read, rebuild the map and run the rules.
        await queue.enqueue(SETTLE_CHECKS, str(doc.project_id), delay=get_settings().checks_debounce_seconds)


async def settle_checks(sessions: Sessions, queue: Queue, project_id: str) -> None:
    pid = uuid.UUID(project_id)
    wait = get_settings().checks_debounce_seconds
    async with sessions() as session:
        pending, last_change = (await session.execute(
            select(
                func.count().filter(Document.status.in_(PENDING)),
                func.max(Document.updated_at),
            ).where(Document.project_id == pid)
        )).one()
        if pending or last_change is None or (utcnow() - last_change).total_seconds() < wait - 1:
            return
        newer_run = await session.scalar(
            select(func.count()).select_from(CheckRun).where(
                CheckRun.project_id == pid, CheckRun.created_at > last_change
            )
        )
        if newer_run:
            return
        run = CheckRun(project_id=pid, rule_set=get_settings().rule_set)
        session.add(run)
        await session.commit()
        await queue.enqueue(RUN_CHECKS, str(run.id))
        await publish(pid, "run", id=run.id, status=run.status)


async def run_checks(sessions: Sessions, queue: Queue, run_id: str) -> None:
    async with sessions() as session:
        run = await session.get(CheckRun, uuid.UUID(run_id))
        if run is None or run.status != RunStatus.QUEUED:
            return

        async def notify(status: str) -> None:
            await publish(run.project_id, "run", id=run.id, status=status)

        await execute_run(session, run, notify=notify)


JOBS = {PROCESS_DOCUMENT: process_document, SETTLE_CHECKS: settle_checks, RUN_CHECKS: run_checks}


async def run_job(sessions: Sessions, queue: Queue, job: str, args: list[str]) -> None:
    await JOBS[job](sessions, queue, *args)


async def resume_pending(sessions: Sessions, queue: Queue) -> None:
    async with sessions() as session:
        docs = (await session.scalars(select(Document.id).where(Document.status.in_(PENDING)))).all()
        runs = (await session.scalars(
            select(CheckRun).where(CheckRun.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]))
        )).all()
        for run in runs:
            run.status = RunStatus.QUEUED
        await session.commit()
    for doc_id in docs:
        await queue.enqueue(PROCESS_DOCUMENT, str(doc_id))
    for run in runs:
        await queue.enqueue(RUN_CHECKS, str(run.id))
    if docs or runs:
        log.info("resumed %d documents and %d check runs", len(docs), len(runs))
