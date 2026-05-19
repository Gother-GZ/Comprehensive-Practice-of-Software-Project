import json
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import Engine, inspect, text


MIGRATION_ID = "20260415_integration_schema_v2"
TRACKED_TABLES = [
    "adsb_tracks",
    "a2_voice_info",
    "a2_voice_track_rel",
    "a2_task_realtime_cfg",
    "a2_task_download_cfg",
    "a2_sys_base_cfg",
    "asr_results",
    "annotation_tasks",
    "annotation_results",
]


@dataclass
class MigrationSummary:
    migration_id: str
    applied: bool = False
    created_tables: list[str] = field(default_factory=list)
    rebuilt_tables: list[str] = field(default_factory=list)
    unchanged_tables: list[str] = field(default_factory=list)
    mapped_fields: dict[str, list[str]] = field(default_factory=dict)
    validations: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "migration_id": self.migration_id,
            "applied": self.applied,
            "created_tables": self.created_tables,
            "rebuilt_tables": self.rebuilt_tables,
            "unchanged_tables": self.unchanged_tables,
            "mapped_fields": self.mapped_fields,
            "validations": self.validations,
        }


def run_migrations(engine: Engine) -> MigrationSummary:
    summary = MigrationSummary(migration_id=MIGRATION_ID)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        exists = conn.execute(
            text("SELECT 1 FROM schema_migrations WHERE migration_id = :migration_id"),
            {"migration_id": MIGRATION_ID},
        ).scalar()
        if exists:
            summary.unchanged_tables.extend(TRACKED_TABLES)
            summary.validations = _validate_tables(conn)
            conn.execute(text("PRAGMA foreign_keys=ON"))
            return summary

        _migrate_integration_tables(conn, summary)
        conn.execute(
            text("INSERT INTO schema_migrations (migration_id) VALUES (:migration_id)"),
            {"migration_id": MIGRATION_ID},
        )
        summary.applied = True
        summary.validations = _validate_tables(conn)
        conn.execute(text("PRAGMA foreign_keys=ON"))
    return summary


