"""Load the PRJ-2026-041 specimen project into the database.

    uv run python -m app.seed             # skip if it already exists
    uv run python -m app.seed --reset     # delete and recreate it
    uv run python -m app.seed --explain   # also generate finding explanations (Gemini calls)

The documents are already extracted, so no files are stored and no extraction calls are made.
"""

import argparse
import asyncio

from sqlalchemy import delete, select

from app.config import get_settings
from app.db import create_tables, make_engine, make_sessionmaker
from app.models import CheckRun, Document, Project
from app.models.document import DocStatus
from app.pipeline.run import execute_run
from app.specimen import specimen

PROJECTS = [
    ("PRJ-2026-041", "Pressure vessel skid", "ASSY PS-3 · 18 WELDS", True),
    ("PRJ-2026-045", "Platform handrails", "NOT SCOPED", False),
]
NEEDS_REVIEW = {"FAB-REC_031.pdf"}


def _pages(extraction: dict) -> int:
    return max((r["page"] for v in extraction.values() if isinstance(v, list) for r in v), default=1)


async def seed(reset: bool, explain: bool) -> None:
    engine = make_engine()
    await create_tables(engine)
    async with make_sessionmaker(engine)() as session:
        for no, name, scope, with_docs in PROJECTS:
            existing = await session.scalar(select(Project).where(Project.no == no))
            if existing and not reset:
                print(f"{no} exists, skipping (use --reset to recreate)")
                continue
            if existing:
                await session.execute(delete(Project).where(Project.id == existing.id))
                await session.commit()

            project = Project(no=no, name=name, scope=scope)
            session.add(project)
            await session.flush()
            if with_docs:
                for doc in specimen():
                    session.add(Document(
                        project_id=project.id, filename=doc.filename, content_type="application/pdf", size=0,
                        pages=_pages(doc.data.model_dump()),
                        storage_key=f"seed/{doc.filename}", doc_type=doc.doc_type, suggested_type=doc.doc_type,
                        status=DocStatus.NEEDS_REVIEW if doc.filename in NEEDS_REVIEW else DocStatus.EXTRACTED,
                        extraction=doc.data.model_dump(mode="json"),
                    ))
                run = CheckRun(project_id=project.id, rule_set=get_settings().rule_set)
                session.add(run)
                await session.commit()
                await execute_run(session, run, with_explanations=explain)
                print(f"{no}: {len(specimen())} documents, run {run.status}, summary {run.summary['counts']}")
            else:
                await session.commit()
                print(f"{no}: empty project")
    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reset", action="store_true")
    p.add_argument("--explain", action="store_true")
    a = p.parse_args()
    asyncio.run(seed(a.reset, a.explain))


if __name__ == "__main__":
    main()
