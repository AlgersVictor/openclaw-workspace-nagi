"""停車場剩餘車位查詢。

接收 city（+ optional keyword），查詢 TDX Parking v1 API。
"""

from __future__ import annotations

from typing import Any

from runtime.tdx.tdx_auth import TDXAuth, TDXAuthError
from runtime.tdx.tdx_client import TDXClient, TDXClientError
from runtime.tdx.tdx_config import TDXConfig
from runtime.tdx.tdx_entity_resolver import TDXEntityResolver
from runtime.tdx.tdx_output import build_output
from runtime.tdx.tdx_url import build_url

SKILL = "tdx-local-query"
SUB_COMMAND = "parking_query"
ENDPOINT_KEY = "parking.availability"


def execute(
    params: dict[str, Any],
    *,
    config: TDXConfig,
    resolver: TDXEntityResolver,
) -> dict[str, Any]:
    """執行停車場查詢。

    Args:
        params: 查詢參數（city, keyword, limit）。
        config: TDXConfig。
        resolver: TDXEntityResolver。

    Returns:
        符合 Tool Output Contract 的 dict。
    """
    city_raw = params.get("city")
    keyword = params.get("keyword")
    limit = params.get("limit", 10)

    if not city_raw:
        return build_output(
            config,
            skill=SKILL,
            sub_command=SUB_COMMAND,
            status="invalid_input",
            needs_clarification=True,
            clarification_question="請提供城市名稱，例如「台北」或「高雄」。",
            errors=["缺少 city"],
        )

    city_result = resolver.resolve_city(city_raw)
    if city_result["needs_clarification"]:
        candidates = city_result.get("candidates", [])
        question = (
            f"城市「{city_raw}」有多個候選：{candidates}，請指定。"
            if candidates
            else f"無法辨識城市「{city_raw}」，請確認。"
        )
        return build_output(
            config,
            skill=SKILL,
            sub_command=SUB_COMMAND,
            status="ambiguous",
            needs_clarification=True,
            clarification_question=question,
            normalized_query={"city": city_result, "keyword": keyword},
            errors=["city ambiguous"],
        )

    city_en = city_result["normalized_value"]
    normalized_query: dict[str, Any] = {
        "city": city_result,
        "keyword": keyword,
    }
    query_params: dict[str, str | int] = {"$top": limit}

    try:
        url = build_url(
            config,
            ENDPOINT_KEY,
            path_params={"city": city_en},
            query_params=query_params,
        )
    except ValueError as exc:
        return build_output(
            config,
            skill=SKILL,
            sub_command=SUB_COMMAND,
            status="upstream_error",
            normalized_query=normalized_query,
            errors=[str(exc)],
        )

    try:
        payload = _build_live_client(config).get(
            ENDPOINT_KEY,
            path_params={"city": city_en},
            query_params=query_params,
        )
    except TDXAuthError as exc:
        result = build_output(
            config,
            skill=SKILL,
            sub_command=SUB_COMMAND,
            status="auth_error",
            summary="TDX OAuth 驗證失敗，無法查詢停車場資料。",
            normalized_query=normalized_query,
            endpoint=url,
            errors=[str(exc)],
        )
        result["source_trace"] = {"stage": "auth", "endpoint": url}
        return result
    except TDXClientError as exc:
        status = "rate_limited" if "429" in str(exc) or "rate limited" in str(exc) else "upstream_error"
        result = build_output(
            config,
            skill=SKILL,
            sub_command=SUB_COMMAND,
            status=status,
            summary="TDX 停車場 API 暫時不可用。",
            normalized_query=normalized_query,
            endpoint=url,
            errors=[str(exc)],
        )
        result["source_trace"] = {"stage": "request", "endpoint": url}
        return result

    items = _normalize_items(payload, keyword)
    result = build_output(
        config,
        skill=SKILL,
        sub_command=SUB_COMMAND,
        status="ok" if items else "no_data",
        summary=(
            f"已取得停車場剩餘車位：{city_en}，共 {len(items)} 筆。"
            if items
            else f"TDX 未回傳 {city_en} 的停車場資料。"
        ),
        normalized_query=normalized_query,
        items=items,
        endpoint=url,
        fallback_used=False,
    )
    result["source_trace"] = {"stage": "live_api", "endpoint": url, "raw_count": len(payload) if isinstance(payload, list) else 0}
    return result


def _build_live_client(config: TDXConfig) -> TDXClient:
    """建立可呼叫 live API 的 TDX client。"""
    return TDXClient(config, TDXAuth(config))


def _normalize_items(payload: Any, keyword: str | None) -> list[dict[str, Any]]:
    """將 TDX ParkingAvailability 原始資料轉成穩定輸出。"""
    if not isinstance(payload, list):
        return []

    items: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        name = (row.get("ParkingName") or {}).get("Zh_tw") or row.get("ParkingName")
        if keyword and name and keyword not in str(name):
            continue
        items.append(
            {
                "parking_id": row.get("ParkingAvailableID") or row.get("ParkingID"),
                "name": name,
                "total_spaces": row.get("TotalSpaces"),
                "available_spaces": row.get("AvailableSpaces"),
                "charge_free": row.get("ChargeFree"),
                "address": (row.get("Address") or {}).get("Zh_tw") or row.get("Address"),
                "update_time": row.get("UpdateTime"),
            }
        )
    return items
