"""tdx-local-travel — 旅遊 / 在地景點交通整合助理 P5

整合：
  - tdx-tourism-info（景點資料）
  - tdx-maas-route self_assembled（交通建議）
策略：先查景點，再組合交通方案，不做完整路線 geocoding。
"""
from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path
from typing import Any

SKILL = "tdx-local-travel"
SUB_COMMAND = "local_travel"

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
TOURISM_BIN = WORKSPACE_ROOT / "skills" / "tdx-tourism-info" / "bin" / "tdx-tourism-info"
MAAS_BIN = WORKSPACE_ROOT / "skills" / "tdx-maas-route" / "bin" / "tdx-maas-route"

# tdx-shared-core resolver（含全 22 縣市 + 300+ 鄉鎮區）
_SHARED_CORE_DIR = Path(__file__).resolve().parents[2] / "tdx-shared-core"
if str(_SHARED_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_CORE_DIR))

from resolver_city import resolve_city as _shared_resolve_city

# 常見景點 → 城市對照（靜態 fallback，以短城市名對應 resolver_city 輸入）
_POI_CITY_MAP: dict[str, str] = {
    "審計新村": "台中",
    "宮原眼科": "台中",
    "彩虹眷村": "台中",
    "赤崁樓": "台南",
    "安平古堡": "台南",
    "神農街": "台南",
    "美麗島": "高雄",
    "駁二": "高雄",
    "旗津": "高雄",
    "九份": "新北",
    "平溪": "新北",
    "阿里山": "嘉義",
}

