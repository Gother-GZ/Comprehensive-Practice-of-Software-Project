const { batchUpsertTracks } = require('./trackService');

const AIRPLANES_LIVE_BASE_URL =
  process.env.AIRPLANES_LIVE_BASE_URL || 'https://api.airplanes.live';

const POINT_PRESETS = {
  hongkong: {
    lat: 22.308,
    lon: 113.9185,
    radius: 250,
  },
  beijing: {
    lat: 40.08,
    lon: 116.58,
    radius: 250,
  },
  switzerland: {
    lat: 47.0,
    lon: 8.0,
    radius: 120,
  },
};

function parseOptionalNumber(value, field) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${field} must be a valid number.`);
  }

  return parsed;
}

function normalizeLimit(value, fallback = 100) {
  const parsed = Number(value ?? fallback);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }

  return Math.min(Math.trunc(parsed), 1000);
}

function normalizePoint(point) {
  if (!point) {
    return null;
  }

  const normalized = {
    lat: parseOptionalNumber(point.lat ?? point.latitude, 'lat'),
    lon: parseOptionalNumber(point.lon ?? point.lng ?? point.longitude, 'lon'),
    radius: parseOptionalNumber(point.radius ?? point.radius_nm, 'radius'),
  };

  if (Object.values(normalized).some((value) => value === undefined)) {
    throw new Error('Airplanes.live point requires lat, lon, and radius.');
  }

  if (normalized.radius <= 0 || normalized.radius > 250) {
    throw new Error('Airplanes.live radius must be between 1 and 250 nautical miles.');
  }

  return normalized;
}

function resolvePoint(options = {}) {
  if (options.point) {
    return normalizePoint(options.point);
  }

  const preset = String(
    options.preset || process.env.AIRPLANES_LIVE_DEFAULT_PRESET || 'hongkong',
  ).toLowerCase();
  const presetPoint = POINT_PRESETS[preset];
  if (!presetPoint) {
    throw new Error(`Unknown Airplanes.live point preset: ${preset}`);
  }

  return presetPoint;
}

function numberOrNull(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function integerOrNull(value) {
  const parsed = numberOrNull(value);
  return parsed === null ? null : Math.round(parsed);
}

function altitudeFeet(value, fallback) {
  if (value === 'ground') {
    return 0;
  }

  const parsed = integerOrNull(value);
  return parsed === null ? integerOrNull(fallback) : parsed;
}

function observedTimeIso(responseNowMs, aircraft) {
  const nowMs = Number(responseNowMs || Date.now());
  const seenSeconds = numberOrNull(aircraft.seen_pos ?? aircraft.seen) || 0;
  return new Date(nowMs - seenSeconds * 1000).toISOString();
}

function decodeAirplanesLiveAircraft(aircraft, responseNowMs) {
  if (!aircraft || typeof aircraft !== 'object') {
    return null;
  }

  const latitude = parseOptionalNumber(aircraft.lat, 'lat');
  const longitude = parseOptionalNumber(aircraft.lon, 'lon');
  if (latitude === undefined || longitude === undefined || !aircraft.hex) {
    return null;
  }

  const observedIso = observedTimeIso(responseNowMs, aircraft);
  const observedSeconds = Math.floor(Date.parse(observedIso) / 1000);

  return {
    track_id: `airplanes:${aircraft.hex}:${observedSeconds}`,
    callsign: String(aircraft.flight || aircraft.hex).trim() || null,
    latitude,
    longitude,
    altitude: altitudeFeet(aircraft.alt_baro, aircraft.alt_geom),
    ground_speed: integerOrNull(aircraft.gs),
    heading: integerOrNull(aircraft.track ?? aircraft.true_heading ?? aircraft.mag_heading),
    timestamp: observedIso,
    source: 'airplanes.live:v2/point',
    raw_payload: {
      provider: 'Airplanes.live',
      endpoint: '/v2/point/{lat}/{lon}/{radius}',
      response_time_ms: responseNowMs,
      decoded_units: {
        altitude: 'ft',
        ground_speed: 'kt',
        heading: 'deg',
      },
      aircraft,
    },
  };
}

function buildPointUrl(options = {}) {
  const point = resolvePoint(options);
  const url = new URL(
    `/v2/point/${point.lat}/${point.lon}/${point.radius}`,
    AIRPLANES_LIVE_BASE_URL,
  );
  return { url, point };
}

async function fetchAirplanesLiveAircraft(options = {}) {
  const { url, point } = buildPointUrl(options);
  const response = await fetch(url);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Airplanes.live request failed: ${response.status} ${response.statusText} ${text}`,
    );
  }

  const payload = await response.json();
  const rawAircraft = Array.isArray(payload.ac) ? payload.ac : [];
  const decoded = rawAircraft
    .map((aircraft) => decodeAirplanesLiveAircraft(aircraft, payload.now))
    .filter(Boolean);
  const limit = normalizeLimit(options.limit, 100);
  const items = decoded.slice(0, limit);

  return {
    provider: 'Airplanes.live',
    endpoint: '/v2/point/{lat}/{lon}/{radius}',
    request_url: url.toString(),
    point,
    response_time_ms: payload.now,
    response_time_iso: new Date(Number(payload.now || Date.now())).toISOString(),
    fetched_count: rawAircraft.length,
    decoded_count: decoded.length,
    skipped_count: rawAircraft.length - decoded.length,
    limited_count: items.length,
    items,
  };
}

async function fetchAndStoreAirplanesLiveAircraft(options = {}) {
  const result = await fetchAirplanesLiveAircraft(options);
  const saved = result.items.length
    ? batchUpsertTracks(result.items, 'airplanes.live:v2/point')
    : [];

  return {
    ...result,
    saved_count: saved.length,
    saved,
  };
}

module.exports = {
  POINT_PRESETS,
  decodeAirplanesLiveAircraft,
  fetchAirplanesLiveAircraft,
  fetchAndStoreAirplanesLiveAircraft,
  normalizeLimit,
  normalizePoint,
  resolvePoint,
};
