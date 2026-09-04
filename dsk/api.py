import json
import logging
import mimetypes
import threading
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Literal, Optional

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None

try:
    import orjson
except Exception:
    orjson = None

from .pow import DeepSeekPOW


ThinkingMode = Literal["detailed", "simple", "disabled"]
SearchMode = Literal["enabled", "disabled"]


class DeepSeekError(Exception):
    pass


class AuthenticationError(DeepSeekError):
    pass


class RateLimitError(DeepSeekError):
    pass


class NetworkError(DeepSeekError):
    pass


class CloudflareError(DeepSeekError):
    pass


class APIError(DeepSeekError):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class POWCache:
    

    def __init__(self, api: "DeepSeekAPI"):
        self.api = api
        self._lock = threading.Lock()
        self._cached: Optional[str] = None
        self._expires: float = 0.0
        self._computing: bool = False

    def warm(self) -> None:
        self._ensure_background()

    def _now(self) -> float:
        return time.time()

    def _normalize_expiry(self, expire_at: Any) -> float:
        
        now = self._now()

        if expire_at is None:
            return now + 30.0

        try:
            ts = float(expire_at)
        except Exception:
            return now + 30.0

        if ts <= 0:
            return now + 30.0

        
        if ts > 10_000_000_000.0:
            ts /= 1000.0

        
        if ts < 1_000_000_000.0:
            return now + ts

        return ts

    def _ensure_background(self) -> None:
        with self._lock:
            if self._computing:
                return

            
            if self._cached is not None and self._expires - self._now() > 2.0:
                return

            self._computing = True

        threading.Thread(target=self._compute, daemon=True).start()

    def _compute(self) -> None:
        try:
            challenge = self.api._get_pow_challenge()
            result = self.api.pow_solver.solve_challenge(challenge)
            expires = self._normalize_expiry(challenge.get("expire_at"))

            with self._lock:
                self._cached = result
                self._expires = expires
        except Exception:
            with self._lock:
                self._cached = None
                self._expires = 0.0
        finally:
            with self._lock:
                self._computing = False

    def get(self) -> str:
        
        now = self._now()

        with self._lock:
            cached = self._cached
            expires = self._expires

            if cached is not None and expires - now > 1.5:
                
                self._cached = None
                self._expires = 0.0
            else:
                cached = None

        if cached is None:
            
            challenge = self.api._get_pow_challenge()
            cached = self.api.pow_solver.solve_challenge(challenge)

        
        self._ensure_background()

        return cached


