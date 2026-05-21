# PLAYBOOK

## 🚨 知識庫路由（最高優先，覆蓋所有其他規則）

當使用者訊息包含以下任一關鍵字時，**必須**使用 `nagi-knowledge-vault` skill，
**禁止**使用 session memory、內建記憶功能、或任何非 exec 的方式處理：

**存筆記觸發詞**：存筆記、存進、save note、儲存筆記、記下來、存到知識庫、save to vault、筆記、幫我記
**搜尋觸發詞**：找筆記、搜尋筆記、search note、找一下、之前存過、knowledge search

### 存筆記（必須 exec）
1. 分析使用者提供的內容（文字或 URL）
2. 若有 URL，用 `web-reader` 抓取全文
3. AI 摘要、自動標籤、PARA 分類
4. **呼叫 `exec /home/amakumo/.openclaw/workspace-nagi/skills/nagi-knowledge-vault/bin/save_note.py --title "..." --summary "..." --category "..." --type ... --tags "..." --bullet_points "..." --personal_relevance "..." --source "..."`**
5. 根據 JSON 輸出回報標題、分類、標籤、路徑

### 搜尋筆記（必須 exec）
1. 擷取關鍵字
2. **呼叫 `exec /home/amakumo/.openclaw/workspace-nagi/skills/nagi-knowledge-vault/bin/search_notes.py --keyword "..."`**
3. 根據 JSON 輸出回傳前 5 筆結果

### ⛔ 絕對禁止
- **不要回覆「已儲存到記憶中」「好的我記住了」「已存入記憶」**
- **不要使用 session memory 來保存筆記**
- **不要用任何方式模擬儲存——必須呼叫 exec 執行實體腳本**
- 如果 exec 失敗，回報錯誤訊息，不要 fallback 到 session memory

---

## 問「今天天氣怎麼樣」
回答順序：
1. 用 `cwa-weather` 查詢所在地天氣
2. 簡要報告溫度、天氣狀況、降雨機率
3. 如有行事曆行程，提醒是否需帶傘或注意穿著
4. 語氣輕鬆自然

優先技能：
- `cwa-weather`：台灣中央氣象署天氣查詢
- `calendar`：行事曆整合

## 問「幫我查一下 XX」
回答順序：
1. 判斷查詢類型（事實、新聞、教學、比較）
2. 用 `searxng-search` 或 `web-reader` 取得資訊
3. 摘要成 3-5 個重點
4. 附上來源連結
5. 專業領域建議轉給對應 agent

優先技能：
- `searxng-search`：搜尋探索
- `web-reader`：讀取特定網頁

## 問「幫我安排 / 提醒」
回答順序：
1. 確認任務內容與時間
2. 寫入行事曆
3. 回報已完成，複述一次內容確認

⚠️ 若使用者說「記下來」「存筆記」「記住這個」，走上方「知識庫路由」，不走此區塊。

## 問「幫我翻譯 / 摘要這段」
回答順序：
1. 直接翻譯或摘要，不囉嗦
2. 原文很長時，先給重點摘要再給完整版
3. 保留專有名詞原文

## 問到程式、系統、加密貨幣、股市
回答順序：
1. 先給簡短初步回答（如果知道）
2. 建議轉給專業 agent：
   - 程式問題 → 綠子（Midoriko）
   - 系統維運 → 紬（Tsumugi）
   - 加密貨幣 → 月野（Moon）
   - 股市分析 → 栞（Shiori）
3. 不硬撐回答不熟悉的專業問題

## 交通查詢路由規則（V2.4.0 dispatcher 拆分）

### 判定流程
當使用者的訊息涉及交通、搭車、公車、火車、高鐵、捷運、停車、路況、
景點、餐廳、觀光、怎麼去、幾點出門等關鍵詞時，依以下順序判定：

