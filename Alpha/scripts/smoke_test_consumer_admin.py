from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.db.init_db import initialize_database
from app.main import app
from app.mq.redis_client import get_redis_client


def main() -> None:
    initialize_database()
    client = TestClient(app)
    redis_client = get_redis_client()
    redis_client.delete("system:log")

    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    publish_response = client.post(
        "/api/v1/system/queues/publish",
        json={
            "queue_name": "system:log",
            "message": {
                "id": "evt_consumer_admin_1",
                "type": "system.log.created",
                "version": "v1",
                "producer": "admin-api",
                "timestamp": "2026-04-22T13:00:00.000Z",
                "trace_id": "trace-consumer-admin-1",
                "payload": {"message": "consumer admin smoke"},
            },
        },
        headers=headers,
    )
    if publish_response.status_code != 200 or publish_response.json().get("code") != 0:
        raise RuntimeError(f"publish failed: {publish_response.status_code} {publish_response.text}")

    consume_response = client.post(
        "/api/v1/system/consumers/run-once",
        json={"queue_name": "system:log"},
        headers=headers,
    )
    consume_body = consume_response.json()
    if consume_response.status_code != 200 or consume_body.get("code") != 0:
        raise RuntimeError(f"consume endpoint failed: {consume_response.status_code} {consume_body}")
    if not consume_body["data"]["consumed"]:
        raise RuntimeError(f"expected consumed=true, got: {consume_body}")
    logs_response = client.get(
        "/api/v1/system/logs",
        params={"trace_id": "trace-consumer-admin-1", "page": 1, "page_size": 20},
        headers=headers,
    )
    logs_body = logs_response.json()
    if logs_response.status_code != 200 or logs_body.get("code") != 0:
        raise RuntimeError(f"logs query failed: {logs_response.status_code} {logs_body}")
    if logs_body["data"]["total"] < 1:
        raise RuntimeError(f"expected persisted system log, got: {logs_body}")

    print("smoke_test_consumer_admin=ok")


if __name__ == "__main__":
    main()
