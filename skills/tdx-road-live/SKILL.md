---
name: tdx-road-live
description: TDX 路況資訊查詢。dispatcher 明確路況問句應優先路由到此 skill；正式可宣稱以 traffic_live_summary 為主。
metadata: {"openclaw": {"emoji": "🚦", "pattern": "retrieval"}}
---

> ⛔ **凪：禁止讀本檔案。** 指令格式已在 PLAYBOOK.md「TDX execution hard guard」列明，以 PLAYBOOK 為唯一來源。

# tdx-road-live

## name
`tdx-road-live`

## description
提供縣市路況資訊查詢。本輪 Phase 2B 僅把 `traffic_live_summary` 做成可接 live 的維護區骨架；`congestion_level`、`traffic_news`、`cctv_info` 只保留 honest `not_prechecked` 輸出。

## trigger
- 使用者詢問某城市現在塞不塞
- 使用者詢問路況摘要
- 使用者詢問即時交通新聞
- 使用者詢問 CCTV 資訊

## scope
- `traffic_live_summary`
- `congestion_level`
- `traffic_news`
- `cctv_info`

## inputs
- `city`
- `intent`
- `keyword`（可選）
- `top`（可選）
- `format`（預設 `JSON`）

## data_sources
- A 級：`docs/tdx/v2.4.0/precheck/precheck_results.json`
- A 級：TDX Swagger `路況資訊 v2`
- B 級：`docs/tdx/v2.4.0/endpoint_matrix.md`
- C 級：`fixtures/tdx/road_live/*.json`

## workflow
1. 先走 shared-core 的 `city resolver`
2. 再由 endpoint registry 決定 endpoint 與 `validation_state`
3. `traffic_live_summary` 可 live call
4. 其他 intents 若未 precheck，回 `not_prechecked` 骨架
5. 若缺少 `city`，回 `needs_clarification`

## output_schema
```json
{
  "status": "ok|needs_clarification|invalid_input|auth_error|upstream_error",
  "intent": "",
  "normalized_city": "",
  "source": {
    "provider": "TDX",
    "endpoint": "",
    "validation_state": "prechecked|mapped_only|not_prechecked"
  },
  "summary": "",
  "items": []
}
```

## fallback_rules
- `traffic_live_summary` 上游失敗時回 `upstream_error`
- `congestion_level`、`traffic_news`、`cctv_info` 本輪先回 honest `not_prechecked`
- 缺城市時一律先澄清
- 不使用外部新聞來源補 `traffic_news`

## validation
- pytest 驗證 intent routing、city resolver 重用、live payload mapping、not_prechecked 標記、錯誤輸出結構
- fixture：`city_live_sample.json` 為主，其他 fixture 只用於 mapper skeleton

## deployment_notes
- Phase C 已建立 bin/ CLI 入口，traffic_live_summary 可 live call TDX API
- 已同步正式區 workspace-nagi（2026-04-04）
- 已知限制：高雄路況端點回 400（TDX 上游問題），台北正常
- congestion_level / traffic_news / cctv_info 仍為 not_prechecked 骨架
