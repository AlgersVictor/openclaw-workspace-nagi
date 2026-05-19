"""國道路段查詢：事件（事故/施工/管制）+ 即時車速。

以起訖交流道名稱為輸入，動態解析 km 範圍後篩選。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[2] / "tdx-shared-core"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from tdx_auth import TdxAuthManager, TdxAuthError
from tdx_client import TdxClient, TdxClientError

TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
BASE      = "https://tdx.transportdata.tw/api/basic"

_EVENT_TYPE = {1:"事故", 2:"故障車", 3:"施工", 4:"特殊管制", 5:"天災", 6:"交通管制", 7:"路況", 8:"其他"}
_EVENT_STEP = {1:"發生中", 2:"已清除", 3:"預告"}
_SEVERITY   = {0:"無影響", 1:"輕微", 2:"中等", 3:"嚴重"}
_LEVEL      = {"1":"暢通", "2":"稍壅塞", "3":"壅塞", "4":"嚴重壅塞",
               "A":"暢通", "B":"稍壅塞", "C":"壅塞", "D":"嚴重壅塞"}


def _normalize_ic(name: str) -> str:
    """去除「交流道」「系統」「服務區」等後綴，取核心關鍵字。"""
    for suffix in ("交流道", "系統交流道", "系統", "服務區", "收費站"):
        name = name.replace(suffix, "")
    return name.strip()


def _km_float(km_str: str) -> float:
    """'358K+500' → 358.5"""
    try:
        parts = km_str.replace("K+", "|").split("|")
        return float(parts[0]) + float(parts[1]) / 1000
    except Exception:
        return -1.0


def _resolve_km_range(
    sections: list[dict],
    road: str,
    direction: str,
    from_kw: str,
    to_kw: str,
) -> tuple[float, float]:
    """從靜態路段資料找起訖交流道的 km 範圍。"""
    matched_km: list[float] = []
    for s in sections:
        if s.get("RoadName") != road:
            continue
        if s.get("RoadDirection") not in (direction[0], direction):
            continue
        sec_start = s.get("RoadSection", {}).get("Start", "")
        sec_end   = s.get("RoadSection", {}).get("End", "")
        if from_kw in sec_start or from_kw in sec_end or to_kw in sec_start or to_kw in sec_end:
            matched_km.append(_km_float(s["SectionMile"]["StartKM"]))
            matched_km.append(_km_float(s["SectionMile"]["EndKM"]))

    if not matched_km:
        return (-1.0, -1.0)
    return (min(matched_km), max(matched_km))


def query_segment(
    road: str,
    direction: str,
    from_ic: str,
    to_ic: str,
) -> dict[str, Any]:
    """
    查詢國道指定路段的即時事件 + 車速。

    Args:
        road:      路名，如「國道1號」
        direction: 「北向」或「南向」
        from_ic:   起點交流道，如「中正交流道」
        to_ic:     終點交流道，如「岡山交流道」
    """
    from_kw = _normalize_ic(from_ic)
    to_kw   = _normalize_ic(to_ic)
    dir_code = "N" if "北" in direction else "S"

    try:
        auth   = TdxAuthManager(TOKEN_URL)
        client = TdxClient(auth)

        # 靜態路段資料（解析 km 範圍）
        sec_resp  = client.get(f"{BASE}/v2/Road/Traffic/Section/Freeway",  params={"$format": "JSON"})
        sections  = sec_resp.data.get("Sections", [])

        km_min, km_max = _resolve_km_range(sections, road, dir_code, from_kw, to_kw)
        km_ok = km_min >= 0 and km_max > km_min

        # 即時事件
        evt_resp = client.get(f"{BASE}/v1/Traffic/RoadEvent/LiveEvent/Freeway", params={"$format": "JSON"})
        all_events = evt_resp.data.get("LiveEvents", [])

        # 即時車速
        live_resp = client.get(f"{BASE}/v2/Road/Traffic/Live/Freeway", params={"$format": "JSON"})
        all_live  = live_resp.data.get("LiveTraffics", [])

    except TdxAuthError as exc:
        return _err("auth_error", road, direction, from_ic, to_ic, str(exc))
    except TdxClientError as exc:
        return _err("upstream_error", road, direction, from_ic, to_ic, str(exc))

    # 建 SectionID → section 靜態 map
    sec_map = {s["SectionID"]: s for s in sections}

    # 篩事件
    events_out: list[dict] = []
    for e in all_events:
        loc = e.get("Location", {}).get("FreeExpressHighway", {})
        if loc.get("Road") != road:
            continue
        if direction not in loc.get("Direction", ""):
            continue
        e_km = _km_float(loc.get("StartKM", ""))
        sec_s = loc.get("SectionStart", "")
        sec_e = loc.get("SectionEnd", "")
        in_km = km_ok and km_min <= e_km <= km_max
        in_kw = from_kw in sec_s or from_kw in sec_e or to_kw in sec_s or to_kw in sec_e
        if in_km or in_kw:
            events_out.append({
                "type":       _EVENT_TYPE.get(e["EventType"], str(e["EventType"])),
                "step":       _EVENT_STEP.get(e["EventStep"], str(e["EventStep"])),
                "severity":   _SEVERITY.get(e["Impact"]["Severity"], str(e["Impact"]["Severity"])),
                "location":   f'{road} {direction} {loc.get("StartKM","")}~{loc.get("EndKM","")}',
                "section":    f'{sec_s}→{sec_e}',
                "description": e.get("Description", ""),
                "effective_time": e.get("EffectiveTime", ""),
            })

    # 篩車速路段
    sections_out: list[dict] = []
    for live in all_live:
        sid  = live["SectionID"]
        info = sec_map.get(sid)
        if not info:
            continue
        if info.get("RoadName") != road or info.get("RoadDirection") != dir_code:
            continue
        s_km = _km_float(info["SectionMile"]["StartKM"])
        e_km = _km_float(info["SectionMile"]["EndKM"])
        if km_ok and not (km_min <= s_km <= km_max or km_min <= e_km <= km_max):
            continue
        sec_s = info.get("RoadSection", {}).get("Start", "")
        sec_e = info.get("RoadSection", {}).get("End", "")
        in_kw = from_kw in sec_s or from_kw in sec_e or to_kw in sec_s or to_kw in sec_e
        if not km_ok and not in_kw:
            continue
        sections_out.append({
            "section":         f'{sec_s}→{sec_e}',
            "km":              f'{info["SectionMile"]["StartKM"]}~{info["SectionMile"]["EndKM"]}',
            "speed_kmh":       live["TravelSpeed"],
            "travel_time_sec": live["TravelTime"],
            "congestion":      _LEVEL.get(live.get("CongestionLevelID", live.get("CongestionLevel", "")),
                                          live.get("CongestionLevel", "")),
        })

    # 摘要
    if events_out:
        active = [e for e in events_out if e["step"] == "發生中"]
        summary = (
            f'{road} {direction} {from_ic}→{to_ic} '
            f'有 {len(active)} 起進行中事件（共 {len(events_out)} 筆）'
        )
    else:
        summary = f'{road} {direction} {from_ic}→{to_ic} 目前無事故或管制事件'

    return {
        "status":     "ok",
        "road":       road,
        "direction":  direction,
        "from_ic":    from_ic,
        "to_ic":      to_ic,
        "km_range":   f"{km_min:.1f}K~{km_max:.1f}K" if km_ok else "未能解析",
        "summary":    summary,
        "events":     events_out,
        "event_count": len(events_out),
        "sections":   sections_out,
    }


def _err(status: str, road: str, direction: str, from_ic: str, to_ic: str, error: str) -> dict[str, Any]:
    return {
        "status":     status,
        "road":       road,
        "direction":  direction,
        "from_ic":    from_ic,
        "to_ic":      to_ic,
        "summary":    error,
        "events":     [],
        "event_count": 0,
        "sections":   [],
        "error":      error,
    }
