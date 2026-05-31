const express = require('express');
const { dbFile, db, getRecord, updateRecord } = require('./db');
const { buildCrudRouter } = require('./routes/crud');
const adsbRouter = require('./routes/adsb');

const app = express();

app.use(express.json({ limit: '5mb' }));

app.get('/', (req, res) => {
  res.json({
    service: 'ADS-B Interface Prototype',
    version: '1.0.0',
    database: dbFile,
    endpoints: [
      '/api/adsb/tracks',
      '/api/adsb/tracks/batch',
      '/api/adsb/ingest',
      '/api/adsb/sources/opensky/fetch',
      '/api/adsb/sources/opensky/presets',
      '/api/adsb/sources/airplanes-live/fetch',
      '/api/adsb/sources/airplanes-live/presets',
      '/api/adsb/routes',
      '/api/adsb/routes/crawl',
      '/api/adsb/routes/rebuild',
      '/api/adsb/routes/crawl-tasks/start',
      '/api/adsb/fusion/voice-track',
      '/api/voice-info',
      '/api/voice-track-rel',
      '/api/tasks/realtime',
      '/api/tasks/download',
      '/api/system/base-config',
      '/api/asr-results',
      '/api/users',
      '/api/annotation/tasks',
      '/api/annotation/results',
      '/api/vsp/airports',
      '/api/vsp/waypoints',
      '/api/vsp/procedures',
      '/api/vsp/airlines',
      '/api/vsp/runways',
      '/api/vsp/frequencies',
      '/api/vsp/navaids',
    ],
  });
});

app.get('/health', (req, res) => {
  db.prepare('SELECT 1').get();
  res.json({
    status: 'ok',
    time: new Date().toISOString(),
    database: dbFile,
  });
});

app.use('/api/adsb', adsbRouter);

app.use(
  '/api/voice-info',
  buildCrudRouter({
    table: 'a2_voice_info',
    idField: 'unique_id',
    autoId: true,
    fields: [
      'unique_id',
      'icao_code',
      'band',
      'original_time',
      'process_time',
      'file_path',
      'file_name',
      'file_size',
      'data_type',
      'created_at',
      'start_at',
      'end_at',
    ],
    integerFields: ['file_size'],
    filterableFields: ['unique_id', 'icao_code', 'band', 'data_type'],
    defaultOrderBy: 'original_time DESC',
  }),
);

app.use(
  '/api/voice-track-rel',
  buildCrudRouter({
    table: 'a2_voice_track_rel',
    idField: 'rel_id',
    fields: ['unique_id', 'track_id', 'create_time'],
    requiredOnCreate: ['unique_id', 'track_id'],
    filterableFields: ['unique_id', 'track_id'],
    defaultOrderBy: 'create_time DESC',
  }),
);

app.use(
  '/api/tasks/realtime',
  buildCrudRouter({
    table: 'a2_task_realtime_cfg',
    idField: 'task_id',
    fields: [
      'task_name',
      'server_addr',
      'server_port',
      'protocol',
      'timeout',
      'heart_beat',
      'icao_code',
      'band',
      'status',
      'create_time',
    ],
    requiredOnCreate: ['task_name', 'server_addr', 'server_port'],
    integerFields: ['server_port', 'timeout', 'heart_beat', 'status'],
    filterableFields: ['status', 'protocol', 'icao_code', 'band'],
    defaultOrderBy: 'task_id DESC',
  }),
);

app.use(
  '/api/tasks/download',
  buildCrudRouter({
    table: 'a2_task_download_cfg',
    idField: 'task_id',
    fields: [
      'task_name',
      'icao_code',
      'band',
      'start_time',
      'end_time',
      'speed_limit',
      'exec_type',
      'exec_time',
      'status',
      'create_time',
    ],
    integerFields: ['speed_limit', 'exec_type', 'status'],
    filterableFields: ['status', 'icao_code', 'band', 'exec_type'],
    defaultOrderBy: 'task_id DESC',
  }),
);

app.get('/api/system/base-config', (req, res) => {
  const data = getRecord('a2_sys_base_cfg', 'id', 1);
  res.json({ data });
});

