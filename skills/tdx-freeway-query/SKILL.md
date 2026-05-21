> ⛔ **凪：禁止讀本檔案。** 指令格式已在 PLAYBOOK.md「TDX execution hard guard」列明，以 PLAYBOOK 為唯一來源。

name: tdx-freeway-query
description: 查詢國道指定路段（起訖交流道）的即時事件（事故/施工/管制）與車速。
trigger: 使用者詢問「國道X號 北/南向 從A交流道到B交流道有沒有事故/塞車/施工」
scope: 國道（NFB）即時事件 + 路段車速，支援任意起訖交流道名稱

inputs:
  road:      路名（如「國道1號」「國道3號」）
  direction: 北向 | 南向
  from_ic:   起點交流道（支援省略「交流道」後綴）
  to_ic:     終點交流道

data_sources:
  - TDX /v2/Road/Traffic/Section/Freeway（靜態路段，解析 km 範圍）
  - TDX /v1/Traffic/RoadEvent/LiveEvent/Freeway（即時事件）
  - TDX /v2/Road/Traffic/Live/Freeway（即時車速）
  - 認證：env TDX_CLIENT_ID, TDX_CLIENT_SECRET

workflow:
  1. 正規化起訖 IC 名稱（去除「交流道/系統/服務區」後綴）
  2. 查靜態路段資料解析 km 範圍（動態，不需硬編碼表）
  3. 查即時事件，依 km 範圍 + 方向篩選
  4. 查即時車速，依 km 範圍篩選路段
  5. 輸出 JSON（事件列表 + 路段車速）

output_schema:
  status: ok | auth_error | upstream_error
  road / direction / from_ic / to_ic: 查詢條件
  km_range: 解析到的公里範圍（如 349.4K~362.4K）
  summary: 一句話摘要
  events: 事件列表（type/step/severity/location/description）
  event_count: 事件數
  sections: 路段車速（section/km/speed_kmh/travel_time_sec/congestion）

fallback_rules:
  - km_range 解析失敗 → 改用 IC 名稱關鍵字匹配（寬鬆模式）
  - event_count=0 → summary 顯示「目前無事故或管制事件」
  - auth_error → 提示設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET

validation:
  - python3 skills/tdx-freeway-query/bin/tdx-freeway-query --road 國道1號 --direction 北向 --from 中正交流道 --to 岡山交流道

deployment:
  - 需設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET（REST API 金鑰）
  - 不需額外申請，基礎方案即可存取 NFB 路段與事件資料

rollback:
  - 移除 skills/tdx-freeway-query/ 目錄即可
