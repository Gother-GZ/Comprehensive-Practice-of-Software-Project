from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.db.init_db import initialize_database
from app.main import app


def main() -> None:
    initialize_database()
    client = TestClient(app)

    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    consumers_response = client.get("/api/v1/system/consumers", headers=headers)
    consumers_body = consumers_response.json()
    if consumers_response.status_code != 200 or consumers_body.get("code") != 0:
        raise RuntimeError(f"consumers list failed: {consumers_response.status_code} {consumers_body}")

    log_export = client.get("/api/v1/system/logs/export", params={"format": "csv"}, headers=headers)
    if log_export.status_code != 200 or "text/csv" not in log_export.headers.get("content-type", ""):
        raise RuntimeError(f"log export failed: {log_export.status_code} {log_export.text}")

    failures_export = client.get("/api/v1/system/events/failures/export", params={"format": "jsonl"}, headers=headers)
    if failures_export.status_code != 200 or "application/x-ndjson" not in failures_export.headers.get("content-type", ""):
        raise RuntimeError(f"failures export failed: {failures_export.status_code} {failures_export.text}")

    dead_export = client.get("/api/v1/system/events/dead-letters/export", params={"format": "csv"}, headers=headers)
    if dead_export.status_code != 200 or "text/csv" not in dead_export.headers.get("content-type", ""):
        raise RuntimeError(f"dead export failed: {dead_export.status_code} {dead_export.text}")

    print("smoke_test_system_exports=ok")


if __name__ == "__main__":
    main()
