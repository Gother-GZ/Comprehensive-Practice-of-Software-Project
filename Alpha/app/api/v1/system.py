from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.common.response import success_response
from app.db.session import get_db
from app.schemas.system import ConsumerRunOut, ConsumerRunRequest, ConsumerStatusOut, DeadLetterOut, FailureOut, QueuePublishOut, QueuePublishRequest, SystemConfigOut, SystemConfigUpsert, SystemLogOut
from app.services.consumer_service import ConsumerService, export_rows
from app.services.event_service import EventService
from app.services.queue_service import QueueService

router = APIRouter()


@router.get("/queues")
def queues(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return success_response(data=QueueService(db).get_queue_stats())


@router.post("/queues/publish")
def publish_queue_message(payload: QueuePublishRequest, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    data = QueueService(db).publish_admin_message(payload.queue_name, payload.message)
    return success_response(data=QueuePublishOut.model_validate(data).model_dump())


@router.get("/consumers")
def list_consumers(_admin=Depends(require_admin)):
    items = [ConsumerStatusOut.model_validate(item).model_dump() for item in ConsumerService().list_consumers()]
    return success_response(data=items)


@router.post("/consumers/run-once")
def run_consumer_once(payload: ConsumerRunRequest, _admin=Depends(require_admin)):
    data = ConsumerService().consume_once(payload.queue_name)
    return success_response(data=ConsumerRunOut.model_validate(data).model_dump())


@router.get("/events/failures")
def failures(queue_name: str | None = None, message_id: str | None = None, page: int = 1, page_size: int = 20, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    data = EventService(db).list_failures(queue_name=queue_name, message_id=message_id, page=page, page_size=page_size)
    data["items"] = [FailureOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/events/failures/export")
def export_failures(queue_name: str | None = None, message_id: str | None = None, format: str = "jsonl", _admin=Depends(require_admin), db: Session = Depends(get_db)):
    items = EventService(db).export_failures(queue_name=queue_name, message_id=message_id)
    content, media_type = export_rows(items, format)
    return Response(content=content, media_type=media_type)


@router.get("/events/dead-letters")
def dead_letters(queue_name: str | None = None, message_id: str | None = None, page: int = 1, page_size: int = 20, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    data = EventService(db).list_dead_letters(queue_name=queue_name, message_id=message_id, page=page, page_size=page_size)
    data["items"] = [DeadLetterOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/events/dead-letters/export")
def export_dead_letters(queue_name: str | None = None, message_id: str | None = None, format: str = "jsonl", _admin=Depends(require_admin), db: Session = Depends(get_db)):
    items = EventService(db).export_dead_letters(queue_name=queue_name, message_id=message_id)
    content, media_type = export_rows(items, format)
    return Response(content=content, media_type=media_type)


@router.get("/logs")
def logs(level: str | None = None, source: str | None = None, trace_id: str | None = None, page: int = 1, page_size: int = 20, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    data = EventService(db).list_logs(level=level, source=source, trace_id=trace_id, page=page, page_size=page_size)
    data["items"] = [SystemLogOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/logs/export")
def export_logs(level: str | None = None, source: str | None = None, trace_id: str | None = None, format: str = "jsonl", _admin=Depends(require_admin), db: Session = Depends(get_db)):
    items = EventService(db).export_logs(level=level, source=source, trace_id=trace_id)
    content, media_type = export_rows(items, format)
    return Response(content=content, media_type=media_type)


@router.get("/configs")
def list_configs(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    items = EventService(db).list_configs()
    return success_response(data=[SystemConfigOut.model_validate(item).model_dump() for item in items])


@router.get("/configs/{config_key}")
def get_config(config_key: str, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    row = EventService(db).get_config_row(config_key)
    if not row:
        return success_response(data=None, message="config not found")
    return success_response(data=SystemConfigOut.model_validate(row).model_dump())


@router.put("/configs/{config_key}")
def upsert_config(config_key: str, payload: SystemConfigUpsert, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    service = EventService(db)
    service.upsert_config(config_key, payload.config_value, payload.description)
    row = service.get_config_row(config_key)
    return success_response(data=SystemConfigOut.model_validate(row).model_dump())
