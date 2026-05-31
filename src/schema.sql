PRAGMA foreign_keys = ON;

-- 1. 语音信息表 (A-2)
CREATE TABLE IF NOT EXISTS a2_voice_info (
    unique_id TEXT PRIMARY KEY,
    icao_code TEXT,
    band TEXT,
    original_time TEXT,
    process_time TEXT,
    file_path TEXT,
    file_name TEXT,
    file_size BIGINT DEFAULT 0,
    data_type TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    end_at TEXT,
    start_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_voice_info_icao ON a2_voice_info(icao_code);
CREATE INDEX IF NOT EXISTS idx_voice_info_band ON a2_voice_info(band);
CREATE INDEX IF NOT EXISTS idx_voice_info_time ON a2_voice_info(original_time);

-- 2. 航迹数据表 (A-1)
-- SQLite 原型中用 latitude / longitude 代替 POINT，便于直接运行。
CREATE TABLE IF NOT EXISTS adsb_tracks (
    track_id TEXT PRIMARY KEY,
    callsign TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    altitude INTEGER,
    ground_speed INTEGER,
    heading INTEGER,
    timestamp TEXT NOT NULL,
    source TEXT,
    raw_payload TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_adsb_callsign ON adsb_tracks(callsign);
CREATE INDEX IF NOT EXISTS idx_adsb_lat_lon ON adsb_tracks(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_adsb_timestamp ON adsb_tracks(timestamp);

CREATE TABLE IF NOT EXISTS adsb_routes (
    route_id TEXT PRIMARY KEY,
    route_key TEXT NOT NULL,
    callsign TEXT,
    aircraft_hex TEXT,
    provider TEXT,
    source TEXT,
    start_time TEXT,
    end_time TEXT,
    point_count INTEGER DEFAULT 0,
    min_latitude REAL,
    min_longitude REAL,
    max_latitude REAL,
    max_longitude REAL,
    path_geojson TEXT,
    sample_track_ids TEXT,
    raw_summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_adsb_routes_key ON adsb_routes(route_key);
CREATE INDEX IF NOT EXISTS idx_adsb_routes_callsign ON adsb_routes(callsign);
CREATE INDEX IF NOT EXISTS idx_adsb_routes_aircraft_hex ON adsb_routes(aircraft_hex);
CREATE INDEX IF NOT EXISTS idx_adsb_routes_time ON adsb_routes(start_time, end_time);

-- 3. 语音与航迹关联表 (A-2 & A-1)
CREATE TABLE IF NOT EXISTS a2_voice_track_rel (
    rel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_id TEXT,
    track_id TEXT,
    create_time TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(unique_id) REFERENCES a2_voice_info(unique_id),
    FOREIGN KEY(track_id) REFERENCES adsb_tracks(track_id)
);
CREATE INDEX IF NOT EXISTS idx_rel_unique_id ON a2_voice_track_rel(unique_id);
CREATE INDEX IF NOT EXISTS idx_rel_track_id ON a2_voice_track_rel(track_id);

-- 4. 实时采集任务配置表 (A-2)
CREATE TABLE IF NOT EXISTS a2_task_realtime_cfg (
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
);

-- 5. 历史下载任务配置表 (A-2)
CREATE TABLE IF NOT EXISTS a2_task_download_cfg (
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
);

-- 6. 系统基础配置表 (A-2)
CREATE TABLE IF NOT EXISTS a2_sys_base_cfg (
    id INTEGER PRIMARY KEY,
    storage_root TEXT DEFAULT '/atc/a2/data/',
    slice_rule TEXT DEFAULT '5min/100MB',
    max_download_task INTEGER DEFAULT 3,
    max_realtime_conn INTEGER DEFAULT 5,
    api_timeout INTEGER DEFAULT 5,
    sync_interval INTEGER DEFAULT 5,
    update_time TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO a2_sys_base_cfg (id)
SELECT 1
WHERE NOT EXISTS (SELECT 1 FROM a2_sys_base_cfg WHERE id = 1);

-- 7. ASR 识别结果表 (A-5)
CREATE TABLE IF NOT EXISTS asr_results (
    result_id TEXT PRIMARY KEY,
    unique_id TEXT,
    vad_segments TEXT,
    transcript TEXT,
    confidence REAL,
    engine TEXT,
    start_time TEXT,
    end_time TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(unique_id) REFERENCES a2_voice_info(unique_id)
);
CREATE INDEX IF NOT EXISTS idx_asr_unique_id ON asr_results(unique_id);

-- 8. 系统用户表 (A-5)
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT DEFAULT NULL
);

-- 9. 标注任务表 (A-5)
CREATE TABLE IF NOT EXISTS annotation_tasks (
    task_id TEXT PRIMARY KEY,
    unique_id TEXT,
    result_id TEXT,
    assignee_id TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 3,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(unique_id) REFERENCES a2_voice_info(unique_id),
    FOREIGN KEY(result_id) REFERENCES asr_results(result_id),
    FOREIGN KEY(assignee_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_task_unique_id ON annotation_tasks(unique_id);

-- 10. 标注结果表 (A-5)
CREATE TABLE IF NOT EXISTS annotation_results (
    annotation_id TEXT PRIMARY KEY,
    task_id TEXT,
    corrected_text TEXT,
    timestamp_corrections TEXT,
    annotations TEXT,
    annotator_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES annotation_tasks(task_id),
    FOREIGN KEY(annotator_id) REFERENCES users(user_id)
);

-- 11. 航路点表 (VSP)
CREATE TABLE IF NOT EXISTS vsp_waypoints (
    waypoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    type TEXT,
    description TEXT
);
CREATE INDEX IF NOT EXISTS idx_waypoint_name ON vsp_waypoints(name);

-- 12. 进离场程序表 (VSP)
CREATE TABLE IF NOT EXISTS vsp_procedures (
    procedure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT,
    runway TEXT,
    waypoints TEXT,
    route_geom TEXT
);
