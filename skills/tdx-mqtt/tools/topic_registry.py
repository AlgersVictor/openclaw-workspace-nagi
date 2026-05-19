"""TDX MQTT Topic 登錄表。

2026-05 開放初期支援的 Topic 清單。
"""

from __future__ import annotations

# topic_key → (topic_pattern, description)
TOPICS: dict[str, tuple[str, str]] = {
    "bus_news_city":      ("v2/Bus/News/City/{city}",             "縣市公車最新消息"),
    "bus_alert_city":     ("v2/Bus/Alert/City/{city}",            "縣市公車營運通阻 v2"),
    "bus_alert_city_v3":  ("v3/Bus/Alert/City/{city}",            "縣市公車營運通阻 v3"),
    "bus_alert_intercity":("v2/Bus/Alert/InterCity",              "公總公車營運通阻"),
    "tra_alert":          ("v3/Rail/TRA/Alert",                   "臺鐵動態營運通阻"),
    "thsr_alert":         ("v2/Rail/THSR/AlertInfo",              "高鐵即時營運通阻"),
    "metro_alert":        ("v2/Rail/Metro/Alert/{operator}",      "捷運/輕軌營運通阻（#=全部）"),
    "ship_alert":         ("v3/Ship/Alert/International",         "航運營運通阻"),
}

# 常用捷運系統代碼
METRO_OPERATORS = {
    "TRTC": "台北捷運", "KLRT": "基隆輕軌", "TYMC": "桃園捷運",
    "NTDLRT": "淡海輕軌", "TRTC_ART": "台北捷運環狀線", "KRTC": "高雄捷運",
    "#": "全部捷運/輕軌",
}


def resolve_topic(key: str, city: str = "#", operator: str = "#") -> str:
    """將 topic_key 展開為實際 Topic 字串。"""
    entry = TOPICS.get(key)
    if not entry:
        raise ValueError(f"未知 topic key: {key}。可用：{list(TOPICS)}")
    pattern, _ = entry
    return pattern.replace("{city}", city).replace("{operator}", operator)


def list_topics() -> list[dict[str, str]]:
    return [{"key": k, "topic": v[0], "description": v[1]} for k, v in TOPICS.items()]
