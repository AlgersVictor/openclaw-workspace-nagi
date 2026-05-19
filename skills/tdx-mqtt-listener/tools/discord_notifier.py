"""Discord Webhook 通知送出器。"""

from __future__ import annotations

import os
import time
from typing import Any

import urllib.request
import urllib.error
import json

_ENV_WEBHOOK = "DISCORD_WEBHOOK_URL"


class DiscordNotifyError(Exception):
    pass


def _load_webhook_url() -> str:
    url = os.environ.get(_ENV_WEBHOOK, "").strip()
    if not url:
        raise DiscordNotifyError(f"env var {_ENV_WEBHOOK} 未設定")
    return url


def send_embed(embed: dict[str, Any], *, dry_run: bool = False) -> None:
    """送出單則 Discord Embed。dry_run=True 時只印 JSON。"""
    payload = json.dumps({"embeds": [embed]}).encode("utf-8")

    if dry_run:
        print("[DRY-RUN] Discord embed:")
        print(json.dumps({"embeds": [embed]}, ensure_ascii=False, indent=2))
        return

    url = _load_webhook_url()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 204):
                raise DiscordNotifyError(f"Webhook 回應異常：HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        raise DiscordNotifyError(f"Webhook HTTP 錯誤：{exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise DiscordNotifyError(f"Webhook 連線失敗：{exc.reason}") from exc