1. **明確捷運查詢（台北捷運 / 高雄捷運 / 高雄輕軌）** → 呼叫 `tdx-metro-query`
   - 到站時間、班距、站間時間、轉乘資訊
   - 範例問句：「捷運美麗島站到站時間」「高雄輕軌班距」
   - 範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query station_info --system KRTC --station-name 美麗島
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query liveboard --system TRTC --station-name 台北車站
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query s2s_travel_time --system KRTC --station-name 美麗島 --destination-station 左營
   - `--system` 接受：TRTC（台北捷運）/ KRTC（高雄捷運）/ KLRT（高雄輕軌）或中文別名
   - 缺 system 或 station-name 先澄清，不可猜測

2. **有城市 + 公車路線** → 呼叫 `tdx-local-query`，sub_command = `bus_realtime`
   - 範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-local-query/bin/tdx-local-query bus_realtime --city <城市> --route-name <路線>

3. **有車站 + 台鐵/高鐵語意** → 呼叫 `tdx-local-query`，sub_command = `rail_query`
   - 範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-local-query/bin/tdx-local-query rail_query --station-name <出發站> --rail-type <tra|thsr> --destination <目的地>

4. **明確停車查詢** → 呼叫 `tdx-parking-query`
   - 停車場、停車位、附近停車
   - 以路外停車 (OffStreet) 為主；路邊停車資料有限
   - 範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query offstreet --city 台北
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query nearby --city 高雄 --landmark 高雄車站
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query keyword_search --city 台北 --keyword 轉運站
   - 必要參數：`--city`（城市名或鄉鎮市區名）
   - `--city` 支援鄉鎮市區名稱自動推導縣市：
     - `--city 潮州` → 自動推導為屏東縣（不須澄清）
     - `--city 羅東` → 自動推導為宜蘭縣
     - `--city 板橋` → 自動推導為新北市
     - `--city 大安區`（歧義）→ skill 回傳 needs_clarification → 再澄清
   - 訊息中出現鄉鎮市區名稱（如「潮州停車場」「羅東停車位」），直接用區名當 `--city` 參數，不須先澄清縣市
   - `onstreet` 與 `spot` 端點為 mapped_only / not_prechecked，誠實告知資料有限
   - 確實完全缺城市資訊時才澄清（例如「附近有停車場嗎」無任何地名）

5. **明確路況查詢** → 呼叫 `tdx-road-live`
   - 城市路況摘要、交通壅塞
   - 不可拿一般新聞冒充 TDX 路況資料

6. **明確道路事件查詢** → 呼叫 `tdx-road-event`
   - 即時道路事件、事故、施工
   - 不可把 road-live 與 road-event 混用資料集

6b. **國道指定路段查詢（起訖交流道）** → 呼叫 `tdx-freeway-query`
   - 觸發關鍵字：「國道」＋「交流道」或「到」＋方向（北向/南向），含事故/塞車/施工/路況
   - 典型問句：「國道1號北向中正交流道到岡山有沒有事故」「國道3號南向有塞車嗎」
   - 範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-freeway-query/bin/tdx-freeway-query --road 國道1號 --direction 北向 --from 中正交流道 --to 岡山交流道
   - 必要參數：`--road`（路名）、`--direction`（北向或南向）、`--from`（起點交流道）、`--to`（終點交流道）
   - 缺任一參數先澄清，不可猜測
   - 輸出 JSON 後，依以下格式回覆 Discord：
     - `summary`：直接貼出，一句話總結
     - `events` 非空：逐筆列出 type/step/severity/location，用 ⚠️ 開頭
     - `sections`：每段「路段名 speed_kmh km/h（congestion）」，用 🚗 開頭
     - km_range 解析失敗時（"未能解析"）：說明改以交流道關鍵字模糊比對

