from functools import lru_cache

import redis

from app.core.config import get_settings


class RedisUnavailableError(RuntimeError):
    pass


@lru_cache
def get_redis_client() -> redis.Redis:
    try:
        return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover
        raise RedisUnavailableError("failed to create redis client") from exc

