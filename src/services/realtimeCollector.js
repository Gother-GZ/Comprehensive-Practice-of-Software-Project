const net = require('net');
const { db } = require('../db');
const { batchUpsertTracks } = require('./trackService');

const collectors = new Map();

function getRealtimeTaskConfig(taskId) {
  return db
    .prepare('SELECT * FROM a2_task_realtime_cfg WHERE task_id = ?')
    .get(taskId);
}

function setRealtimeTaskStatus(taskId, status) {
  db.prepare('UPDATE a2_task_realtime_cfg SET status = ? WHERE task_id = ?').run(
    status,
    taskId,
  );
}

function snapshotState(state) {
  return { ...state };
}

function startRealtimeTask(taskId) {
  const numericTaskId = Number(taskId);

  if (!Number.isInteger(numericTaskId)) {
    throw new Error('taskId must be an integer.');
  }

  if (collectors.has(numericTaskId)) {
    return snapshotState(collectors.get(numericTaskId).state);
  }

  const task = getRealtimeTaskConfig(numericTaskId);
  if (!task) {
    throw new Error('Realtime task config not found.');
  }

  if ((task.protocol || 'TCP').toUpperCase() !== 'TCP') {
    throw new Error('Prototype collector only supports TCP JSON Lines streams.');
  }

  const socket = new net.Socket();
  let buffer = '';

  const state = {
    task_id: numericTaskId,
    task_name: task.task_name,
    server_addr: task.server_addr,
    server_port: task.server_port,
    protocol: task.protocol,
    status: 'connecting',
    received_count: 0,
    error_count: 0,
    last_message_at: null,
    last_error: null,
  };

  collectors.set(numericTaskId, { socket, state });

  socket.setKeepAlive(true, (task.heart_beat || 10) * 1000);
  socket.setTimeout((task.timeout || 30) * 1000);

  socket.connect(task.server_port, task.server_addr, () => {
    state.status = 'running';
    setRealtimeTaskStatus(numericTaskId, 1);
  });

  socket.on('data', (chunk) => {
    buffer += chunk.toString('utf8');

    while (buffer.includes('\n')) {
      const newlineIndex = buffer.indexOf('\n');
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);

      if (!line) {
        continue;
      }

      try {
        const payload = JSON.parse(line);
        const items = Array.isArray(payload) ? payload : [payload];
        const saved = batchUpsertTracks(items, `task:${numericTaskId}`);
        state.received_count += saved.length;
        state.last_message_at = new Date().toISOString();
      } catch (error) {
        state.error_count += 1;
        state.last_error = error.message;
      }
    }
  });

  socket.on('timeout', () => {
    state.status = 'timeout';
    state.last_error = 'Socket timeout';
    setRealtimeTaskStatus(numericTaskId, -1);
    socket.destroy();
  });

  socket.on('error', (error) => {
    state.status = 'error';
    state.error_count += 1;
    state.last_error = error.message;
    setRealtimeTaskStatus(numericTaskId, -1);
  });

  socket.on('close', () => {
    const collector = collectors.get(numericTaskId);
    if (!collector || collector.socket !== socket) {
      return;
    }

    collectors.delete(numericTaskId);

    if (state.status !== 'error' && state.status !== 'timeout') {
      state.status = 'stopped';
      setRealtimeTaskStatus(numericTaskId, 0);
    }
  });

  return snapshotState(state);
}

function stopRealtimeTask(taskId) {
  const numericTaskId = Number(taskId);
  const collector = collectors.get(numericTaskId);

  if (!collector) {
    return null;
  }

  collector.state.status = 'stopped';
  collector.socket.end();
  collector.socket.destroy();
  collectors.delete(numericTaskId);
  setRealtimeTaskStatus(numericTaskId, 0);

  return snapshotState(collector.state);
}

function getRealtimeTaskStatus(taskId) {
  const collector = collectors.get(Number(taskId));
  return collector ? snapshotState(collector.state) : null;
}

function listRealtimeTaskStatus() {
  return Array.from(collectors.values()).map(({ state }) => snapshotState(state));
}

module.exports = {
  startRealtimeTask,
  stopRealtimeTask,
  getRealtimeTaskStatus,
  listRealtimeTaskStatus,
};
