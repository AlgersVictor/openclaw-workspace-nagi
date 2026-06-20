"""Phase 2B road-live query skeleton."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
SHARED_CORE_DIR = CURRENT_DIR.parent / "tdx-shared-core"
if str(SHARED_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_CORE_DIR))

from endpoint_registry import get_endpoint
from query_option_builder import build_query_options
from resolver_city import resolve_city
from tdx_auth import TdxAuthError, TdxAuthManager
from tdx_client import TdxClient, TdxClientError

from road_live_formatter import format_cctv_summary, format_congestion_summary, format_live_traffic_summary, format_mapped_only_summary, format_traffic_news_summary
from road_live_mapper import (
    map_cctv_payload,
    map_congestion_payload,
    map_live_traffic_payload,
    map_traffic_news_payload,
)

TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
INTENT_TO_ENDPOINT = {
    "traffic_live_summary": "road_live_city",
    "congestion_level": "road_congestion_level_city",
    "traffic_news": "road_live_news_city",
    "cctv_info": "road_cctv_city",
}
PRECHECKED_INTENTS = {"traffic_live_summary", "traffic_news", "congestion_level", "cctv_info"}


def _build_output(
    *,
    status: str,
    intent: str,
    normalized_city: str | None,
    endpoint: str,
    validation_state: str,
    summary: str,
    items: list[dict[str, Any]],
    unavailable_reason: str | None = None,
    needs_clarification: bool = False,
    filters_applied: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "intent": intent,
        "normalized_city": normalized_city,
        "source": {
            "provider": "TDX",
            "endpoint": endpoint,
            "validation_state": validation_state,
        },
        "summary": summary,
        "items": items,
    }
    if unavailable_reason:
        payload["unavailable_reason"] = unavailable_reason
    if needs_clarification:
        payload["needs_clarification"] = True
    if filters_applied:
        payload["filters_applied"] = filters_applied
    return payload


def _build_endpoint_url(endpoint_meta: dict[str, str], normalized_city: str) -> str:
    return endpoint_meta["base_url"] + endpoint_meta["path"].replace("{City}", normalized_city)


def _mapped_only_response(intent: str, city_label: str, normalized_city: str) -> dict[str, Any]:
    endpoint_meta = get_endpoint(INTENT_TO_ENDPOINT[intent])
    endpoint_url = _build_endpoint_url(endpoint_meta, normalized_city)
    return _build_output(
        status="ok",
        intent=intent,
        normalized_city=normalized_city,
        endpoint=endpoint_url,
        validation_state=endpoint_meta["validation_state"],
        summary=format_mapped_only_summary(intent, city_label),
        items=[],
        unavailable_reason="not_prechecked_phase_2b",
    )


def execute(params: dict[str, Any], client: TdxClient | None = None) -> dict[str, Any]:
    intent = str(params.get("intent") or "").strip()
    if intent not in INTENT_TO_ENDPOINT:
        return _build_output(
            status="invalid_input",
            intent=intent,
            normalized_city=None,
            endpoint="",
            validation_state="not_prechecked",
            summary=f"不支援的 road-live intent: {intent}",
            items=[],
            unavailable_reason="unsupported_intent",
        )

    city_result = resolve_city(params.get("city"))
    if city_result["needs_clarification"]:
        return _build_output(
            status="needs_clarification",
            intent=intent,
            normalized_city=None,
            endpoint="",
            validation_state="not_prechecked",
            summary="請先提供縣市，例如台北市、台南市、高雄市。",
            items=[],
            unavailable_reason=city_result["details"]["reason"],
            needs_clarification=True,
        )

    normalized_city = str(city_result["normalized_value"])
    city_label = str(city_result["details"]["label"])

    if intent not in PRECHECKED_INTENTS:
        return _mapped_only_response(intent, city_label, normalized_city)

    endpoint_meta = get_endpoint(INTENT_TO_ENDPOINT[intent])
    endpoint_url = _build_endpoint_url(endpoint_meta, normalized_city)
    query_options = build_query_options(top=int(params.get("top", 3)), fmt=str(params.get("format", "JSON")))

    if client is None:  # pragma: no cover
        client = TdxClient(TdxAuthManager(TOKEN_URL))

    try:
        response = client.get(endpoint_url, query_options)
    except TdxAuthError as exc:
        return _build_output(
            status="auth_error",
            intent=intent,
            normalized_city=normalized_city,
            endpoint=endpoint_url,
            validation_state=endpoint_meta["validation_state"],
            summary=str(exc),
            items=[],
            unavailable_reason="auth_error",
        )
    except TdxClientError as exc:
        return _build_output(
            status="upstream_error",
            intent=intent,
            normalized_city=normalized_city,
            endpoint=endpoint_url,
            validation_state=endpoint_meta["validation_state"],
            summary=str(exc),
            items=[],
            unavailable_reason="upstream_error",
        )

    if intent == "traffic_news":
        items = map_traffic_news_payload(response.data)
        summary = format_traffic_news_summary(city_label, len(items))
    elif intent == "congestion_level":
        items = map_congestion_payload(response.data)
        summary = format_congestion_summary(city_label, len(items))
    elif intent == "cctv_info":
        items = map_cctv_payload(response.data)
        if params.get("keyword"):
            kw = str(params["keyword"])
            items = [i for i in items if kw in str(i["road_name"]) or kw in str(i["city"])]
        summary = format_cctv_summary(city_label, len(items))
    else:
        items = map_live_traffic_payload(response.data)
        if params.get("keyword"):
            keyword = str(params["keyword"])
            items = [item for item in items if keyword in str(item["section_id"])]
        summary = format_live_traffic_summary(city_label, len(items))
    return _build_output(
        status="ok",
        intent=intent,
        normalized_city=normalized_city,
        endpoint=response.url,
        validation_state=endpoint_meta["validation_state"],
        summary=summary,
        items=items,
        filters_applied={"keyword": params.get("keyword")},
    )
