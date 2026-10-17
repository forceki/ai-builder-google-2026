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
from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.models import CheckRun, Document
from app.models.document import DocStatus, DocType
from app.pipeline.run import execute_run
from app.queue import RUN_CHECKS, redis_settings

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

        try:
            data = await storage.get(get_settings().documents_bucket, doc.storage_key)
            parts = document_parts(doc.filename, data)
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

        # Once the last pending document of the project is read, rebuild the map and run the rules.
        pending = await session.scalar(
            select(func.count()).select_from(Document).where(
                Document.project_id == doc.project_id,
                Document.status.in_([DocStatus.QUEUED, DocStatus.READING]),
            )
        )
        if not pending:
            run = CheckRun(project_id=doc.project_id, rule_set=get_settings().rule_set)
            session.add(run)
            await session.commit()
            await ctx["redis"].enqueue_job(RUN_CHECKS, str(run.id))


async def run_checks(ctx: dict[str, Any], run_id: str) -> None:
    async with ctx["sessionmaker"]() as session:
        run = await session.get(CheckRun, uuid.UUID(run_id))
        if run is not None:
            await execute_run(session, run)


class WorkerSettings:
    functions = [process_document, run_checks]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()
    max_jobs = 4
    job_timeout = 600
