"""Phase 2A metro query skeleton built on shared-core."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
SHARED_CORE_DIR = CURRENT_DIR.parent / "tdx-shared-core"
if str(SHARED_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_CORE_DIR))

from endpoint_registry import get_endpoint
from query_option_builder import build_query_options
from resolver_rail_system import resolve_rail_system
from resolver_station_alias import resolve_station_alias
from tdx_auth import TdxAuthError, TdxAuthManager
from tdx_client import TdxClient, TdxClientError

from metro_formatter import (
    format_frequency_summary,
    format_liveboard_summary,
    format_route_summary,
    format_s2s_summary,
    format_station_summary,
    format_station_timetable_summary,
    format_transfer_summary,
)
from metro_mapper import (
    map_frequency_payload,
    map_liveboard_payload,
    map_route_payload,
    map_s2s_travel_time_payload,
    map_station_payload,
    map_station_timetable_payload,
    map_transfer_station_payload,
)

TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
LIVE_INTENTS = {
    "station_info": "metro_station",
    "liveboard": "metro_liveboard",
    "frequency": "metro_frequency",
    "s2s_travel_time": "metro_s2s_travel_time",
    "route_info": "metro_route",
    "station_timetable": "metro_station_timetable",
    "transfer_stations": "metro_transfer_stations",
}


def _build_output(
    *,
    status: str,
    intent: str,
    rail_system: str | None,
    normalized_station: str | None,
    endpoint: str,
    validation_state: str,
    summary: str,
    items: list[dict[str, Any]],
    needs_clarification: bool = False,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "intent": intent,
        "rail_system": rail_system,
        "normalized_station": normalized_station,
        "source": {
            "provider": "TDX",
            "endpoint": endpoint,
            "validation_state": validation_state,
        },
        "summary": summary,
        "items": items,
    }
    if needs_clarification:
        payload["needs_clarification"] = True
    if unavailable_reason:
        payload["unavailable_reason"] = unavailable_reason
    return payload


def _resolve_context(params: dict[str, Any]) -> tuple[dict[str, object], dict[str, object]]:
    rail_result = resolve_rail_system(params.get("rail_system"))
    if rail_result["needs_clarification"]:
        return rail_result, {
            "status": "needs_clarification",
            "normalized_value": None,
            "needs_clarification": True,
            "candidates": [],
            "details": {"reason": "rail_system_missing_or_unknown"},
        }
    station_result = resolve_station_alias(params.get("station_name"), rail_result["normalized_value"])
    return rail_result, station_result


def _station_name_matches(api_name: str | None, resolved_name: str | None) -> bool:
    if not api_name or not resolved_name:
        return False
    if api_name == resolved_name:
        return True
    stripped = resolved_name.rstrip("站")
    return api_name == stripped or api_name.rstrip("站") == stripped


def _build_endpoint_url(endpoint_meta: dict[str, str], rail_system: str) -> str:
    return endpoint_meta["base_url"] + endpoint_meta["path"].replace("{RailSystem}", rail_system)


def _load_fixture(name: str) -> list[dict[str, Any]]:
    fixture_path = CURRENT_DIR.parent.parent / "fixtures" / "tdx" / "metro" / name
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def execute(params: dict[str, Any], client: TdxClient | None = None) -> dict[str, Any]:
    intent = str(params.get("intent") or "").strip()
    if not intent:
        return _build_output(
            status="invalid_input",
            intent="",
            rail_system=None,
            normalized_station=None,
            endpoint="",
            validation_state="not_prechecked",
            summary="缺少 intent。",
            items=[],
            needs_clarification=True,
            unavailable_reason="missing_intent",
        )

    rail_result, station_result = _resolve_context(params)
    if rail_result["needs_clarification"]:
        return _build_output(
            status="needs_clarification",
            intent=intent,
            rail_system=None,
            normalized_station=None,
            endpoint="",
            validation_state="not_prechecked",
            summary="請先指定台北捷運、高雄捷運或高雄輕軌。",
            items=[],
            needs_clarification=True,
            unavailable_reason="missing_or_unknown_rail_system",
        )

    rail_system = str(rail_result["normalized_value"])
    normalized_station = station_result.get("normalized_value")

    if intent in {"station_info", "liveboard", "station_timetable"}:
        if station_result["needs_clarification"]:
            reason = station_result["details"]["reason"]
            # 站名在 resolver 未收錄時（unknown_station_alias），改用 raw 站名過濾
            if reason == "unknown_station_alias":
                normalized_station = params.get("station_name", "").strip()
            else:
                return _build_output(
                    status="needs_clarification",
                    intent=intent,
                    rail_system=rail_system,
                    normalized_station=None,
                    endpoint="",
                    validation_state="not_prechecked",
                    summary="站名不足或有歧義，請補充明確站名。",
                    items=[],
                    needs_clarification=True,
                    unavailable_reason=reason,
                )

    if intent not in LIVE_INTENTS:
        return _build_output(
            status="invalid_input",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint="",
            validation_state="not_prechecked",
            summary=f"不支援的 metro intent: {intent}",
            items=[],
            unavailable_reason="unsupported_intent",
        )

    endpoint_key = LIVE_INTENTS[intent]
    endpoint_meta = get_endpoint(endpoint_key)
    endpoint_url = _build_endpoint_url(endpoint_meta, rail_system)
    top = 200 if intent in {"station_info", "station_timetable"} else 50
    query_options = build_query_options(top=top, fmt="JSON")

    if client is None:  # pragma: no cover - tests inject fake client
        client = TdxClient(TdxAuthManager(TOKEN_URL))

    try:
        response = client.get(endpoint_url, query_options)
    except (TdxAuthError, TdxClientError) as exc:
        return _build_output(
            status="auth_error" if isinstance(exc, TdxAuthError) else "upstream_error",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=endpoint_url,
            validation_state=endpoint_meta["validation_state"],
            summary=str(exc),
            items=[],
            unavailable_reason=type(exc).__name__,
        )

    payload = response.data
    if intent == "station_info":
        items = [
            item for item in map_station_payload(payload)
            if _station_name_matches(item["station_name"], normalized_station)
        ]
        summary = format_station_summary(rail_system, normalized_station, len(items))
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=summary,
            items=items,
        )

    if intent == "frequency":
        items = map_frequency_payload(payload)
        summary = format_frequency_summary(rail_system, len(items))
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=summary,
            items=items,
        )

    if intent == "s2s_travel_time":
        items = map_s2s_travel_time_payload(payload)
        dest = params.get("destination_station")
        if dest:
            items = [i for i in items if dest in str(i["to_station_id"])]
        summary = format_s2s_summary(rail_system, len(items))
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=summary,
            items=items,
        )

    if intent == "route_info":
        items = map_route_payload(payload)
        summary = format_route_summary(rail_system, len(items))
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=summary,
            items=items,
        )

    if intent == "station_timetable":
        items = [
            item for item in map_station_timetable_payload(payload)
            if _station_name_matches(item["station_name"], normalized_station)
        ]
        summary = format_station_timetable_summary(rail_system, normalized_station, len(items))
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=summary,
            items=items,
        )

    if intent == "transfer_stations":
        items = map_transfer_station_payload(payload)
        summary = format_transfer_summary(rail_system, len(items))
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=summary,
            items=items,
        )

    items = [
        item for item in map_liveboard_payload(payload)
        if _station_name_matches(item["station_name"], normalized_station)
    ]
    if not items:
        return _build_output(
            status="ok",
            intent=intent,
            rail_system=rail_system,
            normalized_station=normalized_station,
            endpoint=response.url,
            validation_state=endpoint_meta["validation_state"],
            summary=f"{normalized_station} 目前沒有即時看板資料。",
            items=[],
        )

    summary = format_liveboard_summary(rail_system, normalized_station, len(items))
    return _build_output(
        status="ok",
        intent=intent,
        rail_system=rail_system,
        normalized_station=normalized_station,
        endpoint=response.url,
        validation_state=endpoint_meta["validation_state"],
        summary=summary,
        items=items,
    )
