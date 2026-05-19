const express = require('express');
const { db } = require('../db');
const { upsertTrack, batchUpsertTracks } = require('../services/trackService');
const {
  startRealtimeTask,
  stopRealtimeTask,
  getRealtimeTaskStatus,
  listRealtimeTaskStatus,
} = require('../services/realtimeCollector');

const router = express.Router();

function parseLimit(value) {
  const parsed = Number(value || 100);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 100;
  }

  return Math.min(Math.trunc(parsed), 1000);
}

function parseOptionalNumber(value) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Invalid numeric query value: ${value}`);
  }

  return parsed;
}

router.post('/tracks', (req, res, next) => {
  try {
    const data = upsertTrack(req.body, 'api:track');
    res.status(201).json({ data });
  } catch (error) {
    next(error);
  }
});

router.post('/tracks/batch', (req, res, next) => {
  try {
    const body =
      req.body && typeof req.body === 'object' ? req.body : {};
    const items = Array.isArray(body) ? body : body.items;
    const data = batchUpsertTracks(items, 'api:batch');
    res.status(201).json({ data, count: data.length });
  } catch (error) {
    next(error);
  }
});

router.post('/ingest', (req, res, next) => {
  try {
    const body =
      req.body && typeof req.body === 'object' ? req.body : {};
    const items = Array.isArray(body)
      ? body
      : Array.isArray(body.items)
        ? body.items
        : [body];

    const data = batchUpsertTracks(items, 'api:ingest');
    res.status(201).json({ data, count: data.length });
  } catch (error) {
    next(error);
  }
});

router.get('/tracks', (req, res, next) => {
  try {
    const params = {};
    const clauses = ['1 = 1'];

    if (req.query.track_id) {
      clauses.push('track_id = @track_id');
      params.track_id = req.query.track_id;
    }

    if (req.query.callsign) {
      clauses.push('callsign = @callsign');
      params.callsign = req.query.callsign;
    }

    if (req.query.start_time) {
      clauses.push('timestamp >= @start_time');
      params.start_time = req.query.start_time;
    }

    if (req.query.end_time) {
      clauses.push('timestamp <= @end_time');
      params.end_time = req.query.end_time;
    }

    const minLatitude = parseOptionalNumber(req.query.min_latitude);
    const maxLatitude = parseOptionalNumber(req.query.max_latitude);
    const minLongitude = parseOptionalNumber(req.query.min_longitude);
    const maxLongitude = parseOptionalNumber(req.query.max_longitude);
    const minAltitude = parseOptionalNumber(req.query.min_altitude);
    const maxAltitude = parseOptionalNumber(req.query.max_altitude);

    if (minLatitude !== undefined) {
      clauses.push('latitude >= @min_latitude');
      params.min_latitude = minLatitude;
    }

    if (maxLatitude !== undefined) {
      clauses.push('latitude <= @max_latitude');
      params.max_latitude = maxLatitude;
    }

    if (minLongitude !== undefined) {
      clauses.push('longitude >= @min_longitude');
      params.min_longitude = minLongitude;
    }

    if (maxLongitude !== undefined) {
      clauses.push('longitude <= @max_longitude');
      params.max_longitude = maxLongitude;
    }

    if (minAltitude !== undefined) {
      clauses.push('altitude >= @min_altitude');
      params.min_altitude = minAltitude;
    }

    if (maxAltitude !== undefined) {
      clauses.push('altitude <= @max_altitude');
      params.max_altitude = maxAltitude;
    }

    const limit = parseLimit(req.query.limit);
    const sql = `
      SELECT *
      FROM adsb_tracks
      WHERE ${clauses.join(' AND ')}
      ORDER BY timestamp DESC
      LIMIT ${limit}
    `;

    const data = db.prepare(sql).all(params);
    res.json({ data, count: data.length });
  } catch (error) {
    next(error);
  }
});

router.get('/tracks/:trackId', (req, res, next) => {
  try {
    const data = db
      .prepare('SELECT * FROM adsb_tracks WHERE track_id = ?')
      .get(req.params.trackId);

    if (!data) {
      return res.status(404).json({ error: 'Track not found.' });
    }

    return res.json({ data });
  } catch (error) {
    return next(error);
  }
});

router.get('/fusion/voice-track', (req, res, next) => {
  try {
    const params = {};
    const clauses = ['1 = 1'];

    if (req.query.unique_id) {
      clauses.push('v.unique_id = @unique_id');
      params.unique_id = req.query.unique_id;
    }

    if (req.query.track_id) {
      clauses.push('t.track_id = @track_id');
      params.track_id = req.query.track_id;
    }

    if (req.query.callsign) {
      clauses.push('t.callsign = @callsign');
      params.callsign = req.query.callsign;
    }

    const limit = parseLimit(req.query.limit);
    const sql = `
      SELECT
        rel.rel_id,
        rel.create_time,
        v.unique_id,
        v.icao_code,
        v.band,
        v.original_time,
        v.file_path,
        v.file_name,
        t.track_id,
        t.callsign,
        t.latitude,
        t.longitude,
        t.altitude,
        t.ground_speed,
        t.heading,
        t.timestamp AS track_timestamp,
        a.result_id,
        a.transcript,
        a.confidence
      FROM a2_voice_track_rel rel
      JOIN a2_voice_info v ON v.unique_id = rel.unique_id
      JOIN adsb_tracks t ON t.track_id = rel.track_id
      LEFT JOIN asr_results a ON a.unique_id = v.unique_id
      WHERE ${clauses.join(' AND ')}
      ORDER BY rel.create_time DESC
      LIMIT ${limit}
    `;

    const data = db.prepare(sql).all(params);
    res.json({ data, count: data.length });
  } catch (error) {
    next(error);
  }
});

router.post('/realtime-tasks/:taskId/start', (req, res, next) => {
  try {
    const data = startRealtimeTask(req.params.taskId);
    res.json({
      data,
      message: '已启动实时采集任务，当前按 TCP + JSON Lines 格式接收 ADS-B 数据。',
    });
  } catch (error) {
    next(error);
  }
});

router.post('/realtime-tasks/:taskId/stop', (req, res, next) => {
  try {
    const data = stopRealtimeTask(req.params.taskId);

    if (!data) {
      return res.status(404).json({ error: 'Realtime task is not running.' });
    }

    return res.json({ data });
  } catch (error) {
    return next(error);
  }
});

router.get('/realtime-tasks/status', (req, res) => {
  const data = listRealtimeTaskStatus();
  res.json({ data, count: data.length });
});

router.get('/realtime-tasks/:taskId/status', (req, res) => {
  const data = getRealtimeTaskStatus(req.params.taskId);

  if (!data) {
    return res.status(404).json({ error: 'Realtime task is not running.' });
  }

  return res.json({ data });
});

module.exports = router;