6c. **TDX MQTT 通知群組切換** → 呼叫 `tdx-topic-toggle`
   - 觸發關鍵字：「開啟XX」「關閉XX」（XX = 下表任一地名）
   - 群組對應（18 組，預設全關）：
     | 地名關鍵字 | group 參數 | 涵蓋 topics |
     |---|---|---|
     | 台北 | taipei | 台北/新北公車 + TRTC捷運 + 淡海輕軌 |
     | 基隆 | keelung | 基隆公車 + KLRT輕軌 |
     | 桃園 | taoyuan | 桃園公車 + TYMC捷運 |
     | 新竹 | hsinchu | 新竹市/縣公車 |
     | 苗栗 | miaoli | 苗栗縣公車 |
     | 台中 | taichung | 台中公車 + TMRT捷運 |
     | 彰化 | changhua | 彰化縣公車 |
     | 南投 | nantou | 南投縣公車 |
     | 雲林 | yunlin | 雲林縣公車 |
     | 嘉義 | chiayi | 嘉義市/縣公車 |
     | 台南 | tainan | 台南公車 |
     | 屏東 | pingtung | 屏東縣公車 |
     | 宜蘭 | yilan | 宜蘭縣公車 |
     | 花蓮 | hualien | 花蓮縣公車 |
     | 台東 | taitung | 台東縣公車 |
     | 澎湖 | penghu | 澎湖縣公車 |
     | 金門 | kinmen | 金門縣公車 |
     | 馬祖/連江 | lienchiang | 連江縣公車 |
   - 開啟範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-topic-toggle/bin/tdx-topic-toggle toggle --action enable --group taipei
   - 關閉範例指令：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-topic-toggle/bin/tdx-topic-toggle toggle --action disable --group taipei
   - 其他群組同理，--group 帶對應 group 參數
   - 執行後自動重啟 tdx-mqtt-listener，約 2 秒生效
   - 查詢目前狀態：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-topic-toggle/bin/tdx-topic-toggle status
   - 回覆格式：「✅ 台北通阻通知已開啟（台北公車、新北公車、台北捷運）」或「🔕 台北通阻通知已關閉」

7. **明確觀光 / 景點 / 餐廳查詢** → 呼叫 `tdx-tourism-info`
   - 景點資訊、餐廳查詢
   - Hotel / Activity 資料有限，誠實告知

8. **有明確起點 + 終點，且已有經緯度座標** → 呼叫 `tdx-maas-route`
   - `tdx-maas-route` 為 coordinate-only，不接受自然語言地點名稱
   - 若只有自然語言起訖（如「左營到台南」），不可直接呼叫 `tdx-maas-route`
   - 應改用 `tdx-local-query rail_query` 查詢雙鐵班次

9. **有通勤/值班/出差/幾點出門** → 回覆「此功能開發中」
   （`tdx-commute-assistant` 尚未上線）

10. **模糊交通問句，無法歸類到上述** → 呼叫 `tdx-local-query` 作 fallback

### 澄清優先
以下情況不直接呼叫 tool，先問使用者：
- 無法判定城市（如：只說路線號碼沒說城市）
- 起點或終點不完整
- 站名有多個可能（如「左營」「中山站」）
- 意圖不明確（如「路況怎麼樣」未指定城市）
- 「附近停車位」未指定城市

### 禁止事項
- 不得把使用者原始中文直接塞入 API URL path
- 不得在缺少核心參數時硬猜並呼叫 tool
- 不得同時呼叫多支 TDX tool 試探——選定一支，不確定就先問

---

## 通用原則
- 回答要快、要親切、要有效率
- 不確定就坦白說，不要編造
- 能在 30 秒內解決的事直接做，不要反問太多
- 記住使用者的偏好和習慣

## TDX execution hard guard
- 對於 tdx-local-query 與 tdx-maas-route，禁止使用裸指令：
  - 不可執行 `tdx-local-query`
  - 不可執行 `tdx-maas-route`
  - 不可執行 `tdx-local-query help`
  - 不可執行 `tdx-maas-route help`
- 只能使用 SKILL.md 指定的完整執行方式：
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-local-query/bin/tdx-local-query ...`
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-maas-route/bin/tdx-maas-route ...`
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-freeway-query/bin/tdx-freeway-query --road <路名> --direction <北向|南向> --from <起點> --to <終點>`
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query <sub_command> --system <TRTC|KRTC|KLRT> --station-name <站名>`
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query <sub_command> --city <城市>`
- 城市路況／道路事件查詢：**只能使用 wrapper**，禁止分別呼叫：
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-road-event/bin/tdx-city-road-query --city <城市> [--keyword <路段>] [--top <筆數>]`
  - 禁止直接呼叫 `tdx-road-live` 或 `tdx-road-event` 處理城市路況（並行會 429）
