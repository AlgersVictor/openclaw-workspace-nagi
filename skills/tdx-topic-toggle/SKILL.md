name: tdx-topic-toggle
description: TDX MQTT 可切換 Topic 群組開關。開啟/關閉台北、台中等群組，並自動重啟 tdx-mqtt-listener service。
trigger: 使用者說「開啟台北」「關閉台北」「開啟台中」「關閉台中」，或需要查詢目前啟用的群組。
scope: TDX MQTT listener 群組動態管理

inputs:
  action: enable | disable
  group: taipei | taichung
  config: 設定檔路徑（預設 ~/.openclaw/workspace/runtime/tdx/mqtt_groups.json）

群組定義:
  taipei:
    - v2/Bus/Alert/City/Taipei      (台北公車)
    - v2/Bus/Alert/City/NewTaipei   (新北公車)
    - v2/Rail/Metro/Alert/TRTC      (台北捷運)
  taichung:
    - v2/Bus/Alert/City/Taichung    (台中公車)
    - v2/Rail/Metro/Alert/TMRT      (台中捷運)

workflow:
  1. 讀取 mqtt_groups.json（不存在則預設全 false）
  2. 更新指定群組的 enabled 狀態
  3. 寫回 JSON
  4. systemctl --user restart tdx-mqtt-listener.service
  5. 輸出結果 JSON

output_schema:
  status: ok
  group: 群組名稱
  state: 開啟 | 關閉
  topics: 對應的 MQTT topics 清單

fallback_rules:
  - systemd restart 失敗 → 印 WARN，不中止，config 仍已更新
  - 不存在的群組 → argparse 攔截報錯

validation:
  - python3 skills/tdx-topic-toggle/bin/tdx-topic-toggle toggle --action enable --group taipei --no-restart
  - python3 skills/tdx-topic-toggle/bin/tdx-topic-toggle status

deployment:
  - tdx-mqtt-listener service 需加 --groups-config ~/.openclaw/workspace/runtime/tdx/mqtt_groups.json
  - 切換後 service 自動重啟，約 2 秒完成

rollback:
  - python3 skills/tdx-topic-toggle/bin/tdx-topic-toggle toggle --action disable --group taipei
