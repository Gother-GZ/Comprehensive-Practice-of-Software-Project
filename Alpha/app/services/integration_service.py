from uuid import uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.security import utc_now_iso
from app.models.integration import (
    AdsbTrack,
    AnnotationResult,
    AnnotationTask,
    AsrResult,
    SysBaseCfg,
    TaskDownloadCfg,
    TaskRealtimeCfg,
    VoiceInfo,
)
from app.services.event_service import dumps_json


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

    def ingest_track(self, payload):
        track = self.db.get(AdsbTrack, payload.track_id)
        if not track:
            track = AdsbTrack(track_id=payload.track_id, created_at=utc_now_iso())
            self.db.add(track)
        track.callsign = payload.callsign
        track.location = dumps_json(payload.location)
        track.altitude = payload.altitude
        track.ground_speed = payload.ground_speed
        track.heading = payload.heading
        track.timestamp = payload.timestamp
        self.db.commit()
        return {"track_id": track.track_id, "version": payload.version}

    def save_audio_metadata(self, payload):
        voice = self.db.get(VoiceInfo, payload.unique_id)
        if not voice:
            voice = VoiceInfo(unique_id=payload.unique_id, created_at=utc_now_iso())
            self.db.add(voice)
        voice.icao_code = payload.icao_code
        voice.band = payload.band
        voice.original_time = payload.original_time
        voice.process_time = payload.process_time
        voice.file_path = payload.file_path
        voice.file_name = payload.file_name
        voice.file_size = payload.file_size
        voice.data_type = payload.data_type
        voice.start_at = payload.start_at
        voice.end_at = payload.end_at
        self.db.commit()
        return {"unique_id": voice.unique_id, "version": payload.version}

    def save_asr_result(self, payload):
        result = self.db.get(AsrResult, payload.result_id)
        if not result:
            result = AsrResult(result_id=payload.result_id, created_at=utc_now_iso())
            self.db.add(result)
        result.unique_id = payload.unique_id
        result.vad_segments = dumps_json(payload.vad_segments)
        result.engine = payload.engine
        result.transcript = payload.transcript
        result.confidence = payload.confidence
        result.start_time = payload.start_time
        result.end_time = payload.end_time
        self.db.commit()
        return {"result_id": result.result_id, "version": payload.version}

    def load_annotations(self, task_id: str | None, unique_id: str | None):
        if task_id:
            task = self.db.get(AnnotationTask, task_id)
        else:
            task = self.db.scalar(select(AnnotationTask).where(AnnotationTask.unique_id == unique_id)) if unique_id else None
        if not task:
            return None
        result = self.db.scalar(select(AnnotationResult).where(AnnotationResult.task_id == task.task_id))
        return {
            "task_id": task.task_id,
            "unique_id": task.unique_id,
            "result_id": task.result_id,
            "status": task.status,
            "priority": task.priority,
            "annotation_result": {
                "annotation_id": result.annotation_id,
                "annotator_id": result.annotator_id,
                "corrected_text": result.corrected_text,
                "timestamp_corrections": result.timestamp_corrections,
                "annotations": result.annotations,
            }
            if result
            else None,
        }

    def save_annotations(self, payload):
        result = self.db.scalar(select(AnnotationResult).where(AnnotationResult.task_id == payload.task_id))
        now = utc_now_iso()
        if not result:
            result = AnnotationResult(
                annotation_id=uuid4().hex,
                task_id=payload.task_id,
                annotator_id=payload.annotator_id,
                corrected_text=payload.corrected_text,
                timestamp_corrections=dumps_json(payload.timestamp_corrections),
                annotations=dumps_json(payload.annotations),
                created_at=now,
                updated_at=now,
            )
            self.db.add(result)
        else:
            result.annotator_id = payload.annotator_id
            result.corrected_text = payload.corrected_text
            result.timestamp_corrections = dumps_json(payload.timestamp_corrections)
            result.annotations = dumps_json(payload.annotations)
            result.updated_at = now
        task = self.db.get(AnnotationTask, payload.task_id)
        if task:
            task.updated_at = now
        self.db.commit()
        return {"annotation_id": result.annotation_id, "version": payload.version}

    def list_audio(self, unique_id: str | None, icao_code: str | None, band: str | None, start_time: str | None, end_time: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[VoiceInfo]] = select(VoiceInfo)
        if unique_id := _clean_str(unique_id):
            stmt = stmt.where(VoiceInfo.unique_id == unique_id)
        if icao_code := _clean_str(icao_code):
            stmt = stmt.where(VoiceInfo.icao_code == icao_code)
        if band := _clean_str(band):
            stmt = stmt.where(VoiceInfo.band == band)
        if start_time := _clean_str(start_time):
            stmt = stmt.where(VoiceInfo.original_time >= start_time)
        if end_time := _clean_str(end_time):
            stmt = stmt.where(VoiceInfo.original_time <= end_time)
        return _paginate(self.db, stmt, VoiceInfo.unique_id, page, page_size)

    def list_asr(self, result_id: str | None, unique_id: str | None, engine: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[AsrResult]] = select(AsrResult)
        if result_id := _clean_str(result_id):
            stmt = stmt.where(AsrResult.result_id == result_id)
        if unique_id := _clean_str(unique_id):
            stmt = stmt.where(AsrResult.unique_id == unique_id)
        if engine := _clean_str(engine):
            stmt = stmt.where(AsrResult.engine == engine)
        return _paginate(self.db, stmt, AsrResult.created_at, page, page_size, desc=True)

    def list_annotation_tasks(self, task_id: str | None, unique_id: str | None, status: str | None, assignee_id: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[AnnotationTask]] = select(AnnotationTask)
        if task_id := _clean_str(task_id):
            stmt = stmt.where(AnnotationTask.task_id == task_id)
        if unique_id := _clean_str(unique_id):
            stmt = stmt.where(AnnotationTask.unique_id == unique_id)
        if status := _clean_str(status):
            stmt = stmt.where(AnnotationTask.status == status)
        if assignee_id := _clean_str(assignee_id):
            stmt = stmt.where(AnnotationTask.assignee_id == assignee_id)
        return _paginate(self.db, stmt, AnnotationTask.updated_at, page, page_size, desc=True)

    def list_annotation_results(self, task_id: str | None, annotation_id: str | None, annotator_id: str | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[AnnotationResult]] = select(AnnotationResult)
        if task_id := _clean_str(task_id):
            stmt = stmt.where(AnnotationResult.task_id == task_id)
        if annotation_id := _clean_str(annotation_id):
            stmt = stmt.where(AnnotationResult.annotation_id == annotation_id)
        if annotator_id := _clean_str(annotator_id):
            stmt = stmt.where(AnnotationResult.annotator_id == annotator_id)
        return _paginate(self.db, stmt, AnnotationResult.updated_at, page, page_size, desc=True)

    def list_realtime_tasks(self, icao_code: str | None, band: str | None, status: int | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[TaskRealtimeCfg]] = select(TaskRealtimeCfg)
        if icao_code := _clean_str(icao_code):
            stmt = stmt.where(TaskRealtimeCfg.icao_code == icao_code)
        if band := _clean_str(band):
            stmt = stmt.where(TaskRealtimeCfg.band == band)
        if status is not None:
            stmt = stmt.where(TaskRealtimeCfg.status == status)
        return _paginate(self.db, stmt, TaskRealtimeCfg.task_id, page, page_size, desc=True)

    def upsert_realtime_task(self, payload):
        task = self.db.get(TaskRealtimeCfg, payload.task_id) if payload.task_id is not None else None
        if not task:
            task = TaskRealtimeCfg(create_time=utc_now_iso())
            self.db.add(task)
        task.task_name = payload.task_name
        task.server_addr = payload.server_addr
        task.server_port = payload.server_port
        task.protocol = payload.protocol
        task.timeout = payload.timeout
        task.heart_beat = payload.heart_beat
        task.icao_code = payload.icao_code
        task.band = payload.band
        task.status = payload.status
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_download_tasks(self, icao_code: str | None, band: str | None, status: int | None, page: int, page_size: int):
        page, page_size = _normalize_pagination(page, page_size)
        stmt: Select[tuple[TaskDownloadCfg]] = select(TaskDownloadCfg)
        if icao_code := _clean_str(icao_code):
            stmt = stmt.where(TaskDownloadCfg.icao_code == icao_code)
        if band := _clean_str(band):
            stmt = stmt.where(TaskDownloadCfg.band == band)
        if status is not None:
            stmt = stmt.where(TaskDownloadCfg.status == status)
        return _paginate(self.db, stmt, TaskDownloadCfg.task_id, page, page_size, desc=True)

    def upsert_download_task(self, payload):
        task = self.db.get(TaskDownloadCfg, payload.task_id) if payload.task_id is not None else None
        if not task:
            task = TaskDownloadCfg(create_time=utc_now_iso())
            self.db.add(task)
        task.task_name = payload.task_name
        task.icao_code = payload.icao_code
        task.band = payload.band
        task.start_time = payload.start_time
        task.end_time = payload.end_time
        task.speed_limit = payload.speed_limit
        task.exec_type = payload.exec_type
        task.exec_time = payload.exec_time
        task.status = payload.status
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_system_config(self):
        row = self.db.get(SysBaseCfg, 1)
        if row:
            return row
        row = SysBaseCfg(
            id=1,
            storage_root="/atc/a2/data/",
            slice_rule="5min/100MB",
            max_download_task=3,
            max_realtime_conn=5,
            api_timeout=5,
            sync_interval=5,
            update_time=utc_now_iso(),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_system_config(self, payload):
        row = self.get_system_config()
        row.storage_root = payload.storage_root
        row.slice_rule = payload.slice_rule
        row.max_download_task = payload.max_download_task
        row.max_realtime_conn = payload.max_realtime_conn
        row.api_timeout = payload.api_timeout
        row.sync_interval = payload.sync_interval
        row.update_time = utc_now_iso()
        self.db.commit()
        self.db.refresh(row)
        return row


def _paginate(db: Session, stmt, order_column, page: int, page_size: int, desc: bool = False):
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order_by_clause = order_column.desc() if desc else order_column.asc()
    items = db.scalars(stmt.order_by(order_by_clause).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    return safe_page, safe_page_size


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
