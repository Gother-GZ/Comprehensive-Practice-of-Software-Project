import json
from abc import ABC, abstractmethod

from app.common.enums import LogLevel
from app.core.config import get_settings
from app.core.security import utc_now_iso
from app.db.session import SessionLocal
from app.mq.redis_client import RedisUnavailableError, get_redis_client
from app.services.event_service import EventService


class BaseListConsumer(ABC):
    queue_name: str
    consumer_name: str

    @abstractmethod
    def handle_payload(self, payload: dict) -> None:
        raise NotImplementedError

    def consume_once(self) -> bool:
        try:
            client = get_redis_client()
            raw = client.lpop(self.queue_name)
        except Exception as exc:
            raise RedisUnavailableError(str(exc)) from exc
        if not raw:
            return False
        message = json.loads(raw)
        message_id = message.get("id", "unknown")
        event_type = message.get("type", "unknown")
        retry_count = int(message.get("retry_count", 0))
        with SessionLocal() as db:
            event_service = EventService(db)
            try:
                self.handle_payload(message)
                event_service.upsert_config(f"queue:last_consumed_at:{self.queue_name}", utc_now_iso(), "last consume time")
            except Exception as exc:
                retry_count += 1
                message["retry_count"] = retry_count
                event_service.record_failure(self.queue_name, message_id, event_type, self.consumer_name, retry_count, str(exc), message)
                event_service.log(self.consumer_name, f"consumer failed for {event_type}", LogLevel.ERROR, message.get("trace_id"), {"error": str(exc), "message_id": message_id})
                if retry_count >= get_settings().redis_max_retry_count:
                    event_service.record_dead_letter(self.queue_name, message_id, event_type, retry_count, str(exc), message)
                else:
                    client = get_redis_client()
                    client.rpush(self.queue_name, json.dumps(message, ensure_ascii=False))
        return True

