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
        # 無此站（KLRT 無美麗島站）
        "美麗島": {"station_name": None, "station_id": None},
        # 以下站名與 station_id 均來自 TDX API（2026-05-21 驗證）
        "籬仔內": {"station_name": "籬仔內", "station_id": "C1"},
        "凱旋瑞田": {"station_name": "凱旋瑞田", "station_id": "C2"},
        "前鎮之星": {"station_name": "前鎮之星", "station_id": "C3"},
        "凱旋中華": {"station_name": "凱旋中華", "station_id": "C4"},
        "夢時代": {"station_name": "夢時代", "station_id": "C5"},
        "經貿園區": {"station_name": "經貿園區", "station_id": "C6"},
        "軟體園區": {"station_name": "軟體園區", "station_id": "C7"},
        "高雄展覽館": {"station_name": "高雄展覽館", "station_id": "C8"},
        "旅運中心": {"station_name": "旅運中心", "station_id": "C9"},
        "光榮碼頭": {"station_name": "光榮碼頭", "station_id": "C10"},
        "真愛碼頭": {"station_name": "真愛碼頭", "station_id": "C11"},
        "駁二大義": {"station_name": "駁二大義", "station_id": "C12"},
        "駁二蓬萊": {"station_name": "駁二蓬萊", "station_id": "C13"},
        "哈瑪星": {"station_name": "哈瑪星", "station_id": "C14"},
        "壽山公園站": {"station_name": "壽山公園站", "station_id": "C15"},
        "壽山公園": {"station_name": "壽山公園站", "station_id": "C15"},
        "文武聖殿站": {"station_name": "文武聖殿站", "station_id": "C16"},
        "文武聖殿": {"station_name": "文武聖殿站", "station_id": "C16"},
        "鼓山區公所站": {"station_name": "鼓山區公所站", "station_id": "C17"},
        "鼓山區公所": {"station_name": "鼓山區公所站", "station_id": "C17"},
        "鼓山": {"station_name": "鼓山", "station_id": "C18"},
        "馬卡道": {"station_name": "馬卡道", "station_id": "C19"},
        "臺鐵美術館": {"station_name": "臺鐵美術館", "station_id": "C20"},
        "台鐵美術館": {"station_name": "臺鐵美術館", "station_id": "C20"},
        "美術館": {"station_name": "美術館", "station_id": "C21"},
        "內惟藝術中心": {"station_name": "內惟藝術中心", "station_id": "C21A"},
        "聯合醫院": {"station_name": "聯合醫院", "station_id": "C22"},
        "龍華國小": {"station_name": "龍華國小", "station_id": "C23"},
        "愛河之心": {"station_name": "愛河之心", "station_id": "C24"},
        "新上國小": {"station_name": "新上國小", "station_id": "C25"},
        "大順民族": {"station_name": "大順民族", "station_id": "C26"},
        "灣仔內(大順鼎山)": {"station_name": "灣仔內(大順鼎山)", "station_id": "C27"},
        "灣仔內": {"station_name": "灣仔內(大順鼎山)", "station_id": "C27"},
        "大順鼎山": {"station_name": "灣仔內(大順鼎山)", "station_id": "C27"},
        "高雄高工": {"station_name": "高雄高工", "station_id": "C28"},
        "樹德家商": {"station_name": "樹德家商", "station_id": "C29"},
        "科工館": {"station_name": "科工館", "station_id": "C30"},
        "聖功醫院": {"station_name": "聖功醫院", "station_id": "C31"},
        "凱旋公園站": {"station_name": "凱旋公園站", "station_id": "C32"},
        "凱旋公園": {"station_name": "凱旋公園站", "station_id": "C32"},
        "衛生局站": {"station_name": "衛生局站", "station_id": "C33"},
        "衛生局": {"station_name": "衛生局站", "station_id": "C33"},
        "五權國小站": {"station_name": "五權國小站", "station_id": "C34"},
        "五權國小": {"station_name": "五權國小站", "station_id": "C34"},
        "凱旋武昌站": {"station_name": "凱旋武昌站", "station_id": "C35"},
        "凱旋武昌": {"station_name": "凱旋武昌站", "station_id": "C35"},
        "凱旋二聖站": {"station_name": "凱旋二聖站", "station_id": "C36"},
        "凱旋二聖": {"station_name": "凱旋二聖站", "station_id": "C36"},
        "輕軌機廠站": {"station_name": "輕軌機廠站", "station_id": "C37"},
        "輕軌機廠": {"station_name": "輕軌機廠站", "station_id": "C37"},
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
