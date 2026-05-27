const { batchUpsertTracks } = require('./trackService');

const OPEN_SKY_BASE_URL =
  process.env.OPENSKY_BASE_URL || 'https://opensky-network.org/api';
const OPEN_SKY_TOKEN_URL =
  process.env.OPENSKY_TOKEN_URL ||
  'https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token';

const BOUNDING_BOX_PRESETS = {
  hongkong: {
    lamin: 21.8,
    lomin: 112.8,
    lamax: 23.3,
    lomax: 115.0,
  },
  beijing: {
    lamin: 39.2,
    lomin: 115.4,
    lamax: 41.2,
    lomax: 117.6,
  },
  switzerland: {
    lamin: 45.8389,
    lomin: 5.9962,
    lamax: 47.8229,
    lomax: 10.5226,
  },
};

const STATE_VECTOR_FIELDS = [
  'icao24',
  'callsign',
  'origin_country',
  'time_position',
  'last_contact',
  'longitude',
  'latitude',
  'baro_altitude',
  'on_ground',
  'velocity',
  'true_track',
  'vertical_rate',
  'sensors',
  'geo_altitude',
  'squawk',
  'spi',
  'position_source',
  'category',
];

let cachedToken = null;

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

function normalizeBounds(bounds) {
  if (!bounds) {
    return null;
  }

  const normalized = {
    lamin: parseOptionalNumber(
      bounds.lamin ?? bounds.min_latitude ?? bounds.minLatitude,
      'lamin',
    ),
    lomin: parseOptionalNumber(
      bounds.lomin ?? bounds.min_longitude ?? bounds.minLongitude,
      'lomin',
    ),
    lamax: parseOptionalNumber(
      bounds.lamax ?? bounds.max_latitude ?? bounds.maxLatitude,
      'lamax',
    ),
    lomax: parseOptionalNumber(
      bounds.lomax ?? bounds.max_longitude ?? bounds.maxLongitude,
      'lomax',
    ),
  };

  if (Object.values(normalized).some((value) => value === undefined)) {
    throw new Error('OpenSky bounds require lamin, lomin, lamax, and lomax.');
  }

  if (normalized.lamin >= normalized.lamax) {
    throw new Error('OpenSky bounds require lamin < lamax.');
  }

  if (normalized.lomin >= normalized.lomax) {
    throw new Error('OpenSky bounds require lomin < lomax.');
  }

  return normalized;
}

function parseBoundsText(value) {
  if (!value) {
    return null;
  }

  const parts = String(value)
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length !== 4) {
    throw new Error('OPENSKY_DEFAULT_BBOX must be lamin,lomin,lamax,lomax.');
  }

  return normalizeBounds({
    lamin: parts[0],
    lomin: parts[1],
    lamax: parts[2],
    lomax: parts[3],
  });
}

function resolveBounds(options = {}) {
  if (options.bounds === null) {
    return null;
  }

  if (options.bounds) {
    return normalizeBounds(options.bounds);
  }

  const preset = String(
    options.preset || process.env.OPENSKY_DEFAULT_PRESET || 'hongkong',
  ).toLowerCase();
  if (preset === 'global' || preset === 'none') {
    return null;
  }

  if (process.env.OPENSKY_DEFAULT_BBOX) {
    return parseBoundsText(process.env.OPENSKY_DEFAULT_BBOX);
  }

  const presetBounds = BOUNDING_BOX_PRESETS[preset];
  if (!presetBounds) {
    throw new Error(`Unknown OpenSky bounds preset: ${preset}`);
  }

  return presetBounds;
}

function secondsToIso(seconds) {
  if (!seconds) {
    return new Date().toISOString();
  }

  return new Date(Number(seconds) * 1000).toISOString();
}

function metersToFeet(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed * 3.28084) : null;
}

function metersPerSecondToKnots(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed * 1.94384) : null;
}

function roundedInteger(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed) : null;
}

function stateVectorToObject(state) {
  return Object.fromEntries(
    STATE_VECTOR_FIELDS.map((field, index) => [field, state[index] ?? null]),
  );
}