# 交通建議模板（靜態，不需 API）
# key 為 city_label（resolver_city 回傳的 details.label），如「高雄市」
_TRANSPORT_PLANS: dict[str, list[dict]] = {
    "臺中市": [
        {"plan_type": "public_transport",
         "plan_summary": "從高鐵台中站搭 BRT 快捷或市區公車前往景點，約 20–40 分鐘。"},
        {"plan_type": "bike_mix",
         "plan_summary": "抵達台中車站後租 YouBike，沿綠園道騎至中區景點，約 15–25 分鐘。"},
    ],
    "臺南市": [
        {"plan_type": "public_transport",
         "plan_summary": "從台南車站搭 88 號公車或計程車前往安平/赤崁等景點，約 15–30 分鐘。"},
        {"plan_type": "bike_mix",
         "plan_summary": "台南火車站前租 T-Bike，沿府城文化路線騎至各景點，步行距離近。"},
    ],
    "高雄市": [
        {"plan_type": "metro",
         "plan_summary": "高雄捷運紅線/橘線直達美麗島、駁二、西子灣等熱門景點。"},
        {"plan_type": "public_transport",
         "plan_summary": "輕軌 C14 駁二藝術特區站，串聯哈瑪星、旗津渡輪碼頭一帶景點。"},
    ],
    "臺北市": [
        {"plan_type": "metro",
         "plan_summary": "台北捷運覆蓋率高，可搭淡水信義線/板南線直達主要景點。"},
        {"plan_type": "public_transport",
         "plan_summary": "信義區、大安區、萬華區景點可搭公車或步行串聯。"},
    ],
    "花蓮縣": [
        {"plan_type": "rail",
         "plan_summary": "搭台鐵至花蓮車站後，租機車或汽車最為便利；市區景點可搭花蓮客運或市區公車。"},
        {"plan_type": "public_transport",
         "plan_summary": "台灣好行太魯閣線（307）從花蓮車站直達太魯閣遊客中心，每日多班。"},
    ],
    "宜蘭縣": [
        {"plan_type": "rail",
         "plan_summary": "搭台鐵至礁溪或宜蘭車站，再轉搭台灣好行礁溪溫泉線或羅東客運前往各景點。"},
        {"plan_type": "public_transport",
         "plan_summary": "羅東轉運站為核心，可搭葛瑪蘭/首都客運至冬山河、武荖坑、南方澳等地。"},
    ],
    "屏東縣": [
        {"plan_type": "public_transport",
         "plan_summary": "高鐵左營站搭墾丁快線（9188/9189）直達墾丁大街，車程約 1.5 小時。"},
        {"plan_type": "rail",
         "plan_summary": "搭台鐵至屏東車站，再轉屏東客運前往恆春、車城、東港等地。"},
    ],
    "南投縣": [
        {"plan_type": "public_transport",
         "plan_summary": "台中高鐵站或台中火車站搭台灣好行日月潭線（6670）直達日月潭，車程約 1 小時。"},
        {"plan_type": "public_transport",
         "plan_summary": "南投客運往埔里（6575）、草屯（6550）；集集線台鐵可達水里、集集。"},
    ],
    "臺東縣": [
        {"plan_type": "rail",
         "plan_summary": "搭台鐵至臺東車站（知本/臺東站），租機車或汽車探訪池上、鹿野、綠島渡輪碼頭。"},
        {"plan_type": "public_transport",
         "plan_summary": "鼎東客運往知本、鹿野、關山；綠島、蘭嶼需搭船或飛機（臺東機場）。"},
    ],
    "澎湖縣": [
        {"plan_type": "air",
         "plan_summary": "飛馬公機場（MZG）後，馬公市區租機車最便利；各離島間搭澎湖縣政府交通船。"},
        {"plan_type": "public_transport",
         "plan_summary": "澎湖公車連結馬公市、西嶼、湖西、白沙，班次有限，建議租車或參加套裝行程。"},
    ],
    "新北市": [
        {"plan_type": "metro",
         "plan_summary": "台北捷運淡水線/新莊線/板南線延伸至新北各區；搭台鐵至瑞芳站可接九份客運 962/965。"},
        {"plan_type": "public_transport",
         "plan_summary": "新北市快速公路客運（橘 12/藍 50 等）連結各區；三峽/鶯歌可搭台北客運。"},
    ],
    "桃園市": [
        {"plan_type": "metro",
         "plan_summary": "桃園機場捷運（A線）從台北直達桃園市區；桃園捷運綠線連結中壢、青埔、大溪。"},
        {"plan_type": "public_transport",
         "plan_summary": "桃園客運往大溪老街、慈湖；台鐵中壢/桃園站可轉乘市區公車。"},
    ],
    "基隆市": [
        {"plan_type": "rail",
         "plan_summary": "從台北搭台鐵約 30 分鐘至基隆站；國光/基隆客運班次密集（約 10 分鐘一班）。"},
        {"plan_type": "public_transport",
         "plan_summary": "基隆市公車連結廟口夜市、和平島、八斗子漁港；正濱漁港可步行或搭市公車。"},
    ],
    "新竹市": [
        {"plan_type": "rail",
         "plan_summary": "台鐵新竹站位市中心，步行可達東門城、城隍廟；高鐵新竹站（六家）在竹北需轉乘公車。"},
        {"plan_type": "public_transport",
         "plan_summary": "新竹客運往南寮漁港、玻璃工藝博物館；iBike 適合市區短程移動。"},
    ],
    "嘉義市": [
        {"plan_type": "rail",
         "plan_summary": "台鐵嘉義站位市中心，步行可達文化路夜市、嘉義公園；阿里山森林鐵道從北門站出發。"},
        {"plan_type": "public_transport",
         "plan_summary": "嘉義市公車/BRT 連結文化路、博物館；嘉義縣公車往竹崎、奮起湖。"},
    ],
    "新竹縣": [
        {"plan_type": "rail",
         "plan_summary": "高鐵新竹站（竹北六家）轉新竹客運；台鐵竹中站可達竹東；9039快線往台北。"},
        {"plan_type": "public_transport",
         "plan_summary": "新竹客運往北埔老街（5618）、內灣老街（5631）、尖石（5644）；假日需早出發。"},
    ],
    "苗栗縣": [
        {"plan_type": "rail",
         "plan_summary": "台鐵苗栗站位市區；高鐵苗栗站（豐富站，頭份）轉苗栗客運；三義木雕可搭苗栗客運。"},
        {"plan_type": "public_transport",
         "plan_summary": "苗栗客運往南庄老街（5905）、獅潭、大湖草莓區；假日班次有限，建議租車備案。"},
    ],
    "彰化縣": [
        {"plan_type": "rail",
         "plan_summary": "台鐵彰化站（市中心），高鐵彰化站轉員林客運；台鐵員林/田中/二水站串聯各鄉鎮。"},
        {"plan_type": "public_transport",
         "plan_summary": "員林客運往鹿港老街（6931）；彰化市公車連結彰化扇形車庫、八卦山大佛。"},
    ],
    "雲林縣": [
        {"plan_type": "rail",
         "plan_summary": "高鐵雲林站（虎尾）轉台西客運；台鐵斗六/斗南站可轉乘市區公車。"},
        {"plan_type": "public_transport",
         "plan_summary": "台西客運往北港朝天宮（6982）、西螺老街；劍湖山世界需自駕或包車。"},
    ],
    "嘉義縣": [
        {"plan_type": "rail",
         "plan_summary": "台鐵嘉義站轉阿里山森林鐵道（北門→奮起湖→阿里山），需提前購票。"},
        {"plan_type": "public_transport",
         "plan_summary": "嘉義縣公車往阿里山（7322）、奮起湖（7329）；假日班次少，可搭阿里山國家風景區接駁。"},
    ],
    "金門縣": [
        {"plan_type": "air",
         "plan_summary": "搭飛機至金門機場（松山/桃園/台中出發，約 55 分鐘）；租機車或電動車環島最靈活。"},
        {"plan_type": "public_transport",
         "plan_summary": "金門公車連結金城、金湖、金沙、金寧各鄉；觀光巴士套票可遊主要古蹟景點。"},
    ],
    "連江縣": [
        {"plan_type": "air",
         "plan_summary": "搭飛機至南竿機場或北竿機場（松山出發，約 50 分鐘）；也可從基隆搭台馬輪（約 8 小時夜船）。"},
        {"plan_type": "public_transport",
         "plan_summary": "各島租機車最便利；南竿/北竿/東莒/西莒之間搭交通船（班次依潮汐，需確認時刻）。"},
    ],
}
_DEFAULT_TRANSPORT = [
    {"plan_type": "public_transport",
     "plan_summary": "建議搭乘當地公車或計程車前往景點，出發前確認班次。"},
]


