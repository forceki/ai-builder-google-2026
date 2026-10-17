"""Background job queue (arq on Redis). Job functions live in app.worker."""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

PROCESS_DOCUMENT = "process_document"
SETTLE_CHECKS = "settle_checks"
RUN_CHECKS = "run_checks"


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def connect() -> ArqRedis:
    return await create_pool(redis_settings())
