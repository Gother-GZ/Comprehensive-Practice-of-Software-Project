from app.common.enums import LogLevel, QueueName
from app.db.session import SessionLocal
from app.mq.consumer_base import BaseListConsumer
from app.schemas.integration import TrackIngestRequest
from app.services.event_service import EventService
from app.services.integration_service import IntegrationService


class TrackIngestConsumer(BaseListConsumer):
    queue_name = QueueName.TRACK_INGEST.value
    consumer_name = "track-ingest-consumer"

    def handle_payload(self, payload: dict) -> None:
        payload_body = payload.get("payload")
        if not isinstance(payload_body, dict):
            raise ValueError("missing payload")
        request = TrackIngestRequest.model_validate({**payload_body, "version": payload.get("version", "v1")})
        with SessionLocal() as db:
            IntegrationService(db).ingest_track(request)
            EventService(db).log(
                self.consumer_name,
                f"track ingested: {request.track_id}",
                LogLevel.INFO,
                payload.get("trace_id"),
                {"message_id": payload.get("id"), "queue_name": self.queue_name},
            )


class AudioProcessConsumer(BaseListConsumer):
    queue_name = QueueName.AUDIO_PROCESS.value
    consumer_name = "audio-process-consumer"

    def handle_payload(self, payload: dict) -> None:
        payload_body = payload.get("payload")
        if not isinstance(payload_body, dict):
            raise ValueError("missing payload")
        if not payload_body.get("unique_id") or not payload_body.get("file_path"):
            raise ValueError("missing audio process fields")
        with SessionLocal() as db:
            EventService(db).log(
                self.consumer_name,
                f"audio process requested: {payload_body['unique_id']}",
                LogLevel.INFO,
                payload.get("trace_id"),
                {"message_id": payload.get("id"), "queue_name": self.queue_name, "payload": payload_body},
            )


class AnnotationNotifyConsumer(BaseListConsumer):
    queue_name = QueueName.ANNOTATION_NOTIFY.value
    consumer_name = "annotation-notify-consumer"

    def handle_payload(self, payload: dict) -> None:
        payload_body = payload.get("payload")
        if not isinstance(payload_body, dict):
            raise ValueError("missing payload")
        if not payload_body.get("task_id"):
            raise ValueError("missing annotation task_id")
        with SessionLocal() as db:
            EventService(db).log(
                self.consumer_name,
                f"annotation notify accepted: {payload_body['task_id']}",
                LogLevel.INFO,
                payload.get("trace_id"),
                {"message_id": payload.get("id"), "queue_name": self.queue_name, "payload": payload_body},
            )


class SystemLogConsumer(BaseListConsumer):
    queue_name = QueueName.SYSTEM_LOG.value
    consumer_name = "system-log-consumer"

    def handle_payload(self, payload: dict) -> None:
        if "type" not in payload:
            raise ValueError("missing event type")
        payload_body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        level_value = str(payload_body.get("level", LogLevel.INFO.value)).lower()
        level = LogLevel(level_value) if level_value in {item.value for item in LogLevel} else LogLevel.INFO
        source = payload_body.get("source") or payload.get("producer") or self.consumer_name
        message = payload_body.get("message") or f"system event accepted: {payload.get('type')}"
        context = payload_body.get("context")
        if context is None:
            context = {"message_id": payload.get("id"), "queue_name": self.queue_name}
        with SessionLocal() as db:
            EventService(db).log(source, message, level, payload.get("trace_id"), context)
