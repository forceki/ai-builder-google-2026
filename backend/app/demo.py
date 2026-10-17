import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.auth import upsert_user
from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.models import CheckRun, Document, Project, Signoff
from app.models.document import DocStatus
from app.pipeline.run import execute_run

DATA = Path(__file__).parent / "demo_data"
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

PROJECTS = [
    ("DEMO-2026-003", "Spool 04 · supplier first issue", "LOT 24-117 · 5 WELDS", "defective", set(), None),
    ("DEMO-2026-002", "Spool 04 · interim dossier", "LOT 24-117 · 4 WELDS", "clean",
     {"RT-2232_W-03.pdf", "WPQ_W-512.pdf"}, None),
    ("DEMO-2026-001", "Spool 04 · final dossier", "LOT 24-117 · 4 WELDS", "clean", set(),
     ("release", "All four checks pass. Released for shipment.")),
]
SIGNER = "Demo QA inspector"


async def load(session: AsyncSession, *, reset: bool = False, explain: bool = True) -> list[str]:
    s = get_settings()
    demo_user = await upsert_user(
        session, s.demo_email, "Demo inspector", s.demo_password.get_secret_value(), "Demo account"
    )
    await session.execute(update(Project).where(Project.owner_id.is_(None)).values(owner_id=demo_user.id))
    await session.commit()

    created = []
    for no, name, scope, dossier, left_out, signoff in PROJECTS:
        existing = await session.scalar(select(Project).where(Project.no == no))
        if existing and not reset:
            continue
        if existing:
            await session.execute(delete(Project).where(Project.id == existing.id))
            await session.commit()

        project = Project(no=no, name=name, scope=scope, owner_id=demo_user.id)
        session.add(project)
        await session.flush()
        for doc in json.loads((DATA / f"{dossier}.json").read_text(encoding="utf-8")):
            if doc["filename"] in left_out:
                continue
            content_type = CONTENT_TYPES.get(Path(doc["filename"]).suffix, "application/octet-stream")
            key = f"{no}/{doc['filename']}"
            if not await storage.exists(s.documents_bucket, key):
                data = (DATA / "files" / dossier / doc["filename"]).read_bytes()
                await storage.put(s.documents_bucket, key, data, content_type)
            session.add(Document(
                project_id=project.id, filename=doc["filename"], content_type=content_type,
                size=doc["size"], pages=doc["pages"], storage_key=key,
                doc_type=doc["doc_type"], suggested_type=doc["doc_type"],
                status=DocStatus.NEEDS_REVIEW if doc["needs_review"] else DocStatus.EXTRACTED,
                extraction=doc["extraction"],
            ))
        run = CheckRun(project_id=project.id, rule_set=s.rule_set)
        session.add(run)
        await session.commit()
        await execute_run(session, run, with_explanations=explain)
        if signoff:
            decision, comment = signoff
            session.add(Signoff(project_id=project.id, run_id=run.id, decision=decision, name=SIGNER, comment=comment))
            await session.commit()
        created.append(no)
    return created


async def _main(reset: bool, explain: bool) -> None:
    engine = make_engine()
    async with make_sessionmaker(engine)() as session:
        created = await load(session, reset=reset, explain=explain)
    await engine.dispose()
    print(f"demo account {get_settings().demo_email} saved")
    print(f"created {', '.join(created)}" if created else "demo projects exist, skipping (use --reset to recreate)")


def main() -> None:
    p = argparse.ArgumentParser(description="Create the demo account and the three demo projects.")
    p.add_argument("--reset", action="store_true", help="delete and recreate the demo projects")
    p.add_argument("--no-explain", action="store_true", help="skip the Gemini finding explanations")
    a = p.parse_args()
    asyncio.run(_main(a.reset, not a.no_explain))


if __name__ == "__main__":
    main()
