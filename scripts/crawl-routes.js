const {
  crawlRoutesOnce,
  rebuildRoutesFromStoredTracks,
} = require('../src/services/routeCrawlerService');
const { normalizeBounds } = require('../src/services/openSkyCollector');
const { normalizePoint } = require('../src/services/airplanesLiveCollector');

function parseArgs(argv) {
  const options = {};
  const positional = [];

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!arg.startsWith('--')) {
      positional.push(arg);
      continue;
    }

    const [rawKey, inlineValue] = arg.slice(2).split('=', 2);
    const key = rawKey.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    const value =
      inlineValue !== undefined
        ? inlineValue
        : argv[index + 1] && !argv[index + 1].startsWith('--')
          ? argv[++index]
          : true;

    options[key] = value;
  }

  if (!options.provider && positional[0]) {
    options.provider = positional[0];
  }

  if (!options.preset && positional[1]) {
    options.preset = positional[1];
  }

  if (!options.limit && positional[2]) {
    options.limit = positional[2];
  }

  return options;
}

function buildBounds(args) {
  const bounds = {
    lamin: args.lamin ?? args.minLatitude,
    lomin: args.lomin ?? args.minLongitude,
    lamax: args.lamax ?? args.maxLatitude,
    lomax: args.lomax ?? args.maxLongitude,
  };
  const hasBounds = Object.values(bounds).some(
    (value) => value !== undefined && value !== null && value !== '',
  );

  return hasBounds ? normalizeBounds(bounds) : undefined;
}

function buildPoint(args) {
  const point = {
    lat: args.lat ?? args.latitude,
    lon: args.lon ?? args.lng ?? args.longitude,
    radius: args.radius ?? args.radiusNm,
  };
  const hasPoint = Object.values(point).some(
    (value) => value !== undefined && value !== null && value !== '',
  );

  return hasPoint ? normalizePoint(point) : undefined;
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

function sanitizeRoute(route) {
  return {
    route_id: route.route_id,
    route_key: route.route_key,
    callsign: route.callsign,
    aircraft_hex: route.aircraft_hex,
    provider: route.provider,
    source: route.source,
    start_time: route.start_time,
    end_time: route.end_time,
    point_count: route.point_count,
  };
}

async function run() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) {
    console.log(
      [
        'usage:',
        '  node scripts/crawl-routes.js [airplanes-live|opensky] [preset] [limit]',
        '  node scripts/crawl-routes.js --provider airplanes-live --preset hongkong --limit 50',
        '  node scripts/crawl-routes.js --provider opensky --lamin 45 --lomin 6 --lamax 48 --lomax 11 --limit 50',
        '  node scripts/crawl-routes.js --rebuild --callsign SWR4WG --limit 5000',
      ].join('\n'),
    );
    return;
  }

  const options = {
    provider: args.provider,
    preset: args.preset,
    bounds: buildBounds(args),
    point: buildPoint(args),
    limit: args.limit,
    max_route_points: args.maxRoutePoints,
    icao24: args.icao24,
    time: args.time,
    extended: parseBoolean(args.extended),
    merge_sources: parseBoolean(args.mergeSources),
    live_only: parseBoolean(args.liveOnly) || parseBoolean(args.freshOnly) || parseBoolean(args.noStore),
    callsign: args.callsign,
    source: args.source,
    start_time: args.startTime,
    end_time: args.endTime,
  };

  const result = parseBoolean(args.rebuild)
    ? rebuildRoutesFromStoredTracks(options)
    : await crawlRoutesOnce(options);

  console.log(
    JSON.stringify(
      {
        provider: result.provider,
        live_only: result.live_only,
        fetch: result.fetch,
        track_count: result.track_count,
        route_count: result.route_count,
        routes: result.routes.slice(0, 10).map(sanitizeRoute),
      },
      null,
      2,
    ),
  );
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