def _migrate_integration_tables(conn, summary: MigrationSummary) -> None:  # type: ignore[no-untyped-def]
    inspector = inspect(conn)

    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="adsb_tracks",
        create_sql="""
            CREATE TABLE adsb_tracks (
                track_id TEXT PRIMARY KEY,
                callsign TEXT,
                location POINT,
                altitude INTEGER,
                ground_speed INTEGER,
                heading INTEGER,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=[
            "CREATE INDEX IF NOT EXISTS idx_adsb_callsign ON adsb_tracks(callsign)",
            "CREATE INDEX IF NOT EXISTS idx_adsb_location ON adsb_tracks(location)",
            "CREATE INDEX IF NOT EXISTS idx_adsb_timestamp ON adsb_tracks(timestamp)",
        ],
        row_mapper=_map_adsb_track,
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="a2_voice_info",
        create_sql="""
            CREATE TABLE a2_voice_info (
                unique_id TEXT PRIMARY KEY,
                icao_code TEXT,
                band TEXT,
                original_time TEXT,
                process_time TEXT,
                file_path TEXT,
                file_name TEXT,
                file_size BIGINT DEFAULT 0,
                data_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                end_at TEXT,
                start_at TEXT
            )
        """,
        indexes=[
            "CREATE INDEX IF NOT EXISTS idx_voice_info_icao ON a2_voice_info(icao_code)",
            "CREATE INDEX IF NOT EXISTS idx_voice_info_band ON a2_voice_info(band)",
            "CREATE INDEX IF NOT EXISTS idx_voice_info_time ON a2_voice_info(original_time)",
        ],
        row_mapper=_map_voice_info,
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="a2_voice_track_rel",
        create_sql="""
            CREATE TABLE a2_voice_track_rel (
                rel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_id TEXT,
                track_id TEXT,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=[
            "CREATE INDEX IF NOT EXISTS idx_rel_unique_id ON a2_voice_track_rel(unique_id)",
            "CREATE INDEX IF NOT EXISTS idx_rel_track_id ON a2_voice_track_rel(track_id)",
        ],
        row_mapper=lambda row: {
            "rel_id": row.get("rel_id"),
            "unique_id": row.get("unique_id"),
            "track_id": row.get("track_id"),
            "create_time": row.get("create_time"),
        },
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="a2_task_realtime_cfg",
        create_sql="""
            CREATE TABLE a2_task_realtime_cfg (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                server_addr TEXT,
                server_port INTEGER,
                protocol TEXT DEFAULT 'TCP',
                timeout INTEGER DEFAULT 30,
                heart_beat INTEGER DEFAULT 10,
                icao_code TEXT,
                band TEXT,
                status INTEGER DEFAULT 0,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=[],
        row_mapper=lambda row: {
            "task_id": row.get("task_id"),
            "task_name": row.get("task_name"),
            "server_addr": row.get("server_addr"),
            "server_port": row.get("server_port"),
            "protocol": row.get("protocol"),
            "timeout": row.get("timeout"),
            "heart_beat": row.get("heart_beat"),
            "icao_code": row.get("icao_code"),
            "band": row.get("band"),
            "status": row.get("status"),
            "create_time": row.get("create_time"),
        },
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="a2_task_download_cfg",
        create_sql="""
            CREATE TABLE a2_task_download_cfg (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                icao_code TEXT,
                band TEXT,
                start_time TEXT,
                end_time TEXT,
                speed_limit INTEGER DEFAULT 0,
                exec_type INTEGER DEFAULT 1,
                exec_time TEXT DEFAULT NULL,
                status INTEGER DEFAULT 0,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=[],
        row_mapper=lambda row: {
            "task_id": row.get("task_id"),
            "task_name": row.get("task_name"),
            "icao_code": row.get("icao_code"),
            "band": row.get("band"),
            "start_time": row.get("start_time"),
            "end_time": row.get("end_time"),
            "speed_limit": row.get("speed_limit"),
            "exec_type": row.get("exec_type"),
            "exec_time": row.get("exec_time"),
            "status": row.get("status"),
            "create_time": row.get("create_time"),
        },
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="a2_sys_base_cfg",
        create_sql="""
            CREATE TABLE a2_sys_base_cfg (
                id INTEGER PRIMARY KEY,
                storage_root TEXT DEFAULT '/atc/a2/data/',
                slice_rule TEXT DEFAULT '5min/100MB',
                max_download_task INTEGER DEFAULT 3,
                max_realtime_conn INTEGER DEFAULT 5,
                api_timeout INTEGER DEFAULT 5,
                sync_interval INTEGER DEFAULT 5,
                update_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=[],
        row_mapper=lambda row: {
            "id": row.get("id"),
            "storage_root": row.get("storage_root"),
            "slice_rule": row.get("slice_rule"),
            "max_download_task": row.get("max_download_task"),
            "max_realtime_conn": row.get("max_realtime_conn"),
            "api_timeout": row.get("api_timeout"),
            "sync_interval": row.get("sync_interval"),
            "update_time": row.get("update_time"),
        },
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="asr_results",
        create_sql="""
            CREATE TABLE asr_results (
                result_id TEXT PRIMARY KEY,
                unique_id TEXT,
                vad_segments TEXT,
                transcript TEXT NOT NULL,
                confidence REAL,
                engine TEXT,
                start_time TEXT,
                end_time TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=["CREATE INDEX IF NOT EXISTS idx_asr_unique_id ON asr_results(unique_id)"],
        row_mapper=_map_asr_result,
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="annotation_tasks",
        create_sql="""
            CREATE TABLE annotation_tasks (
                task_id TEXT PRIMARY KEY,
                unique_id TEXT,
                result_id TEXT,
                assignee_id TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 3,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (result_id) REFERENCES asr_results(result_id),
                FOREIGN KEY (assignee_id) REFERENCES users(user_id)
            )
        """,
        indexes=["CREATE INDEX IF NOT EXISTS idx_task_unique_id ON annotation_tasks(unique_id)"],
        row_mapper=_map_annotation_task,
    )
    _rebuild_table(
        conn,
        inspector,
        summary,
        table_name="annotation_results",
        create_sql="""
            CREATE TABLE annotation_results (
                annotation_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                corrected_text TEXT,
                timestamp_corrections TEXT,
                annotations TEXT,
                annotator_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES annotation_tasks(task_id),
                FOREIGN KEY (annotator_id) REFERENCES users(user_id)
            )
        """,
        indexes=["CREATE INDEX IF NOT EXISTS idx_annotation_results_task_id ON annotation_results(task_id)"],
        row_mapper=_map_annotation_result,
    )


def _rebuild_table(conn, inspector, summary: MigrationSummary, table_name: str, create_sql: str, indexes: list[str], row_mapper: Callable[[dict], dict]) -> None:  # type: ignore[no-untyped-def]
    if not inspector.has_table(table_name):
        conn.execute(text(create_sql))
        for index_sql in indexes:
            conn.execute(text(index_sql))
        summary.created_tables.append(table_name)
        return

    rows = conn.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
    expected_columns = _extract_expected_columns(create_sql)
    current_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if current_columns == expected_columns:
        for index_sql in indexes:
            conn.execute(text(index_sql))
        summary.unchanged_tables.append(table_name)
        return

    conn.execute(text(f"ALTER TABLE {table_name} RENAME TO {table_name}__legacy"))
    conn.execute(text(create_sql))

    if rows:
        transformed_rows = [row_mapper(dict(row)) for row in rows]
        valid_rows = [{k: v for k, v in item.items() if v is not None} for item in transformed_rows]
        valid_rows = [item for item in valid_rows if item]
        if valid_rows:
            columns = sorted({column for item in valid_rows for column in item.keys()})
            placeholders = ", ".join(f":{column}" for column in columns)
            conn.execute(
                text(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"),
                [{column: item.get(column) for column in columns} for item in valid_rows],
            )
        mapped_fields = sorted(
            {
                key
                for source_row, target_row in zip(rows, transformed_rows, strict=False)
                for key, value in target_row.items()
                if value is not None and (key not in source_row or source_row.get(key) != value)
            }
        )
        if mapped_fields:
            summary.mapped_fields[table_name] = mapped_fields

    conn.execute(text(f"DROP TABLE {table_name}__legacy"))
    for index_sql in indexes:
        conn.execute(text(index_sql))
    summary.rebuilt_tables.append(table_name)


def _extract_expected_columns(create_sql: str) -> set[str]:
    columns: set[str] = set()
    for raw_line in create_sql.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line or line.startswith("CREATE TABLE") or line == ")" or line.startswith("FOREIGN KEY"):
            continue
        column_name = line.split(" ", 1)[0]
        columns.add(column_name)
    return columns


def _validate_tables(conn) -> dict[str, list[str]]:  # type: ignore[no-untyped-def]
    inspector = inspect(conn)
    validations: dict[str, list[str]] = {}
    expected = {
        "adsb_tracks": {"columns": {"track_id", "location", "altitude", "ground_speed", "heading", "timestamp", "created_at"}},
        "a2_voice_info": {"columns": {"unique_id", "icao_code", "band", "original_time", "process_time", "file_path", "file_name", "file_size", "data_type", "created_at", "end_at", "start_at"}},
        "a2_voice_track_rel": {"columns": {"rel_id", "unique_id", "track_id", "create_time"}},
        "a2_task_realtime_cfg": {"columns": {"task_id", "task_name", "server_addr", "server_port", "protocol", "timeout", "heart_beat", "icao_code", "band", "status", "create_time"}},
        "a2_task_download_cfg": {"columns": {"task_id", "task_name", "icao_code", "band", "start_time", "end_time", "speed_limit", "exec_type", "exec_time", "status", "create_time"}},
        "a2_sys_base_cfg": {"columns": {"id", "storage_root", "slice_rule", "max_download_task", "max_realtime_conn", "api_timeout", "sync_interval", "update_time"}},
        "asr_results": {"columns": {"result_id", "unique_id", "vad_segments", "transcript", "confidence", "engine", "start_time", "end_time", "created_at"}},
        "annotation_tasks": {"columns": {"task_id", "unique_id", "result_id", "assignee_id", "status", "priority", "created_at", "updated_at"}},
        "annotation_results": {"columns": {"annotation_id", "task_id", "corrected_text", "timestamp_corrections", "annotations", "annotator_id", "created_at", "updated_at"}},
    }
    for table_name, config in expected.items():
        checks: list[str] = []
        if not inspector.has_table(table_name):
            validations[table_name] = ["missing_table"]
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = sorted(config["columns"] - columns)
        if missing_columns:
            checks.append(f"missing_columns:{','.join(missing_columns)}")
        pk = inspector.get_pk_constraint(table_name)
        pk_columns = pk.get("constrained_columns") or []
        if not pk_columns:
            checks.append("missing_primary_key")
        indexes = inspector.get_indexes(table_name)
        checks.append(f"index_count:{len(indexes)}")
        if not missing_columns and pk_columns:
            checks.append("ok")
        validations[table_name] = checks
    return validations


def _map_adsb_track(row: dict) -> dict:
    location = row.get("location")
    if not location:
        lat = row.get("lat")
        lng = row.get("lng")
        if lat is not None and lng is not None:
            location = json.dumps({"lat": lat, "lng": lng}, ensure_ascii=False)
    return {
        "track_id": row.get("track_id"),
        "callsign": row.get("callsign"),
        "location": location,
        "altitude": row.get("altitude", row.get("altitude_ft")),
        "ground_speed": _to_int(row.get("ground_speed", row.get("ground_speed_kt"))),
        "heading": _to_int(row.get("heading", row.get("heading_deg"))),
        "timestamp": row.get("timestamp"),
        "created_at": row.get("created_at"),
    }


def _map_voice_info(row: dict) -> dict:
    return {
        "unique_id": row.get("unique_id", row.get("voice_id")),
        "icao_code": row.get("icao_code"),
        "band": row.get("band"),
        "original_time": row.get("original_time", row.get("recorded_at")),
        "process_time": row.get("process_time"),
        "file_path": row.get("file_path"),
        "file_name": row.get("file_name"),
        "file_size": row.get("file_size", row.get("file_size_bytes")),
        "data_type": row.get("data_type"),
        "created_at": row.get("created_at"),
        "end_at": row.get("end_at"),
        "start_at": row.get("start_at"),
    }


def _map_asr_result(row: dict) -> dict:
    return {
        "result_id": row.get("result_id"),
        "unique_id": row.get("unique_id", row.get("voice_id")),
        "vad_segments": row.get("vad_segments", row.get("vad_segments_json")),
        "transcript": row.get("transcript"),
        "confidence": row.get("confidence"),
        "engine": row.get("engine"),
        "start_time": row.get("start_time"),
        "end_time": row.get("end_time"),
        "created_at": row.get("created_at"),
    }


def _map_annotation_task(row: dict) -> dict:
    return {
        "task_id": row.get("task_id"),
        "unique_id": row.get("unique_id", row.get("voice_id")),
        "result_id": row.get("result_id"),
        "assignee_id": row.get("assignee_id", row.get("assignee_user_id")),
        "status": row.get("status"),
        "priority": row.get("priority"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _map_annotation_result(row: dict) -> dict:
    return {
        "annotation_id": row.get("annotation_id"),
        "task_id": row.get("task_id"),
        "corrected_text": row.get("corrected_text"),
        "timestamp_corrections": row.get("timestamp_corrections", row.get("timestamp_corrections_json")),
        "annotations": row.get("annotations", row.get("annotations_json")),
        "annotator_id": row.get("annotator_id", row.get("annotator_user_id")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
