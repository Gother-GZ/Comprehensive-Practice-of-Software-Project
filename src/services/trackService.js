const { randomUUID } = require('crypto');
const { db } = require('../db');

function parseNumber(value, field, integer = false, nullable = true) {
  if (value === undefined || value === null || value === '') {
    if (nullable) {
      return null;
    }

    throw new Error(`${field} is required.`);
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${field} must be a valid number.`);
  }

  return integer ? Math.trunc(parsed) : parsed;
}

function normalizeLocation(input) {
  if (input.location !== undefined && input.location !== null && input.location !== '') {
    return String(input.location);
  }

  // Accept frontend-friendly latitude/longitude fields and store them as POINT(lng lat).
  const latitude = parseNumber(input.latitude ?? input.lat, 'latitude', false, false);
  const longitude = parseNumber(input.longitude ?? input.lng, 'longitude', false, false);
  return `POINT(${longitude} ${latitude})`;
}

function normalizeTrack(input, fallbackSource) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new Error('Track payload must be an object.');
  }

  return {
    track_id: input.track_id || randomUUID(),
    callsign: input.callsign || null,
    location: normalizeLocation(input),
    altitude: parseNumber(input.altitude, 'altitude', true, true),
    ground_speed: parseNumber(input.ground_speed, 'ground_speed', true, true),
    heading: parseNumber(input.heading, 'heading', true, true),
    timestamp: input.timestamp || new Date().toISOString(),
  };
}

const upsertTrackStatement = db.prepare(`
  INSERT INTO adsb_tracks (
    track_id,
    callsign,
    location,
    altitude,
    ground_speed,
    heading,
    timestamp
  ) VALUES (
    @track_id,
    @callsign,
    @location,
    @altitude,
    @ground_speed,
    @heading,
    @timestamp
  )
  ON CONFLICT(track_id) DO UPDATE SET
    callsign = excluded.callsign,
    location = excluded.location,
    altitude = excluded.altitude,
    ground_speed = excluded.ground_speed,
    heading = excluded.heading,
    timestamp = excluded.timestamp
`);

const batchUpsertTransaction = db.transaction((items, fallbackSource) =>
  items.map((item) => {
    const track = normalizeTrack(item, fallbackSource);
    upsertTrackStatement.run(track);
    return track;
  }),
);

function upsertTrack(item, fallbackSource) {
  const track = normalizeTrack(item, fallbackSource);
  upsertTrackStatement.run(track);
  return track;
}

function batchUpsertTracks(items, fallbackSource) {
  if (!Array.isArray(items) || !items.length) {
    throw new Error('items must be a non-empty array.');
  }

  return batchUpsertTransaction(items, fallbackSource);
}

module.exports = {
  normalizeTrack,
  upsertTrack,
  batchUpsertTracks,
};
