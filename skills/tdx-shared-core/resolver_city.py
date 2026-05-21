"""TDX City resolver for common Chinese aliases."""

from __future__ import annotations

CITY_ALIASES = {
    # 直轄市
    "台北": {"city": "Taipei", "label": "台北市"},
    "臺北": {"city": "Taipei", "label": "台北市"},
    "台北市": {"city": "Taipei", "label": "台北市"},
    "臺北市": {"city": "Taipei", "label": "台北市"},
    "新北": {"city": "NewTaipei", "label": "新北市"},
    "新北市": {"city": "NewTaipei", "label": "新北市"},
    "桃園": {"city": "Taoyuan", "label": "桃園市"},
    "桃園市": {"city": "Taoyuan", "label": "桃園市"},
    "台中": {"city": "Taichung", "label": "台中市"},
    "臺中": {"city": "Taichung", "label": "台中市"},
    "台中市": {"city": "Taichung", "label": "台中市"},
    "臺中市": {"city": "Taichung", "label": "台中市"},
    "台南": {"city": "Tainan", "label": "台南市"},
    "臺南": {"city": "Tainan", "label": "台南市"},
    "台南市": {"city": "Tainan", "label": "台南市"},
    "臺南市": {"city": "Tainan", "label": "台南市"},
    "高雄": {"city": "Kaohsiung", "label": "高雄市"},
    "高雄市": {"city": "Kaohsiung", "label": "高雄市"},
    # 省轄市
    "基隆": {"city": "Keelung", "label": "基隆市"},
    "基隆市": {"city": "Keelung", "label": "基隆市"},
    "新竹市": {"city": "Hsinchu", "label": "新竹市"},
    "嘉義市": {"city": "ChiayiCity", "label": "嘉義市"},
    # 縣
    "新竹": {"city": "HsinchuCounty", "label": "新竹縣"},
    "新竹縣": {"city": "HsinchuCounty", "label": "新竹縣"},
    "苗栗": {"city": "MiaoliCounty", "label": "苗栗縣"},
    "苗栗縣": {"city": "MiaoliCounty", "label": "苗栗縣"},
    "彰化": {"city": "ChanghuaCounty", "label": "彰化縣"},
    "彰化縣": {"city": "ChanghuaCounty", "label": "彰化縣"},
    "南投": {"city": "NantouCounty", "label": "南投縣"},
    "南投縣": {"city": "NantouCounty", "label": "南投縣"},
    "雲林": {"city": "YunlinCounty", "label": "雲林縣"},
    "雲林縣": {"city": "YunlinCounty", "label": "雲林縣"},
    "嘉義": {"city": "ChiayiCounty", "label": "嘉義縣"},
    "嘉義縣": {"city": "ChiayiCounty", "label": "嘉義縣"},
    "屏東": {"city": "PingtungCounty", "label": "屏東縣"},
    "屏東縣": {"city": "PingtungCounty", "label": "屏東縣"},
    "宜蘭": {"city": "YilanCounty", "label": "宜蘭縣"},
    "宜蘭縣": {"city": "YilanCounty", "label": "宜蘭縣"},
    "花蓮": {"city": "HualienCounty", "label": "花蓮縣"},
    "花蓮縣": {"city": "HualienCounty", "label": "花蓮縣"},
    "台東": {"city": "TaitungCounty", "label": "台東縣"},
    "臺東": {"city": "TaitungCounty", "label": "台東縣"},
    "台東縣": {"city": "TaitungCounty", "label": "台東縣"},
    "臺東縣": {"city": "TaitungCounty", "label": "台東縣"},
    "澎湖": {"city": "PenghuCounty", "label": "澎湖縣"},
    "澎湖縣": {"city": "PenghuCounty", "label": "澎湖縣"},
    "金門": {"city": "KinmenCounty", "label": "金門縣"},
    "金門縣": {"city": "KinmenCounty", "label": "金門縣"},
    "連江": {"city": "LienchiangCounty", "label": "連江縣"},
    "連江縣": {"city": "LienchiangCounty", "label": "連江縣"},
    "馬祖": {"city": "LienchiangCounty", "label": "連江縣"},
}


def resolve_city(raw: str | None) -> dict[str, object]:
    """Resolve a common Chinese city alias into TDX City."""

    value = (raw or "").strip()
    if not value:
        return {
            "status": "invalid_input",
            "normalized_value": None,
            "needs_clarification": True,
            "candidates": [],
            "details": {"reason": "missing_city"},
        }

    match = CITY_ALIASES.get(value)
    if match:
        return {
            "status": "ok",
            "normalized_value": match["city"],
            "needs_clarification": False,
            "candidates": [],
            "details": {"label": match["label"], "raw": value},
        }

    return {
        "status": "needs_clarification",
        "normalized_value": None,
        "needs_clarification": True,
        "candidates": sorted({entry["label"] for entry in CITY_ALIASES.values()}),
        "details": {"reason": "unknown_city_alias", "raw": value},
    }