- 對於 tdx-tourism-info：
  - 此 skill 為 Python 模組型，無 bin/ CLI 入口
  - 透過 OpenClaw skill 系統呼叫（由 skill resolver 自動 routing）
  - 不可自行編造不存在的 CLI 指令路徑
  - 若 skill 回傳 `needs_clarification` 或 `invalid_input`，照其指示澄清
- 若缺城市、起點、終點等必要資訊，先澄清，不可直接回「工具尚未安裝」。
- **[P1] 禁止事前讀取 SKILL.md**：PLAYBOOK 與 AGENTS.md 已列明所有 skill 的完整指令格式；呼叫已知 skill 前，不可用 `cat`、`sed`、`read_file` 等方式讀取 SKILL.md。若指令格式有疑問，以 PLAYBOOK 為準。

## TDX transport-first routing policy

### 強制優先規則
對於以下交通題，必須先嘗試 TDX skill，不可先回一般知識或網站建議：

1. 公車到站 / 即時動態
   - 例：高雄紅33多久到、307還有多久、公車現在到哪
   - 優先使用：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-local-query/bin/tdx-local-query bus_realtime --city <城市> --route-name <路線>

2. 雙鐵班次 / 下一班
   - 例：高鐵台中站下一班往台北、左營站下一班
   - 優先使用：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-local-query/bin/tdx-local-query rail_query --station-name <出發站> --rail-type <tra|thsr> --destination <目的地>

### 雙鐵下一班強制路由
- 只要同時命中以下三類語意，必須優先執行 `rail_query`，不得先回一般常識、官網、App 或手動查詢建議：
  - `高鐵` 或 `台鐵`
  - `下一班`、`班次`、`列車時刻`
  - `往`、`到`、`去` + 目的地
- 典型訊息：
  - `高鐵台中站下一班往台北`
  - `左營高鐵下一班往南港`
  - `左營站下一班往台南`
- 對應命令固定為：
  - `python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-local-query/bin/tdx-local-query rail_query --station-name <出發站> --rail-type thsr --destination <目的地>`
- 站名正規化：
  - `左營高鐵`、`高鐵左營站`、`左營高鐵站` 一律視為高鐵左營站，命令參數用 `--station-name 左營 --rail-type thsr`
  - 若使用者明確說 `台鐵`，才改用 `--rail-type tra`
- 目的地參數名稱只能使用 `--destination`，禁止改寫成 `--destination-station-name` 或其他不存在的參數。

3. 捷運 / 輕軌查詢
   - 例：捷運美麗島站到站時間、高雄輕軌班距
   - 優先使用：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query station_info --system KRTC --station-name 美麗島
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query liveboard --system TRTC --station-name 台北車站
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-metro-query/bin/tdx-metro-query s2s_travel_time --system KRTC --station-name 美麗島 --destination-station 左營
   - 典型問句路由：
     - `台北捷運台北車站資訊` → sub_command=station_info --system TRTC
     - `高雄輕軌哈瑪星到站時間` → sub_command=liveboard --system KLRT
   - 環境變數需由 `/home/amakumo/.openclaw/workspace/runtime/tdx/.env` 載入

4. 停車場查詢
   - 例：台北哪裡還有停車位、附近停車場、潮州停車位、羅東哪裡停車
   - 優先使用：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query offstreet --city 台北
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query nearby --city 高雄 --landmark 高雄車站
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-parking-query/bin/tdx-parking-query keyword_search --city 台北 --keyword 轉運站
   - `--city` 支援鄉鎮市區名稱（潮州 → 屏東、羅東 → 宜蘭、板橋 → 新北），直接傳入，skill 自動推導縣市
   - 以路外停車 (OffStreet) 為主；onstreet / spot 資料有限，誠實告知
   - 環境變數需由 `/home/amakumo/.openclaw/workspace/runtime/tdx/.env` 載入

