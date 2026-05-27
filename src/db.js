const fs = require('fs');
const path = require('path');
const Database = require('better-sqlite3');

const dataDir = path.join(__dirname, '..', 'data');
fs.mkdirSync(dataDir, { recursive: true });

const dbFile = process.env.DB_FILE || path.join(dataDir, 'adsb-interface.db');
const schemaFile =
  process.env.DB_SCHEMA_FILE ||
  (fs.existsSync(path.join(__dirname, '..', 'Alpha', 'db', 'schema_v1.sql'))
    ? path.join(__dirname, '..', 'Alpha', 'db', 'schema_v1.sql')
    : path.join(__dirname, 'schema.sql'));

const db = new Database(dbFile);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
db.exec(fs.readFileSync(schemaFile, 'utf8'));

function ensureColumns(table, columns) {
  const existing = new Set(
    db.prepare(`PRAGMA table_info(${table})`)
      .all()
      .map((column) => column.name),
  );

  for (const [name, definition] of Object.entries(columns)) {
    if (!existing.has(name)) {
      db.prepare(`ALTER TABLE ${table} ADD COLUMN ${name} ${definition}`).run();
    }
  }
}

ensureColumns('adsb_tracks', {
  source: 'TEXT',
  raw_payload: 'TEXT',
});

function omitUndefined(source = {}) {
  return Object.fromEntries(
    Object.entries(source).filter(([, value]) => value !== undefined),
  );
}

function insertRecord(table, payload = {}) {
  const data = omitUndefined(payload);
  const keys = Object.keys(data);
  const statement = keys.length
    ? db.prepare(
        `INSERT INTO ${table} (${keys.join(', ')}) VALUES (${keys
          .map((key) => `@${key}`)
          .join(', ')})`,
      )
    : db.prepare(`INSERT INTO ${table} DEFAULT VALUES`);

  return statement.run(data);
}

function updateRecord(table, idField, idValue, payload = {}) {
  const data = omitUndefined(payload);
  const keys = Object.keys(data);

  if (!keys.length) {
    return { changes: 0 };
  }

  const setClause = keys.map((key) => `${key} = @${key}`).join(', ');
  const statement = db.prepare(
    `UPDATE ${table} SET ${setClause} WHERE ${idField} = @__id`,
  );

  return statement.run({ ...data, __id: idValue });
}

function getRecord(table, idField, idValue) {
  return db.prepare(`SELECT * FROM ${table} WHERE ${idField} = ?`).get(idValue);
}

function deleteRecord(table, idField, idValue) {
  return db.prepare(`DELETE FROM ${table} WHERE ${idField} = ?`).run(idValue);
}

function listRecords(table, filters = {}, options = {}) {
  const data = omitUndefined(filters);
  const clauses = Object.keys(data).map((key) => `${key} = @${key}`);
  const whereSql = clauses.length ? ` WHERE ${clauses.join(' AND ')}` : '';
  const limit = Number(options.limit || 100);
  const safeLimit =
    Number.isFinite(limit) && limit > 0 ? Math.min(limit, 500) : 100;
  const orderBy = options.orderBy || 'created_at DESC';
  const sql = `SELECT * FROM ${table}${whereSql} ORDER BY ${orderBy} LIMIT ${safeLimit}`;

  return db.prepare(sql).all(data);
}

module.exports = {
  db,
  dbFile,
  insertRecord,
  updateRecord,
  getRecord,
  deleteRecord,
  listRecords,
  omitUndefined,
};
