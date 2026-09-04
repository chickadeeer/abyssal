from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional


class BaseProvider(ABC):
    
    name = "base"
    supports_uploads = False
    server_sessions = False   

    @abstractmethod
    def verify(self) -> None: ...

    @abstractmethod
    def create_session(self) -> str: ...

    @abstractmethod
    def chat_completion(
        self,
        chat_session_id: str,
        prompt: str,
        parent_message_id: Optional[int] = None,
        model_type: str = "default",
        thinking_enabled: bool = False,
        search_enabled: bool = False,
        ref_file_ids: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]: ...

    
    def upload_file(self, path: str, model_type: str = "default",
                    thinking_enabled: bool = False) -> str:
        raise NotImplementedError(f"{self.name} does not support file uploads")

    def list_sessions(self) -> List[Dict[str, Any]]:
        return []

    def delete_session(self, session_id: str) -> None:
        pass

    def rename_session(self, session_id: str, name: str) -> None:
        pass