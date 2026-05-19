# Alpha A-5 今日设计基线

## 1. 今日范围

本次仅冻结 A-5 当前可以主导或先行冻结的设计，不实现 A-1、A-2、A-3、A-4 的最终业务逻辑。

今日交付目标：

- 用户与鉴权设计
- A-5 主控数据库 canonical schema
- 协商型业务表的最小兼容结构
- A-5 主控 API v1 契约
- Redis 消息中间件 v1 契约
- 模块对接矩阵

## 2. 核心原则

- 数据库第一落地目标为 SQLite
- 所有时间统一为 UTC ISO 8601 文本
- 所有 JSON 字段第一版统一为 `TEXT`
- 所有地理字段第一版统一为 `lat` / `lng`
- API 统一采用 `/api/v1/...`
- 响应统一采用 `code/message/data`
- Redis 统一使用稳定消息外壳，业务 `payload` 可迭代

## 3. 今日冻结的主控域

以下内容由 A-5 完全主导，可直接作为第一版基线：

- 用户与鉴权
- VSP/AIP 支撑数据
- 消息中间件治理
- 审计、日志、死信、系统配置类支撑表

## 4. 今日冻结的协商域

以下内容仅冻结“最小兼容结构”，不冻结完整业务语义：

- `adsb_tracks`
- `a2_voice_info`
- `asr_results`
- `annotation_tasks`
- `annotation_results`

处理原则：

- 只保留当前联调必要字段
- 不在今天写死状态机和完整流程
- 预留 `raw_payload`、`extra_json`、`version` 等扩展位

## 5. 用户与鉴权方案

采用“单表起步 + 后续可平滑拆分”的轻量方案。

### 5.1 角色模型

- `admin`
- `annotator`

### 5.2 主表

- `users`

关键字段：

- `user_id`
- `username`
- `password_hash`
- `display_name`
- `role`
- `status`
- `created_at`
- `updated_at`
- `last_login_at`

### 5.3 支撑表

- `user_login_audit`
- `user_refresh_tokens`

### 5.4 扩展路径

若后续仍只有两角色，不拆 RBAC。
若后续出现接口级、菜单级、数据域级权限，再新增：

- `roles`
- `permissions`
- `user_roles`
- `role_permissions`

## 6. 数据库分层策略

### 6.1 主控表

- `users`
- `user_login_audit`
- `user_refresh_tokens`
- `vsp_airports`
- `vsp_waypoints`
- `vsp_procedures`
- `vsp_airlines`
- `event_consume_failures`
- `event_dead_letters`
- `system_logs`
- `system_configs`

### 6.2 兼容接入表

- `adsb_tracks`
- `a2_voice_info`
- `asr_results`
- `annotation_tasks`
- `annotation_results`

### 6.3 设计取舍

- 不依赖 `POINT`
- 不依赖 `JSONB`
- 不依赖 `NOW()`
- 不依赖 SpatiaLite 才能运行

## 7. API 基线

### 7.1 可直接定稿

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users/me`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `GET /api/v1/vsp/airports`
- `GET /api/v1/vsp/waypoints`
- `GET /api/v1/vsp/procedures`
- `GET /api/v1/vsp/airlines`
- `GET /api/v1/vsp/geojson/procedures/{procedure_id}`
- `GET /api/v1/system/queues`
- `GET /api/v1/system/events/failures`
- `GET /api/v1/system/logs`

### 7.2 仅冻结入口

- `POST /api/v1/tracks/ingest`
- `POST /api/v1/audio/metadata`
- `POST /api/v1/asr/results`
- `GET /api/v1/annotations/load`
- `POST /api/v1/annotations/save`

## 8. Redis 中间件基线

### 8.1 队列名

- `track:ingest`
- `audio:process`
- `annotation:notify`
- `system:log`

### 8.2 消息外壳

- `id`
- `type`
- `version`
- `producer`
- `timestamp`
- `trace_id`
- `payload`

### 8.3 失败治理

- 消费失败先写 `event_consume_failures`
- 达到阈值后写 `event_dead_letters`
- 监控暴露队列长度、失败次数、最近消费时间、死信数量

## 9. 后续编码顺序

1. 先按 `db/schema_v1.sql` 建立 SQLite 基线
2. 再按 API 契约实现 FastAPI 路由与 Pydantic 模型
3. 再补 Redis producer / consumer 封装
4. 再做模拟数据联调

