import asyncio
import json
import uuid
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager

_subscribers: defaultdict[str, set[asyncio.Queue[str]]] = defaultdict(set)


async def publish(project_id: uuid.UUID | str, event: str, **data: object) -> None:
    message = json.dumps({"event": event, **data}, default=str)
    for inbox in list(_subscribers.get(str(project_id), ())):
        inbox.put_nowait(message)


@contextmanager
def subscribe(project_id: uuid.UUID | str) -> Iterator[asyncio.Queue[str]]:
    key = str(project_id)
    inbox: asyncio.Queue[str] = asyncio.Queue()
    _subscribers[key].add(inbox)
    try:
        yield inbox
    finally:
        _subscribers[key].discard(inbox)
        if not _subscribers[key]:
            del _subscribers[key]
