const app = require('../src/app');

async function run() {
  const server = app.listen(0);

  try {
    await new Promise((resolve) => server.once('listening', resolve));
    const { port } = server.address();
    const baseUrl = `http://127.0.0.1:${port}`;

    const health = await fetch(`${baseUrl}/health`).then((res) => res.json());
    const created = await fetch(`${baseUrl}/api/adsb/tracks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        callsign: 'CCA123',
        latitude: 39.9042,
        longitude: 116.4074,
        altitude: 10500,
        ground_speed: 780,
        heading: 90,
        timestamp: '2026-04-06T12:00:00Z',
      }),
    }).then((res) => res.json());

    const listed = await fetch(
      `${baseUrl}/api/adsb/tracks?callsign=CCA123&limit=5`,
    ).then((res) => res.json());

    console.log(
      JSON.stringify(
        {
          health,
          created,
          listed,
        },
        null,
        2,
      ),
    );
  } finally {
    server.close();
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
