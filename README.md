# ADS-B Interface Prototype

这是一个 Node.js 原型项目，用来演示 ADS-B 航迹数据接入、航线生成、语音与航迹关联、VSP 基础数据管理等接口能力。

项目当前重点能力：

- 写入、批量写入、查询 ADS-B 航迹点。
- 从公开数据源实时拉取 ADS-B 飞机状态。
- 基于实时 ADS-B 采样点生成航线 GeoJSON。
- 支持严格实时模式 `live_only`，只使用本次公网返回，不读取或写入本地航线历史。
- 支持后台定时爬取航线。
- 支持语音信息、ASR、标注任务、VSP 基础数据的 CRUD 接口。

## 重要说明

这里的“航线爬取”指的是：

1. 从 Airplanes.live 或 OpenSky 实时获取飞机状态点。
2. 将同一航班号或机体编号的点按时间聚合。
3. 生成一条已飞航迹折线，也就是 GeoJSON `LineString`。

它不是航空公司提交的计划航路，也不保证包含起飞机场、降落机场、计划航路点。公开 ADS-B 状态接口通常只提供位置、高度、速度、航向、呼号等实时状态。

## 数据模式

项目有两种工作方式：

| 模式 | 是否联网 | 是否读本地历史 | 是否写入本地库 | 用途 |
| --- | --- | --- | --- | --- |
| 普通爬取 | 是 | 会利用已存航迹点补全折线 | 是 | 正常采集、保存、查询 |
| `live_only` | 是 | 否 | 否 | 证明数据来自本次公网实时返回 |
| 查询接口 | 否 | 是 | 否 | 查询已保存的本地结果 |

默认数据库是 SQLite：

```text
data/adsb-interface.db
```

核心表：

- `adsb_tracks`：保存 ADS-B 航迹点。
- `adsb_routes`：保存由航迹点聚合出的航线 GeoJSON。

## 启动

```bash
npm install
npm start
```

服务默认运行在：

```text
http://localhost:3000
```

常用检查：

```bash
npm run check
npm run smoke
```

## 真实实时爬取验证

如果你想证明不是拿本地数据冒充，使用 `live_only`。

命令行方式：

```bash
node scripts/crawl-routes.js --provider=airplanes-live --preset=switzerland --limit=2 --live-only
```

API 方式：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/routes/crawl ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\":\"airplanes-live\",\"preset\":\"switzerland\",\"limit\":2,\"live_only\":true}"
```

返回中重点看这些字段：

```json
{
  "live_only": true,
  "fetch": {
    "request_url": "https://api.airplanes.live/v2/point/47/8/120",
    "response_time_iso": "2026-05-31T10:10:55.001Z",
    "fetched_count": 236,
    "saved_count": 0
  },
  "route_count": 1
}
```

含义：

- `request_url` 是真实公网请求地址。
- `response_time_iso` 是本次公网响应时间。
- `fetched_count` 是本次公网返回数量。
- `saved_count: 0` 表示没有写入本地库。
- `live_only: true` 表示没有读取本地航线历史。

## 航线爬取

### 普通爬取并保存

普通模式会联网获取实时 ADS-B 点，写入 `adsb_tracks`，再生成或更新 `adsb_routes`。

```bash
npm run crawl:routes -- airplanes-live switzerland 20
```

等价 API：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/routes/crawl ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\":\"airplanes-live\",\"preset\":\"switzerland\",\"limit\":20}"
```

### 查询已保存航线

```bash
curl.exe "http://localhost:3000/api/adsb/routes?provider=airplanes-live&limit=20"
```

查询某条航线详情：

```bash
curl.exe "http://localhost:3000/api/adsb/routes/{routeId}"
```

详情里的 `path_geojson` 可以直接给地图前端使用。

### 从已有航迹点重建航线

如果本地已经有 `adsb_tracks`，可以重新聚合生成航线：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/routes/rebuild ^
  -H "Content-Type: application/json" ^
  -d "{\"source\":\"airplanes.live:v2/point\",\"limit\":5000}"
```

按呼号重建：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/routes/rebuild ^
  -H "Content-Type: application/json" ^
  -d "{\"callsign\":\"SWR4WG\",\"limit\":5000}"
```

### 后台定时爬取

启动一个后台任务，每隔一段时间拉取一次公开数据源并更新本地航线：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/routes/crawl-tasks/start ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\":\"airplanes-live\",\"preset\":\"hongkong\",\"limit\":100,\"interval_seconds\":30}"
```

查看任务状态：

```bash
curl.exe "http://localhost:3000/api/adsb/routes/crawl-tasks/status"
```

停止任务：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/routes/crawl-tasks/{taskId}/stop
```

## ADS-B 状态点拉取

### Airplanes.live

Airplanes.live 返回已经解码的飞机状态 JSON，项目会保留高度英尺、速度节、航向角等字段。

命令行：

```bash
npm run fetch:airplanes -- switzerland 20
```

API：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/sources/airplanes-live/fetch ^
  -H "Content-Type: application/json" ^
  -d "{\"preset\":\"switzerland\",\"limit\":20}"
```

也可以指定中心点和半径，半径单位是 nautical miles：

```bash
node scripts/fetch-airplanes-live.js --lat=47 --lon=8 --radius=120 --limit=20
```

### OpenSky

OpenSky `/states/all` 返回状态向量，项目会转换字段并保存原始 payload。

命令行：

```bash
node scripts/fetch-opensky.js --preset=switzerland --limit=20
```

API：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/sources/opensky/fetch ^
  -H "Content-Type: application/json" ^
  -d "{\"preset\":\"switzerland\",\"limit\":20}"
```

