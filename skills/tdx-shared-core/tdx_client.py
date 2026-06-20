"""Centralized TDX GET client for Phase 2A skills."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from tdx_auth import TdxAuthManager, TdxAuthError


class TdxClientError(RuntimeError):
    """Raised for upstream or transport errors."""


@dataclass
class TdxClientResponse:
    status_code: int
    data: Any
    url: str


class TdxClient:
    """Perform authenticated GET requests against TDX endpoints."""

    def __init__(self, auth_manager: TdxAuthManager) -> None:
        self.auth_manager = auth_manager

    def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        accept: str = "application/json",
    ) -> TdxClientResponse:
        query = urllib.parse.urlencode(params or {})
        final_url = f"{url}?{query}" if query else url

        def _do_request() -> TdxClientResponse:
            headers = {
                "Authorization": f"Bearer {self.auth_manager.get_access_token()}",
                "Accept": accept,
            }
            req = urllib.request.Request(final_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                data: Any = payload if "xml" in accept.lower() else json.loads(payload)
                return TdxClientResponse(status_code=response.status, data=data, url=final_url)

        try:
            return _do_request()
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and self.auth_manager.switch_to_backup():
                try:
                    return _do_request()
                except Exception as exc2:
                    raise TdxClientError(f"TDX GET 失敗（備援）: {exc2}") from exc2
            raise TdxClientError(f"TDX GET 失敗: {exc}") from exc
        except TdxAuthError:
            raise
        except Exception as exc:  # pragma: no cover - network path mocked in tests
            raise TdxClientError(f"TDX GET 失敗: {exc}") from exc
