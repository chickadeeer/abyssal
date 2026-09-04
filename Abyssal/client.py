from __future__ import annotations

from typing import Any, Dict, List

try:
    from dsk.api import (
        APIError,
        AuthenticationError,
        DeepSeekAPI,
        DeepSeekError,
        NetworkError,
        RateLimitError,
    )
except ImportError:
    try:
        from api import (  
            APIError,
            AuthenticationError,
            DeepSeekAPI,
            DeepSeekError,
            NetworkError,
            RateLimitError,
        )
    except ImportError as exc:
        raise ImportError(
            "Could not import DeepSeekAPI. Run this from the project directory "
            "or ensure the `dsk` package / api.py is available."
        ) from exc


class DeepSeekClient:
    def __init__(self, token: str, debug: bool = False):
        self.api = DeepSeekAPI(token, debug=debug)

    def verify(self) -> None:
        self.list_sessions()

    def create_session(self) -> str:
        return self.api.create_chat_session()

    def list_sessions(self) -> List[Dict[str, Any]]:
        resp = self.api._make_request("POST", "/chat_session/list", {})
        biz = resp.get("data", {}).get("biz_data", {})

        if isinstance(biz, list):
            return biz

        if isinstance(biz, dict):
            for key in ("chat_sessions", "sessions", "list", "items"):
                if isinstance(biz.get(key), list):
                    return biz[key]

        return []

    def delete_session(self, session_id: str) -> None:
        self.api._make_request("POST", "/chat_session/delete", {"id": session_id})

    def rename_session(self, session_id: str, name: str) -> None:
        self.api._make_request("POST", "/chat_session/rename", {"id": session_id, "name": name})