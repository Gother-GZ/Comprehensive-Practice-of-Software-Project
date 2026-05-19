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

function normalizeTrack(input, fallbackSource) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new Error('Track payload must be an object.');
  }

  return {
    track_id: input.track_id || randomUUID(),
    callsign: input.callsign || null,
    latitude: parseNumber(input.latitude, 'latitude', false, false),
    longitude: parseNumber(input.longitude, 'longitude', false, false),
    altitude: parseNumber(input.altitude, 'altitude', true, true),
    ground_speed: parseNumber(input.ground_speed, 'ground_speed', true, true),
    heading: parseNumber(input.heading, 'heading', true, true),
    timestamp: input.timestamp || new Date().toISOString(),
    source: input.source || fallbackSource || null,
    raw_payload:
      input.raw_payload === undefined || input.raw_payload === null
        ? null
        : typeof input.raw_payload === 'string'
          ? input.raw_payload
          : JSON.stringify(input.raw_payload),
  };
}

const upsertTrackStatement = db.prepare(`
  INSERT INTO adsb_tracks (
    track_id,
    callsign,
    latitude,
    longitude,
    altitude,
    ground_speed,
    heading,
    timestamp,
    source,
    raw_payload
  ) VALUES (
    @track_id,
    @callsign,
    @latitude,
    @longitude,
    @altitude,
    @ground_speed,
    @heading,
    @timestamp,
    @source,
    @raw_payload
  )
  ON CONFLICT(track_id) DO UPDATE SET
    callsign = excluded.callsign,
    latitude = excluded.latitude,
    longitude = excluded.longitude,
    altitude = excluded.altitude,
    ground_speed = excluded.ground_speed,
    heading = excluded.heading,
    timestamp = excluded.timestamp,
    source = excluded.source,
    raw_payload = excluded.raw_payload
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
