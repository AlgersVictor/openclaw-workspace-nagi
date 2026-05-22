# TOOLS.md - 在地工具備忘（Nagi）

Skills 定義工具如何運作；本檔案記錄此環境特有的資訊。

## 環境資訊

- 主機：Ubuntu x86_64（openclaw）
- 使用者：amakumo
- 時區：Asia/Taipei
- 語言：繁體中文（台灣）

## 已安裝的自訂 skills

- `cwa-weather`：台灣中央氣象署縣市與鄉鎮天氣預報
- `web-reader`：讀取靜態與動態網頁內容，支援 Google Calendar ICS
- `searxng-search`：透過本機 SearXNG（port 8888）搜尋
- `calendar`：行事曆管理與排程
- `tdx-metro-query`：台北捷運 / 高雄捷運 / 高雄輕軌即時查詢
  - 路徑：`/home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query`
- `tdx-parking-query`：TDX 路外停車場即時餘位查詢
  - 路徑：`/home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query`
- `tdx-freeway-query`：國道指定路段路況查詢
  - 路徑：`/home/amakumo/.openclaw/workspace-nagi/skills/tdx-freeway-query/bin/tdx-freeway-query`
- `tdx-city-road-query`：城市道路即時路況（wrapper，必須用此取代直接呼叫 road-live/road-event 城市 intent）
  - 路徑：`/home/amakumo/.openclaw/workspace-nagi/skills/tdx-road-event/bin/tdx-city-road-query`
- `tdx-topic-toggle`：TDX MQTT 通阻通知縣市群組開關
  - 路徑：`/home/amakumo/.openclaw/workspace-nagi/skills/tdx-topic-toggle/bin/tdx-topic-toggle`

**所有 TDX skill 路徑均為硬式絕對路徑，禁止用環境變數拼接。**

## 使用規則
1. TDX skill 路徑與用法以 AGENTS.md 各 section 為準，**不可讀 SKILL.md**（P1 hard guard）。
2. 非 TDX skill（cwa-weather / web-reader 等）不確定用法時，才讀其 SKILL.md。
3. skill 執行失敗時，說明原因並提供替代方案。
4. 台灣天氣優先用 `cwa-weather`；讀已知網頁用 `web-reader`；搜尋探索用 `searxng-search`。
