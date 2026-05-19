# Alpha A-5 API 契约 v1

## 1. 统一规则

- 前缀统一为 `/api/v1`
- 鉴权采用 `Authorization: Bearer <token>`
- 成功响应统一：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

- 失败响应统一：

```json
{
  "code": 40001,
  "message": "invalid credentials",
  "data": null
}
```

## 2. 用户与鉴权 API

### `POST /api/v1/auth/login`

用途：用户登录，返回 access token 和 refresh token。

请求体：

- `username: string`
- `password: string`

响应 `data`：

- `access_token: string`
- `refresh_token: string`
- `token_type: string`
- `expires_in: int`
- `user`

### `POST /api/v1/auth/refresh`

用途：使用 refresh token 刷新 access token。

请求体：

- `refresh_token: string`

响应 `data`：

- `access_token: string`
- `refresh_token: string`
- `token_type: string`
- `expires_in: int`

### `POST /api/v1/auth/logout`

用途：注销当前 refresh token。

请求体：

- `refresh_token: string`

响应 `data`：

- `revoked: boolean`

### `GET /api/v1/users/me`

用途：获取当前登录用户信息。

响应 `data`：

- `user_id`
- `username`
- `display_name`
- `role`
- `status`
- `last_login_at`

### `GET /api/v1/users`

用途：管理员分页查询用户列表。

查询参数：

- `page`
- `page_size`
- `role`
- `status`
- `keyword`

响应 `data`：

- `items`
- `total`
- `page`
- `page_size`

### `POST /api/v1/users`

用途：管理员创建用户。

请求体：

- `username`
- `password`
- `display_name`
- `role`
- `status`

### `PATCH /api/v1/users/{user_id}`

用途：管理员更新用户基础信息。

请求体可选字段：

- `display_name`
- `role`
- `status`
- `password`

## 3. VSP API

### `GET /api/v1/vsp/airports`

用途：查询机场基础信息。

查询参数：

- `icao_code`

### `GET /api/v1/vsp/waypoints`

用途：分页查询航点。

查询参数：

- `keyword`
- `type`
- `page`
- `page_size`

### `GET /api/v1/vsp/procedures`

用途：查询进离场程序。

查询参数：

- `airport_id`
- `procedure_type`
- `runway`
- `keyword`

### `GET /api/v1/vsp/airlines`

用途：查询航司映射。

查询参数：

- `keyword`
- `airline_code`

### `GET /api/v1/vsp/geojson/procedures/{procedure_id}`

用途：返回指定程序的 GeoJSON。

响应 `data`：

- `procedure_id`
- `procedure_name`
- `geojson`

## 4. 运维与中间件 API

### `GET /api/v1/system/queues`

用途：查看队列监控摘要。

响应 `data.items[*]`：

- `queue_name`
- `queue_length`
- `last_consumed_at`
- `last_failure_at`
- `last_dead_letter_at`
- `last_failure_message_id`
- `last_dead_letter_message_id`
- `failure_count`
- `dead_letter_count`

### `POST /api/v1/system/queues/publish`

用途：管理员向受支持队列直接发布一条标准消息，用于联调和运维验证。

请求体：

- `queue_name`
- `message`

请求体中的 `message` 必须符合统一消息外壳：

- `id`
- `type`
- `version`
- `producer`
- `timestamp`
- `trace_id`
- `payload`

### `GET /api/v1/system/consumers`

用途：查看当前受支持的 consumer 列表。

响应 `data[*]`：

- `queue_name`
- `consumer_name`
- `enabled`

### `POST /api/v1/system/consumers/run-once`

用途：管理员触发指定队列消费一次。

请求体：

- `queue_name`

### `GET /api/v1/system/events/failures`

用途：分页查询消费失败记录。

查询参数：

- `queue_name`
- `message_id`
- `page`
- `page_size`

### `GET /api/v1/system/events/failures/export`

用途：导出消费失败记录。

