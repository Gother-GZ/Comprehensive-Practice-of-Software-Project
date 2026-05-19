import json
from uuid import uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.common.enums import LogLevel
from app.core.security import utc_now_iso
from app.models.event import EventConsumeFailure, EventDeadLetter, SystemConfig, SystemLog


def dumps_json(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def log(self, source: str, message: str, level: LogLevel = LogLevel.INFO, trace_id: str | None = None, context=None) -> SystemLog:
        log = SystemLog(
            log_id=uuid4().hex,
            log_level=level.value,
            source=source,
            message=message,
            trace_id=trace_id,
            context_json=dumps_json(context),
            created_at=utc_now_iso(),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def record_failure(self, queue_name: str, message_id: str, event_type: str, consumer_name: str, retry_count: int, error_message: str, payload) -> EventConsumeFailure:
        failure = EventConsumeFailure(
            failure_id=uuid4().hex,
            queue_name=queue_name,
            message_id=message_id,
            event_type=event_type,
            consumer_name=consumer_name,
            retry_count=retry_count,
            error_message=error_message,
            payload_json=dumps_json(payload) or "{}",
            failed_at=utc_now_iso(),
        )
        self.db.add(failure)
        self.db.commit()
        self.db.refresh(failure)
        return failure

    def record_dead_letter(self, queue_name: str, message_id: str, event_type: str, retry_count: int, last_error_message: str, payload) -> EventDeadLetter:
        dead = EventDeadLetter(
            dead_letter_id=uuid4().hex,
            queue_name=queue_name,
            message_id=message_id,
            event_type=event_type,
            payload_json=dumps_json(payload) or "{}",
            last_error_message=last_error_message,
            retry_count=retry_count,
            created_at=utc_now_iso(),
        )
        self.db.add(dead)
        self.db.commit()
        self.db.refresh(dead)
        return dead

    def upsert_config(self, key: str, value: str, description: str | None = None) -> None:
        existing = self.db.get(SystemConfig, key)
        if existing:
            existing.config_value = value
            existing.description = description or existing.description
            existing.updated_at = utc_now_iso()
        else:
            existing = SystemConfig(config_key=key, config_value=value, description=description, updated_at=utc_now_iso())
            self.db.add(existing)
        self.db.commit()

    def get_config(self, key: str) -> str | None:
        existing = self.db.get(SystemConfig, key)
        return existing.config_value if existing else None

    def get_config_row(self, key: str) -> SystemConfig | None:
        return self.db.get(SystemConfig, key)

    def list_configs(self):
        return self.db.scalars(select(SystemConfig).order_by(SystemConfig.config_key.asc())).all()

    def list_failures(self, queue_name: str | None, message_id: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[EventConsumeFailure]] = select(EventConsumeFailure)
        if queue_name := _clean_str(queue_name):
            stmt = stmt.where(EventConsumeFailure.queue_name == queue_name)
        if message_id := _clean_str(message_id):
            stmt = stmt.where(EventConsumeFailure.message_id == message_id)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = self.db.scalars(stmt.order_by(EventConsumeFailure.failed_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def export_failures(self, queue_name: str | None, message_id: str | None) -> list[dict]:
        stmt: Select[tuple[EventConsumeFailure]] = select(EventConsumeFailure).order_by(EventConsumeFailure.failed_at.desc())
        if queue_name := _clean_str(queue_name):
            stmt = stmt.where(EventConsumeFailure.queue_name == queue_name)
        if message_id := _clean_str(message_id):
            stmt = stmt.where(EventConsumeFailure.message_id == message_id)
        items = self.db.scalars(stmt).all()
        return [
            {
                "failure_id": item.failure_id,
                "queue_name": item.queue_name,
                "message_id": item.message_id,
                "event_type": item.event_type,
                "consumer_name": item.consumer_name,
                "retry_count": item.retry_count,
                "error_message": item.error_message,
                "payload_json": item.payload_json,
                "failed_at": item.failed_at,
            }
            for item in items
        ]

    def list_dead_letters(self, queue_name: str | None, message_id: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[EventDeadLetter]] = select(EventDeadLetter)
        if queue_name := _clean_str(queue_name):
            stmt = stmt.where(EventDeadLetter.queue_name == queue_name)
        if message_id := _clean_str(message_id):
            stmt = stmt.where(EventDeadLetter.message_id == message_id)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = self.db.scalars(stmt.order_by(EventDeadLetter.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def export_dead_letters(self, queue_name: str | None, message_id: str | None) -> list[dict]:
        stmt: Select[tuple[EventDeadLetter]] = select(EventDeadLetter).order_by(EventDeadLetter.created_at.desc())
        if queue_name := _clean_str(queue_name):
            stmt = stmt.where(EventDeadLetter.queue_name == queue_name)
        if message_id := _clean_str(message_id):
            stmt = stmt.where(EventDeadLetter.message_id == message_id)
        items = self.db.scalars(stmt).all()
        return [
            {
                "dead_letter_id": item.dead_letter_id,
                "queue_name": item.queue_name,
                "message_id": item.message_id,
                "event_type": item.event_type,
                "payload_json": item.payload_json,
                "last_error_message": item.last_error_message,
                "retry_count": item.retry_count,
                "created_at": item.created_at,
            }
            for item in items
        ]

    def list_logs(self, level: str | None, source: str | None, trace_id: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[SystemLog]] = select(SystemLog)
        if level := _clean_str(level):
            stmt = stmt.where(SystemLog.log_level == level)
        if source := _clean_str(source):
            stmt = stmt.where(SystemLog.source == source)
        if trace_id := _clean_str(trace_id):
            stmt = stmt.where(SystemLog.trace_id == trace_id)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = self.db.scalars(stmt.order_by(SystemLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def export_logs(self, level: str | None, source: str | None, trace_id: str | None) -> list[dict]:
        stmt: Select[tuple[SystemLog]] = select(SystemLog).order_by(SystemLog.created_at.desc())
        if level := _clean_str(level):
            stmt = stmt.where(SystemLog.log_level == level)
        if source := _clean_str(source):
            stmt = stmt.where(SystemLog.source == source)
        if trace_id := _clean_str(trace_id):
            stmt = stmt.where(SystemLog.trace_id == trace_id)
        items = self.db.scalars(stmt).all()
        return [
            {
                "log_id": item.log_id,
                "log_level": item.log_level,
                "source": item.source,
                "message": item.message,
                "trace_id": item.trace_id,
                "context_json": item.context_json,
                "created_at": item.created_at,
            }
            for item in items
        ]


def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    return safe_page, safe_page_size


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
