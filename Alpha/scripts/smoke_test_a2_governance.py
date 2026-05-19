from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.db.init_db import initialize_database
from app.db.seed_data import seed_demo_vsp_data
from app.db.session import SessionLocal
from app.main import app
from app.models.integration import AnnotationTask


def ensure_seed_state() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_vsp_data(db)
        if not db.get(AnnotationTask, "task_a2_gov_1"):
            db.add(
                AnnotationTask(
                    task_id="task_a2_gov_1",
                    unique_id="voice_a2_gov_1",
                    result_id=None,
                    assignee_id="bootstrap-admin",
                    status="pending",
                    priority=3,
                    created_at="2026-04-22T00:00:00.000Z",
                    updated_at="2026-04-22T00:00:00.000Z",
                )
            )
            db.commit()


def main() -> None:
    ensure_seed_state()
    client = TestClient(app)

    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    writes = [
        (
            "/api/v1/audio/metadata",
            {
                "unique_id": "voice_a2_gov_1",
                "version": "v1",
                "icao_code": "VHHH",
                "band": "118.2MHz",
                "original_time": "2026-04-22T00:00:00.000Z",
                "process_time": "2026-04-22T00:00:02.000Z",
                "file_path": "/tmp/a2_gov.wav",
                "file_name": "a2_gov.wav",
                "file_size": 4096,
                "data_type": "S",
                "start_at": "2026-04-22T00:00:00.000Z",
                "end_at": "2026-04-22T00:00:20.000Z",
            },
        ),
        (
            "/api/v1/asr/results",
            {
                "result_id": "res_a2_gov_1",
                "version": "v1",
                "unique_id": "voice_a2_gov_1",
                "vad_segments": [{"start": 0, "end": 2}],
                "transcript": "alpha governance test",
                "confidence": 0.95,
                "engine": "sensevoice",
                "start_time": "2026-04-22T00:00:00.000Z",
                "end_time": "2026-04-22T00:00:20.000Z",
            },
        ),
        (
            "/api/v1/annotations/save",
            {
                "task_id": "task_a2_gov_1",
                "annotator_id": "bootstrap-admin",
                "corrected_text": "alpha governance checked",
                "version": "v1",
                "timestamp_corrections": [{"start": 0.0, "end": 2.1}],
                "annotations": {"status": "checked"},
            },
        ),
        (
            "/api/v1/integration/a2/realtime-tasks",
            {
                "task_name": "gov-realtime",
                "server_addr": "127.0.0.1",
                "server_port": 9001,
                "protocol": "TCP",
                "timeout": 30,
                "heart_beat": 10,
                "icao_code": "VHHH",
                "band": "118.2MHz",
                "status": 1,
            },
        ),
        (
            "/api/v1/integration/a2/download-tasks",
            {
                "task_name": "gov-download",
                "icao_code": "VHHH",
                "band": "118.2MHz",
                "start_time": "2026-04-22T00:00:00.000Z",
                "end_time": "2026-04-22T01:00:00.000Z",
                "speed_limit": 1024,
                "exec_type": 1,
                "exec_time": "2026-04-22T02:00:00.000Z",
                "status": 1,
            },
        ),
    ]
    for path, payload in writes:
        response = client.post(path, json=payload, headers=headers if "/integration/a2/" in path else None)
        body = response.json()
        if response.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(f"write failed: {path} -> {response.status_code} {body}")

    config_response = client.put(
        "/api/v1/integration/a2/system-config",
        json={
            "storage_root": "/atc/a2/test/",
            "slice_rule": "10min/200MB",
            "max_download_task": 4,
            "max_realtime_conn": 6,
            "api_timeout": 8,
            "sync_interval": 10,
        },
        headers=headers,
    )
    config_body = config_response.json()
    if config_response.status_code != 200 or config_body.get("code") != 0:
        raise RuntimeError(f"config update failed: {config_response.status_code} {config_body}")

    reads = [
        "/api/v1/integration/audio?unique_id=voice_a2_gov_1",
        "/api/v1/integration/asr?result_id=res_a2_gov_1",
        "/api/v1/integration/annotation-tasks?task_id=task_a2_gov_1",
        "/api/v1/integration/annotation-results?task_id=task_a2_gov_1",
        "/api/v1/integration/a2/realtime-tasks?icao_code=VHHH",
        "/api/v1/integration/a2/download-tasks?icao_code=VHHH",
        "/api/v1/integration/a2/system-config",
    ]
    for path in reads:
        response = client.get(path, headers=headers)
        body = response.json()
        if response.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(f"read failed: {path} -> {response.status_code} {body}")

    print("smoke_test_a2_governance=ok")


if __name__ == "__main__":
    main()
