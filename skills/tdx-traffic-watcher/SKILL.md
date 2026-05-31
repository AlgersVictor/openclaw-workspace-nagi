name: tdx-traffic-watcher
description: TDX 交通事件 Discord 推播監視器。定時輪詢國道 + 縣市路況事件，偵測新增/解除事件及壅塞變化，透過 Discord Webhook 推播通知。
trigger: 以 systemd user service 背景運行，每 5 分鐘輪詢一次。可透過 tdx-traffic-toggle 控制開啟/關閉縣市。
scope: 國道即時事件 + 縣市路況事件 + 縣市壅塞警示

inputs:
  --once:     只執行一次 poll（測試用）
  --dry-run:  不送 Discord，只印 embed JSON
  --interval: 輪詢間隔秒數（預設 300）

data_sources:
  - TDX /v1/Traffic/RoadEvent/LiveEvent/Freeway（國道即時事件）
  - TDX /v1/Traffic/RoadEvent/LiveEvent/City/{city}（縣市即時事件）
  - TDX /v2/Road/Traffic/Live/City/{city}（縣市路況速度/壅塞）
  - 認證：env TDX_CLIENT_ID, TDX_CLIENT_SECRET
  - 通知目標：env DISCORD_WEBHOOK_URL

config:
  路徑：~/.openclaw/workspace/runtime/tdx/traffic_watcher_config.json
  預設值：
    freeway: true           # 國道永遠開啟
    cities:
      Kaohsiung: true       # 高雄預設開啟，其他縣市預設關閉
    congestion_alert_threshold: 0.35   # 壅塞路段比例超過 35% 才告警
    congestion_clear_threshold: 0.10   # 降至 10% 以下才發「恢復」通知

state:
  路徑：~/.openclaw/workspace/runtime/tdx/traffic_watcher_state.json
  用途：追蹤上次 poll 的事件 ID，計算新增/解除 diff

workflow:
  1. 讀取 traffic_watcher_config.json（預設值：國道+高雄）
  2. 讀取上次 state（traffic_watcher_state.json）
  3. Poll 國道事件 → diff → 送新增/解除 Discord embed
  4. 依 config 開啟的縣市，分別 poll 事件 + 路況
  5. 縣市事件 diff → 送新增/解除 Discord embed
  6. 縣市路況壅塞比例 diff → 超過閾值送告警 / 低於閾值送恢復
  7. 寫回 state，等待下一輪（daemon 模式）

output_schema:
  Discord Embed 類型：
    🚨 XX 事故/施工（新增）  → 紅色（15158332）
    🟢 XX 事件解除          → 綠色（3066993）
    🟡 XX 路況壅塞          → 橙色（15105570）
    🔵 XX 路況恢復          → 藍色（3447003）

fallback_rules:
  - 任一縣市 poll 失敗 → 記 log，繼續其他縣市（不中止）
  - Discord 通知失敗 → 記 log，state 仍正常更新
  - TDX 認證失敗 → 記 error，daemon 停止（等 systemd restart）

validation:
  # 不送 Discord，只印 embed JSON（需設定 TDX env var）
  python3 skills/tdx-traffic-watcher/bin/tdx-traffic-watcher --once --dry-run
  # 執行單元測試
  cd workspace-nagi && pytest skills/tdx-traffic-watcher/tests/ -v

deployment:
  1. 設定 env var：TDX_CLIENT_ID, TDX_CLIENT_SECRET, DISCORD_WEBHOOK_URL
     → 加到 ~/.openclaw/workspace/runtime/tdx/.env
  2. 安裝 systemd service：
     cp deploy/systemd/tdx-traffic-watcher.service ~/.config/systemd/user/
     systemctl --user daemon-reload
     systemctl --user enable tdx-traffic-watcher.service
     systemctl --user start tdx-traffic-watcher.service
  3. 確認運行：
     systemctl --user status tdx-traffic-watcher.service
     journalctl --user -u tdx-traffic-watcher -f

rollback:
  systemctl --user stop tdx-traffic-watcher.service
  systemctl --user disable tdx-traffic-watcher.service

notes:
  - MQTT 沒有道路 topic，必須用 REST 輪詢（5 分鐘）
  - 高雄壅塞監測不可用（TDX 設計限制，非暫時故障）：
      端點 v2/Road/Traffic/Live/City/Kaohsiung → HTTP 400
      TDX 回傳：「City: 'Kaohsiung' is not accepted but YilanCounty,
      HsinchuCounty, ..., Taipei, Taichung, Tainan, Taoyuan, KinmenCounty」
      v1/v3 變體均 404，KaohsiungCity/高雄市 命名皆無效。
      已確認 TDX 無高雄壅塞替代端點（2026-05-31 調查）。
      服務遇到此錯誤會 log ERROR 並繼續，壅塞告警功能對高雄無作用。
      事件新增/解除監測（/v1/Traffic/RoadEvent/LiveEvent/City/Kaohsiung）不受影響。
  - 與 tdx-mqtt-listener 共用同一個 DISCORD_WEBHOOK_URL
  - tdx-traffic-toggle skill 可動態控制縣市開關（Nagi 指令）
