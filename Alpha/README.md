# Alpha A-5 Service

Alpha A-5 is the backend foundation for:

- user authentication and management
- VSP/AIP query services
- system logs and queue failure tracking
- Redis List based message publishing and consumer scaffolding
- minimal integration endpoints for A-1 / A-2 / A-3 / A-4

## Quick Start

1. Create and activate a Python environment.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

4. Start the service:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

If you need to run migrations explicitly:

```powershell
python scripts/run_migrations.py
```

5. Open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

The root path now redirects to `/docs`, and Swagger bearer authorization can be used directly for protected endpoints.

## Default Admin

If `.env` keeps the default values, startup initializes:

- username: `admin`
- password: `admin123456`

## Seed Demo VSP Data

```powershell
python scripts/seed_demo_data.py
```

This inserts demo records for:

- `VHHH`
- sample waypoints
- one demo procedure
- one sample airline

## Import Real VSP Data

To import your real VSP and airline Excel files:

```powershell
python scripts/import_vsp_excel.py "C:\Users\31438\Downloads\VSP数据.xlsx" "C:\Users\31438\Downloads\航司及其对应关系表格.xlsx"
```

To verify import counts in a temporary database:

```powershell
python scripts/verify_vsp_import.py "C:\Users\31438\Downloads\VSP数据.xlsx" "C:\Users\31438\Downloads\航司及其对应关系表格.xlsx"
```

## Run Example Consumer Once

Requires Redis to be running locally:

```powershell
python scripts/run_consumer_once.py track:ingest
python scripts/run_consumer_once.py system:log
python scripts/publish_queue_message.py track:ingest
```

## Current Implementation Notes

- SQLite is the runtime database.
- Redis is optional for startup. If Redis is unavailable, queue monitoring degrades gracefully and returns `redis_available=false`.
- Integration tables now follow the original external SQL field set for non-master tables, while `users`, `vsp_*`, and system governance tables keep the A-5 owned schema.
- Integration endpoints currently implement minimal DTO validation and storage only.
- Real VSP Excel import is supported for the current `VSP数据.xlsx` and airline mapping workbook format, including airports, runways, frequencies, navaids, compatible waypoints, and airlines.
- Migration output now includes a summary of created, rebuilt, unchanged, and validated non-master tables.
- A-2 governance APIs are intended for maintenance and integration testing, not for the full A-2 business workflow.

## Integration Field Notes

The current integration APIs keep the same paths but use the original external SQL naming for non-master tables:

- `POST /api/v1/tracks/ingest`: `track_id`, `timestamp`, `location`, `callsign`, `altitude`, `ground_speed`, `heading`, `version`
- `POST /api/v1/audio/metadata`: `unique_id`, `icao_code`, `band`, `original_time`, `process_time`, `file_path`, `file_name`, `file_size`, `data_type`, `start_at`, `end_at`, `version`
- `POST /api/v1/asr/results`: `result_id`, `unique_id`, `vad_segments`, `transcript`, `confidence`, `engine`, `start_time`, `end_time`, `version`
- `GET /api/v1/annotations/load`: `task_id` or `unique_id`
- `POST /api/v1/annotations/save`: `task_id`, `annotator_id`, `corrected_text`, `timestamp_corrections`, `annotations`, `version`

## Smoke Test

You can run a local end-to-end API smoke test with:

```powershell
python scripts/smoke_test_api.py
```

You can run a VSP import and query smoke test against your real Excel files with:

```powershell
python scripts/smoke_test_vsp.py "C:\Users\31438\Downloads\VSP数据.xlsx" "C:\Users\31438\Downloads\航司及其对应关系表格.xlsx"
```

You can validate migration from a legacy integration schema with:

```powershell
python scripts/smoke_test_migration.py
```

You can validate the admin-governed A-2 query and maintenance endpoints with:

```powershell
python scripts/smoke_test_a2_governance.py
```

You can validate message retry, failure logging, and dead-letter handling with:

```powershell
python scripts/smoke_test_mq.py
```

You can validate admin-side queue publishing and successful consumption with:

```powershell
python scripts/smoke_test_queue_admin.py
```

You can validate export endpoints and admin-side consumer control with:

```powershell
python scripts/smoke_test_system_exports.py
python scripts/smoke_test_consumer_admin.py
```

## Swagger Auth

1. Call `POST /api/v1/auth/login` with `admin / admin123456`
2. Copy `access_token`
3. In `/docs`, click `Authorize`
4. Paste `Bearer <access_token>`
5. Call protected endpoints such as `/api/v1/users/me`, `/api/v1/integration/audio`, `/api/v1/system/queues`

## System Observability APIs

- `GET /api/v1/system/queues`
- `POST /api/v1/system/queues/publish`
- `GET /api/v1/system/consumers`
- `POST /api/v1/system/consumers/run-once`
- `GET /api/v1/system/events/failures`
- `GET /api/v1/system/events/failures/export`
- `GET /api/v1/system/events/dead-letters`
- `GET /api/v1/system/events/dead-letters/export`
- `GET /api/v1/system/logs`
- `GET /api/v1/system/logs/export`
