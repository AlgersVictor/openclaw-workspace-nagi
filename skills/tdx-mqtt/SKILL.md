name: tdx-mqtt
description: TDX MQTT 即時通阻/通知訂閱器。連線 mqtt.transportdata.tw:8883，訂閱指定 Topic，以 JSON 輸出收到的推播訊息。
trigger: 使用者查詢公車/捷運/台鐵/高鐵「即時通阻」、「營運異常」、「服務異常」，或需要長期監聽 TDX 推播資料。
scope: TDX MQTT 動態資料：公車通阻/消息、台鐵/高鐵通阻、捷運/輕軌通阻、航運通阻
inputs:
  topic: MQTT Topic（支援 # 萬用字元），例如 v2/Rail/Metro/Alert/#
  timeout: 等待秒數（預設 30），逾時後輸出已收到訊息並結束
  mode: oneshot（收到第一筆即結束）| collect（等滿 timeout 後輸出所有）| daemon（持續輸出，不自動結束）
  qos: 0|1|2（預設 1）
data_sources:
  - TDX MQTT 服務：mqtt.transportdata.tw:8883（MQTTS）
  - 認證：env TDX_MQTT_CLIENT_ID, TDX_MQTT_USERNAME, TDX_MQTT_PASSWORD（從 TDX 會員中心取得）
workflow:
  1. 讀取 MQTT 認證 env var
  2. 建立 MQTTS 連線（TLS 1.2+）
  3. 訂閱指定 Topic（QoS 可設定）
  4. 依 mode 決定輸出時機
  5. 輸出 JSON（status, topic, messages, count, elapsed_seconds）
output_schema:
  status: ok | timeout | auth_error | connect_error
  topic: 訂閱的 Topic
  messages: 收到的訊息列表（raw JSON payload）
  count: 收到訊息數
  elapsed_seconds: 耗時
fallback_rules:
  - auth_error → 提示檢查 TDX_MQTT_* env var（注意：MQTT 認證與 REST API 金鑰不同）
  - connect_error → 提示確認網路 + port 8883 是否開放
  - timeout 且 count=0 → 該 Topic 目前無資料推送（屬正常，動態資料只在異動時推送）
validation:
  - python3 skills/tdx-mqtt/bin/tdx-mqtt --topic v2/Rail/Metro/Alert/TRTC --timeout 10 --mode oneshot
deployment:
  - 設定 env：TDX_MQTT_CLIENT_ID, TDX_MQTT_USERNAME, TDX_MQTT_PASSWORD
  - 認證資訊從 TDX 會員中心 → 資料服務 → 資料存取金鑰 取得
rollback:
  - 移除 skills/tdx-mqtt/ 目錄即可，不影響其他 skill
notes:
  - MQTT 認證（ClientId/Username/Password）與 REST API 金鑰（Client Id/Secret）是不同的兩組憑證
  - 同一組 MQTT 帳號只能建立一條連線；若已有連線則舊連線自動中斷
  - 2026-05 開放初期暫不計點數，未來將納入計算
  - 目前開放 Topic：Bus/News, Bus/Alert, Rail/TRA/Alert, Rail/THSR/AlertInfo, Rail/Metro/Alert, Ship/Alert
