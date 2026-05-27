const app = require('./app');
const { dbFile } = require('./db');

const port = Number(process.env.PORT || 3001);

app.listen(port, () => {
  console.log(`ADS-B interface listening on http://localhost:${port}`);
  console.log(`SQLite database: ${dbFile}`);
});