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
- `tdx-topic-toggle`：TDX MQTT 通阻通知縣市群組開關
  - 路徑：`/home/amakumo/.openclaw/workspace-nagi/skills/tdx-topic-toggle/bin/tdx-topic-toggle`

**所有 TDX skill 路徑均為硬式絕對路徑，禁止用 `$OPENCLAW_HOME` 等環境變數拼接。**

## 使用規則
1. 任務明確對應某 skill 時，先讀該 skill 的 SKILL.md。
2. 不要猜測 skill 用法，不確定就先查。
3. skill 執行失敗時，說明原因並提供替代方案。
4. 台灣天氣優先用 `cwa-weather`；讀已知網頁用 `web-reader`；搜尋探索用 `searxng-search`。