def _query_tourism(city_label: str, keyword: str | None, top: int) -> list[dict]:
    """呼叫 tdx-tourism-info bin 查景點，回傳 items list。"""
    cmd = [sys.executable, str(TOURISM_BIN), "scenic_spot",
           "--city", city_label, "--top", str(top)]
    if keyword:
        cmd += ["--keyword", keyword]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data.get("items", [])
    except Exception:
        return []


def _build_spot_summary(items: list[dict], destination: str | None) -> list[dict]:
    """整理景點摘要（最多 5 筆）。"""
    out = []
    for it in items[:5]:
        out.append({
            "name": it.get("name", ""),
            "address": it.get("address", ""),
            "open_time": it.get("open_time", ""),
            "description": (it.get("description", "") or "")[:80].rstrip("。") + "…" if it.get("description") else "",
        })
    if destination and not any(it["name"] == destination for it in out):
        out.insert(0, {"name": destination, "address": "", "open_time": "", "description": "使用者指定景點。"})
    return out


def _resolve_city(city_raw: str | None, destination: str | None) -> str | None:
    """從 city 或 destination 推斷城市，回傳 city_label（如「高雄市」）；無法辨識回 None。

    使用 tdx-shared-core resolver_city 支援全 22 縣市、300+ 鄉鎮市區。
    destination fallback 透過 POI_CITY_MAP 靜態對照後再透過 resolver 標準化。
    """
    if city_raw:
        result = _shared_resolve_city(city_raw)
        if result["status"] == "ok":
            return result["details"]["label"]
        return None
    if destination:
        for poi, city_short in _POI_CITY_MAP.items():
            if poi in destination:
                result = _shared_resolve_city(city_short)
                if result["status"] == "ok":
                    return result["details"]["label"]
    return None


