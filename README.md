# ADS-B Interface Prototype

这是一个可以直接启动的 Node.js 原型，用来演示你这套航迹系统里 ADS-B 数据获取接口应该怎么设计、怎么落地。

## 设计思路

这个原型分成两层：

1. 通用业务表接口
   直接覆盖你给的 12 张表，提供基础 CRUD，方便前端、调度器、ASR、标注系统先联调起来。
2. ADS-B 专用接口
   单独处理实时写入、批量写入、按时间/空间范围查询航迹、语音与航迹融合查询、实时采集任务启动/停止。

## 关键说明

- 你原始 DDL 里的 `POINT` 在 SQLite 中不方便直接使用，所以这里拆成了 `latitude` 和 `longitude` 两列。
- `a2_voice_info` 的建表语句末尾原本多了一个逗号，这里已经修正。
- `vsp_procedures.waypoints` 和 `route_geom` 在接口层支持直接传 JSON，对数据库按字符串保存。
- 原型库默认是 SQLite，正式环境建议切 PostgreSQL + PostGIS。

## 启动

```bash
npm install
npm start
```

启动后访问：

- `GET /health`
- `GET /api/adsb/tracks`
- `GET /api/system/base-config`

## 典型接口

### 1. 写入单条 ADS-B 航迹

```bash
curl -X POST http://localhost:3000/api/adsb/tracks ^
  -H "Content-Type: application/json" ^
  -d "{\"callsign\":\"CCA123\",\"latitude\":39.9042,\"longitude\":116.4074,\"altitude\":10500,\"ground_speed\":780,\"heading\":90,\"timestamp\":\"2026-04-06T12:00:00Z\"}"
```

### 2. 批量写入 ADS-B 航迹

```bash
curl -X POST http://localhost:3000/api/adsb/tracks/batch ^
  -H "Content-Type: application/json" ^
  -d "{\"items\":[{\"callsign\":\"CCA123\",\"latitude\":39.90,\"longitude\":116.40,\"timestamp\":\"2026-04-06T12:00:00Z\"},{\"callsign\":\"CES456\",\"latitude\":31.23,\"longitude\":121.47,\"timestamp\":\"2026-04-06T12:00:10Z\"}]}"
```

### 3. 查询航迹

```bash
curl "http://localhost:3000/api/adsb/tracks?callsign=CCA123&start_time=2026-04-06T00:00:00Z&end_time=2026-04-06T23:59:59Z&limit=100"
```

### 4. 写入语音信息

```bash
curl -X POST http://localhost:3000/api/voice-info ^
  -H "Content-Type: application/json" ^
  -d "{\"icao_code\":\"ZBAA\",\"band\":\"VHF\",\"file_path\":\"/atc/a2/data/20260406/001.wav\",\"file_name\":\"001.wav\",\"file_size\":204800,\"data_type\":\"voice\"}"
```

### 5. 建立语音和航迹关联

```bash
curl -X POST http://localhost:3000/api/voice-track-rel ^
  -H "Content-Type: application/json" ^
  -d "{\"unique_id\":\"voice-uuid\",\"track_id\":\"track-uuid\"}"
```

### 6. 语音与航迹融合查询

```bash
curl "http://localhost:3000/api/adsb/fusion/voice-track?callsign=CCA123&limit=20"
```

### 7. 创建实时采集任务

```bash
curl -X POST http://localhost:3000/api/tasks/realtime ^
  -H "Content-Type: application/json" ^
  -d "{\"task_name\":\"beijing-feed\",\"server_addr\":\"127.0.0.1\",\"server_port\":9001,\"protocol\":\"TCP\",\"timeout\":30,\"heart_beat\":10}"
```

### 8. 启动实时采集任务

```bash
curl -X POST http://localhost:3000/api/adsb/realtime-tasks/1/start
```

这里的实时采集器默认按 `TCP + JSON Lines` 工作，也就是上游持续推送：

```json
{"track_id":"t-1","callsign":"CCA123","latitude":39.90,"longitude":116.40,"altitude":9800,"timestamp":"2026-04-06T12:00:00Z"}
{"track_id":"t-2","callsign":"CES456","latitude":31.23,"longitude":121.47,"altitude":11200,"timestamp":"2026-04-06T12:00:05Z"}
```

### 9. Fetch real OpenSky ADS-B states

OpenSky `/states/all` returns decoded state vectors, so this prototype decodes the vector fields,
converts altitude from meters to feet, converts velocity from m/s to knots, stores coordinates as
`POINT(lng lat)`, and keeps the raw vector in `raw_payload`.

```bash
npm run fetch:opensky -- --preset switzerland --limit 20
```

Or call it through the API:

```bash
curl -X POST http://localhost:3000/api/adsb/sources/opensky/fetch ^
  -H "Content-Type: application/json" ^
  -d "{\"preset\":\"switzerland\",\"limit\":20}"
```

Built-in presets: `hongkong`, `beijing`, `switzerland`, `global`.
Optional authentication uses `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET`.

If OpenSky anonymous credits are exhausted, use Airplanes.live:

```bash
npm run fetch:airplanes -- --preset switzerland --limit 20
```

Or call it through the API:

```bash
curl -X POST http://localhost:3000/api/adsb/sources/airplanes-live/fetch ^
  -H "Content-Type: application/json" ^
  -d "{\"preset\":\"switzerland\",\"limit\":20}"
```

Airplanes.live data is already decoded JSON; altitude is kept in feet and ground speed in knots.

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
    trackService.js
```

## 后续怎么接真实 ADS-B 数据源

如果你的上游不是 JSON Lines，而是：

- SBS-1 文本流
- Beast 二进制流
- Kafka / MQTT
- HTTP 拉取历史数据

建议做法是保留现在的 `trackService.js` 不动，只替换 `realtimeCollector.js` 里的解析逻辑。也就是说：

1. 上游协议负责“解码”
2. `trackService.js` 负责“标准化入库”
3. `adsb_tracks` 和关联表负责“统一查询”

这样你的业务接口不会因为采集源变化而全部重写。