app.put('/api/system/base-config', (req, res, next) => {
  try {
    const body =
      req.body && typeof req.body === 'object' ? req.body : {};
    const payload = {};

    for (const field of [
      'storage_root',
      'slice_rule',
      'max_download_task',
      'max_realtime_conn',
      'api_timeout',
      'sync_interval',
    ]) {
      if (body[field] !== undefined) {
        payload[field] = body[field];
      }
    }

    for (const numberField of [
      'max_download_task',
      'max_realtime_conn',
      'api_timeout',
      'sync_interval',
    ]) {
      if (payload[numberField] !== undefined) {
        const parsed = Number(payload[numberField]);
        if (!Number.isFinite(parsed)) {
          throw new Error(`${numberField} must be a valid number.`);
        }

        payload[numberField] = Math.trunc(parsed);
      }
    }

    payload.update_time = new Date().toISOString();
    updateRecord('a2_sys_base_cfg', 'id', 1, payload);

    res.json({ data: getRecord('a2_sys_base_cfg', 'id', 1) });
  } catch (error) {
    next(error);
  }
});

app.use(
  '/api/asr-results',
  buildCrudRouter({
    table: 'asr_results',
    idField: 'result_id',
    autoId: true,
    fields: [
      'result_id',
      'unique_id',
      'vad_segments',
      'transcript',
      'confidence',
      'engine',
      'start_time',
      'end_time',
      'created_at',
    ],
    floatFields: ['confidence'],
    jsonFields: ['vad_segments'],
    filterableFields: ['result_id', 'unique_id', 'engine'],
    defaultOrderBy: 'created_at DESC',
  }),
);