OpenSky 可以匿名调用，但额度有限。正式使用建议配置：

```text
OPENSKY_CLIENT_ID
OPENSKY_CLIENT_SECRET
```

## 手动写入和查询航迹点

写入单条 ADS-B 航迹：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/tracks ^
  -H "Content-Type: application/json" ^
  -d "{\"callsign\":\"CCA123\",\"latitude\":39.9042,\"longitude\":116.4074,\"altitude\":10500,\"ground_speed\":780,\"heading\":90,\"timestamp\":\"2026-04-06T12:00:00Z\"}"
```

批量写入：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/tracks/batch ^
  -H "Content-Type: application/json" ^
  -d "{\"items\":[{\"callsign\":\"CCA123\",\"latitude\":39.90,\"longitude\":116.40,\"timestamp\":\"2026-04-06T12:00:00Z\"},{\"callsign\":\"CES456\",\"latitude\":31.23,\"longitude\":121.47,\"timestamp\":\"2026-04-06T12:00:10Z\"}]}"
```

查询航迹：

```bash
curl.exe "http://localhost:3000/api/adsb/tracks?callsign=CCA123&limit=100"
```

按时间范围查询：

```bash
curl.exe "http://localhost:3000/api/adsb/tracks?start_time=2026-04-06T00:00:00Z&end_time=2026-04-06T23:59:59Z&limit=100"
```

## TCP 实时接收

项目还支持从上游 TCP 服务接收 JSON Lines 格式的实时航迹流。

创建任务：

```bash
curl.exe -X POST http://localhost:3000/api/tasks/realtime ^
  -H "Content-Type: application/json" ^
  -d "{\"task_name\":\"beijing-feed\",\"server_addr\":\"127.0.0.1\",\"server_port\":9001,\"protocol\":\"TCP\",\"timeout\":30,\"heart_beat\":10}"
```

启动任务：

```bash
curl.exe -X POST http://localhost:3000/api/adsb/realtime-tasks/1/start
```

上游推送格式示例：

```json
{"track_id":"t-1","callsign":"CCA123","latitude":39.90,"longitude":116.40,"altitude":9800,"timestamp":"2026-04-06T12:00:00Z"}
{"track_id":"t-2","callsign":"CES456","latitude":31.23,"longitude":121.47,"altitude":11200,"timestamp":"2026-04-06T12:00:05Z"}
```

## 其他业务接口

语音信息：

```bash
curl.exe -X POST http://localhost:3000/api/voice-info ^
  -H "Content-Type: application/json" ^
  -d "{\"icao_code\":\"ZBAA\",\"band\":\"VHF\",\"file_path\":\"/atc/a2/data/20260406/001.wav\",\"file_name\":\"001.wav\",\"file_size\":204800,\"data_type\":\"voice\"}"
```

建立语音和航迹关联：

```bash
curl.exe -X POST http://localhost:3000/api/voice-track-rel ^
  -H "Content-Type: application/json" ^
  -d "{\"unique_id\":\"voice-uuid\",\"track_id\":\"track-uuid\"}"
```

语音与航迹融合查询：

```bash
curl.exe "http://localhost:3000/api/adsb/fusion/voice-track?callsign=CCA123&limit=20"
```

还有这些通用 CRUD 接口：

- `GET /api/voice-info`
- `GET /api/tasks/realtime`
- `GET /api/tasks/download`
- `GET /api/asr-results`
- `GET /api/users`
- `GET /api/annotation/tasks`
- `GET /api/annotation/results`
- `GET /api/vsp/airports`
- `GET /api/vsp/waypoints`
- `GET /api/vsp/procedures`
- `GET /api/vsp/airlines`
- `GET /api/vsp/runways`
- `GET /api/vsp/frequencies`
- `GET /api/vsp/navaids`

## 常用测试命令

语法检查：

```bash
npm run check
```

基础接口 smoke test：

```bash
npm run smoke
```

实时公网验证，不读写本地航线历史：

```bash
node scripts/crawl-routes.js --provider=airplanes-live --preset=switzerland --limit=2 --live-only
```

查看本地数据库当前数量：

```bash
node -e "const {db}=require('./src/db'); console.log({tracks: db.prepare('select count(*) as n from adsb_tracks').get().n, routes: db.prepare('select count(*) as n from adsb_routes').get().n})"
```

## 目录结构

```text
src/
  app.js
  db.js
  schema.sql
  routes/
    adsb.js
    crud.js
  services/
    airplanesLiveCollector.js
    openSkyCollector.js
    realtimeCollector.js
    routeCrawlerService.js
    trackService.js
scripts/
  crawl-routes.js
  fetch-airplanes-live.js
  fetch-opensky.js
  smoke-test.js
data/
  adsb-interface.db
```

## 后续扩展建议

如果要做更完整的航空业务系统，可以继续扩展：

- 接入能提供计划航路、起飞机场、降落机场的数据源。
- 将 SQLite 切换为 PostgreSQL + PostGIS，增强空间查询能力。
- 增加前端地图页面，直接渲染 `adsb_routes.path_geojson`。
- 对后台爬取任务做持久化，服务重启后自动恢复。
