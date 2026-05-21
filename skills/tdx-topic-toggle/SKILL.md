name: tdx-topic-toggle
description: TDX MQTT 可切換 Topic 群組開關。開啟/關閉台北、台中等群組，並自動重啟 tdx-mqtt-listener service。
trigger: 使用者說「開啟台北」「關閉台北」「開啟台中」「關閉台中」，或需要查詢目前啟用的群組。
scope: TDX MQTT listener 群組動態管理

inputs:
  action: enable | disable
  group: taipei|keelung|taoyuan|hsinchu|miaoli|taichung|changhua|nantou|yunlin|chiayi|tainan|pingtung|yilan|hualien|taitung|penghu|kinmen|lienchiang
  config: 設定檔路徑（預設 ~/.openclaw/workspace/runtime/tdx/mqtt_groups.json）

群組定義（18組）:
  # 北部
  taipei:      台北公車 + 新北公車 + TRTC捷運 + 淡海輕軌
  keelung:     基隆公車 + KLRT輕軌
  taoyuan:     桃園公車 + TYMC捷運
  hsinchu:     新竹市/縣公車
  # 中部
  miaoli:      苗栗縣公車
  taichung:    台中公車 + TMRT捷運
  changhua:    彰化縣公車
  nantou:      南投縣公車
  yunlin:      雲林縣公車
  # 南部
  chiayi:      嘉義市/縣公車
  tainan:      台南公車
  pingtung:    屏東縣公車
  # 東部
  yilan:       宜蘭縣公車
  hualien:     花蓮縣公車
  taitung:     台東縣公車
  # 離島
  penghu:      澎湖縣公車
  kinmen:      金門縣公車
  lienchiang:  連江縣公車（馬祖）

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