app.use(
  '/api/users',
  buildCrudRouter({
    table: 'users',
    idField: 'user_id',
    autoId: true,
    fields: [
      'user_id',
      'username',
      'password_hash',
      'display_name',
      'role',
      'status',
      'created_at',
      'updated_at',
      'last_login_at',
    ],
    requiredOnCreate: ['username', 'password_hash', 'display_name', 'role', 'status'],
    createDefaults: {
      display_name: (payload) => payload.username,
      role: 'annotator',
      status: 'active',
    },
    filterableFields: ['username', 'role', 'status'],
    defaultOrderBy: 'created_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/annotation/tasks',
  buildCrudRouter({
    table: 'annotation_tasks',
    idField: 'task_id',
    autoId: true,
    fields: [
      'task_id',
      'unique_id',
      'result_id',
      'assignee_id',
      'status',
      'priority',
      'created_at',
      'updated_at',
    ],
    integerFields: ['priority'],
    filterableFields: ['unique_id', 'result_id', 'assignee_id', 'status'],
    defaultOrderBy: 'created_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/annotation/results',
  buildCrudRouter({
    table: 'annotation_results',
    idField: 'annotation_id',
    autoId: true,
    fields: [
      'annotation_id',
      'task_id',
      'corrected_text',
      'timestamp_corrections',
      'annotations',
      'annotator_id',
      'created_at',
      'updated_at',
    ],
    jsonFields: ['timestamp_corrections', 'annotations'],
    filterableFields: ['task_id', 'annotator_id'],
    defaultOrderBy: 'created_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/airports',
  buildCrudRouter({
    table: 'vsp_airports',
    idField: 'airport_id',
    autoId: true,
    fields: [
      'airport_id',
      'icao_code',
      'iata_code',
      'airport_name',
      'city_name',
      'country_name',
      'lat',
      'lng',
      'elevation_ft',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    aliases: {
      lat: ['latitude'],
      lng: ['longitude'],
    },
    requiredOnCreate: ['icao_code', 'airport_name', 'lat', 'lng'],
    integerFields: ['elevation_ft'],
    floatFields: ['lat', 'lng'],
    jsonFields: ['extra_json'],
    filterableFields: ['airport_id', 'icao_code', 'iata_code', 'city_name', 'country_name'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/waypoints',
  buildCrudRouter({
    table: 'vsp_waypoints',
    idField: 'waypoint_id',
    autoId: true,
    fields: [
      'waypoint_id',
      'name',
      'type',
      'lat',
      'lng',
      'description',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    aliases: {
      lat: ['latitude'],
      lng: ['longitude'],
    },
    requiredOnCreate: ['name', 'lat', 'lng'],
    floatFields: ['lat', 'lng'],
    jsonFields: ['extra_json'],
    filterableFields: ['name', 'type'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/procedures',
  buildCrudRouter({
    table: 'vsp_procedures',
    idField: 'procedure_id',
    autoId: true,
    fields: [
      'procedure_id',
      'airport_id',
      'procedure_code',
      'procedure_name',
      'procedure_type',
      'runway',
      'waypoint_sequence_json',
      'path_geojson',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    aliases: {
      procedure_name: ['name'],
      procedure_type: ['type'],
      waypoint_sequence_json: ['waypoints'],
      path_geojson: ['route_geom'],
    },
    requiredOnCreate: [
      'airport_id',
      'procedure_code',
      'procedure_name',
      'procedure_type',
    ],
    jsonFields: ['waypoint_sequence_json', 'path_geojson', 'extra_json'],
    filterableFields: ['airport_id', 'procedure_code', 'procedure_type', 'runway'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/airlines',
  buildCrudRouter({
    table: 'vsp_airlines',
    idField: 'airline_id',
    autoId: true,
    fields: [
      'airline_id',
      'airline_code',
      'airline_name',
      'airline_short_name',
      'country_name',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    requiredOnCreate: ['airline_code', 'airline_name'],
    jsonFields: ['extra_json'],
    filterableFields: ['airline_id', 'airline_code', 'country_name'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/runways',
  buildCrudRouter({
    table: 'vsp_runways',
    idField: 'runway_id',
    autoId: true,
    fields: [
      'runway_id',
      'airport_id',
      'runway_designator',
      'surface_type',
      'runway_length_m',
      'runway_width_m',
      'bearing_deg',
      'threshold_lat',
      'threshold_lng',
      'elevation_ft',
      'remarks',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    requiredOnCreate: ['airport_id', 'runway_designator'],
    integerFields: ['runway_length_m', 'runway_width_m', 'elevation_ft'],
    floatFields: ['bearing_deg', 'threshold_lat', 'threshold_lng'],
    jsonFields: ['extra_json'],
    filterableFields: ['airport_id', 'runway_designator', 'surface_type'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/frequencies',
  buildCrudRouter({
    table: 'vsp_frequencies',
    idField: 'frequency_id',
    autoId: true,
    fields: [
      'frequency_id',
      'airport_id',
      'service_designator',
      'callsign',
      'frequency',
      'hours_of_operation',
      'remarks',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    requiredOnCreate: ['airport_id', 'frequency'],
    jsonFields: ['extra_json'],
    filterableFields: ['airport_id', 'service_designator', 'callsign', 'frequency'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use(
  '/api/vsp/navaids',
  buildCrudRouter({
    table: 'vsp_navaids',
    idField: 'navaid_id',
    autoId: true,
    fields: [
      'navaid_id',
      'airport_id',
      'ident',
      'name',
      'navaid_type',
      'frequency',
      'lat',
      'lng',
      'elevation_ft',
      'hours_of_operation',
      'remarks',
      'extra_json',
      'created_at',
      'updated_at',
    ],
    aliases: {
      lat: ['latitude'],
      lng: ['longitude'],
    },
    requiredOnCreate: ['airport_id', 'ident', 'lat', 'lng'],
    integerFields: ['elevation_ft'],
    floatFields: ['lat', 'lng'],
    jsonFields: ['extra_json'],
    filterableFields: ['airport_id', 'ident', 'navaid_type', 'frequency'],
    defaultOrderBy: 'updated_at DESC',
    touchUpdatedAt: 'updated_at',
  }),
);

app.use((req, res) => {
  res.status(404).json({ error: 'Route not found.' });
});

app.use((error, req, res, next) => {
  console.error(error);
  const statusCode = error.statusCode || 500;
  res.status(statusCode).json({
    error: error.message || 'Internal server error.',
  });
});

module.exports = app;
