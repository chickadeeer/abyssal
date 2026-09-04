from __future__ import annotations

from typing import Any, Dict, Optional

from .base import BaseProvider

__all__ = ["BaseProvider", "make_provider"]


def make_provider(cfg: Dict[str, Any], token: Optional[str] = None,
                  debug: bool = False) -> BaseProvider:
    
    pcfg = dict(cfg.get("provider") or {})
    ptype = pcfg.get("type", "deepseek")
    if ptype == "openai":
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(
            base_url=pcfg.get("base_url", "http://localhost:11434/v1"),
            api_key=pcfg.get("api_key", ""),
            model=pcfg.get("model", "local-model"),
            debug=debug,
        )
    from .deepseek_provider import DeepSeekProvider
    return DeepSeekProvider(token or "", debug=debug)