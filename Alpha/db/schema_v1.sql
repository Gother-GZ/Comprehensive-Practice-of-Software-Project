PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'annotator')),
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'disabled')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS user_login_audit (
    audit_id TEXT PRIMARY KEY,
    user_id TEXT,
    username TEXT NOT NULL,
    login_result TEXT NOT NULL CHECK (login_result IN ('success', 'failure')),
    failure_reason TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS user_refresh_tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS vsp_airports (
    airport_id TEXT PRIMARY KEY,
    icao_code TEXT NOT NULL UNIQUE,
    iata_code TEXT,
    airport_name TEXT NOT NULL,
    city_name TEXT,
    country_name TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    elevation_ft INTEGER,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS vsp_waypoints (
    waypoint_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    description TEXT,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS vsp_procedures (
    procedure_id TEXT PRIMARY KEY,
    airport_id TEXT NOT NULL,
    procedure_code TEXT NOT NULL,
    procedure_name TEXT NOT NULL,
    procedure_type TEXT NOT NULL,
    runway TEXT,
    waypoint_sequence_json TEXT,
    path_geojson TEXT,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (airport_id) REFERENCES vsp_airports(airport_id)
);

CREATE TABLE IF NOT EXISTS vsp_airlines (
    airline_id TEXT PRIMARY KEY,
    airline_code TEXT NOT NULL UNIQUE,
    airline_name TEXT NOT NULL,
    airline_short_name TEXT,
    country_name TEXT,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS vsp_runways (
    runway_id TEXT PRIMARY KEY,
    airport_id TEXT NOT NULL,
    runway_designator TEXT NOT NULL,
    surface_type TEXT,
    runway_length_m INTEGER,
    runway_width_m INTEGER,
    bearing_deg REAL,
    threshold_lat REAL,
    threshold_lng REAL,
    elevation_ft INTEGER,
    remarks TEXT,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (airport_id) REFERENCES vsp_airports(airport_id)
);

CREATE TABLE IF NOT EXISTS vsp_frequencies (
    frequency_id TEXT PRIMARY KEY,
    airport_id TEXT NOT NULL,
    service_designator TEXT,
    callsign TEXT,
    frequency TEXT NOT NULL,
    hours_of_operation TEXT,
    remarks TEXT,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (airport_id) REFERENCES vsp_airports(airport_id)
);

CREATE TABLE IF NOT EXISTS vsp_navaids (
    navaid_id TEXT PRIMARY KEY,
    airport_id TEXT NOT NULL,
    ident TEXT NOT NULL,
    name TEXT,
    navaid_type TEXT,
    frequency TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    elevation_ft INTEGER,
    hours_of_operation TEXT,
    remarks TEXT,
    extra_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (airport_id) REFERENCES vsp_airports(airport_id)
);

CREATE TABLE IF NOT EXISTS event_consume_failures (
    failure_id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,
    message_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    consumer_name TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    failed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS event_dead_letters (
    dead_letter_id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,
    message_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    last_error_message TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS system_logs (
    log_id TEXT PRIMARY KEY,
    log_level TEXT NOT NULL CHECK (log_level IN ('info', 'warning', 'error')),
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    trace_id TEXT,
    context_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS system_configs (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS adsb_tracks (
    track_id TEXT PRIMARY KEY,
    callsign TEXT,
    location POINT,
    altitude INTEGER,
    ground_speed INTEGER,
    heading INTEGER,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_at TEXT,
    start_at TEXT
);

CREATE TABLE IF NOT EXISTS a2_voice_track_rel (
    rel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_id TEXT,
    track_id TEXT,
    create_time TEXT DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS asr_results (
    result_id TEXT PRIMARY KEY,
    unique_id TEXT,
    vad_segments TEXT,
    transcript TEXT NOT NULL,
    confidence REAL,
    engine TEXT,
    start_time TEXT,
    end_time TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS annotation_tasks (
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
);

CREATE TABLE IF NOT EXISTS annotation_results (
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
);

CREATE INDEX IF NOT EXISTS idx_voice_info_icao ON a2_voice_info(icao_code);
CREATE INDEX IF NOT EXISTS idx_voice_info_band ON a2_voice_info(band);
CREATE INDEX IF NOT EXISTS idx_voice_info_time ON a2_voice_info(original_time);
CREATE INDEX IF NOT EXISTS idx_adsb_callsign ON adsb_tracks(callsign);
CREATE INDEX IF NOT EXISTS idx_adsb_location ON adsb_tracks(location);
CREATE INDEX IF NOT EXISTS idx_adsb_timestamp ON adsb_tracks(timestamp);
CREATE INDEX IF NOT EXISTS idx_rel_unique_id ON a2_voice_track_rel(unique_id);
CREATE INDEX IF NOT EXISTS idx_rel_track_id ON a2_voice_track_rel(track_id);
CREATE INDEX IF NOT EXISTS idx_asr_unique_id ON asr_results(unique_id);
CREATE INDEX IF NOT EXISTS idx_task_unique_id ON annotation_tasks(unique_id);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_user_login_audit_user_id ON user_login_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_user_refresh_tokens_user_id ON user_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_vsp_airports_icao_code ON vsp_airports(icao_code);
CREATE INDEX IF NOT EXISTS idx_vsp_waypoints_name ON vsp_waypoints(name);
CREATE INDEX IF NOT EXISTS idx_vsp_procedures_airport_id ON vsp_procedures(airport_id);
CREATE INDEX IF NOT EXISTS idx_vsp_procedures_type ON vsp_procedures(procedure_type);
CREATE INDEX IF NOT EXISTS idx_vsp_airlines_code ON vsp_airlines(airline_code);
CREATE INDEX IF NOT EXISTS idx_vsp_runways_airport_id ON vsp_runways(airport_id);
CREATE INDEX IF NOT EXISTS idx_vsp_runways_designator ON vsp_runways(runway_designator);
CREATE INDEX IF NOT EXISTS idx_vsp_frequencies_airport_id ON vsp_frequencies(airport_id);
CREATE INDEX IF NOT EXISTS idx_vsp_frequencies_service_designator ON vsp_frequencies(service_designator);
CREATE INDEX IF NOT EXISTS idx_vsp_navaids_airport_id ON vsp_navaids(airport_id);
CREATE INDEX IF NOT EXISTS idx_vsp_navaids_ident ON vsp_navaids(ident);
CREATE INDEX IF NOT EXISTS idx_event_consume_failures_queue_name ON event_consume_failures(queue_name);
CREATE INDEX IF NOT EXISTS idx_event_dead_letters_queue_name ON event_dead_letters(queue_name);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_trace_id ON system_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_annotation_results_task_id ON annotation_results(task_id);
