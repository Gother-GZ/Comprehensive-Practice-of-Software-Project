from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AdsbTrack(Base):
    __tablename__ = "adsb_tracks"

    track_id: Mapped[str] = mapped_column(String, primary_key=True)
    callsign: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    altitude: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ground_speed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class VoiceInfo(Base):
    __tablename__ = "a2_voice_info"

    unique_id: Mapped[str] = mapped_column(String, primary_key=True)
    icao_code: Mapped[str | None] = mapped_column(String, nullable=True)
    band: Mapped[str | None] = mapped_column(String, nullable=True)
    original_time: Mapped[str | None] = mapped_column(String, nullable=True)
    process_time: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_type: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    end_at: Mapped[str | None] = mapped_column(String, nullable=True)
    start_at: Mapped[str | None] = mapped_column(String, nullable=True)


class VoiceTrackRel(Base):
    __tablename__ = "a2_voice_track_rel"

    rel_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unique_id: Mapped[str | None] = mapped_column(String, nullable=True)
    track_id: Mapped[str | None] = mapped_column(String, nullable=True)
    create_time: Mapped[str | None] = mapped_column(String, nullable=True)


class TaskRealtimeCfg(Base):
    __tablename__ = "a2_task_realtime_cfg"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str | None] = mapped_column(String, nullable=True)
    server_addr: Mapped[str | None] = mapped_column(String, nullable=True)
    server_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String, nullable=True)
    timeout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_beat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icao_code: Mapped[str | None] = mapped_column(String, nullable=True)
    band: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    create_time: Mapped[str | None] = mapped_column(String, nullable=True)


class TaskDownloadCfg(Base):
    __tablename__ = "a2_task_download_cfg"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str | None] = mapped_column(String, nullable=True)
    icao_code: Mapped[str | None] = mapped_column(String, nullable=True)
    band: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String, nullable=True)
    end_time: Mapped[str | None] = mapped_column(String, nullable=True)
    speed_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exec_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exec_time: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    create_time: Mapped[str | None] = mapped_column(String, nullable=True)


class SysBaseCfg(Base):
    __tablename__ = "a2_sys_base_cfg"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storage_root: Mapped[str | None] = mapped_column(Text, nullable=True)
    slice_rule: Mapped[str | None] = mapped_column(String, nullable=True)
    max_download_task: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_realtime_conn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_timeout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    update_time: Mapped[str | None] = mapped_column(String, nullable=True)


class AsrResult(Base):
    __tablename__ = "asr_results"

    result_id: Mapped[str] = mapped_column(String, primary_key=True)
    unique_id: Mapped[str | None] = mapped_column(String, nullable=True)
    vad_segments: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    engine: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String, nullable=True)
    end_time: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class AnnotationTask(Base):
    __tablename__ = "annotation_tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    unique_id: Mapped[str | None] = mapped_column(String, nullable=True)
    result_id: Mapped[str | None] = mapped_column(ForeignKey("asr_results.result_id"), nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class AnnotationResult(Base):
    __tablename__ = "annotation_results"

    annotation_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("annotation_tasks.task_id"), nullable=False)
    annotator_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    corrected_text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_corrections: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
