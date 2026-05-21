"""Minimal station alias resolver for Phase 2A metro scope."""

from __future__ import annotations

STATION_ALIAS_MAP = {
    "TRTC": {
        "台北車站": {"station_name": "台北車站", "station_id": "BL12/R10"},
        "北車": {"station_name": "台北車站", "station_id": "BL12/R10"},
    },
    "KRTC": {
        "美麗島": {"station_name": "美麗島站", "station_id": "R10/O5"},
        "左營": {"station_name": "左營站", "station_id": "R16"},
        "哈瑪星": {"station_name": "哈瑪星", "station_id": "O1"},
    },
    "KLRT": {
        "美麗島": {"station_name": None, "station_id": None},
        "哈瑪星": {"station_name": "哈瑪星", "station_id": "C14"},
        "駁二蓬萊": {"station_name": "駁二蓬萊", "station_id": "C13"},
        "駁二大義": {"station_name": "駁二大義", "station_id": "C15"},
        "光榮碼頭": {"station_name": "光榮碼頭", "station_id": "C12"},
        "高雄展覽館": {"station_name": "高雄展覽館", "station_id": "C11"},
    },
}

AMBIGUOUS_ALIASES = {
    "左營": ["高鐵左營站", "新左營站", "高雄捷運左營站"],
}


def resolve_station_alias(raw: str | None, rail_system: str | None = None) -> dict[str, object]:
    value = (raw or "").strip()
    if not value:
        return {
            "status": "invalid_input",
            "normalized_value": None,
            "needs_clarification": True,
            "candidates": [],
            "details": {"reason": "missing_station"},
        }

    if rail_system:
        mapping = STATION_ALIAS_MAP.get(rail_system, {})
        match = mapping.get(value)
        if match and match["station_name"]:
            return {
                "status": "ok",
                "normalized_value": match["station_name"],
                "needs_clarification": False,
                "candidates": [],
                "details": {
                    "station_id": match["station_id"],
                    "rail_system": rail_system,
                    "raw": value,
                },
            }

    if value in AMBIGUOUS_ALIASES:
        return {
            "status": "needs_clarification",
            "normalized_value": None,
            "needs_clarification": True,
            "candidates": AMBIGUOUS_ALIASES[value],
            "details": {"reason": "ambiguous_station_alias", "raw": value, "rail_system": rail_system},
        }

    return {
        "status": "needs_clarification",
        "normalized_value": None,
        "needs_clarification": True,
        "candidates": [],
        "details": {"reason": "unknown_station_alias", "raw": value, "rail_system": rail_system},
    }
