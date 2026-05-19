name: tdx-mqtt-listener
description: TDX MQTT 即時通阻監聽器。持續訂閱 TDX MQTT Topic，收到推播後格式化並送出 Discord Webhook 通知。
trigger: 需要長期監聽 TDX 公車/捷運/台鐵/高鐵即時通阻，並在有異常時主動推播到 Discord。
scope: TDX MQTT 動態推播 → Discord Webhook 通知

inputs:
  topics: 訂閱 Topic 清單（逗號分隔），預設 v2/Rail/Metro/Alert/#
  reconnect_delay: 斷線重連等待秒數（預設 30）
  dry_run: true 時只印 JSON，不送 Discord

data_sources:
  - TDX MQTT 服務：mqtt.transportdata.tw:8883（MQTTS）
  - MQTT 認證：env TDX_MQTT_CLIENT_ID, TDX_MQTT_USERNAME, TDX_MQTT_PASSWORD
  - 通知目標：env DISCORD_WEBHOOK_URL

workflow:
  1. 讀取 MQTT 認證 + Discord Webhook URL
  2. 訂閱指定 Topic（daemon 模式，持續運行）
  3. 收到訊息 → alert_formatter 格式化為 Discord Embed
  4. discord_notifier 送出 Webhook POST
  5. 斷線時自動重連（reconnect_delay 秒後）

output_schema:
  每筆通阻推播為一則 Discord Embed：
    title: 通阻類型 + 路線/路段
    description: 通阻說明
    color: 15158332（紅色）
    footer: TDX MQTT | 收到時間（Asia/Taipei）

fallback_rules:
  - auth_error → 停止並印出缺少的 env var
  - webhook_error → 印錯誤，繼續監聽（不因通知失敗停止）
  - connect_error → 等 reconnect_delay 秒後重連，最多重試不限次

validation:
  - python3 skills/tdx-mqtt-listener/bin/tdx-mqtt-listener --topics v2/Rail/Metro/Alert/# --dry-run
  - 需設定 TDX_MQTT_CLIENT_ID/USERNAME/PASSWORD + DISCORD_WEBHOOK_URL

deployment:
  - 設定 env（含 TDX MQTT 三組 + DISCORD_WEBHOOK_URL）
  - 前台測試：python3 bin/tdx-mqtt-listener --topics v2/Rail/Metro/Alert/#
  - 背景運行：nohup python3 bin/tdx-mqtt-listener ... &
  - 或以 systemd user service 管理

rollback:
  - kill 對應 process 即可，無 side effect
  - 移除 skills/tdx-mqtt-listener/ 目錄