function decodeOpenSkyStateVector(state, responseTime) {
  if (!Array.isArray(state)) {
    return null;
  }

  const decoded = stateVectorToObject(state);
  const latitude = parseOptionalNumber(decoded.latitude, 'latitude');
  const longitude = parseOptionalNumber(decoded.longitude, 'longitude');
  if (latitude === undefined || longitude === undefined || !decoded.icao24) {
    return null;
  }

  const observedAt =
    decoded.time_position || decoded.last_contact || responseTime || Math.floor(Date.now() / 1000);
  const altitude = metersToFeet(decoded.baro_altitude ?? decoded.geo_altitude);
  const track = {
    track_id: `opensky:${decoded.icao24}:${observedAt}`,
    callsign: String(decoded.callsign || decoded.icao24).trim() || null,
    latitude,
    longitude,
    altitude,
    ground_speed: metersPerSecondToKnots(decoded.velocity),
    heading: roundedInteger(decoded.true_track),
    timestamp: secondsToIso(observedAt),
    source: 'opensky:states/all',
    raw_payload: {
      provider: 'OpenSky Network',
      endpoint: '/states/all',
      response_time: responseTime,
      decoded_units: {
        altitude: 'ft',
        ground_speed: 'kt',
        heading: 'deg',
      },
      state_vector: decoded,
    },
  };

  return track;
}

async function fetchOpenSkyToken() {
  const clientId = process.env.OPENSKY_CLIENT_ID;
  const clientSecret = process.env.OPENSKY_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    return null;
  }

  const now = Math.floor(Date.now() / 1000);
  if (cachedToken && cachedToken.expiresAt > now + 30) {
    return cachedToken.accessToken;
  }

  const body = new URLSearchParams({
    grant_type: 'client_credentials',
    client_id: clientId,
    client_secret: clientSecret,
  });
  const response = await fetch(OPEN_SKY_TOKEN_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `OpenSky token request failed: ${response.status} ${response.statusText} ${text}`,
    );
  }

  const token = await response.json();
  cachedToken = {
    accessToken: token.access_token,
    expiresAt: now + Number(token.expires_in || 0),
  };
  return cachedToken.accessToken;
}

async function buildOpenSkyHeaders() {
  const token = await fetchOpenSkyToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function buildStatesUrl(options = {}) {
  const url = new URL('/api/states/all', OPEN_SKY_BASE_URL);
  const bounds = resolveBounds(options);

  if (bounds) {
    url.searchParams.set('lamin', bounds.lamin);
    url.searchParams.set('lomin', bounds.lomin);
    url.searchParams.set('lamax', bounds.lamax);
    url.searchParams.set('lomax', bounds.lomax);
  }

  if (options.icao24) {
    url.searchParams.set('icao24', String(options.icao24).toLowerCase());
  }

  if (options.time) {
    url.searchParams.set('time', String(options.time));
  }

  if (options.extended) {
    url.searchParams.set('extended', '1');
  }

  return { url, bounds };
}

function rateLimitHeaders(response) {
  return {
    limit: response.headers.get('x-rate-limit-limit'),
    remaining: response.headers.get('x-rate-limit-remaining'),
    reset: response.headers.get('x-rate-limit-reset'),
    retry_after: response.headers.get('retry-after'),
  };
}

async function fetchOpenSkyStates(options = {}) {
  const { url, bounds } = buildStatesUrl(options);
  const response = await fetch(url, {
    headers: await buildOpenSkyHeaders(),
  });
  const rate_limit = rateLimitHeaders(response);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `OpenSky states request failed: ${response.status} ${response.statusText} ${text}`,
    );
  }

  const payload = await response.json();
  const rawStates = Array.isArray(payload.states) ? payload.states : [];
  const decoded = rawStates
    .map((state) => decodeOpenSkyStateVector(state, payload.time))
    .filter(Boolean);
  const limit = normalizeLimit(options.limit, 100);
  const items = decoded.slice(0, limit);

  return {
    provider: 'OpenSky Network',
    endpoint: '/states/all',
    request_url: url.toString(),
    bounds,
    response_time: payload.time,
    response_time_iso: secondsToIso(payload.time),
    fetched_count: rawStates.length,
    decoded_count: decoded.length,
    skipped_count: rawStates.length - decoded.length,
    limited_count: items.length,
    rate_limit,
    items,
  };
}

async function fetchAndStoreOpenSkyStates(options = {}) {
  const result = await fetchOpenSkyStates(options);
  const saved = result.items.length
    ? batchUpsertTracks(result.items, 'opensky:states/all')
    : [];

  return {
    ...result,
    saved_count: saved.length,
    saved,
  };
}

module.exports = {
  BOUNDING_BOX_PRESETS,
  decodeOpenSkyStateVector,
  fetchAndStoreOpenSkyStates,
  fetchOpenSkyStates,
  normalizeBounds,
  normalizeLimit,
  resolveBounds,
};
