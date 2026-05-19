from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.common.response import success_response
from app.db.session import get_db
from app.schemas.integration import (
    AnnotationResultOut,
    AnnotationSaveRequest,
    AnnotationTaskOut,
    AsrResultOut,
    AsrResultRequest,
    AudioMetadataRequest,
    SysBaseCfgOut,
    SysBaseCfgUpsert,
    TaskDownloadCfgOut,
    TaskDownloadCfgUpsert,
    TaskRealtimeCfgOut,
    TaskRealtimeCfgUpsert,
    TrackIngestRequest,
    VoiceInfoOut,
)
from app.services.integration_service import IntegrationService

router = APIRouter()


@router.post("/tracks/ingest")
def ingest_track(payload: TrackIngestRequest, db: Session = Depends(get_db)):
    return success_response(data=IntegrationService(db).ingest_track(payload))


@router.post("/audio/metadata")
def save_audio_metadata(payload: AudioMetadataRequest, db: Session = Depends(get_db)):
    return success_response(data=IntegrationService(db).save_audio_metadata(payload))


@router.post("/asr/results")
def save_asr_result(payload: AsrResultRequest, db: Session = Depends(get_db)):
    return success_response(data=IntegrationService(db).save_asr_result(payload))


@router.get("/annotations/load")
def load_annotations(task_id: str | None = None, unique_id: str | None = None, db: Session = Depends(get_db)):
    data = IntegrationService(db).load_annotations(task_id=task_id, unique_id=unique_id)
    if not data:
        return success_response(data=None, message="annotation task not found")
    return success_response(data=data)


@router.post("/annotations/save")
def save_annotations(payload: AnnotationSaveRequest, db: Session = Depends(get_db)):
    return success_response(data=IntegrationService(db).save_annotations(payload))


@router.get("/integration/audio")
def list_audio(
    unique_id: str | None = None,
    icao_code: str | None = None,
    band: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = IntegrationService(db).list_audio(unique_id, icao_code, band, start_time, end_time, page, page_size)
    data["items"] = [VoiceInfoOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/integration/asr")
def list_asr(
    result_id: str | None = None,
    unique_id: str | None = None,
    engine: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = IntegrationService(db).list_asr(result_id, unique_id, engine, page, page_size)
    data["items"] = [AsrResultOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/integration/annotation-tasks")
def list_annotation_tasks(
    task_id: str | None = None,
    unique_id: str | None = None,
    status: str | None = None,
    assignee_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = IntegrationService(db).list_annotation_tasks(task_id, unique_id, status, assignee_id, page, page_size)
    data["items"] = [AnnotationTaskOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/integration/annotation-results")
def list_annotation_results(
    task_id: str | None = None,
    annotation_id: str | None = None,
    annotator_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = IntegrationService(db).list_annotation_results(task_id, annotation_id, annotator_id, page, page_size)
    data["items"] = [AnnotationResultOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/integration/a2/realtime-tasks")
def list_realtime_tasks(
    icao_code: str | None = None,
    band: str | None = None,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = IntegrationService(db).list_realtime_tasks(icao_code, band, status, page, page_size)
    data["items"] = [TaskRealtimeCfgOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.post("/integration/a2/realtime-tasks")
def upsert_realtime_task(payload: TaskRealtimeCfgUpsert, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    task = IntegrationService(db).upsert_realtime_task(payload)
    return success_response(data=TaskRealtimeCfgOut.model_validate(task).model_dump())


@router.get("/integration/a2/download-tasks")
def list_download_tasks(
    icao_code: str | None = None,
    band: str | None = None,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = IntegrationService(db).list_download_tasks(icao_code, band, status, page, page_size)
    data["items"] = [TaskDownloadCfgOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.post("/integration/a2/download-tasks")
def upsert_download_task(payload: TaskDownloadCfgUpsert, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    task = IntegrationService(db).upsert_download_task(payload)
    return success_response(data=TaskDownloadCfgOut.model_validate(task).model_dump())


@router.get("/integration/a2/system-config")
def get_system_config(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    row = IntegrationService(db).get_system_config()
    return success_response(data=SysBaseCfgOut.model_validate(row).model_dump())


@router.put("/integration/a2/system-config")
def update_system_config(payload: SysBaseCfgUpsert, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    row = IntegrationService(db).update_system_config(payload)
    return success_response(data=SysBaseCfgOut.model_validate(row).model_dump())
