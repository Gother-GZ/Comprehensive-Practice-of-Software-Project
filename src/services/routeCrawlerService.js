const { randomUUID } = require('crypto');
const { db } = require('../db');
const {
  fetchAndStoreOpenSkyStates,
  fetchOpenSkyStates,
} = require('./openSkyCollector');
const {
  fetchAndStoreAirplanesLiveAircraft,
  fetchAirplanesLiveAircraft,
} = require('./airplanesLiveCollector');

const DEFAULT_ROUTE_LIMIT = 5000;
const MAX_ROUTE_LIMIT = 50000;
const DEFAULT_CRAWL_INTERVAL_SECONDS = 30;
const MIN_CRAWL_INTERVAL_SECONDS = 10;

const crawlTasks = new Map();

function normalizeLimit(value, fallback = DEFAULT_ROUTE_LIMIT, max = MAX_ROUTE_LIMIT) {
  const parsed = Number(value ?? fallback);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }

  return Math.min(Math.trunc(parsed), max);
}

function normalizeIntervalSeconds(value) {
  const parsed = Number(value ?? DEFAULT_CRAWL_INTERVAL_SECONDS);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_CRAWL_INTERVAL_SECONDS;
  }

  return Math.max(Math.trunc(parsed), MIN_CRAWL_INTERVAL_SECONDS);
}

function normalizeProvider(value) {
  const provider = String(value || 'airplanes-live').toLowerCase();
  if (['airplanes', 'airplanes-live', 'airplanes.live'].includes(provider)) {
    return 'airplanes-live';
  }

  if (['opensky', 'open-sky', 'opensky-network'].includes(provider)) {
    return 'opensky';
  }

  throw new Error('provider must be airplanes-live or opensky.');
}

