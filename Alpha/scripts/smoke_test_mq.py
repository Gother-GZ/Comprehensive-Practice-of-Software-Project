from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.init_db import initialize_database
from app.main import app
from app.mq.consumer_base import BaseListConsumer
from app.mq.redis_client import get_redis_client


class AlwaysFailTrackConsumer(BaseListConsumer):
    queue_name = "track:ingest"
    consumer_name = "always-fail-track-consumer"

    def handle_payload(self, payload: dict) -> None:
        raise ValueError("forced smoke failure")


def main() -> None:
    initialize_database()
    client = TestClient(app)
    redis_client = get_redis_client()
    redis_client.delete("track:ingest")

    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    message = {
        "id": "evt_smoke_dead_1",
        "type": "track.ingest",
        "version": "v1",
        "producer": "smoke-test",
        "timestamp": "2026-04-22T10:00:00.000Z",
        "trace_id": "trace-smoke-dead-1",
        "payload": {
            "track_id": "trk_smoke_dead_1",
            "timestamp": "2026-04-22T10:00:00.000Z",
            "callsign": "CPA404",
            "location": {"type": "Point", "coordinates": [113.92, 22.31]},
            "altitude": 12000,
            "ground_speed": 320,
            "heading": 250,
        },
    }
    redis_client.rpush("track:ingest", json.dumps(message, ensure_ascii=False))

    consumer = AlwaysFailTrackConsumer()
    for _ in range(get_settings().redis_max_retry_count):
        consumed = consumer.consume_once()
        if not consumed:
            raise RuntimeError("expected queued message to be consumed")

    queue_response = client.get("/api/v1/system/queues", headers=headers)
    queue_body = queue_response.json()
    if queue_response.status_code != 200 or queue_body.get("code") != 0:
        raise RuntimeError(f"queue stats failed: {queue_response.status_code} {queue_body}")

    failures_response = client.get(
        "/api/v1/system/events/failures",
        params={"message_id": "evt_smoke_dead_1", "page": 1, "page_size": 20},
        headers=headers,
    )
    failures_body = failures_response.json()
    if failures_response.status_code != 200 or failures_body.get("code") != 0:
        raise RuntimeError(f"failures endpoint failed: {failures_response.status_code} {failures_body}")
    if failures_body["data"]["total"] < get_settings().redis_max_retry_count:
        raise RuntimeError(f"expected retry failures, got: {failures_body}")

    dead_response = client.get(
        "/api/v1/system/events/dead-letters",
        params={"message_id": "evt_smoke_dead_1", "page": 1, "page_size": 20},
        headers=headers,
    )
    dead_body = dead_response.json()
    if dead_response.status_code != 200 or dead_body.get("code") != 0:
        raise RuntimeError(f"dead-letter endpoint failed: {dead_response.status_code} {dead_body}")
    if dead_body["data"]["total"] < 1:
        raise RuntimeError(f"expected dead letter record, got: {dead_body}")

    logs_response = client.get(
        "/api/v1/system/logs",
        params={"trace_id": "trace-smoke-dead-1", "page": 1, "page_size": 20},
        headers=headers,
    )
    logs_body = logs_response.json()
    if logs_response.status_code != 200 or logs_body.get("code") != 0:
        raise RuntimeError(f"logs endpoint failed: {logs_response.status_code} {logs_body}")
    if logs_body["data"]["total"] < 1:
        raise RuntimeError(f"expected consumer error log, got: {logs_body}")

    print("smoke_test_mq=ok")


if __name__ == "__main__":
    main()
