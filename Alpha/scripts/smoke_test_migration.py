from pathlib import Path
import os
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "tmp" / "legacy_migration_test.db"
os.environ["SQLITE_PATH"] = str(DB_PATH)

from fastapi.testclient import TestClient

from app.db.init_db import initialize_database
from app.db.migrations import run_migrations
from app.db.session import engine
from app.main import app


def build_legacy_db(path: Path) -> None:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE adsb_tracks (
            track_id TEXT PRIMARY KEY,
            callsign TEXT,
            timestamp TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            altitude_ft INTEGER,
            ground_speed_kt REAL,
            heading_deg REAL,
            source TEXT,
            raw_payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE a2_voice_info (
            voice_id TEXT PRIMARY KEY,
            icao_code TEXT NOT NULL,
            band TEXT,
            recorded_at TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            duration_ms INTEGER,
            file_size_bytes INTEGER,
            source TEXT,
            raw_payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE asr_results (
            result_id TEXT PRIMARY KEY,
            voice_id TEXT NOT NULL,
            engine TEXT NOT NULL,
            engine_version TEXT,
            transcript TEXT NOT NULL,
            vad_segments_json TEXT,
            confidence REAL,
            raw_payload TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE annotation_tasks (
            task_id TEXT PRIMARY KEY,
            voice_id TEXT NOT NULL,
            result_id TEXT,
            assignee_user_id TEXT,
            status TEXT NOT NULL,
            priority INTEGER,
            extra_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE annotation_results (
            annotation_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            annotator_user_id TEXT NOT NULL,
            corrected_text TEXT NOT NULL,
            timestamp_corrections_json TEXT,
            annotations_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        INSERT INTO adsb_tracks VALUES
        ('trk_legacy_1', 'CPA100', '2026-04-15T00:00:00.000Z', 22.308, 113.9185, 15000, 340, 251, 'legacy', '{}', '2026-04-15T00:00:00.000Z')
        """
    )
    cur.execute(
        """
        INSERT INTO a2_voice_info VALUES
        ('voice_legacy_1', 'VHHH', '118.2MHz', '2026-04-15T00:00:00.000Z', '/tmp/legacy.wav', 'legacy.wav', 30000, 2048, 'legacy', '{}', '2026-04-15T00:00:00.000Z')
        """
    )
    cur.execute(
        """
        INSERT INTO asr_results VALUES
        ('res_legacy_1', 'voice_legacy_1', 'legacy-engine', '1.0', 'legacy text', '[{\"start\":0,\"end\":3}]', 0.9, '{}', '2026-04-15T00:00:00.000Z')
        """
    )
    cur.execute(
        """
        INSERT INTO annotation_tasks VALUES
        ('task_legacy_1', 'voice_legacy_1', 'res_legacy_1', 'bootstrap-admin', 'pending', 3, '{}', '2026-04-15T00:00:00.000Z', '2026-04-15T00:00:00.000Z')
        """
    )
    cur.execute(
        """
        INSERT INTO annotation_results VALUES
        ('ann_legacy_1', 'task_legacy_1', 'bootstrap-admin', 'legacy corrected', '[{\"start\":0,\"end\":3}]', '{\"label\":\"legacy\"}', '2026-04-15T00:00:00.000Z', '2026-04-15T00:00:00.000Z')
        """
    )
    conn.commit()
    conn.close()


def main() -> None:
    build_legacy_db(DB_PATH)
    initialize_database()
    summary = run_migrations(engine)
    if "adsb_tracks" not in summary.validations or "ok" not in summary.validations["adsb_tracks"]:
        raise RuntimeError(f"migration validation missing for adsb_tracks: {summary.to_dict()}")
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456"})
    login.raise_for_status()
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    checks = [
        client.get("/api/v1/integration/audio", params={"unique_id": "voice_legacy_1"}, headers=headers),
        client.get("/api/v1/integration/asr", params={"result_id": "res_legacy_1"}, headers=headers),
        client.get("/api/v1/integration/annotation-tasks", params={"task_id": "task_legacy_1"}, headers=headers),
        client.get("/api/v1/integration/annotation-results", params={"annotation_id": "ann_legacy_1"}, headers=headers),
    ]
    for response in checks:
        body = response.json()
        if response.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(f"migration smoke failed: {response.status_code} {body}")
    print("smoke_test_migration=ok")
    print(summary.to_dict())


if __name__ == "__main__":
    main()
