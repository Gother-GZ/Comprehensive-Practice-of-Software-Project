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


def ensure_smoke_data() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_vsp_data(db)
        if not db.get(AnnotationTask, "task_smoke_1"):
            db.add(
                AnnotationTask(
                    task_id="task_smoke_1",
                    unique_id="voice_smoke_1",
                    result_id=None,
                    assignee_id="bootstrap-admin",
                    status="pending",
                    priority=3,
                    created_at="2026-04-15T00:00:00.000Z",
                    updated_at="2026-04-15T00:00:00.000Z",
                )
            )
            db.commit()


def main() -> None:
    ensure_smoke_data()
    client = TestClient(app)

    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    login_body = login.json()
    if login_body["code"] != 0:
        raise RuntimeError(f"login failed: {login_body}")
    headers = {"Authorization": f"Bearer {login_body['data']['access_token']}"}

    readonly_checks = [
        ("GET", "/health", None, None),
        ("GET", "/api/v1/users/me", None, headers),
        ("GET", "/api/v1/users?page=1&page_size=5", None, headers),
        ("GET", "/api/v1/vsp/airports", None, None),
        ("GET", "/api/v1/vsp/waypoints?page=1&page_size=5", None, None),
        ("GET", "/api/v1/vsp/procedures?airport_id=airport_vhhh", None, None),
        ("GET", "/api/v1/vsp/airlines?airline_code=CX", None, None),
        ("GET", "/api/v1/vsp/runways?airport_id=airport_vhhh", None, None),
        ("GET", "/api/v1/vsp/frequencies?airport_id=airport_vhhh", None, None),
        ("GET", "/api/v1/vsp/navaids?airport_id=airport_vhhh", None, None),
        ("GET", "/api/v1/vsp/geojson/procedures/proc_vhhh_star_01", None, None),
        ("GET", "/api/v1/system/queues", None, headers),
        ("GET", "/api/v1/system/logs?page=1&page_size=5", None, headers),
    ]
    for method, path, payload, request_headers in readonly_checks:
        response = client.request(method, path, json=payload, headers=request_headers)
        body = response.json()
        if response.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(f"request failed: {path} -> {response.status_code} {body}")

    writes = [
        (
            "/api/v1/tracks/ingest",
            {
                "track_id": "trk_smoke_1",
                "timestamp": "2026-04-15T00:00:00.000Z",
                "version": "v1",
                "callsign": "CPA001",
                "location": {"type": "Point", "coordinates": [113.9185, 22.308]},
                "altitude": 15000,
                "ground_speed": 340,
                "heading": 251,
            },
        ),
        (
            "/api/v1/audio/metadata",
            {
                "unique_id": "voice_smoke_1",
                "version": "v1",
                "icao_code": "VHHH",
                "band": "118.2MHz",
                "original_time": "2026-04-15T00:00:00.000Z",
                "process_time": "2026-04-15T00:00:03.000Z",
                "file_path": "/tmp/voice.wav",
                "file_name": "voice.wav",
                "file_size": 2048,
                "data_type": "S",
                "start_at": "2026-04-15T00:00:00.000Z",
                "end_at": "2026-04-15T00:00:30.000Z",
            },
        ),
        (
            "/api/v1/asr/results",
            {
                "result_id": "res_smoke_1",
                "version": "v1",
                "unique_id": "voice_smoke_1",
                "vad_segments": [{"start": 0, "end": 3}],
                "transcript": "hello approach",
                "confidence": 0.93,
                "engine": "sensevoice",
                "start_time": "2026-04-15T00:00:00.000Z",
                "end_time": "2026-04-15T00:00:30.000Z",
            },
        ),
        (
            "/api/v1/annotations/save",
            {
                "task_id": "task_smoke_1",
                "annotator_id": "bootstrap-admin",
                "corrected_text": "hello hong kong approach",
                "version": "v1",
                "timestamp_corrections": [{"start": 0.0, "end": 3.2}],
                "annotations": {"status": "ok"},
            },
        ),
    ]
    for path, payload in writes:
        response = client.post(path, json=payload)
        body = response.json()
        if response.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(f"request failed: {path} -> {response.status_code} {body}")

    load = client.get("/api/v1/annotations/load", params={"unique_id": "voice_smoke_1"})
    load_body = load.json()
    if load.status_code != 200 or load_body.get("code") != 0:
        raise RuntimeError(f"request failed: /api/v1/annotations/load -> {load.status_code} {load_body}")

    print("smoke_test_api=ok")


if __name__ == "__main__":
    main()