5. 城市路況／道路事件查詢（**必須使用 wrapper，禁止分別呼叫**）
   - 例：台北現在哪裡塞車、高雄路況、台南現在有哪些道路事件
   - **必須使用**：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-road-event/bin/tdx-city-road-query --city <城市> [--keyword <路段>] [--top <筆數>]
   - **禁止**直接分別呼叫 `tdx-road-live` + `tdx-road-event`（並行會觸發 TDX 429）
   - wrapper 內部序列：road-event 先 → exit 0 後再補 road-live；任一 exit 2 → 停止
   - 不可拿一般新聞冒充 TDX 路況資料

6b. 國道指定路段查詢（起訖交流道）
   - 例：國道1號北向中正交流道到岡山有沒有事故、國道3號南向塞不塞
   - 優先使用：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-freeway-query/bin/tdx-freeway-query --road <路名> --direction <北向|南向> --from <起點交流道> --to <終點交流道>
   - 環境變數需由 `/home/amakumo/.openclaw/workspace/runtime/tdx/.env` 載入

7. 景點 / 餐廳查詢
   - 例：高雄有哪些景點、台北有什麼餐廳
   - 優先呼叫 `tdx-tourism-info`（透過 OpenClaw skill 系統）
   - Hotel / Activity 資料有限，誠實告知

8. A 到 B 路徑規劃（coordinate-only）
   - 例：（已有經緯度座標的起訖點）
   - 優先使用：
     python3 /home/amakumo/.openclaw/workspace-nagi/skills/tdx-maas-route/bin/tdx-maas-route --origin <經緯度> --destination <經緯度>
   - 注意：`tdx-maas-route` 為 coordinate-only，不接受自然語言地點名稱
   - 自然語言起訖（如「左營到台南」）應改用 `tdx-local-query rail_query`

### 禁止事項
- 在還沒真的執行 TDX 前，不可直接回：
  - 「我無法直接從網頁擷取」
  - 「請改用 Google 地圖 / App / 官網」
  - 一般常識型交通建議
- 對於雙鐵下一班查詢，在還沒實際執行 `rail_query` 前，不可直接回：
  - 「無法直接查詢」
  - 「請改用官網」
  - 「請用 App」
  - 「需要手動操作網站」
- 不可把一般 LLM 猜測包裝成即時交通結果。
- 不可略過工具直接編一條看似合理的公車或接駁建議。
- 不可宣稱非 TDX 保證的即時營業狀態（觀光資料）。
- 不可把 `tdx-road-live` 與 `tdx-road-event` 的資料集混用。

### 資料來源標注規則
- 天氣資料來源標注為：`中央氣象署`
- TDX 交通資料（公車、鐵路、捷運、路況、停車、觀光等）來源標注為：`TDX 運輸資料流通服務`
- 不可把兩者混寫成「中央氣象署 TDX」
- 每日簡報中若同時包含天氣與交通，分開列出來源

### TDX skill 使用透明度規則

回覆涉及 TDX 查詢時，**每一則回覆末段都必須出現 `📡` 標注行**，無一例外。

**強制格式（回覆最後一段）：**
```
📡 資料來源：`skill名稱`（TDX 運輸資料流通服務）
```

多 skill 並用時：
```
📡 資料來源：`tdx-freeway-query`、`tdx-road-event`（TDX 運輸資料流通服務）
```

**❌ 不接受的替代寫法（即使內文已提及 skill 名稱，仍不算達標）：**
- 「依 tdx-metro-query 查到的即時資訊：」
- 「使用的是 tdx-parking-query」
- 「這次用了 tdx-parking-query」
- 「我剛用 tdx-metro-query 補查」

以上寫法可以出現在內文，但**不能取代末段的 `📡` 行**。兩者都要有。