class DeepSeekAPI:
    BASE_URL = "https://chat.deepseek.com/api/v0"

    def __init__(self, auth_token: str, debug: bool = False):
        if not auth_token or not isinstance(auth_token, str):
            raise AuthenticationError("Invalid auth token provided")

        self.auth_token = auth_token
        self.debug = debug
        self.logger: Optional[logging.Logger] = None

        if self.debug:
            self._setup_logger()

        self.cookies = {}
        cookies_path = Path(__file__).parent / "cookies.json"

        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
                self.cookies = cookie_data.get("cookies", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        self.pow_solver = DeepSeekPOW()

        
        self._session = self._build_session()

        self.pow_cache = POWCache(self)

        
        self.pow_cache.warm()

    def close(self) -> None:
        
        self._session.close()

    def _build_session(self) -> requests.Session:
        
        session = requests.Session()

        if Retry is not None:
            retries = Retry(
                connect=2,
                read=0,
                redirect=0,
                status=0,
                backoff_factor=0.05,
            )
        else:
            retries = 0

        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            pool_block=False,
            max_retries=retries,
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update(
            {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "authorization": f"Bearer {self.auth_token}",
                "origin": "https://chat.deepseek.com",
                "referer": "https://chat.deepseek.com/",
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/132.0.0.0 Safari/537.36"
                ),
                "x-client-bundle-id": "com.deepseek.chat",
                "x-client-locale": "en_US",
                "x-client-platform": "web",
                "x-client-version": "2.3.0",
                "x-client-timezone-offset": "-14400",
            }
        )

        if self.cookies:
            session.cookies.update(self.cookies)

        
        
        session.trust_env = False

        return session

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger("DeepSeekAPI")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        if not self.logger.handlers:
            fh = logging.FileHandler("debug.txt", mode="a", encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        self.logger.debug("=" * 60)
        self.logger.debug("DeepSeekAPI logger started (debug=True)")

    def _log(self, message: str) -> None:
        if self.debug and self.logger:
            self.logger.debug(message)

    def _safe_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        safe = dict(headers or {})

        for key in list(safe.keys()):
            lower = key.lower()

            if lower == "authorization":
                safe[key] = "Bearer [REDACTED]"
            elif lower == "x-ds-pow-response":
                safe[key] = "[REDACTED]"

        return safe

    def _json_bytes(self, data: Dict[str, Any]) -> bytes:
        
        if orjson is not None:
            return orjson.dumps(data)

        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _parse_json(self, response: requests.Response) -> Any:
        
        if orjson is not None:
            return orjson.loads(response.content)

        return response.json()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict[str, Any],
    ) -> Any:
        url = f"{self.BASE_URL}{endpoint}"
        body = self._json_bytes(json_data)

        log = self.logger.debug if self.debug and self.logger else None

        if log:
            safe_headers = self._safe_headers(
                {
                    **self._session.headers,
                    "content-type": "application/json",
                }
            )
            log(f"REQUEST  {method} {url}")
            log(f"HEADERS  {json.dumps(safe_headers, indent=2)}")
            log(f"BODY     {body.decode('utf-8', 'replace')}")

        try:
            response = self._session.request(
                method=method,
                url=url,
                data=body,
                headers={"content-type": "application/json"},
                timeout=(10, 30),
            )
        except requests.exceptions.RequestException as e:
            if log:
                log(f"NETWORK ERROR: {e}")
            raise NetworkError(f"Network error: {str(e)}")

        status = response.status_code

        if log:
            log(f"RESPONSE status={status}")

        try:
            parsed = self._parse_json(response)
            if log:
                log(f"BODY     {json.dumps(parsed, indent=2, ensure_ascii=False)}")
        except Exception:
            parsed = None
            if log:
                log(f"BODY     {response.text[:2000]}")

        if status == 401:
            raise AuthenticationError("Invalid or expired authentication token")

        if status == 429:
            raise RateLimitError("API rate limit exceeded")

        if status >= 500:
            raise APIError(f"Server error: {response.text}", status)

        if status != 200:
            raise APIError(f"Request failed: {response.text}", status)

        if parsed is None:
            raise APIError("Invalid non-JSON response", status)

        return parsed

    def _get_pow_challenge(self) -> Dict[str, Any]:
        try:
            response = self._make_request(
                "POST",
                "/chat/create_pow_challenge",
                {"target_path": "/api/v0/chat/completion"},
            )
            return response["data"]["biz_data"]["challenge"]
        except KeyError:
            raise APIError("Invalid challenge response format")

    def _get_pow_for_path(self, target_path: str) -> str:
        response = self._make_request(
            "POST",
            "/chat/create_pow_challenge",
            {"target_path": target_path},
        )

        try:
            challenge = response["data"]["biz_data"]["challenge"]
        except KeyError:
            raise APIError("Invalid challenge response format")

        return self.pow_solver.solve_challenge(challenge)

    def create_chat_session(self) -> str:
        try:
            response = self._make_request(
                "POST",
                "/chat_session/create",
                {"character_id": None},
            )

            biz_data = response["data"]["biz_data"]

            if "chat_session" in biz_data:
                return biz_data["chat_session"]["id"]

            return biz_data["id"]
        except KeyError:
            raise APIError("Invalid session creation response")

    def upload_file(
        self,
        file_path: str,
        model_type: str = "default",
        thinking_enabled: bool = False,
    ) -> str:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = path.stat().st_size
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

        pow_response = self._get_pow_for_path("/api/v0/file/upload_file")

        headers = {
            "x-ds-pow-response": pow_response,
            "x-file-size": str(file_size),
            "x-model-type": model_type,
            "x-thinking-enabled": "1" if thinking_enabled else "0",
        }

        url = f"{self.BASE_URL}/file/upload_file"

        log = self.logger.debug if self.debug and self.logger else None

        if log:
            log(f"UPLOAD   {path.name} ({file_size} bytes)")

        try:
            with open(path, "rb") as f:
                response = self._session.post(
                    url,
                    headers=headers,
                    files={"file": (path.name, f, mime)},
                    timeout=(10, 120),
                )
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Upload network error: {e}")

        status = response.status_code

        if log:
            log(f"UPLOAD   status={status}")

        try:
            body = self._parse_json(response)
            if log:
                log(f"BODY     {json.dumps(body, indent=2)}")
        except Exception:
            raise APIError(
                f"Upload failed: non-JSON response (status={status}): {response.text[:500]}",
                status,
            )

        if status == 401:
            raise AuthenticationError("Invalid or expired authentication token")

        if status == 429:
            raise RateLimitError("Rate limit exceeded during upload")

        if status != 200:
            raise APIError(f"Upload failed: {response.text}", status)

        biz = body.get("data", {}).get("biz_data", {})

        if biz.get("status") != "SUCCESS":
            raise APIError(f"Upload not successful: {biz.get('error_code')} — {body}")

        file_id = biz.get("id")

        if not file_id:
            raise APIError(f"No file id in upload response: {body}")

        if log:
            log(f"UPLOAD   file_id={file_id} tokens={biz.get('token_usage')}")

        return file_id

    def _stream_response(
        self,
        endpoint: str,
        json_data: Dict[str, Any],
    ) -> Generator[Dict[str, Any], None, None]:
        
        pow_response = self.pow_cache.get()

        url = f"{self.BASE_URL}{endpoint}"
        body = self._json_bytes(json_data)

        request_headers = {
            "content-type": "application/json",
            "x-ds-pow-response": pow_response,
        }

        log = self.logger.debug if self.debug and self.logger else None

        if log:
            safe_headers = self._safe_headers(
                {
                    **self._session.headers,
                    **request_headers,
                }
            )
            log(f"REQUEST  POST {url}  (streaming)")
            log(f"HEADERS  {json.dumps(safe_headers, indent=2)}")
            log(f"BODY     {body.decode('utf-8', 'replace')}")

        try:
            response = self._session.post(
                url,
                data=body,
                headers=request_headers,
                stream=True,
                timeout=(10, None),
            )

            if log:
                log(f"RESPONSE status={response.status_code} (stream started)")

            if response.status_code != 200:
                error_body = response.text
                response.close()

                if log:
                    log(f"BODY     {error_body[:2000]}")

                status = response.status_code

                if status == 401:
                    raise AuthenticationError(
                        "Invalid or expired authentication token"
                    )

                if status == 429:
                    raise RateLimitError("API rate limit exceeded")

                raise APIError(f"Request failed: {status}", status)

            
            active_path: Optional[str] = None
            response_message_id: Optional[int] = None
            event_type: Optional[str] = None
            current_fragment_type: Optional[str] = None

            loads = orjson.loads if orjson is not None else json.loads

            EVENT_PREFIX = b"event: "
            DATA_PREFIX = b"data: "
            DONE = b"[DONE]"

            for raw in response.iter_lines(decode_unicode=False):
                if not raw:
                    continue

                if raw.startswith(EVENT_PREFIX):
                    event_type = raw[len(EVENT_PREFIX) :].decode("utf-8", "ignore")
                    continue

                if not raw.startswith(DATA_PREFIX):
                    continue

                payload = raw[len(DATA_PREFIX) :]

                if not payload or payload == DONE:
                    continue

                if log:
                    log(f"STREAM   {raw.decode('utf-8', 'replace')}")

                try:
                    obj = loads(payload)
                except Exception:
                    continue

                if not isinstance(obj, dict):
                    continue

                
                if event_type == "ready" or "response_message_id" in obj:
                    if "response_message_id" in obj:
                        response_message_id = obj["response_message_id"]

                    event_type = None
                    continue

                
                if event_type in ("close", "finish"):
                    meta = {
                        "type": "meta",
                        "response_message_id": response_message_id,
                        "finish_reason": "stop",
                    }

                    if log:
                        log(f"YIELD    {meta}")

                    yield meta
                    return

                event_type = None

                v = obj.get("v")
                p = obj.get("p")
                o = obj.get("o")

                
                
                
                if isinstance(v, dict) and "response" in v:
                    resp = v["response"]

                    
                    content = resp.get("content")

                    if isinstance(content, str) and content:
                        active_path = "response/content"
                        current_fragment_type = "RESPONSE"

                        chunk = {
                            "type": "text",
                            "content": content,
                        }

                        if log:
                            log(f"YIELD    {chunk}")

                        yield chunk

                    
                    fragments = resp.get("fragments") or []

                    for frag in fragments:
                        ftype = frag.get("type")
                        fcontent = frag.get("content") or ""

                        if ftype == "THINK" and fcontent:
                            current_fragment_type = "THINK"
                            active_path = "response/fragments/-1/content"

                            chunk = {
                                "type": "thinking",
                                "content": fcontent,
                            }

                            if log:
                                log(f"YIELD    {chunk}")

                            yield chunk

                        elif ftype == "RESPONSE" and fcontent:
                            current_fragment_type = "RESPONSE"
                            active_path = "response/fragments/-1/content"

                            chunk = {
                                "type": "text",
                                "content": fcontent,
                            }

                            if log:
                                log(f"YIELD    {chunk}")

                            yield chunk

                        elif ftype == "TOOL_SEARCH":
                            current_fragment_type = "TOOL_SEARCH"

                    continue

                
                
                
                if p is not None:
                    active_path = p

                    if o == "APPEND" and isinstance(v, str):
                        if active_path and active_path.endswith("content"):
                            chunk = {
                                "type": (
                                    "thinking"
                                    if current_fragment_type == "THINK"
                                    else "text"
                                ),
                                "content": v,
                            }

                            if log:
                                log(f"YIELD    {chunk}")

                            yield chunk

                    elif o == "SET":
                        if p.endswith("results") and isinstance(v, list):
                            chunk = {
                                "type": "search",
                                "results": v,
                            }

                            if log:
                                log(f"YIELD    {chunk}")

                            yield chunk

                    elif o == "BATCH" and isinstance(v, list):
                        for item in v:
                            ip = item.get("p")
                            io = item.get("o")
                            iv = item.get("v")

                            if (
                                ip == "fragments"
                                and io == "APPEND"
                                and isinstance(iv, list)
                            ):
                                for new_frag in iv:
                                    ftype = new_frag.get("type")
                                    fcontent = new_frag.get("content") or ""

                                    current_fragment_type = ftype

                                    if ftype == "THINK" and fcontent:
                                        active_path = "response/fragments/-1/content"

                                        chunk = {
                                            "type": "thinking",
                                            "content": fcontent,
                                        }

                                        if log:
                                            log(f"YIELD    {chunk}")

                                        yield chunk

                                    elif ftype == "RESPONSE" and fcontent:
                                        active_path = "response/fragments/-1/content"

                                        chunk = {
                                            "type": "text",
                                            "content": fcontent,
                                        }

                                        if log:
                                            log(f"YIELD    {chunk}")

                                        yield chunk

                                    elif ftype == "TOOL_SEARCH":
                                        queries = new_frag.get("queries") or []

                                        chunk = {
                                            "type": "search",
                                            "status": new_frag.get("status", "WIP"),
                                            "queries": [
                                                q.get("query")
                                                if isinstance(q, dict)
                                                else q
                                                for q in queries
                                            ],
                                            "results": new_frag.get("results") or [],
                                        }

                                        if log:
                                            log(f"YIELD    {chunk}")

                                        yield chunk

                            elif (
                                ip
                                and ip.endswith("content")
                                and isinstance(iv, str)
                            ):
                                chunk = {
                                    "type": (
                                        "thinking"
                                        if current_fragment_type == "THINK"
                                        else "text"
                                    ),
                                    "content": iv,
                                }

                                if log:
                                    log(f"YIELD    {chunk}")

                                yield chunk

                    continue

                
                
                
                if (
                    isinstance(v, str)
                    and active_path
                    and active_path.endswith("content")
                ):
                    chunk = {
                        "type": (
                            "thinking"
                            if current_fragment_type == "THINK"
                            else "text"
                        ),
                        "content": v,
                    }

                    if log:
                        log(f"YIELD    {chunk}")

                    yield chunk

        except requests.exceptions.RequestException as e:
            if log:
                log(f"NETWORK ERROR during streaming: {e}")

            raise NetworkError(f"Network error during streaming: {str(e)}")

    def chat_completion(
        self,
        chat_session_id: str,
        prompt: str,
        parent_message_id: Optional[int] = None,
        model_type: str = "default",
        thinking_enabled: bool = False,
        search_enabled: bool = False,
        ref_file_ids: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        payload = {
            "chat_session_id": chat_session_id,
            "parent_message_id": parent_message_id,
            "model_type": None if ref_file_ids else model_type,
            "prompt": prompt,
            "ref_file_ids": ref_file_ids or [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
            "action": None,
            "preempt": False,
        }

        return self._stream_response("/chat/completion", payload)

    def edit_message(
        self,
        chat_session_id: str,
        message_id: int,
        prompt: str,
        thinking_enabled: bool = False,
        search_enabled: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        payload = {
            "chat_session_id": chat_session_id,
            "message_id": message_id,
            "ref_file_ids": [],
            "prompt": prompt,
            "search_enabled": search_enabled,
            "thinking_enabled": thinking_enabled,
            "action": None,
        }

        return self._stream_response("/chat/edit_message", payload)