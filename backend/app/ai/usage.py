import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import make_engine, make_sessionmaker
from app.models import AiLog

log = logging.getLogger(__name__)

_context: ContextVar[dict[str, Any]] = ContextVar("ai_context", default={})
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


@contextmanager
def ai_context(**fields: uuid.UUID | str | None) -> Iterator[None]:
    token = _context.set({**_context.get(), **fields})
    try:
        yield
    finally:
        _context.reset(token)


async def record(*, purpose: str, model: str, duration_ms: int, usage: Any = None, error: str | None = None) -> None:
    global _sessionmaker
    ctx = _context.get()
    entry = AiLog(
        purpose=purpose,
        model=model,
        project_id=ctx.get("project_id"),
        document_id=ctx.get("document_id"),
        item_key=ctx.get("item_key"),
        status="error" if error else "ok",
        error=error[:2000] if error else None,
        duration_ms=duration_ms,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        thinking_tokens=getattr(usage, "thoughts_token_count", None),
        cached_tokens=getattr(usage, "cached_content_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
    )
    try:
        if _sessionmaker is None:
            _sessionmaker = make_sessionmaker(make_engine())
        async with _sessionmaker() as session:
            session.add(entry)
            await session.commit()
    except Exception:
        log.warning("could not write ai_logs row for %s %s", purpose, model, exc_info=True)
