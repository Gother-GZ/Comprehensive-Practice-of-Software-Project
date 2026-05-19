import json

from app.mq.redis_client import RedisUnavailableError, get_redis_client


def publish_message(queue_name: str, message: dict) -> int:
    try:
        client = get_redis_client()
        return client.rpush(queue_name, json.dumps(message, ensure_ascii=False))
    except Exception as exc:
        raise RedisUnavailableError(str(exc)) from exc