查询参数：

- `queue_name`
- `message_id`
- `format = jsonl | csv`

### `GET /api/v1/system/events/dead-letters`

用途：分页查询死信记录。

查询参数：

- `queue_name`
- `message_id`
- `page`
- `page_size`

### `GET /api/v1/system/events/dead-letters/export`

用途：导出死信记录。

查询参数：

- `queue_name`
- `message_id`
- `format = jsonl | csv`

### `GET /api/v1/system/logs`

用途：分页查询系统日志。

查询参数：

- `level`
- `source`
- `trace_id`
- `page`
- `page_size`

### `GET /api/v1/system/logs/export`

用途：导出系统日志。

查询参数：

- `level`
- `source`
- `trace_id`
- `format = jsonl | csv`

## 5. 协商型 API 入口

以下接口本次只冻结入口和最小字段，不冻结完整业务细节。

### `POST /api/v1/tracks/ingest`

最小请求体：

- `track_id`
- `timestamp`
- `location`
- `version`

说明：

- HTTP 入口会直接写入 `adsb_tracks`
- `track:ingest` consumer 也会按相同字段体系消费 Redis 消息并写入 `adsb_tracks`

### `POST /api/v1/audio/metadata`

最小请求体：

- `unique_id`
- `version`

### `POST /api/v1/asr/results`

最小请求体：

- `result_id`
- `unique_id`
- `transcript`
- `version`

### `GET /api/v1/annotations/load`

最小查询参数：

- `unique_id` 或 `task_id`

### `POST /api/v1/annotations/save`

最小请求体：

- `task_id`
- `annotator_id`
- `corrected_text`
- `version`

### `GET /api/v1/integration/audio`

用途：分页查询 `a2_voice_info`。

查询参数：

- `unique_id`
- `icao_code`
- `band`
- `start_time`
- `end_time`
- `page`
- `page_size`

### `GET /api/v1/integration/asr`

用途：分页查询 `asr_results`。

查询参数：

- `result_id`
- `unique_id`
- `engine`
- `page`
- `page_size`

### `GET /api/v1/integration/annotation-tasks`

用途：分页查询 `annotation_tasks`。

查询参数：

- `task_id`
- `unique_id`
- `status`
- `assignee_id`
- `page`
- `page_size`

### `GET /api/v1/integration/annotation-results`

用途：分页查询 `annotation_results`。

查询参数：

- `task_id`
- `annotation_id`
- `annotator_id`
- `page`
- `page_size`

### `GET /api/v1/integration/a2/realtime-tasks`

用途：分页查询 `a2_task_realtime_cfg`。

### `POST /api/v1/integration/a2/realtime-tasks`

用途：最小创建或更新实时采集任务配置。

### `GET /api/v1/integration/a2/download-tasks`

用途：分页查询 `a2_task_download_cfg`。

### `POST /api/v1/integration/a2/download-tasks`

用途：最小创建或更新历史下载任务配置。

### `GET /api/v1/integration/a2/system-config`

用途：查询 `a2_sys_base_cfg` 单行系统配置。

### `PUT /api/v1/integration/a2/system-config`

用途：更新 `a2_sys_base_cfg` 单行系统配置。

## 6. 当前 consumer 实现范围

当前已接入的 consumer：

- `track:ingest`
  - 校验并写入 `adsb_tracks`
- `audio:process`
  - 校验最小字段并写系统日志
- `annotation:notify`
  - 校验最小字段并写系统日志
- `system:log`
  - 直接写入 `system_logs`

## 7. 错误码建议

### 通用

- `40000` 请求参数错误
- `40001` 登录失败
- `40003` 无权限
- `40004` 资源不存在
- `40009` 请求冲突
- `50000` 服务内部错误

### 业务

- `41001` 用户已禁用
- `42001` VSP 记录不存在
- `43001` 队列不可用
- `43002` 消息消费失败
- `44001` 协商型数据版本不兼容
