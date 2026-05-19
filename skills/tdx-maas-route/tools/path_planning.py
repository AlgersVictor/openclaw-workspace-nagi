"""方案 A：TDX MaaS /routing live 路徑規劃。"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from runtime.tdx.tdx_auth import TDXAuth, TDXAuthError
from runtime.tdx.tdx_client import TDXClient, TDXClientError
from runtime.tdx.tdx_config import TDXConfig
from runtime.tdx.tdx_poi_data import KNOWN_COORDINATES as _KNOWN_COORDINATES

from .self_assembled import _CITY_CENTER

ROUTING_METHOD = "path_planning_api"
_MAAS_ROUTING_PATH = "/routing"
_GC_VALUE = 1        # 0=door-to-door, 1=station-to-station（max allowed by TDX）
_TOP_VALUE = 3
_TRANSIT_VALUE = 15  # bitmask: THSR=1|TRA=2|MRT=4|BUS=8


def execute(
    origin_resolved: dict[str, Any],
    destination_resolved: dict[str, Any],
    *,
    config: TDXConfig,
    depart_time: dict[str, Any] | None = None,
    preference: str = "fastest",
) -> dict[str, Any]:
    """嘗試使用 TDX MaaS /routing live API。"""
    del preference

    origin_coords = resolve_coordinates(origin_resolved, config=config)
    destination_coords = resolve_coordinates(destination_resolved, config=config)
    if not origin_coords or not destination_coords:
        return {
            "available": False,
            "routing_method": ROUTING_METHOD,
            "reason": "起點或終點無法轉成 MaaS /routing 需要的 lat,lng。",
            "items": [],
            "coordinates": {
                "origin": origin_coords,
                "destination": destination_coords,
            },
        }

    endpoint = f"{getattr(config.api, 'maas_base_url', 'https://tdx.transportdata.tw/api/maas')}{_MAAS_ROUTING_PATH}"
    query_params = {
        "origin": _format_coords(origin_coords),
        "destination": _format_coords(destination_coords),
        "gc": _GC_VALUE,
        "top": _TOP_VALUE,
        "transit": _TRANSIT_VALUE,
    }
    iso_depart = (depart_time or {}).get("normalized_iso8601")
    if iso_depart:
        query_params["depart"] = iso_depart
    endpoint_with_query = f"{endpoint}?{urlencode(query_params)}"

    try:
        token = TDXAuth(config).get_token()
        response = requests.get(
            endpoint,
            params=query_params,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": config.api.user_agent,
            },
            timeout=(config.api.connect_timeout, config.api.read_timeout),
        )
    except TDXAuthError as exc:
        return _failure(f"TDX OAuth 驗證失敗：{exc}", endpoint_with_query, "auth")
    except requests.RequestException as exc:
        return _failure(f"MaaS /routing 請求失敗：{exc}", endpoint_with_query, "request")

    if response.status_code == 429:
        return _failure("MaaS /routing rate limited (429)。", endpoint_with_query, "request", 429)
    if response.status_code >= 400:
        return _failure(
            f"MaaS /routing 回傳 {response.status_code}：{response.text[:300]}",
            endpoint_with_query,
            "request",
            response.status_code,
        )

    body = response.json()
    routes = (((body or {}).get("data") or {}).get("routes")) or []
    items = _normalize_routes(routes)
    if not items:
        return _failure("MaaS /routing live API 無可用路線。", endpoint_with_query, "live_api")

    return {
        "available": True,
        "routing_method": ROUTING_METHOD,
        "summary": f"已取得 {len(items)} 條 MaaS live 路線方案。",
        "items": items,
        "endpoint": endpoint_with_query,
        "coordinates": {
            "origin": origin_coords,
            "destination": destination_coords,
        },
        "source_trace": {"stage": "live_api", "endpoint": endpoint_with_query, "raw_count": len(routes)},
    }


def resolve_coordinates(resolved: dict[str, Any], *, config: TDXConfig) -> dict[str, float] | None:
    """將 resolver 結果轉成 lat,lng。"""
    name = str(resolved.get("normalized_value") or "").strip()
    if name in _KNOWN_COORDINATES:
        lat, lng = _KNOWN_COORDINATES[name]
        return {"lat": lat, "lng": lng}

    city = resolved.get("city")
    if city and city in _CITY_CENTER:
        lng, lat = _CITY_CENTER[city]
        return {"lat": lat, "lng": lng}

    station_coords = _lookup_station_coordinates(name, config=config)
    if station_coords:
        return station_coords
    return None


def _lookup_station_coordinates(name: str, *, config: TDXConfig) -> dict[str, float] | None:
    """用 live station API 補站點座標。"""
    if not name:
        return None

    try:
        client = TDXClient(config, TDXAuth(config))
    except TDXAuthError:
        return None
    query_params = {"$top": 1, "$filter": f"contains(StationName/Zh_tw,'{name}')"}
    for endpoint_key in ("thsr.station", "tra.station"):
        try:
            payload = client.get(endpoint_key, query_params=query_params)
        except (TDXAuthError, TDXClientError):
            continue

        rows = payload.get("Stations", []) if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not rows:
            continue
        position = rows[0].get("StationPosition") or {}
        lat = position.get("PositionLat")
        lng = position.get("PositionLon")
        if lat is not None and lng is not None:
            return {"lat": lat, "lng": lng}
    return None


def _normalize_routes(routes: Any) -> list[dict[str, Any]]:
    """將 MaaS routes 簡化成 skill 輸出。"""
    if not isinstance(routes, list):
        return []

    items: list[dict[str, Any]] = []
    for index, route in enumerate(routes[:3], start=1):
        if not isinstance(route, dict):
            continue

        sections = route.get("sections") or []
        legs: list[dict[str, Any]] = []
        total_minutes = 0
        for section in sections:
            if not isinstance(section, dict):
                continue
            transport = section.get("transport") or {}
            travel_summary = section.get("travelSummary") or {}
            duration = travel_summary.get("duration")
            minutes = int(duration // 60) if isinstance(duration, (int, float)) else None
            if minutes:
                total_minutes += minutes
            legs.append(
                {
                    "mode": transport.get("mode") or section.get("type"),
                    "from": (section.get("from") or {}).get("name"),
                    "to": (section.get("to") or {}).get("name"),
                    "label": transport.get("shortName") or transport.get("name") or section.get("instruction"),
                    "estimated_minutes": minutes,
                    "note": "TDX MaaS live route",
                }
            )

        if not legs:
            continue

        items.append(
            {
                "route_index": index,
                "routing_method": ROUTING_METHOD,
                "mode_primary": legs[0].get("mode"),
                "legs": legs,
                "transfer_count": max(len(legs) - 1, 0),
                "total_estimated_minutes": total_minutes or None,
                "note": "TDX MaaS live route",
            }
        )
    return items


def _format_coords(coords: dict[str, float]) -> str:
    """輸出 lat,lng 字串。"""
    return f"{coords['lat']:.6f},{coords['lng']:.6f}"


def _failure(reason: str, endpoint: str, stage: str, status_code: int | None = None) -> dict[str, Any]:
    """統一失敗輸出。"""
    payload = {
        "available": False,
        "routing_method": ROUTING_METHOD,
        "reason": reason,
        "items": [],
        "endpoint": endpoint,
        "source_trace": {"stage": stage, "endpoint": endpoint},
    }
    if status_code is not None:
        payload["source_trace"]["status_code"] = status_code
    return payload
