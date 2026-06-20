"""Minimal TDX auth manager with in-process token cache."""

from __future__ import annotations

import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

# 憑證優先順序：主要 → 備援1 → 備援2
_CRED_KEYS = [
    ("TDX_CLIENT_ID", "TDX_CLIENT_SECRET"),
    ("TDX_BACKUP_CLIENT_ID", "TDX_BACKUP_CLIENT_SECRET"),
    ("TDX_BACKUP2_CLIENT_ID", "TDX_BACKUP2_CLIENT_SECRET"),
]


class TdxAuthError(RuntimeError):
    """Raised when token acquisition fails."""


@dataclass
class TdxTokenRecord:
    access_token: str
    expires_at: float


class TdxAuthManager:
    """Fetch and cache a bearer token using client credentials."""

    def __init__(self, token_url: str, cache_seconds: int = 300) -> None:
        self.token_url = token_url
        self.cache_seconds = cache_seconds
        self._cache: TdxTokenRecord | None = None
        self._cred_index = 0

    def _get_credentials(self) -> tuple[str, str]:
        cid_key, csec_key = _CRED_KEYS[self._cred_index]
        cid = os.getenv(cid_key)
        csec = os.getenv(csec_key)
        if not cid or not csec:
            raise TdxAuthError(f"缺少 {cid_key} 或 {csec_key}。")
        return cid, csec

    def switch_to_backup(self) -> bool:
        """切換至下一組備援憑證並清除快取。無可用備援時回傳 False。"""
        next_idx = self._cred_index + 1
        while next_idx < len(_CRED_KEYS):
            cid_key, _ = _CRED_KEYS[next_idx]
            if os.getenv(cid_key):
                self._cred_index = next_idx
                self._cache = None
                return True
            next_idx += 1
        return False

    def _request_token(self, client_id: str, client_secret: str) -> tuple[str, int]:
        """向 TDX 認證伺服器取得 token，回傳 (access_token, expires_in)。"""
        payload = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                import json

                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network path mocked in tests
            raise TdxAuthError(f"取 token 失敗: {exc}") from exc

        access_token = body.get("access_token")
        if not access_token:
            raise TdxAuthError("token 回應缺少 access_token。")
        return access_token, int(body.get("expires_in", self.cache_seconds))

    def get_access_token(self) -> str:
        now = time.time()
        if self._cache and self._cache.expires_at > now:
            return self._cache.access_token

        cid, csec = self._get_credentials()
        while True:
            try:
                access_token, expires_in = self._request_token(cid, csec)
                break
            except TdxAuthError:
                if self.switch_to_backup():
                    print(f"[TDX] 憑證失敗，切換至備援 {self._cred_index}", file=sys.stderr)
                    cid, csec = self._get_credentials()
                else:
                    raise

        ttl = max(min(expires_in - 60, self.cache_seconds), 30)
        self._cache = TdxTokenRecord(access_token=access_token, expires_at=now + ttl)
        return access_token