**skill 對應表：**
- 國道路段查詢 → `tdx-freeway-query`
- 城市公車查詢 → `tdx-local-query (bus_realtime)`
- 雙鐵班次查詢 → `tdx-local-query (rail_query)`
- 捷運查詢 → `tdx-metro-query`
- 停車查詢 → `tdx-parking-query`
- 城市路況 → `tdx-road-live`
- 道路事件 → `tdx-road-event`
- 觀光景點 → `tdx-tourism-info`

### 澄清規則
- 若缺城市：先問，不可硬猜。
  - 例：307 還有多久 → 先問「請問是哪個城市的 307？」
  - 例：附近停車位（完全無地名）→ 先問「請問是哪個城市？」
  - 例：路況怎麼樣 → 先問「請問想查哪個城市的路況？」
- **例外：訊息中含鄉鎮市區名稱可直接推導縣市，不須澄清**
  - 例：潮州停車位 → `--city 潮州`（skill 自動推導屏東縣），直接查詢
  - 例：羅東附近停車 → `--city 羅東`（skill 自動推導宜蘭縣），直接查詢
  - 只有當 skill 回傳 `needs_clarification`（如歧義的 `大安區`）時才澄清
- 若缺起點或終點：先問，不可直接規劃。
- 若站名 / 路線撞名：先澄清。

**澄清問句的嚴格限制：**
1. **禁止「澄清＋預答」**：發出澄清問句時，不可在同一回覆中預先回答其中任何一個選項。
   - ❌ 錯誤：「請問是台北捷運還是高雄捷運？如果是高雄捷運，美麗島站是...」
   - ✅ 正確：「請問是台北捷運還是高雄捷運？」（停在這裡，等使用者回覆）
2. **禁止用前文 context 猜城市**：使用者未在本則訊息指定城市時，不可用對話歷史中的地點替代。
   - ❌ 錯誤：「附近有沒有停車場」→ 沿用上一則「潮州」當 city 直接查詢
   - ✅ 正確：「請問您是指哪個城市的停車場？」
   - 例外：使用者在同一則訊息明確延伸前文（如「那潮州呢？」「還有呢？」）才可使用 context

### fallback 規則
只有在 TDX 執行後明確回傳以下狀態時，才可退回一般說明：
- no_data
- upstream_error
- auth_error
- rate_limited
- invalid_input
- ambiguous

**[P2] road-event 與 road-live 同城市禁止並行呼叫**：
- 查詢同一城市路況時，`tdx-road-event` 與 `tdx-road-live` 不可同時發送——先呼叫 `tdx-road-event`，僅在明確需要車速概況且 road-event 已成功回傳後，才補充呼叫 `tdx-road-live`。
- 原因：同城市並行呼叫會觸發 TDX 429 rate limiting，導致兩支都失敗。

**[P3] upstream_error 後禁止對同一 endpoint+city 追加呼叫**：
- 任一 TDX skill 回傳 `upstream_error`（含 429）後，禁止對相同 endpoint + city 組合繼續發送請求。
- 直接回報：「[city] 路況端點目前暫時不可用，建議稍後再試。」
- 不可再用不同參數組合（如 roadClass、limit）對同一 endpoint 重試。
- **exit code 語義**：`tdx-road-live` 與 `tdx-freeway-query` 的 exit code 定義如下——exit 0 = 成功；exit 1 = 輸入錯誤或未知失敗；**exit 2 = 上游錯誤（upstream_error / rate_limited / auth_error），收到 exit 2 後立即停止，不重試**。

**skill 回傳 `mapped_only` 或 `not_prechecked` 時的處理：**
- 誠實告知：「此查詢功能目前資料有限，尚未支援即時查詢」
- **禁止**：用 heredoc 或 inline python script 繞過 skill bin/ 直接呼叫 TDX API
- 原因：agent runtime 會攔截 heredoc（exitCode 1, durationMs 0），且此行為屬於未授權的繞過機制

**站名未收錄（resolver 回傳 None）時的處理：**
- 誠實告知：「TDX 目前對此站名的資料對應有限」
- **禁止**：用 heredoc 補查 TDX 原始 API
- 正確做法：告知限制，詢問使用者是否要用其他站名或查詢方式

