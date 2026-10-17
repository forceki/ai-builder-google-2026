"""One rule run: rebuild the traceability map from extracted documents, apply the rules,
explain the findings, and store everything on the CheckRun."""

import asyncio
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.explain import explain
from app.models import CheckRun, Document, Finding, TraceItem, TraceLink
from app.models._common import utcnow
from app.models.check import RunStatus
from app.models.document import DocStatus, DocType
from app.pipeline.mapper import Extracted, build_graph, to_map
from app.rules import run_all
from app.rules.types import RuleFinding, Status, TraceGraph

log = logging.getLogger(__name__)

EXPLAIN_CONCURRENCY = 4


async def execute_run(session: AsyncSession, run: CheckRun, *, with_explanations: bool = True) -> None:
    run.status = RunStatus.RUNNING
    await session.commit()
    try:
        docs = (await session.scalars(
            select(Document).where(
                Document.project_id == run.project_id,
                Document.status.in_([DocStatus.EXTRACTED, DocStatus.NEEDS_REVIEW]),
            )
        )).all()
        graph = build_graph([
            Extracted.from_json(d.filename, DocType(d.doc_type), d.extraction)
            for d in docs if d.doc_type and d.extraction
        ])
        await _replace_map(session, run.project_id, graph)

        results = run_all(graph)
        findings = [f for r in results for f in r.findings]
        explanations = await _explain_all(findings) if with_explanations else [(None, None)] * len(findings)
        for f, (text, next_step) in zip(findings, explanations, strict=True):
            session.add(Finding(
                run_id=run.id, check_id=f.check, rule_id=f.rule, item_key=f.item, status=f.status,
                message=f.message, sources=[{"document": s.document, "page": s.page} for s in f.sources],
                explanation=text, next_step=next_step,
            ))

        # An item counts once, at its worst status.
        item_status: dict[str, Status] = {}
        for f in findings:
            if item_status.get(f.item) != Status.REJECT:
                item_status[f.item] = f.status
        open_welds = sum(1 for k in item_status if k in graph.welds)
        run.summary = {
            "checks": [
                {"check": r.check, "name": r.name, "question": r.question, "status": r.status, "issues": len(r.findings)}
                for r in results
            ],
            "counts": {
                "pass": len(graph.welds) - open_welds,
                "hold": sum(s == Status.HOLD for s in item_status.values()),
                "reject": sum(s == Status.REJECT for s in item_status.values()),
            },
            "documents": len(docs),
            "welds": len(graph.welds),
            "fields": sum(_field_count(d.extraction) for d in docs if d.extraction),
        }
        run.status = RunStatus.COMPLETE
    except Exception as e:
        log.exception("rule run %s failed", run.id)
        await session.rollback()
        run = await session.get(CheckRun, run.id)
        run.status = RunStatus.FAILED
        run.error = str(e)[:2000]
    run.finished_at = utcnow()
    await session.commit()


def _field_count(extraction: dict) -> int:
    """Number of extracted values (record fields, excluding page/confidence bookkeeping)."""
    n = 0
    for records in extraction.values():
        if isinstance(records, list):
            for r in records:
                if isinstance(r, dict):
                    n += sum(1 for k in r if k not in ("page", "confidence"))
    return n


async def _explain_all(findings: list[RuleFinding]) -> list[tuple[str | None, str | None]]:
    """Best-effort: a model failure leaves the explanation empty and never affects the status."""
    sem = asyncio.Semaphore(EXPLAIN_CONCURRENCY)

    async def one(f: RuleFinding) -> tuple[str | None, str | None]:
        async with sem:
            try:
                e = await explain(f)
                return e.explanation, e.next_step
            except Exception:  # noqa: BLE001 - any model, API or network error
                log.warning("explanation failed for %s %s", f.rule, f.item, exc_info=True)
                return None, None

    return await asyncio.gather(*(one(f) for f in findings))


async def _replace_map(session: AsyncSession, project_id: uuid.UUID, graph: TraceGraph) -> None:
    await session.execute(delete(TraceLink).where(TraceLink.project_id == project_id))
    await session.execute(delete(TraceItem).where(TraceItem.project_id == project_id))
    nodes, edges = to_map(graph)
    items: dict[tuple[str, str], TraceItem] = {}
    for n in nodes:
        item = TraceItem(project_id=project_id, kind=n.kind, key=n.key, label=n.label, attributes=n.attributes,
                         sources=[{"document": s.document, "page": s.page} for s in n.sources])
        session.add(item)
        items[(n.kind, n.key)] = item
    await session.flush()
    for e in edges:
        session.add(TraceLink(project_id=project_id, from_item_id=items[e.from_key].id,
                              to_item_id=items[e.to_key].id, kind=e.kind))
