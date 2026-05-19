"""tdx-local-travel — 旅遊 / 在地景點交通整合助理 P5

整合：
  - tdx-tourism-info（景點資料）
  - tdx-maas-route self_assembled（交通建議）
策略：先查景點，再組合交通方案，不做完整路線 geocoding。
"""
from __future__ import annotations

import importlib.util
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

# runtime.tdx 可透過 workspace-nagi/runtime/tdx symlink 存取
_WORKSPACE_NAGI = Path(__file__).resolve().parents[3]
if str(_WORKSPACE_NAGI) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_NAGI))

# 城市別名（對應 tourism-info --city 參數）
_CITY_ALIASES: dict[str, str] = {
    "台中": "台中", "臺中": "台中",
    "台南": "台南", "臺南": "台南",
    "高雄": "高雄",
    "台北": "台北", "臺北": "台北",
    "新北": "新北",
    "桃園": "桃園",
    "基隆": "基隆",
    "嘉義": "嘉義",
    "新竹": "新竹",
}

# 常見景點 → 城市對照（無法查 API 時的靜態 fallback）
from runtime.tdx.tdx_poi_data import POI_CITY_MAP as _POI_CITY_MAP

# 交通建議模板（靜態，不需 API）
_TRANSPORT_PLANS: dict[str, list[dict]] = {
    "台中": [
        {"plan_type": "public_transport",
         "plan_summary": "從高鐵台中站搭 BRT 快捷或市區公車前往景點，約 20–40 分鐘。"},
        {"plan_type": "bike_mix",
         "plan_summary": "抵達台中車站後租 YouBike，沿綠園道騎至中區景點，約 15–25 分鐘。"},
    ],
    "台南": [
        {"plan_type": "public_transport",
         "plan_summary": "從台南車站搭 88 號公車或計程車前往安平/赤崁等景點，約 15–30 分鐘。"},
        {"plan_type": "bike_mix",
         "plan_summary": "台南火車站前租 T-Bike，沿府城文化路線騎至各景點，步行距離近。"},
    ],
    "高雄": [
        {"plan_type": "metro",
         "plan_summary": "高雄捷運紅線/橘線直達美麗島、駁二、西子灣等熱門景點。"},
        {"plan_type": "public_transport",
         "plan_summary": "輕軌 C14 駁二藝術特區站，串聯哈瑪星、旗津渡輪碼頭一帶景點。"},
    ],
    "台北": [
        {"plan_type": "metro",
         "plan_summary": "台北捷運覆蓋率高，可搭淡水信義線/板南線直達主要景點。"},
        {"plan_type": "public_transport",
         "plan_summary": "信義區、大安區、萬華區景點可搭公車或步行串聯。"},
    ],
}
_DEFAULT_TRANSPORT = [
    {"plan_type": "public_transport",
     "plan_summary": "建議搭乘當地公車或計程車前往景點，出發前確認班次。"},
]


def _query_tourism(city: str, keyword: str | None, top: int) -> list[dict]:
    """呼叫 tdx-tourism-info bin 查景點，回傳 items list。"""
    cmd = [sys.executable, str(TOURISM_BIN), "scenic_spot",
           "--city", city, "--top", str(top)]
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
    """從 city 或 destination 推斷城市名；無法辨識回 None。"""
    if city_raw:
        resolved = _CITY_ALIASES.get(city_raw)
        if resolved:
            return resolved
        # 部分匹配（如「高雄市」→「高雄」）
        for alias, city in _CITY_ALIASES.items():
            if alias in city_raw or city_raw in alias:
                return city
        return None  # 完全未知城市
    if destination:
        for poi, city in _POI_CITY_MAP.items():
            if poi in destination:
                return city
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

    city = _resolve_city(city_raw, destination)
    if not city:
        return _output(
            status="ambiguous", needs_clarification=True,
            clarification_question=f"無法辨識「{city_raw or destination}」的城市，請確認城市名稱（如台中、台南、高雄）。",
            summary="城市無法辨識。",
        )

    normalized_query = {
        "city": city,
        "destination": destination,
        "origin": origin,
        "travel_theme": travel_theme,
        "time_budget": time_budget,
    }

    # --- 查景點 ---
    keyword = destination or travel_theme
    spot_items = _query_tourism(city, keyword, top)
    spots = _build_spot_summary(spot_items, destination)

    # --- 交通方案（靜態模板）---
    transport_plans = _TRANSPORT_PLANS.get(city, _DEFAULT_TRANSPORT).copy()

    # 若有 origin，加 maas self_assembled
    if origin:
        transport_plans.insert(0, {
            "plan_type": "from_origin",
            "plan_summary": f"從{origin}前往{destination or city}：可搭高鐵/台鐵至{city}後轉乘市區交通（公車/輕軌/YouBike）。",
        })

    # --- 組合輸出 ---
    result_items = []

    # 景點摘要 item
    if spots:
        result_items.append({
            "item_type": "spots",
            "city": city,
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
            summary=f"找不到「{city}」的景點或交通資訊。",
            normalized_query=normalized_query,
        )

    spot_count = len(spots)
    dest_label = f"「{destination}」" if destination else f"{city}市景點"
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
