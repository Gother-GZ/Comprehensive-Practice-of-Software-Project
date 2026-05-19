from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.db.init_db import initialize_database
from app.db.session import SessionLocal
from app.main import app
from app.models.integration import AdsbTrack
from app.mq.example_consumers import TrackIngestConsumer
from app.mq.redis_client import get_redis_client


def main() -> None:
    initialize_database()
    client = TestClient(app)
    redis_client = get_redis_client()
    redis_client.delete("track:ingest")

    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    publish_response = client.post(
        "/api/v1/system/queues/publish",
        json={
            "queue_name": "track:ingest",
            "message": {
                "id": "evt_admin_publish_1",
                "type": "track.ingest",
                "version": "v1",
                "producer": "admin-api",
                "timestamp": "2026-04-22T12:30:00.000Z",
                "trace_id": "trace-admin-publish-1",
                "payload": {
                    "track_id": "trk_admin_publish_1",
                    "timestamp": "2026-04-22T12:30:00.000Z",
                    "callsign": "CPA555",
                    "location": {"type": "Point", "coordinates": [113.92, 22.31]},
                    "altitude": 15000,
                    "ground_speed": 350,
                    "heading": 251,
                },
            },
        },
        headers=headers,
    )
    publish_body = publish_response.json()
    if publish_response.status_code != 200 or publish_body.get("code") != 0:
        raise RuntimeError(f"publish api failed: {publish_response.status_code} {publish_body}")

    queue_response = client.get("/api/v1/system/queues", headers=headers)
    queue_body = queue_response.json()
    if queue_response.status_code != 200 or queue_body.get("code") != 0:
        raise RuntimeError(f"queue stats failed: {queue_response.status_code} {queue_body}")
    track_item = next((item for item in queue_body["data"]["items"] if item["queue_name"] == "track:ingest"), None)
    if not track_item or (track_item["queue_length"] or 0) < 1:
        raise RuntimeError(f"expected queued item after publish, got: {queue_body}")

    consumed = TrackIngestConsumer().consume_once()
    if not consumed:
        raise RuntimeError("expected track consumer to consume published message")

    queue_after_response = client.get("/api/v1/system/queues", headers=headers)
    queue_after_body = queue_after_response.json()
    if queue_after_response.status_code != 200 or queue_after_body.get("code") != 0:
        raise RuntimeError(f"queue stats after consume failed: {queue_after_response.status_code} {queue_after_body}")
    track_after = next((item for item in queue_after_body["data"]["items"] if item["queue_name"] == "track:ingest"), None)
    if not track_after or track_after["last_consumed_at"] is None:
        raise RuntimeError(f"expected last_consumed_at after consume, got: {queue_after_body}")
    with SessionLocal() as db:
        if db.get(AdsbTrack, "trk_admin_publish_1") is None:
            raise RuntimeError("expected track message to be persisted into adsb_tracks")

    print("smoke_test_queue_admin=ok")


if __name__ == "__main__":
    main()
