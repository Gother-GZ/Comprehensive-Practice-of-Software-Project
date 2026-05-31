const express = require('express');
const { db } = require('../db');
const { upsertTrack, batchUpsertTracks } = require('../services/trackService');
const {
  BOUNDING_BOX_PRESETS,
  fetchAndStoreOpenSkyStates,
  normalizeBounds,
  normalizeLimit,
} = require('../services/openSkyCollector');
const {
  POINT_PRESETS,
  fetchAndStoreAirplanesLiveAircraft,
  normalizePoint,
  normalizeLimit: normalizeAirplanesLimit,
} = require('../services/airplanesLiveCollector');
const {
  startRealtimeTask,
  stopRealtimeTask,
  getRealtimeTaskStatus,
  listRealtimeTaskStatus,
} = require('../services/realtimeCollector');
const {
  crawlRoutesOnce,
  rebuildRoutesFromStoredTracks,
  listRoutes,
  getRoute,
  startRouteCrawlTask,
  stopRouteCrawlTask,
  getRouteCrawlTaskStatus,
  listRouteCrawlTaskStatus,
} = require('../services/routeCrawlerService');

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

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== '');
}

function parseBoolean(value) {
  if (value === undefined || value === null || value === '') {
    return false;
  }

  if (typeof value === 'boolean') {
    return value;
  }

  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function parseOpenSkyFetchOptions(req) {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  const query = req.query || {};
  const boundsSource = body.bounds || {
    lamin: firstDefined(body.lamin, body.min_latitude, body.minLatitude, query.lamin, query.min_latitude, query.minLatitude),
    lomin: firstDefined(body.lomin, body.min_longitude, body.minLongitude, query.lomin, query.min_longitude, query.minLongitude),
    lamax: firstDefined(body.lamax, body.max_latitude, body.maxLatitude, query.lamax, query.max_latitude, query.maxLatitude),
    lomax: firstDefined(body.lomax, body.max_longitude, body.maxLongitude, query.lomax, query.max_longitude, query.maxLongitude),
  };
  const hasBounds = Object.values(boundsSource).some(
    (value) => value !== undefined && value !== null && value !== '',
  );

  return {
    preset: firstDefined(body.preset, query.preset),
    bounds: hasBounds ? normalizeBounds(boundsSource) : undefined,
    limit: normalizeLimit(firstDefined(body.limit, query.limit), 100),
    icao24: firstDefined(body.icao24, query.icao24),
    time: firstDefined(body.time, query.time),
    extended: parseBoolean(firstDefined(body.extended, query.extended)),
  };
}

function parseAirplanesLiveFetchOptions(req) {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  const query = req.query || {};
  const pointSource = body.point || {
    lat: firstDefined(body.lat, body.latitude, query.lat, query.latitude),
    lon: firstDefined(body.lon, body.lng, body.longitude, query.lon, query.lng, query.longitude),
    radius: firstDefined(body.radius, body.radius_nm, query.radius, query.radius_nm),
  };
  const hasPoint = Object.values(pointSource).some(
    (value) => value !== undefined && value !== null && value !== '',
  );

  return {
    preset: firstDefined(body.preset, query.preset),
    point: hasPoint ? normalizePoint(pointSource) : undefined,
    limit: normalizeAirplanesLimit(firstDefined(body.limit, query.limit), 100),
  };
}

function parseRouteCrawlOptions(req) {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  const query = req.query || {};
  const boundsSource = body.bounds || {
    lamin: firstDefined(body.lamin, body.min_latitude, body.minLatitude, query.lamin, query.min_latitude, query.minLatitude),
    lomin: firstDefined(body.lomin, body.min_longitude, body.minLongitude, query.lomin, query.min_longitude, query.minLongitude),
    lamax: firstDefined(body.lamax, body.max_latitude, body.maxLatitude, query.lamax, query.max_latitude, query.maxLatitude),
    lomax: firstDefined(body.lomax, body.max_longitude, body.maxLongitude, query.lomax, query.max_longitude, query.maxLongitude),
  };
  const pointSource = body.point || {
    lat: firstDefined(body.lat, body.latitude, query.lat, query.latitude),
    lon: firstDefined(body.lon, body.lng, body.longitude, query.lon, query.lng, query.longitude),
    radius: firstDefined(body.radius, body.radius_nm, query.radius, query.radius_nm),
  };
  const hasBounds = Object.values(boundsSource).some(
    (value) => value !== undefined && value !== null && value !== '',
  );
  const hasPoint = Object.values(pointSource).some(
    (value) => value !== undefined && value !== null && value !== '',
  );

  return {
    provider: firstDefined(body.provider, query.provider),
    preset: firstDefined(body.preset, query.preset),
    bounds: hasBounds ? normalizeBounds(boundsSource) : undefined,
    point: hasPoint ? normalizePoint(pointSource) : undefined,
    limit: firstDefined(body.limit, query.limit),
    max_route_points: firstDefined(body.max_route_points, body.maxRoutePoints, query.max_route_points, query.maxRoutePoints),
    icao24: firstDefined(body.icao24, query.icao24),
    time: firstDefined(body.time, query.time),
    extended: parseBoolean(firstDefined(body.extended, query.extended)),
    merge_sources: parseBoolean(firstDefined(body.merge_sources, body.mergeSources, query.merge_sources, query.mergeSources)),
    live_only: parseBoolean(firstDefined(body.live_only, body.liveOnly, query.live_only, query.liveOnly)),
    fresh_only: parseBoolean(firstDefined(body.fresh_only, body.freshOnly, query.fresh_only, query.freshOnly)),
    no_store: parseBoolean(firstDefined(body.no_store, body.noStore, query.no_store, query.noStore)),
    interval_seconds: firstDefined(body.interval_seconds, body.intervalSeconds, query.interval_seconds, query.intervalSeconds),
    task_id: firstDefined(body.task_id, body.taskId, query.task_id, query.taskId),
  };
}

function parseRouteQueryOptions(req) {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  const query = req.query || {};

  return {
    route_id: firstDefined(body.route_id, body.routeId, query.route_id, query.routeId),
    route_key: firstDefined(body.route_key, body.routeKey, query.route_key, query.routeKey),
    callsign: firstDefined(body.callsign, query.callsign),
    aircraft_hex: firstDefined(body.aircraft_hex, body.aircraftHex, query.aircraft_hex, query.aircraftHex),
    provider: firstDefined(body.provider, query.provider),
    source: firstDefined(body.source, query.source),
    start_time: firstDefined(body.start_time, body.startTime, query.start_time, query.startTime),
    end_time: firstDefined(body.end_time, body.endTime, query.end_time, query.endTime),
    limit: firstDefined(body.limit, query.limit),
    merge_sources: parseBoolean(firstDefined(body.merge_sources, body.mergeSources, query.merge_sources, query.mergeSources)),
  };
}

function parseTrackLocation(location) {
  if (!location) {
    return {};
  }

  const value = String(location).trim();
  // Alpha database stores ADS-B coordinates in a single POINT(lng lat) column.
  const pointMatch = value.match(/^POINT\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\)$/i);
  if (pointMatch) {
    return {
      longitude: Number(pointMatch[1]),
      latitude: Number(pointMatch[2]),
    };
  }

  // Keep a fallback for older/demo data that may have been stored as "lat,lng".
  const commaMatch = value.match(/^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$/);
  if (commaMatch) {
    return {
      latitude: Number(commaMatch[1]),
      longitude: Number(commaMatch[2]),
    };
  }

  return {};
}

