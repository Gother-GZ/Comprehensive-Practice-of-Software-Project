from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.common.enums import QueueName
from app.db.init_db import initialize_database
from app.db.session import SessionLocal
from app.services.queue_service import QueueService


def _build_demo_message(queue_name: str) -> dict:
    if queue_name == QueueName.TRACK_INGEST.value:
        return {
            "id": "evt_cli_track_001",
            "type": "track.ingest",
            "version": "v1",
            "producer": "cli-publisher",
            "timestamp": "2026-04-22T12:00:00.000Z",
            "trace_id": "trace-cli-track-001",
            "payload": {
                "track_id": "trk_cli_001",
                "timestamp": "2026-04-22T12:00:00.000Z",
                "callsign": "CPA321",
                "location": {"type": "Point", "coordinates": [113.92, 22.31]},
                "altitude": 14000,
                "ground_speed": 340,
                "heading": 255,
            },
        }
    if queue_name == QueueName.SYSTEM_LOG.value:
        return {
            "id": "evt_cli_log_001",
            "type": "system.log.created",
            "version": "v1",
            "producer": "cli-publisher",
            "timestamp": "2026-04-22T12:05:00.000Z",
            "trace_id": "trace-cli-log-001",
            "payload": {"message": "cli smoke log"},
        }
    if queue_name == QueueName.AUDIO_PROCESS.value:
        return {
            "id": "evt_cli_audio_001",
            "type": "audio.process.requested",
            "version": "v1",
            "producer": "cli-publisher",
            "timestamp": "2026-04-22T12:06:00.000Z",
            "trace_id": "trace-cli-audio-001",
            "payload": {
                "unique_id": "voice_cli_001",
                "file_path": "/tmp/voice_cli_001.wav",
                "icao_code": "VHHH",
                "original_time": "2026-04-22T12:06:00.000Z",
            },
        }
    if queue_name == QueueName.ANNOTATION_NOTIFY.value:
        return {
            "id": "evt_cli_annotation_001",
            "type": "annotation.saved",
            "version": "v1",
            "producer": "cli-publisher",
            "timestamp": "2026-04-22T12:07:00.000Z",
            "trace_id": "trace-cli-annotation-001",
            "payload": {
                "annotation_id": "ann_cli_001",
                "task_id": "task_cli_001",
                "annotator_id": "bootstrap-admin",
            },
        }
    return {
        "id": f"evt_cli_{queue_name.replace(':', '_')}_001",
        "type": f"{queue_name.replace(':', '.')}.requested",
        "version": "v1",
        "producer": "cli-publisher",
        "timestamp": "2026-04-22T12:10:00.000Z",
        "trace_id": f"trace-cli-{queue_name.replace(':', '-')}-001",
        "payload": {},
    }


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        print("usage: python scripts/publish_queue_message.py <queue_name> [json_message_path]")
        raise SystemExit(1)

    queue_name = sys.argv[1]
    initialize_database()

    if len(sys.argv) == 3:
        message = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    else:
        message = _build_demo_message(queue_name)

    with SessionLocal() as db:
        result = QueueService(db).publish_admin_message(queue_name, message)
    print(result)


if __name__ == "__main__":
    main()
