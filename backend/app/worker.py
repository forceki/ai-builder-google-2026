"""Background jobs (arq on Redis): read documents, then build the map and run the rules.

Run with:  arq app.worker.WorkerSettings
"""

import logging
import uuid
from typing import Any

from sqlalchemy import func, select

from app import storage
from app.ai.classify import classify
from app.ai.extract import extract, needs_review
from app.ai.inputs import document_parts
from app.ai.usage import ai_context
from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.events import publish
from app.models import CheckRun, Document
from app.models._common import utcnow
from app.models.document import DocStatus, DocType
from app.pipeline.run import execute_run
from app.queue import RUN_CHECKS, SETTLE_CHECKS, redis_settings

log = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["engine"] = make_engine()
    ctx["sessionmaker"] = make_sessionmaker(ctx["engine"])


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()


async def process_document(ctx: dict[str, Any], document_id: str) -> None:
    async with ctx["sessionmaker"]() as session:
        doc = await session.get(Document, uuid.UUID(document_id))
        if doc is None:
            return
        doc.status = DocStatus.READING
        doc.error = None
        await session.commit()
        await publish(ctx["redis"], doc.project_id, "document", id=doc.id, status=doc.status)

        try:
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
        except Exception as e:
            log.exception("extraction failed for %s", doc.filename)
            doc.status = DocStatus.FAILED
            doc.error = str(e)[:2000]
        await session.commit()
        await publish(ctx["redis"], doc.project_id, "document", id=doc.id, status=doc.status)

        # Once the last pending document of the project is read, rebuild the map and run the rules.
        await ctx["redis"].enqueue_job(
            SETTLE_CHECKS, str(doc.project_id), _defer_by=get_settings().checks_debounce_seconds
        )


async def settle_checks(ctx: dict[str, Any], project_id: str) -> None:
    pid = uuid.UUID(project_id)
    wait = get_settings().checks_debounce_seconds
    async with ctx["sessionmaker"]() as session:
        pending, last_change = (await session.execute(
            select(
                func.count().filter(Document.status.in_([DocStatus.QUEUED, DocStatus.READING])),
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
        await ctx["redis"].enqueue_job(RUN_CHECKS, str(run.id))
        await publish(ctx["redis"], pid, "run", id=run.id, status=run.status)


async def run_checks(ctx: dict[str, Any], run_id: str) -> None:
    async with ctx["sessionmaker"]() as session:
        run = await session.get(CheckRun, uuid.UUID(run_id))
        if run is not None:
            async def notify(status: str) -> None:
                await publish(ctx["redis"], run.project_id, "run", id=run.id, status=status)

            await execute_run(session, run, notify=notify)


class WorkerSettings:
    functions = [process_document, settle_checks, run_checks]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()
    max_jobs = 4
    job_timeout = 600
