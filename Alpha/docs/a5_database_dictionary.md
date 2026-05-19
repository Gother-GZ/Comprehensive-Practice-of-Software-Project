# Alpha A-5 数据库字段字典 v1

## 1. 说明

本字典分为两类：

- A-5 主控表：可直接作为第一版实现基线
- 协商接入表：只定义最小兼容字段，后续按联调再扩展

所有字段命名统一采用 snake_case。

## 2. A-5 主控表

### `users`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `user_id` | TEXT | PK | 用户唯一标识 |
| `username` | TEXT | UNIQUE NOT NULL | 登录名 |
| `password_hash` | TEXT | NOT NULL | 密码哈希 |
| `display_name` | TEXT | NOT NULL | 显示名称 |
| `role` | TEXT | NOT NULL | `admin` / `annotator` |
| `status` | TEXT | NOT NULL | `active` / `inactive` / `disabled` |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |
| `last_login_at` | TEXT | NULL | 最近登录时间 |

### `user_login_audit`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `audit_id` | TEXT | PK | 审计记录 ID |
| `user_id` | TEXT | FK NULL | 用户 ID，失败登录可为空 |
| `username` | TEXT | NOT NULL | 登录时提交的用户名 |
| `login_result` | TEXT | NOT NULL | `success` / `failure` |
| `failure_reason` | TEXT | NULL | 失败原因 |
| `ip_address` | TEXT | NULL | 来源 IP |
| `user_agent` | TEXT | NULL | 客户端 UA |
| `created_at` | TEXT | NOT NULL | 记录时间 |

### `user_refresh_tokens`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `token_id` | TEXT | PK | refresh token 记录 ID |
| `user_id` | TEXT | FK NOT NULL | 所属用户 |
| `token_hash` | TEXT | NOT NULL | refresh token 哈希 |
| `issued_at` | TEXT | NOT NULL | 签发时间 |
| `expires_at` | TEXT | NOT NULL | 过期时间 |
| `revoked_at` | TEXT | NULL | 撤销时间 |
| `created_at` | TEXT | NOT NULL | 创建时间 |

### `vsp_airports`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `airport_id` | TEXT | PK | 机场记录 ID |
| `icao_code` | TEXT | UNIQUE NOT NULL | ICAO 代码 |
| `iata_code` | TEXT | NULL | IATA 代码 |
| `airport_name` | TEXT | NOT NULL | 机场名称 |
| `city_name` | TEXT | NULL | 城市名 |
| `country_name` | TEXT | NULL | 国家或地区 |
| `lat` | REAL | NOT NULL | 纬度 |
| `lng` | REAL | NOT NULL | 经度 |
| `elevation_ft` | INTEGER | NULL | 标高 |
| `extra_json` | TEXT | NULL | 扩展信息 |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

### `vsp_waypoints`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `waypoint_id` | TEXT | PK | 航点记录 ID |
| `name` | TEXT | UNIQUE NOT NULL | 航点名称 |
| `type` | TEXT | NULL | fix / vor / ndb / airport |
| `lat` | REAL | NOT NULL | 纬度 |
| `lng` | REAL | NOT NULL | 经度 |
| `description` | TEXT | NULL | 说明 |
| `extra_json` | TEXT | NULL | 扩展信息 |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

### `vsp_procedures`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `procedure_id` | TEXT | PK | 程序 ID |
| `airport_id` | TEXT | FK NOT NULL | 关联机场 |
| `procedure_code` | TEXT | NOT NULL | 程序编号 |
| `procedure_name` | TEXT | NOT NULL | 程序名称 |
| `procedure_type` | TEXT | NOT NULL | sid / star / approach / taxi |
| `runway` | TEXT | NULL | 关联跑道 |
| `waypoint_sequence_json` | TEXT | NULL | 航点序列 JSON |
| `path_geojson` | TEXT | NULL | GeoJSON 路径 |
| `extra_json` | TEXT | NULL | 扩展信息 |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

### `vsp_airlines`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `airline_id` | TEXT | PK | 航司记录 ID |
| `airline_code` | TEXT | UNIQUE NOT NULL | 航司代码 |
| `airline_name` | TEXT | NOT NULL | 航司全称 |
| `airline_short_name` | TEXT | NULL | 航司简称 |
| `country_name` | TEXT | NULL | 国家或地区 |
| `extra_json` | TEXT | NULL | 扩展信息 |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

### `event_consume_failures`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `failure_id` | TEXT | PK | 失败记录 ID |
| `queue_name` | TEXT | NOT NULL | 队列名 |
| `message_id` | TEXT | NOT NULL | 消息 ID |
| `event_type` | TEXT | NOT NULL | 事件类型 |
| `consumer_name` | TEXT | NOT NULL | 消费者名称 |
| `retry_count` | INTEGER | NOT NULL | 当前重试次数 |
| `error_message` | TEXT | NOT NULL | 错误摘要 |
| `payload_json` | TEXT | NOT NULL | 原始消息 |
| `failed_at` | TEXT | NOT NULL | 失败时间 |

