"""List "Request a demo" submissions from the landing page.

    uv run python -m app.demo_requests            # last 50, newest first
    uv run python -m app.demo_requests --csv      # all of them as CSV
"""

import argparse
import asyncio
import csv
import sys

from sqlalchemy import select

from app.db import make_engine, make_sessionmaker
from app.models.demo_request import DemoRequest


async def _list(limit: int | None, as_csv: bool) -> None:
    engine = make_engine()
    async with make_sessionmaker(engine)() as session:
        q = select(DemoRequest).order_by(DemoRequest.created_at.desc())
        rows = (await session.scalars(q.limit(limit) if limit else q)).all()
    await engine.dispose()
    if as_csv:
        w = csv.writer(sys.stdout)
        w.writerow(["received_at", "email"])
        w.writerows([r.created_at.isoformat(timespec="seconds"), r.email] for r in rows)
        return
    for r in rows:
        print(f"{r.created_at:%Y-%m-%d %H:%M} UTC  {r.email}")
    print(f"{len(rows)} request(s)")


def main() -> None:
    p = argparse.ArgumentParser(description="List demo requests from the landing page.")
    p.add_argument("--csv", action="store_true", help="print every request as CSV")
    a = p.parse_args()
    asyncio.run(_list(None if a.csv else 50, a.csv))


if __name__ == "__main__":
    main()
