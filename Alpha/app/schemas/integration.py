from pydantic import BaseModel, ConfigDict


class TrackIngestRequest(BaseModel):
    track_id: str
    timestamp: str
    version: str
    callsign: str | None = None
    location: dict | list | str | None = None
    altitude: int | None = None
    ground_speed: int | None = None
    heading: int | None = None


class AudioMetadataRequest(BaseModel):
    unique_id: str
    version: str
    icao_code: str | None = None
    band: str | None = None
    original_time: str | None = None
    process_time: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    data_type: str | None = None
    start_at: str | None = None
    end_at: str | None = None


class AsrResultRequest(BaseModel):
    result_id: str
    version: str
    unique_id: str | None = None
    vad_segments: dict | list | str | None = None
    transcript: str
    confidence: float | None = None
    engine: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class AnnotationSaveRequest(BaseModel):
    task_id: str
    annotator_id: str | None = None
    corrected_text: str
    version: str
    timestamp_corrections: dict | list | str | None = None
    annotations: dict | list | str | None = None


class VoiceInfoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unique_id: str
    icao_code: str | None = None
    band: str | None = None
    original_time: str | None = None
    process_time: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    data_type: str | None = None
    created_at: str
    end_at: str | None = None
    start_at: str | None = None


class AsrResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result_id: str
    unique_id: str | None = None
    vad_segments: str | None = None
    transcript: str
    confidence: float | None = None
    engine: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    created_at: str


class AnnotationTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    unique_id: str | None = None
    result_id: str | None = None
    assignee_id: str | None = None
    status: str | None = None
    priority: int | None = None
    created_at: str
    updated_at: str


class AnnotationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    annotation_id: str
    task_id: str
    corrected_text: str | None = None
    timestamp_corrections: str | None = None
    annotations: str | None = None
    annotator_id: str | None = None
    created_at: str
    updated_at: str


class TaskRealtimeCfgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    task_name: str | None = None
    server_addr: str | None = None
    server_port: int | None = None
    protocol: str | None = None
    timeout: int | None = None
    heart_beat: int | None = None
    icao_code: str | None = None
    band: str | None = None
    status: int | None = None
    create_time: str | None = None


class TaskRealtimeCfgUpsert(BaseModel):
    task_id: int | None = None
    task_name: str | None = None
    server_addr: str | None = None
    server_port: int | None = None
    protocol: str | None = "TCP"
    timeout: int | None = 30
    heart_beat: int | None = 10
    icao_code: str | None = None
    band: str | None = None
    status: int | None = 0


class TaskDownloadCfgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    task_name: str | None = None
    icao_code: str | None = None
    band: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    speed_limit: int | None = None
    exec_type: int | None = None
    exec_time: str | None = None
    status: int | None = None
    create_time: str | None = None


class TaskDownloadCfgUpsert(BaseModel):
    task_id: int | None = None
    task_name: str | None = None
    icao_code: str | None = None
    band: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    speed_limit: int | None = 0
    exec_type: int | None = 1
    exec_time: str | None = None
    status: int | None = 0


class SysBaseCfgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage_root: str | None = None
    slice_rule: str | None = None
    max_download_task: int | None = None
    max_realtime_conn: int | None = None
    api_timeout: int | None = None
    sync_interval: int | None = None
    update_time: str | None = None


class SysBaseCfgUpsert(BaseModel):
    storage_root: str | None = "/atc/a2/data/"
    slice_rule: str | None = "5min/100MB"
    max_download_task: int | None = 3
    max_realtime_conn: int | None = 5
    api_timeout: int | None = 5
    sync_interval: int | None = 5
