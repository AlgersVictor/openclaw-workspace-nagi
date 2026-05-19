"""Human-readable summaries for road-live results."""

from __future__ import annotations


def format_live_traffic_summary(city_label: str, item_count: int) -> str:
    return f"{city_label} 路況摘要查詢完成，共整理 {item_count} 筆路段資訊。"


def format_traffic_news_summary(city_label: str, item_count: int) -> str:
    return f"{city_label} 交通新聞查詢完成，共 {item_count} 則。"


def format_mapped_only_summary(intent: str, city_label: str) -> str:
    return f"{intent} 目前僅完成骨架，{city_label} 端點尚未完成 live 驗證。"
