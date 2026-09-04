
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Generator, List, Optional

import requests

try:
    from dsk.api import (APIError, AuthenticationError, NetworkError,
                         RateLimitError)
except ImportError:
    from api import (APIError, AuthenticationError, NetworkError,  
                     RateLimitError)

from .base import BaseProvider


class OpenAICompatProvider(BaseProvider):
    name = "openai"
    supports_uploads = False
    server_sessions = False

    def __init__(self, base_url: str, api_key: str = "",
                 model: str = "local-model", debug: bool = False):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or "local-model"
        self.debug = debug
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        self._http = requests.Session()
        headers = {"accept": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        self._http.headers.update(headers)

    
    def verify(self) -> None:
        try:
            r = self._http.get(f"{self.base_url}/models", timeout=(5, 15))
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Cannot reach {self.base_url}: {e}")
        if r.status_code == 401:
            raise AuthenticationError("OpenAI-compatible endpoint rejected the API key")
        if r.status_code >= 400:
            raise APIError(f"Endpoint error {r.status_code}: {r.text[:200]}",
                           r.status_code)

    def create_session(self) -> str:
        sid = uuid.uuid4().hex
        self._sessions[sid] = []
        return sid

    
    def chat_completion(self, chat_session_id, prompt,
                        parent_message_id=None, model_type="default",
                        thinking_enabled=False, search_enabled=False,
                        ref_file_ids=None) -> Generator[Dict[str, Any], None, None]:
        history = self._sessions.setdefault(chat_session_id, [])
        history.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": history,
            "stream": True,
        }
        try:
            resp = self._http.post(f"{self.base_url}/chat/completions",
                                   json=payload, stream=True,
                                   timeout=(10, None))
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error: {e}")
        if resp.status_code == 401:
            raise AuthenticationError("Invalid or missing API key")
        if resp.status_code == 429:
            raise RateLimitError("Local endpoint rate limit exceeded")
        if resp.status_code != 200:
            raise APIError(f"Request failed: {resp.text[:200]}", resp.status_code)

        text_buf: List[str] = []
        think_buf: List[str] = []
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                rc = delta.get("reasoning_content")
                if rc:
                    think_buf.append(rc)
                    yield {"type": "thinking", "content": rc}
                c = delta.get("content")
                if c:
                    text_buf.append(c)
                    yield {"type": "text", "content": c}
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error during streaming: {e}")

        if text_buf:
            history.append({"role": "assistant", "content": "".join(text_buf)})
        yield {"type": "meta", "response_message_id": None}