function truthy(value) {
  if (value === undefined || value === null || value === '') {
    return false;
  }

  if (typeof value === 'boolean') {
    return value;
  }

  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function sanitizeIdPart(value) {
  return (
    String(value || 'unknown')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'unknown'
  );
}

function parseTimestamp(value) {
  const millis = Date.parse(value);
  return Number.isFinite(millis) ? millis : Date.now();
}

function isoTimestamp(value) {
  return new Date(parseTimestamp(value)).toISOString();
}

function dateBucket(value) {
  return isoTimestamp(value).slice(0, 10);
}

function nextDateBucketStart(bucket) {
  const date = new Date(`${bucket}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString();
}

function numberOrNull(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseTrackLocation(track) {
  if (track.latitude !== undefined && track.longitude !== undefined) {
    const latitude = numberOrNull(track.latitude);
    const longitude = numberOrNull(track.longitude);
    if (latitude !== null && longitude !== null) {
      return { latitude, longitude };
    }
  }

  const value = String(track.location || '').trim();
  const pointMatch = value.match(
    /^POINT\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\)$/i,
  );
  if (pointMatch) {
    return {
      longitude: Number(pointMatch[1]),
      latitude: Number(pointMatch[2]),
    };
  }

  const commaMatch = value.match(
    /^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$/,
  );
  if (commaMatch) {
    return {
      latitude: Number(commaMatch[1]),
      longitude: Number(commaMatch[2]),
    };
  }

  return null;
}

function parseRawPayload(value) {
  if (!value) {
    return null;
  }

  if (typeof value === 'object') {
    return value;
  }

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function extractAircraftHex(track, rawPayload) {
  const fromOpenSky = rawPayload?.state_vector?.icao24;
  const fromAirplanes = rawPayload?.aircraft?.hex;
  const fromTrackId = String(track.track_id || '').match(/^(?:opensky|airplanes):([^:]+):/);
  const value = fromOpenSky || fromAirplanes || fromTrackId?.[1];
  return value ? String(value).trim().toLowerCase() : null;
}

function normalizeTrackForRoute(track) {
  const coordinates = parseTrackLocation(track);
  if (!coordinates) {
    return null;
  }

  const rawPayload = parseRawPayload(track.raw_payload);
  const callsign = String(track.callsign || '').trim() || null;
  const aircraftHex = extractAircraftHex(track, rawPayload);
  const routeKey = callsign || aircraftHex;

  if (!routeKey) {
    return null;
  }

  const timestamp = isoTimestamp(track.timestamp);
  return {
    ...track,
    ...coordinates,
    callsign,
    aircraft_hex: aircraftHex,
    route_key: routeKey,
    timestamp,
    timestamp_ms: parseTimestamp(timestamp),
    source: track.source || null,
  };
}

function providerFromTrack(track, fallbackProvider) {
  if (fallbackProvider) {
    return fallbackProvider;
  }

  const source = String(track.source || '').toLowerCase();
  if (source.includes('opensky')) {
    return 'opensky';
  }

  if (source.includes('airplanes')) {
    return 'airplanes-live';
  }

  return 'unknown';
}

function routeIdFor(group) {
  return [
    'adsb-route',
    sanitizeIdPart(group.provider),
    sanitizeIdPart(group.source || 'mixed'),
    sanitizeIdPart(group.route_key),
    group.bucket,
  ].join(':');
}

function groupRouteTracks(tracks, options = {}) {
  const groups = new Map();

  for (const track of tracks) {
    const normalized = normalizeTrackForRoute(track);
    if (!normalized) {
      continue;
    }

    const bucket = dateBucket(normalized.timestamp);
    const provider = providerFromTrack(normalized, options.provider);
    const source = options.merge_sources ? null : normalized.source;
    const key = [
      provider,
      source || 'mixed',
      normalized.route_key.toLowerCase(),
      bucket,
    ].join('|');

    if (!groups.has(key)) {
      groups.set(key, {
        provider,
        source,
        route_key: normalized.route_key,
        callsign: normalized.callsign,
        aircraft_hex: normalized.aircraft_hex,
        bucket,
        tracks: [],
      });
    }

    const group = groups.get(key);
    group.callsign ||= normalized.callsign;
    group.aircraft_hex ||= normalized.aircraft_hex;
    group.tracks.push(normalized);
  }

  return Array.from(groups.values());
}

function dedupeAndSortTracks(tracks) {
  const seen = new Set();
  const sorted = [...tracks].sort((left, right) => left.timestamp_ms - right.timestamp_ms);
  const unique = [];

  for (const track of sorted) {
    const key = [
      track.track_id || '',
      track.timestamp,
      track.latitude.toFixed(6),
      track.longitude.toFixed(6),
    ].join('|');

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    unique.push(track);
  }

  return unique;
}

function buildPathGeoJson(summary, tracks) {
  const coordinates = tracks.map((track) => [track.longitude, track.latitude]);
  const geometry =
    coordinates.length > 1
      ? { type: 'LineString', coordinates }
      : { type: 'Point', coordinates: coordinates[0] || null };

  return {
    type: 'Feature',
    geometry,
    properties: {
      route_id: summary.route_id,
      route_key: summary.route_key,
      callsign: summary.callsign,
      aircraft_hex: summary.aircraft_hex,
      provider: summary.provider,
      source: summary.source,
      start_time: summary.start_time,
      end_time: summary.end_time,
      point_count: summary.point_count,
    },
  };
}

function summarizeRoute(group, tracks, rawSummary = null) {
  const points = dedupeAndSortTracks(tracks);
  if (!points.length) {
    return null;
  }

  const latitudes = points.map((point) => point.latitude);
  const longitudes = points.map((point) => point.longitude);
  const summary = {
    route_id: routeIdFor(group),
    route_key: group.route_key,
    callsign: group.callsign,
    aircraft_hex: group.aircraft_hex,
    provider: group.provider,
    source: group.source,
    start_time: points[0].timestamp,
    end_time: points[points.length - 1].timestamp,
    point_count: points.length,
    min_latitude: Math.min(...latitudes),
    min_longitude: Math.min(...longitudes),
    max_latitude: Math.max(...latitudes),
    max_longitude: Math.max(...longitudes),
    sample_track_ids: JSON.stringify(points.slice(0, 100).map((point) => point.track_id)),
    raw_summary: rawSummary ? JSON.stringify(rawSummary) : null,
    updated_at: new Date().toISOString(),
  };

  summary.path_geojson = JSON.stringify(buildPathGeoJson(summary, points));
  return summary;
}

const upsertRouteStatement = db.prepare(`
  INSERT INTO adsb_routes (
    route_id,
    route_key,
    callsign,
    aircraft_hex,
    provider,
    source,
    start_time,
    end_time,
    point_count,
    min_latitude,
    min_longitude,
    max_latitude,
    max_longitude,
    path_geojson,
    sample_track_ids,
    raw_summary,
    updated_at
  ) VALUES (
    @route_id,
    @route_key,
    @callsign,
    @aircraft_hex,
    @provider,
    @source,
    @start_time,
    @end_time,
    @point_count,
    @min_latitude,
    @min_longitude,
    @max_latitude,
    @max_longitude,
    @path_geojson,
    @sample_track_ids,
    @raw_summary,
    @updated_at
  )
  ON CONFLICT(route_id) DO UPDATE SET
    route_key = excluded.route_key,
    callsign = excluded.callsign,
    aircraft_hex = excluded.aircraft_hex,
    provider = excluded.provider,
    source = excluded.source,
    start_time = excluded.start_time,
    end_time = excluded.end_time,
    point_count = excluded.point_count,
    min_latitude = excluded.min_latitude,
    min_longitude = excluded.min_longitude,
    max_latitude = excluded.max_latitude,
    max_longitude = excluded.max_longitude,
    path_geojson = excluded.path_geojson,
    sample_track_ids = excluded.sample_track_ids,
    raw_summary = excluded.raw_summary,
    updated_at = excluded.updated_at
`);

const upsertRoutesTransaction = db.transaction((summaries) => {
  for (const summary of summaries) {
    upsertRouteStatement.run(summary);
  }
});

function parseJsonColumn(value) {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function hydrateRoute(row) {
  if (!row) {
    return null;
  }

  return {
    ...row,
    path_geojson: parseJsonColumn(row.path_geojson),
    sample_track_ids: parseJsonColumn(row.sample_track_ids) || [],
    raw_summary: parseJsonColumn(row.raw_summary),
  };
}

function queryTracksForGroup(group, limit) {
  const params = {
    day_start: `${group.bucket}T00:00:00.000Z`,
    day_end: nextDateBucketStart(group.bucket),
    limit,
  };
  const clauses = ['timestamp >= @day_start', 'timestamp < @day_end'];

  if (group.source) {
    clauses.push('source = @source');
    params.source = group.source;
  }

  if (group.callsign) {
    clauses.push('callsign = @callsign');
    params.callsign = group.callsign;
  } else if (group.aircraft_hex) {
    clauses.push('track_id LIKE @track_prefix');
    params.track_prefix = `%:${group.aircraft_hex}:%`;
  } else {
    return [];
  }

  return db
    .prepare(
      `
        SELECT *
        FROM adsb_tracks
        WHERE ${clauses.join(' AND ')}
        ORDER BY timestamp ASC
        LIMIT @limit
      `,
    )
    .all(params);
}

function storeRouteSummaries(groups, options = {}) {
  const routeLimit = normalizeLimit(options.max_route_points, DEFAULT_ROUTE_LIMIT);
  const summaries = [];

  for (const group of groups) {
    const tracks = options.use_saved_only
      ? group.tracks
      : queryTracksForGroup(group, routeLimit);
    const normalizedTracks = tracks
      .map((track) => normalizeTrackForRoute(track))
      .filter(Boolean);
    const summary = summarizeRoute(group, normalizedTracks, options.raw_summary);

    if (summary) {
      summaries.push(summary);
    }
  }

  if (summaries.length && options.persist !== false) {
    upsertRoutesTransaction(summaries);
  }

  return summaries.map((summary) => hydrateRoute(summary));
}

function summarizeFetchResult(result) {
  return {
    provider: result.provider,
    endpoint: result.endpoint,
    request_url: result.request_url,
    response_time_iso: result.response_time_iso,
    fetched_count: result.fetched_count,
    decoded_count: result.decoded_count,
    skipped_count: result.skipped_count,
    limited_count: result.limited_count,
    saved_count: result.saved_count || 0,
  };
}

async function crawlRoutesOnce(options = {}) {
  const provider = normalizeProvider(options.provider);
  const liveOnly = truthy(options.live_only) || truthy(options.fresh_only) || truthy(options.no_store);
  const result =
    provider === 'opensky'
      ? liveOnly
        ? await fetchOpenSkyStates(options)
        : await fetchAndStoreOpenSkyStates(options)
      : liveOnly
        ? await fetchAirplanesLiveAircraft(options)
        : await fetchAndStoreAirplanesLiveAircraft(options);

  const tracks = liveOnly ? result.items || [] : result.saved || [];
  const groups = groupRouteTracks(tracks, {
    provider,
    merge_sources: options.merge_sources,
  });
  const routes = storeRouteSummaries(groups, {
    use_saved_only: liveOnly,
    persist: !liveOnly,
    max_route_points: options.max_route_points,
    raw_summary: {
      ...summarizeFetchResult(result),
      live_only: liveOnly,
    },
  });

  return {
    provider,
    live_only: liveOnly,
    fetch: summarizeFetchResult(result),
    track_count: tracks.length,
    route_count: routes.length,
    routes,
  };
}

function rebuildRoutesFromStoredTracks(options = {}) {
  const params = {
    limit: normalizeLimit(options.limit, DEFAULT_ROUTE_LIMIT),
  };
  const clauses = ['1 = 1'];

  if (options.callsign) {
    clauses.push('callsign = @callsign');
    params.callsign = options.callsign;
  }

  if (options.source) {
    clauses.push('source = @source');
    params.source = options.source;
  }

  if (options.start_time) {
    clauses.push('timestamp >= @start_time');
    params.start_time = options.start_time;
  }

  if (options.end_time) {
    clauses.push('timestamp <= @end_time');
    params.end_time = options.end_time;
  }

  const tracks = db
    .prepare(
      `
        SELECT *
        FROM adsb_tracks
        WHERE ${clauses.join(' AND ')}
        ORDER BY timestamp ASC
        LIMIT @limit
      `,
    )
    .all(params);
  const groups = groupRouteTracks(tracks, {
    provider: options.provider,
    merge_sources: options.merge_sources,
  });
  const routes = storeRouteSummaries(groups, {
    use_saved_only: true,
    raw_summary: {
      rebuilt_from: 'adsb_tracks',
      track_count: tracks.length,
      start_time: options.start_time || null,
      end_time: options.end_time || null,
    },
  });

  return {
    track_count: tracks.length,
    route_count: routes.length,
    routes,
  };
}

function listRoutes(options = {}) {
  const params = {
    limit: normalizeLimit(options.limit, 100, 1000),
  };
  const clauses = ['1 = 1'];

  for (const field of ['route_id', 'route_key', 'callsign', 'aircraft_hex', 'provider', 'source']) {
    if (options[field]) {
      clauses.push(`${field} = @${field}`);
      params[field] = options[field];
    }
  }

  if (options.start_time) {
    clauses.push('end_time >= @start_time');
    params.start_time = options.start_time;
  }

  if (options.end_time) {
    clauses.push('start_time <= @end_time');
    params.end_time = options.end_time;
  }

  return db
    .prepare(
      `
        SELECT *
        FROM adsb_routes
        WHERE ${clauses.join(' AND ')}
        ORDER BY updated_at DESC
        LIMIT @limit
      `,
    )
    .all(params)
    .map(hydrateRoute);
}

function getRoute(routeId) {
  return hydrateRoute(
    db.prepare('SELECT * FROM adsb_routes WHERE route_id = ?').get(routeId),
  );
}

function snapshotTask(task) {
  const { timer, ...state } = task.state;
  return state;
}

function startRouteCrawlTask(options = {}) {
  const taskId = options.task_id || randomUUID();

  if (crawlTasks.has(taskId)) {
    return snapshotTask(crawlTasks.get(taskId));
  }

  const intervalSeconds = normalizeIntervalSeconds(options.interval_seconds);
  const task = {
    running: false,
    stopped: false,
    timer: null,
    state: {
      task_id: taskId,
      provider: normalizeProvider(options.provider),
      preset: options.preset || null,
      interval_seconds: intervalSeconds,
      status: 'starting',
      run_count: 0,
      error_count: 0,
      last_started_at: null,
      last_finished_at: null,
      last_error: null,
      last_fetch: null,
      last_route_count: 0,
      created_at: new Date().toISOString(),
    },
  };

  async function runOnceForTask() {
    if (task.running || task.stopped) {
      return;
    }

    task.running = true;
    task.state.status = 'running';
    task.state.last_started_at = new Date().toISOString();

    try {
      const result = await crawlRoutesOnce(options);
      task.state.run_count += 1;
      task.state.last_error = null;
      task.state.last_fetch = result.fetch;
      task.state.last_route_count = result.route_count;
      task.state.status = 'waiting';
    } catch (error) {
      task.state.error_count += 1;
      task.state.last_error = error.message;
      task.state.status = 'error';
    } finally {
      task.state.last_finished_at = new Date().toISOString();
      task.running = false;
    }
  }

  crawlTasks.set(taskId, task);
  task.timer = setInterval(runOnceForTask, intervalSeconds * 1000);
  runOnceForTask();

  return snapshotTask(task);
}

function stopRouteCrawlTask(taskId) {
  const task = crawlTasks.get(taskId);
  if (!task) {
    return null;
  }

  task.stopped = true;
  clearInterval(task.timer);
  crawlTasks.delete(taskId);
  task.state.status = 'stopped';
  task.state.last_finished_at = new Date().toISOString();
  return snapshotTask(task);
}

function getRouteCrawlTaskStatus(taskId) {
  const task = crawlTasks.get(taskId);
  return task ? snapshotTask(task) : null;
}

function listRouteCrawlTaskStatus() {
  return Array.from(crawlTasks.values()).map(snapshotTask);
}

module.exports = {
  crawlRoutesOnce,
  rebuildRoutesFromStoredTracks,
  listRoutes,
  getRoute,
  startRouteCrawlTask,
  stopRouteCrawlTask,
  getRouteCrawlTaskStatus,
  listRouteCrawlTaskStatus,
};
