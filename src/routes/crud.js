const express = require('express');
const { randomUUID } = require('crypto');
const {
  insertRecord,
  updateRecord,
  getRecord,
  deleteRecord,
  listRecords,
} = require('../db');

function parseNumber(value, field, integer = false) {
  if (value === null || value === '') {
    return null;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${field} must be a valid number.`);
  }

  return integer ? Math.trunc(parsed) : parsed;
}

function normalizeJson(value) {
  if (value === null || value === undefined) {
    return null;
  }

  return typeof value === 'string' ? value : JSON.stringify(value);
}

function applyDefaults(payload, defaults) {
  if (!defaults) {
    return payload;
  }

  const resolved = typeof defaults === 'function' ? defaults(payload) : defaults;

  for (const [key, value] of Object.entries(resolved)) {
    if (payload[key] === undefined) {
      payload[key] = typeof value === 'function' ? value(payload) : value;
    }
  }

  return payload;
}

function sanitizePayload(body, config, isCreate) {
  const source =
    body && typeof body === 'object' && !Array.isArray(body) ? body : {};
  const payload = {};

  for (const field of config.fields || []) {
    if (source[field] !== undefined) {
      payload[field] = source[field];
      continue;
    }

    for (const alias of config.aliases?.[field] || []) {
      if (source[alias] !== undefined) {
        payload[field] = source[alias];
        break;
      }
    }
  }

  if (isCreate && config.autoId && !payload[config.idField]) {
    payload[config.idField] = randomUUID();
  }

  applyDefaults(payload, isCreate ? config.createDefaults : config.updateDefaults);

  for (const field of config.integerFields || []) {
    if (payload[field] !== undefined) {
      payload[field] = parseNumber(payload[field], field, true);
    }
  }

  for (const field of config.floatFields || []) {
    if (payload[field] !== undefined) {
      payload[field] = parseNumber(payload[field], field, false);
    }
  }

  for (const field of config.jsonFields || []) {
    if (payload[field] !== undefined) {
      payload[field] = normalizeJson(payload[field]);
    }
  }

  if (!isCreate && config.touchUpdatedAt) {
    payload[config.touchUpdatedAt] = new Date().toISOString();
  }

  for (const field of config.requiredOnCreate || []) {
    if (
      isCreate &&
      (payload[field] === undefined || payload[field] === null || payload[field] === '')
    ) {
      throw new Error(`${field} is required.`);
    }
  }

  if (typeof config.transform === 'function') {
    return config.transform(payload, { isCreate, source });
  }

  return payload;
}

function buildCrudRouter(config) {
  const router = express.Router();

  router.get('/', (req, res, next) => {
    try {
      const filters = {};

      for (const field of config.filterableFields || []) {
        if (req.query[field] !== undefined && req.query[field] !== '') {
          filters[field] = req.query[field];
        }
      }

      const limit = req.query.limit || config.defaultLimit || 100;
      const data = listRecords(config.table, filters, {
        orderBy: config.defaultOrderBy,
        limit,
      });

      res.json({ data, count: data.length });
    } catch (error) {
      next(error);
    }
  });

  router.get(`/:${config.idField}`, (req, res, next) => {
    try {
      const record = getRecord(
        config.table,
        config.idField,
        req.params[config.idField],
      );

      if (!record) {
        return res.status(404).json({ error: `${config.table} record not found.` });
      }

      return res.json({ data: record });
    } catch (error) {
      return next(error);
    }
  });

  router.post('/', (req, res, next) => {
    try {
      const payload = sanitizePayload(req.body, config, true);
      const result = insertRecord(config.table, payload);
      const recordId = payload[config.idField] || result.lastInsertRowid;
      const record = getRecord(config.table, config.idField, recordId);

      res.status(201).json({ data: record });
    } catch (error) {
      next(error);
    }
  });

  router.put(`/:${config.idField}`, (req, res, next) => {
    try {
      const recordId = req.params[config.idField];
      const payload = sanitizePayload(req.body, config, false);
      const result = updateRecord(config.table, config.idField, recordId, payload);

      if (!result.changes) {
        return res.status(404).json({ error: `${config.table} record not found.` });
      }

      return res.json({
        data: getRecord(config.table, config.idField, recordId),
      });
    } catch (error) {
      return next(error);
    }
  });

  router.delete(`/:${config.idField}`, (req, res, next) => {
    try {
      const result = deleteRecord(
        config.table,
        config.idField,
        req.params[config.idField],
      );

      if (!result.changes) {
        return res.status(404).json({ error: `${config.table} record not found.` });
      }

      return res.status(204).send();
    } catch (error) {
      return next(error);
    }
  });

  return router;
}

module.exports = {
  buildCrudRouter,
};