function withTrackCoordinates(track) {
  if (!track) {
    return track;
  }

  // Expose latitude/longitude to API callers while preserving the DB location field.
  return {
    ...track,
    ...parseTrackLocation(track.location),
  };
}

function isWithinBounds(track, bounds) {
  const { latitude, longitude } = withTrackCoordinates(track);

  // SQLite has no spatial POINT comparison here, so coordinate bounds are applied in JS.
  if (
    (bounds.minLatitude !== undefined || bounds.maxLatitude !== undefined) &&
    latitude === undefined
  ) {
    return false;
  }

  if (
    (bounds.minLongitude !== undefined || bounds.maxLongitude !== undefined) &&
    longitude === undefined
  ) {
    return false;
  }

  return (
    (bounds.minLatitude === undefined || latitude >= bounds.minLatitude) &&
    (bounds.maxLatitude === undefined || latitude <= bounds.maxLatitude) &&
    (bounds.minLongitude === undefined || longitude >= bounds.minLongitude) &&
    (bounds.maxLongitude === undefined || longitude <= bounds.maxLongitude)
  );
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

router.post('/sources/opensky/fetch', async (req, res, next) => {
  try {
    const options = parseOpenSkyFetchOptions(req);
    const result = await fetchAndStoreOpenSkyStates(options);
    res.status(201).json({
      data: {
        provider: result.provider,
        endpoint: result.endpoint,
        request_url: result.request_url,
        bounds: result.bounds,
        response_time: result.response_time,
        response_time_iso: result.response_time_iso,
        fetched_count: result.fetched_count,
        decoded_count: result.decoded_count,
        skipped_count: result.skipped_count,
        limited_count: result.limited_count,
        saved_count: result.saved_count,
        rate_limit: result.rate_limit,
        sample: result.saved.slice(0, 5).map(({ raw_payload, ...track }) => track),
      },
    });
  } catch (error) {
    next(error);
  }
});

router.get('/sources/opensky/presets', (req, res) => {
  res.json({
    data: BOUNDING_BOX_PRESETS,
  });
});

router.post('/sources/airplanes-live/fetch', async (req, res, next) => {
  try {
    const options = parseAirplanesLiveFetchOptions(req);
    const result = await fetchAndStoreAirplanesLiveAircraft(options);
    res.status(201).json({
      data: {
        provider: result.provider,
        endpoint: result.endpoint,
        request_url: result.request_url,
        point: result.point,
        response_time_ms: result.response_time_ms,
        response_time_iso: result.response_time_iso,
        fetched_count: result.fetched_count,
        decoded_count: result.decoded_count,
        skipped_count: result.skipped_count,
        limited_count: result.limited_count,
        saved_count: result.saved_count,
        sample: result.saved.slice(0, 5).map(({ raw_payload, ...track }) => track),
      },
    });
  } catch (error) {
    next(error);
  }
});

router.get('/sources/airplanes-live/presets', (req, res) => {
  res.json({
    data: POINT_PRESETS,
  });
});

router.post('/routes/crawl', async (req, res, next) => {
  try {
    const data = await crawlRoutesOnce(parseRouteCrawlOptions(req));
    res.status(201).json({ data });
  } catch (error) {
    next(error);
  }
});

router.post('/routes/rebuild', (req, res, next) => {
  try {
    const data = rebuildRoutesFromStoredTracks(parseRouteQueryOptions(req));
    res.status(201).json({ data });
  } catch (error) {
    next(error);
  }
});

router.get('/routes', (req, res, next) => {
  try {
    const data = listRoutes(parseRouteQueryOptions(req));
    res.json({ data, count: data.length });
  } catch (error) {
    next(error);
  }
});

router.get('/routes/:routeId', (req, res, next) => {
  try {
    const data = getRoute(req.params.routeId);
    if (!data) {
      return res.status(404).json({ error: 'Route not found.' });
    }

    return res.json({ data });
  } catch (error) {
    return next(error);
  }
});

router.post('/routes/crawl-tasks/start', (req, res, next) => {
  try {
    const data = startRouteCrawlTask(parseRouteCrawlOptions(req));
    res.status(202).json({ data });
  } catch (error) {
    next(error);
  }
});

router.post('/routes/crawl-tasks/:taskId/stop', (req, res, next) => {
  try {
    const data = stopRouteCrawlTask(req.params.taskId);
    if (!data) {
      return res.status(404).json({ error: 'Route crawl task is not running.' });
    }

    return res.json({ data });
  } catch (error) {
    return next(error);
  }
});

router.get('/routes/crawl-tasks/status', (req, res) => {
  const data = listRouteCrawlTaskStatus();
  res.json({ data, count: data.length });
});

router.get('/routes/crawl-tasks/:taskId/status', (req, res) => {
  const data = getRouteCrawlTaskStatus(req.params.taskId);
  if (!data) {
    return res.status(404).json({ error: 'Route crawl task is not running.' });
  }

  return res.json({ data });
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

    // Latitude/longitude are parsed from location after the SQL query.
    if (minLatitude !== undefined) {
      params.min_latitude = minLatitude;
    }

    if (maxLatitude !== undefined) {
      params.max_latitude = maxLatitude;
    }

    if (minLongitude !== undefined) {
      params.min_longitude = minLongitude;
    }

    if (maxLongitude !== undefined) {
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

    const rows = db.prepare(sql).all(params);
    const data = rows
      .filter((track) =>
        isWithinBounds(track, {
          minLatitude,
          maxLatitude,
          minLongitude,
          maxLongitude,
        }),
      )
      .map(withTrackCoordinates);
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

    return res.json({ data: withTrackCoordinates(data) });
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
        t.location,
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

    const data = db.prepare(sql).all(params).map((row) => ({
      ...row,
      ...parseTrackLocation(row.location),
    }));
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
