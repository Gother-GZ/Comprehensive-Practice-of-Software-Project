# Alpha A-5 Redis 消息契约 v1

## 1. 目标

第一版采用 Redis List，目标不是实现最复杂的消息系统，而是先得到：

- 统一队列命名
- 统一消息外壳
- 清晰的失败治理策略
- 便于联调和后续替换的版本化机制

## 2. 队列定义

| 队列名 | 生产方 | 消费方 | 用途 |
| --- | --- | --- | --- |
| `track:ingest` | A-1 / 模拟端 | A-5 | 航迹接入 |
| `audio:process` | A-2 / 调度器 | A-5 / A-3 | 音频处理触发 |
| `annotation:notify` | A-5 | A-4 / 通知侧 | 标注事件通知 |
| `system:log` | A-5 各子模块 | A-5 | 系统事件记录 |

## 3. 消息外壳

所有消息统一采用以下结构：

```json
{
  "id": "evt_20260413_000001",
  "type": "track.ingest",
  "version": "v1",
  "producer": "a1-tracker",
  "timestamp": "2026-04-13T10:00:00.000Z",
  "trace_id": "trace-123",
  "payload": {}
}
```

字段说明：

- `id`：消息唯一 ID
- `type`：事件类型
- `version`：事件版本
- `producer`：生产方标识
- `timestamp`：消息创建时间
- `trace_id`：链路追踪 ID
- `payload`：业务内容

## 4. 事件类型建议

- `track.ingest`
- `audio.metadata.created`
- `audio.process.requested`
- `asr.result.created`
- `annotation.saved`
- `system.log.created`

## 5. payload 最小字段

### `track.ingest`

- `track_id`
- `timestamp`
- `location`

### `audio.process.requested`

- `unique_id`
- `file_path`
- `icao_code`
- `original_time`

### `asr.result.created`

- `result_id`
- `unique_id`
- `engine`

### `annotation.saved`

- `annotation_id`
- `task_id`
- `annotator_id`

## 6. 消费与重试策略

- 生产者只负责入队，不感知消费细节
- 消费者处理失败时：
  - 首先记录 `event_consume_failures`
  - 增加 `retry_count`
  - 未达阈值时可重新入队
  - 达到阈值后写入 `event_dead_letters`

建议默认阈值：

- `max_retry_count = 3`

当前 A-5 内置 consumer 行为：

- `track:ingest`
  - 使用与 `POST /api/v1/tracks/ingest` 相同的字段体系写入 `adsb_tracks`
- `audio:process`
  - 校验 `unique_id` 与 `file_path` 后写系统日志
- `annotation:notify`
  - 校验 `task_id` 后写系统日志
- `system:log`
  - 按 `payload.message / payload.level / payload.source / payload.context` 写入 `system_logs`

## 7. 幂等建议

第一版按以下规则实现幂等：

- 消息主键以 `message_id` 为唯一幂等键
- 业务写入可结合 `track_id`、`unique_id`、`result_id` 做二次去重
- 重复消息允许被识别并安全忽略

## 8. 监控指标

第一版至少暴露以下指标：

- 队列长度
- 最近消费时间
- 消费失败次数
- 死信数量
- 最近失败消息 ID
- 最近死信消息 ID

当前运维接口：

- `GET /api/v1/system/queues`
- `POST /api/v1/system/queues/publish`
- `GET /api/v1/system/consumers`
- `POST /api/v1/system/consumers/run-once`
- `GET /api/v1/system/events/failures`
- `GET /api/v1/system/events/failures/export`
- `GET /api/v1/system/events/dead-letters`
- `GET /api/v1/system/events/dead-letters/export`
- `GET /api/v1/system/logs`
- `GET /api/v1/system/logs/export`

## 9. 升级路径

若后续需要更强确认机制，可以从 Redis List 升级到 Redis Streams，但升级时保持以下不变：

- 队列语义
- 消息外壳字段
- 事件版本机制