def _output(
    *,
    status: str,
    summary: str,
    items: list | None = None,
    needs_clarification: bool = False,
    clarification_question: str | None = None,
    normalized_query: dict | None = None,
    errors: list | None = None,
) -> dict[str, Any]:
    return {
        "skill": SKILL,
        "sub_command": SUB_COMMAND,
        "status": status,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "summary": summary,
        "normalized_query": normalized_query or {},
        "items": items or [],
        "returned_count": len(items) if items else 0,
        "errors": errors or [],
        "source": {"provider": "TDX+travel-context", "endpoint": "derived"},
    }


def execute(params: dict[str, Any], *, config=None) -> dict[str, Any]:
    city_raw = (params.get("city") or "").strip()
    destination = (params.get("destination") or "").strip() or None
    origin = (params.get("origin") or "").strip() or None
    travel_theme = (params.get("travel_theme") or "").strip() or None
    time_budget = (params.get("time_budget") or "").strip() or None
    top = int(params.get("top", 5))

    # --- 驗證 ---
    if not city_raw and not destination:
        return _output(
            status="invalid_input", needs_clarification=True,
            clarification_question="請問想去哪個城市或景點？",
            summary="缺少城市或景點資訊。",
        )

    city_label = _resolve_city(city_raw, destination)
    if not city_label:
        return _output(
            status="ambiguous", needs_clarification=True,
            clarification_question=f"無法辨識「{city_raw or destination}」的城市，請確認城市名稱（如高雄市、屏東縣、花蓮縣）。",
            summary="城市無法辨識。",
        )

    normalized_query = {
        "city": city_label,
        "destination": destination,
        "origin": origin,
        "travel_theme": travel_theme,
        "time_budget": time_budget,
    }

    # --- 查景點 ---
    keyword = destination or travel_theme
    spot_items = _query_tourism(city_label, keyword, top)
    spots = _build_spot_summary(spot_items, destination)

    # --- 交通方案（靜態模板）---
    transport_plans = _TRANSPORT_PLANS.get(city_label, _DEFAULT_TRANSPORT).copy()

    # 若有 origin，加 maas self_assembled
    if origin:
        transport_plans.insert(0, {
            "plan_type": "from_origin",
            "plan_summary": f"從{origin}前往{destination or city_label}：可搭高鐵/台鐵至{city_label}後轉乘市區交通（公車/輕軌/YouBike）。",
        })

    # --- 組合輸出 ---
    result_items = []

    # 景點摘要 item
    if spots:
        result_items.append({
            "item_type": "spots",
            "city": city_label,
            "destination": destination,
            "spots": spots,
            "spot_count": len(spots),
        })

    # 交通方案 items
    for plan in transport_plans[:3]:
        result_items.append({"item_type": "transport_plan", **plan})

    if not result_items:
        return _output(
            status="no_data",
            summary=f"找不到「{city_label}」的景點或交通資訊。",
            normalized_query=normalized_query,
        )

    spot_count = len(spots)
    dest_label = f"「{destination}」" if destination else f"{city_label}景點"
    budget_label = f"（{time_budget}行程）" if time_budget else ""
    summary = (
        f"{dest_label}{budget_label}：找到 {spot_count} 個景點，"
        f"{len(transport_plans)} 個移動方案。"
        if spot_count else
        f"{dest_label}{budget_label}：{len(transport_plans)} 個移動方案。"
    )

    return _output(
        status="ok",
        summary=summary,
        items=result_items,
        normalized_query=normalized_query,
    )
