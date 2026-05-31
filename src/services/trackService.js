const { randomUUID } = require("crypto");
const { db } = require("../db");

const adsbTrackColumns = new Set(
  db
    .prepare("PRAGMA table_info(adsb_tracks)")
    .all()
    .map((column) => column.name),
);

function parseNumber(value, field, integer = false, nullable = true) {
  if (value === undefined || value === null || value === "") {
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

function coordinatePairFromLocation(location) {
  if (location === undefined || location === null || location === "") {
    return null;
  }

  if (typeof location === "string") {
    const pointMatch = location.match(
      /^POINT\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\)$/i,
    );
    if (pointMatch) {
      return {
        longitude: Number(pointMatch[1]),
        latitude: Number(pointMatch[2]),
        location,
      };
    }

    const commaMatch = location.match(
      /^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$/,
    );
    if (commaMatch) {
      const latitude = Number(commaMatch[1]);
      const longitude = Number(commaMatch[2]);
      return {
        latitude,
        longitude,
        location: `POINT(${longitude} ${latitude})`,
      };
    }

    return {
      latitude: null,
      longitude: null,
      location,
    };
  }

  if (Array.isArray(location) && location.length >= 2) {
    const longitude = parseNumber(location[0], "longitude", false, false);
    const latitude = parseNumber(location[1], "latitude", false, false);
    return {
      latitude,
      longitude,
      location: `POINT(${longitude} ${latitude})`,
    };
  }

  if (typeof location === "object") {
    if (
      Array.isArray(location.coordinates) &&
      location.coordinates.length >= 2
    ) {
      const longitude = parseNumber(location.coordinates[0], "longitude", false, false);
      const latitude = parseNumber(location.coordinates[1], "latitude", false, false);
      return {
        latitude,
        longitude,
        location: `POINT(${longitude} ${latitude})`,
      };
    }

    const latitudeValue = location.latitude ?? location.lat;
    const longitudeValue = location.longitude ?? location.lng ?? location.lon;
    if (latitudeValue !== undefined || longitudeValue !== undefined) {
      const latitude = parseNumber(latitudeValue, "latitude", false, false);
      const longitude = parseNumber(longitudeValue, "longitude", false, false);
      return {
        latitude,
        longitude,
        location: `POINT(${longitude} ${latitude})`,
      };
    }

    return {
      latitude: null,
      longitude: null,
      location: JSON.stringify(location),
    };
  }

  return null;
}

function normalizeCoordinates(input) {
  const locationPair = coordinatePairFromLocation(input.location);
  if (locationPair) {
    return locationPair;
  }

  const latitude = parseNumber(
    input.latitude ?? input.lat,
    "latitude",
    false,
    false,
  );
  const longitude = parseNumber(
    input.longitude ?? input.lng ?? input.lon,
    "longitude",
    false,
    false,
  );
  return {
    latitude,
    longitude,
    location: `POINT(${longitude} ${latitude})`,
  };
}

function normalizeRawPayload(value) {
  if (value === undefined) {
    return undefined;
  }

  if (value === null || typeof value === "string") {
    return value;
  }

  return JSON.stringify(value);
}

function normalizeTrack(input, fallbackSource) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("Track payload must be an object.");
  }

  const coordinates = normalizeCoordinates(input);
  const track = {
    track_id: input.track_id || randomUUID(),
    callsign: input.callsign || null,
    altitude: parseNumber(input.altitude, "altitude", true, true),
    ground_speed: parseNumber(input.ground_speed, "ground_speed", true, true),
    heading: parseNumber(input.heading, "heading", true, true),
    timestamp: input.timestamp || new Date().toISOString(),
  };

  if (adsbTrackColumns.has("location")) {
    track.location = coordinates.location;
  }

  if (adsbTrackColumns.has("latitude")) {
    track.latitude = coordinates.latitude;
  }

  if (adsbTrackColumns.has("longitude")) {
    track.longitude = coordinates.longitude;
  }

  if (adsbTrackColumns.has("source")) {
    track.source = input.source || fallbackSource || null;
  }

  if (adsbTrackColumns.has("raw_payload")) {
    track.raw_payload = normalizeRawPayload(
      input.raw_payload ?? input.rawPayload,
    );
  }

  return track;
}

const upsertColumns = [
  "track_id",
  "callsign",
  "location",
  "latitude",
  "longitude",
  "altitude",
  "ground_speed",
  "heading",
  "timestamp",
  "source",
  "raw_payload",
].filter((column) => adsbTrackColumns.has(column));

const upsertAssignments = upsertColumns
  .filter((column) => column !== "track_id")
  .map((column) => `${column} = excluded.${column}`)
  .join(",\n    ");

const upsertTrackStatement = db.prepare(`
  INSERT INTO adsb_tracks (
    ${upsertColumns.join(",\n    ")}
  ) VALUES (
    ${upsertColumns.map((column) => `@${column}`).join(",\n    ")}
  )
  ON CONFLICT(track_id) DO UPDATE SET
    ${upsertAssignments}
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
    throw new Error("items must be a non-empty array.");
  }

  return batchUpsertTransaction(items, fallbackSource);
}

module.exports = {
  normalizeTrack,
  upsertTrack,
  batchUpsertTracks,
};
