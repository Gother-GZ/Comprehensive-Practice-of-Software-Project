from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums import QueueName
from app.models.event import EventConsumeFailure, EventDeadLetter
from app.mq.publisher import publish_message
from app.mq.redis_client import RedisUnavailableError, get_redis_client
from app.services.event_service import EventService


class QueueService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    def publish(self, queue_name: QueueName | str, message: dict) -> int:
        queue_name_value = self._normalize_queue_name(queue_name)
        return publish_message(queue_name_value, message)

    def publish_admin_message(self, queue_name: QueueName | str, message: dict) -> dict:
        queue_name_value = self._normalize_queue_name(queue_name)
        queue_length = self.publish(queue_name_value, message)
        return {
            "queue_name": queue_name_value,
            "queue_length": queue_length,
            "message_id": message.get("id"),
            "event_type": message.get("type"),
            "trace_id": message.get("trace_id"),
        }

    def get_queue_stats(self) -> dict:
        items = []
        redis_available = True
        redis_error = None
        try:
            redis_client = get_redis_client()
            redis_client.ping()
        except Exception as exc:
            redis_available = False
            redis_error = str(exc)
            redis_client = None
        for queue_name in QueueName:
            failure_count = self.db.scalar(select(func.count()).select_from(EventConsumeFailure).where(EventConsumeFailure.queue_name == queue_name.value)) or 0
            dead_letter_count = self.db.scalar(select(func.count()).select_from(EventDeadLetter).where(EventDeadLetter.queue_name == queue_name.value)) or 0
            last_consumed_at = self.event_service.get_config(f"queue:last_consumed_at:{queue_name.value}")
            last_failure_at = self.db.scalar(
                select(EventConsumeFailure.failed_at)
                .where(EventConsumeFailure.queue_name == queue_name.value)
                .order_by(EventConsumeFailure.failed_at.desc())
                .limit(1)
            )
            last_dead_letter_at = self.db.scalar(
                select(EventDeadLetter.created_at)
                .where(EventDeadLetter.queue_name == queue_name.value)
                .order_by(EventDeadLetter.created_at.desc())
                .limit(1)
            )
            last_failure_message_id = self.db.scalar(
                select(EventConsumeFailure.message_id)
                .where(EventConsumeFailure.queue_name == queue_name.value)
                .order_by(EventConsumeFailure.failed_at.desc())
                .limit(1)
            )
            last_dead_letter_message_id = self.db.scalar(
                select(EventDeadLetter.message_id)
                .where(EventDeadLetter.queue_name == queue_name.value)
                .order_by(EventDeadLetter.created_at.desc())
                .limit(1)
            )
            queue_length = redis_client.llen(queue_name.value) if redis_client is not None else None
            items.append(
                {
                    "queue_name": queue_name.value,
                    "queue_length": queue_length,
                    "last_consumed_at": last_consumed_at,
                    "last_failure_at": last_failure_at,
                    "last_dead_letter_at": last_dead_letter_at,
                    "last_failure_message_id": last_failure_message_id,
                    "last_dead_letter_message_id": last_dead_letter_message_id,
                    "failure_count": failure_count,
                    "dead_letter_count": dead_letter_count,
                    "redis_available": redis_available,
                    "error": redis_error,
                }
            )
        return {"items": items, "redis_available": redis_available, "error": redis_error}

    @staticmethod
    def _normalize_queue_name(queue_name: QueueName | str) -> str:
        queue_name_value = str(queue_name)
        valid_names = {item.value for item in QueueName}
        if queue_name_value not in valid_names:
            raise ValueError(f"unsupported queue name: {queue_name_value}")
        return queue_name_value
