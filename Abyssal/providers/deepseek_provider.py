from __future__ import annotations

from typing import Any, Dict, List

try:
    from dsk.api import DeepSeekAPI
except ImportError:
    from api import DeepSeekAPI  

from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    
    name = "deepseek"
    supports_uploads = True
    server_sessions = True

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
        self.api._make_request("POST", "/chat_session/rename",
                               {"id": session_id, "name": name})

    def upload_file(self, path: str, model_type: str = "default",
                    thinking_enabled: bool = False) -> str:
        return self.api.upload_file(path, model_type=model_type,
                                    thinking_enabled=thinking_enabled)

    def chat_completion(self, chat_session_id, prompt,
                        parent_message_id=None, model_type="default",
                        thinking_enabled=False, search_enabled=False,
                        ref_file_ids=None):
        return self.api.chat_completion(
            chat_session_id=chat_session_id,
            prompt=prompt,
            parent_message_id=parent_message_id,
            model_type=model_type,
            thinking_enabled=thinking_enabled,
            search_enabled=search_enabled,
            ref_file_ids=ref_file_ids,
        )

    def edit_message(self, chat_session_id, message_id, prompt,
                     thinking_enabled=False, search_enabled=False):
        return self.api.edit_message(
            chat_session_id, message_id, prompt,
            thinking_enabled=thinking_enabled,
            search_enabled=search_enabled)