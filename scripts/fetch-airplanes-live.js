const {
  POINT_PRESETS,
  fetchAndStoreAirplanesLiveAircraft,
  normalizePoint,
} = require('../src/services/airplanesLiveCollector');

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

  if (!options.preset && positional[0]) {
    options.preset = positional[0];
  }

  if (!options.limit && positional[1]) {
    options.limit = positional[1];
  }

  return options;
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

function sanitizeTrack(track) {
  const { raw_payload, ...rest } = track;
  return rest;
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const options = {
    preset: args.preset,
    point: buildPoint(args),
    limit: args.limit,
  };

  if (args.help) {
    console.log(
      [
        'usage: node scripts/fetch-airplanes-live.js [--preset hongkong|beijing|switzerland] [--limit 50]',
        '       node scripts/fetch-airplanes-live.js --lat 47 --lon 8 --radius 120 --limit 20',
        '',
        `presets: ${Object.keys(POINT_PRESETS).join(', ')}`,
      ].join('\n'),
    );
    return;
  }

  const result = await fetchAndStoreAirplanesLiveAircraft(options);
  console.log(
    JSON.stringify(
      {
        provider: result.provider,
        endpoint: result.endpoint,
        request_url: result.request_url,
        response_time_iso: result.response_time_iso,
        fetched_count: result.fetched_count,
        decoded_count: result.decoded_count,
        skipped_count: result.skipped_count,
        limited_count: result.limited_count,
        saved_count: result.saved_count,
        sample: result.saved.slice(0, 5).map(sanitizeTrack),
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
