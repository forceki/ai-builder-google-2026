import json
import logging
import uuid

from redis.asyncio import Redis

log = logging.getLogger(__name__)


def channel(project_id: uuid.UUID | str) -> str:
    return f"heatmark:project:{project_id}"


async def publish(redis: Redis, project_id: uuid.UUID | str, event: str, **data: object) -> None:
    try:
        await redis.publish(channel(project_id), json.dumps({"event": event, **data}, default=str))
    except Exception:
        log.warning("could not publish %s for project %s", event, project_id, exc_info=True)