### `event_dead_letters`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `dead_letter_id` | TEXT | PK | 死信记录 ID |
| `queue_name` | TEXT | NOT NULL | 来源队列 |
| `message_id` | TEXT | NOT NULL | 消息 ID |
| `event_type` | TEXT | NOT NULL | 事件类型 |
| `payload_json` | TEXT | NOT NULL | 原始消息 |
| `last_error_message` | TEXT | NOT NULL | 最后一次错误 |
| `retry_count` | INTEGER | NOT NULL | 总重试次数 |
| `created_at` | TEXT | NOT NULL | 写入死信时间 |

### `system_logs`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `log_id` | TEXT | PK | 日志 ID |
| `log_level` | TEXT | NOT NULL | info / warning / error |
| `source` | TEXT | NOT NULL | 来源模块 |
| `message` | TEXT | NOT NULL | 日志内容 |
| `trace_id` | TEXT | NULL | 链路 ID |
| `context_json` | TEXT | NULL | 上下文 JSON |
| `created_at` | TEXT | NOT NULL | 记录时间 |

### `system_configs`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `config_key` | TEXT | PK | 配置键 |
| `config_value` | TEXT | NOT NULL | 配置值 |
| `description` | TEXT | NULL | 说明 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

## 3. 协商接入表

### `adsb_tracks`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `track_id` | TEXT | PK | 航迹 ID |
| `callsign` | TEXT | NULL | 航班呼号 |
| `aircraft_hex` | TEXT | NULL | 机体识别码 |
| `timestamp` | TEXT | NOT NULL | 轨迹时间 |
| `lat` | REAL | NOT NULL | 纬度 |
| `lng` | REAL | NOT NULL | 经度 |
| `altitude_ft` | INTEGER | NULL | 高度 |
| `ground_speed_kt` | REAL | NULL | 地速 |
| `heading_deg` | REAL | NULL | 航向 |
| `source` | TEXT | NULL | 数据来源 |
| `raw_payload` | TEXT | NULL | 原始载荷 |
| `created_at` | TEXT | NOT NULL | 创建时间 |

### `a2_voice_info`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `voice_id` | TEXT | PK | 语音 ID |
| `icao_code` | TEXT | NOT NULL | 机场代码 |
| `band` | TEXT | NULL | 频段 |
| `recorded_at` | TEXT | NOT NULL | 录制时间 |
| `file_path` | TEXT | NOT NULL | 文件路径 |
| `file_name` | TEXT | NOT NULL | 文件名 |
| `duration_ms` | INTEGER | NULL | 时长 |
| `file_size_bytes` | INTEGER | NULL | 文件大小 |
| `source` | TEXT | NULL | 来源 |
| `raw_payload` | TEXT | NULL | 原始载荷 |
| `created_at` | TEXT | NOT NULL | 创建时间 |

### `asr_results`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `result_id` | TEXT | PK | 结果 ID |
| `voice_id` | TEXT | FK NOT NULL | 语音 ID |
| `engine` | TEXT | NOT NULL | 引擎标识 |
| `engine_version` | TEXT | NULL | 引擎版本 |
| `transcript` | TEXT | NOT NULL | 识别文本 |
| `vad_segments_json` | TEXT | NULL | VAD 片段 JSON |
| `confidence` | REAL | NULL | 置信度 |
| `raw_payload` | TEXT | NULL | 原始结果 |
| `created_at` | TEXT | NOT NULL | 创建时间 |

### `annotation_tasks`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `task_id` | TEXT | PK | 标注任务 ID |
| `voice_id` | TEXT | FK NOT NULL | 语音 ID |
| `result_id` | TEXT | FK NULL | ASR 结果 ID |
| `assignee_user_id` | TEXT | FK NULL | 分配用户 |
| `status` | TEXT | NOT NULL | 当前状态 |
| `priority` | INTEGER | NULL | 优先级 |
| `extra_json` | TEXT | NULL | 扩展字段 |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

### `annotation_results`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `annotation_id` | TEXT | PK | 标注结果 ID |
| `task_id` | TEXT | FK NOT NULL | 任务 ID |
| `annotator_user_id` | TEXT | FK NOT NULL | 标注用户 |
| `corrected_text` | TEXT | NOT NULL | 修正文本 |
| `timestamp_corrections_json` | TEXT | NULL | 时间修正 JSON |
| `annotations_json` | TEXT | NULL | 标注附加信息 JSON |
| `created_at` | TEXT | NOT NULL | 创建时间 |
| `updated_at` | TEXT | NOT NULL | 更新时间 |

## 4. 暂不冻结的对象

以下对象今天不进入正式 schema：

- `a2_task_realtime_cfg`
- `a2_task_download_cfg`
- 完整 RBAC 表
- SpatiaLite 专属空间表

原因是当前仍明显依赖 A-2 或后续权限细化策略。

