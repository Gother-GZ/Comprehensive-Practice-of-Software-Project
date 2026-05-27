const {
  BOUNDING_BOX_PRESETS,
  fetchAndStoreOpenSkyStates,
  normalizeBounds,
} = require('../src/services/openSkyCollector');

function parseArgs(argv) {
  const options = {};

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!arg.startsWith('--')) {
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

function parseBoolean(value) {
  if (value === undefined || value === null || value === '') {
    return false;
  }

  if (typeof value === 'boolean') {
    return value;
  }

  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function sanitizeTrack(track) {
  const { raw_payload, ...rest } = track;
  return rest;
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const options = {
    preset: args.preset,
    bounds: buildBounds(args),
    limit: args.limit,
    icao24: args.icao24,
    time: args.time,
    extended: parseBoolean(args.extended),
  };

  if (args.help) {
    console.log(
      [
        'usage: node scripts/fetch-opensky.js [--preset hongkong|beijing|switzerland|global] [--limit 50]',
        '       node scripts/fetch-opensky.js --lamin 45 --lomin 6 --lamax 48 --lomax 11 --limit 20',
        '',
        `presets: ${Object.keys(BOUNDING_BOX_PRESETS).join(', ')}, global`,
        'env: OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET are optional for authenticated requests.',
      ].join('\n'),
    );
    return;
  }

  const result = await fetchAndStoreOpenSkyStates(options);
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
        rate_limit: result.rate_limit,
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
