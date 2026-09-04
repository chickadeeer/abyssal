

from __future__ import annotations
from typing import Any, Dict

DEFAULT_VISUAL: Dict[str, Any] = {
    "tool_calls": "tab",       
    "codeblocks": "normal",    
    "thinking": "panel",       
    "search": "inline",        
    "accent": "#0d9488",       
    "border": "rounded",       
    "timestamps": "off",       
    "flash": 2.5,              
    "show_tool_stream": "on",  
}

CHOICES: Dict[str, list] = {
    "tool_calls": ["tab", "inline", "raw", "hidden", "compact"],
    "codeblocks": ["normal", "compact"],
    "thinking": ["panel", "inline", "hidden"],
    "search": ["inline", "panel", "hidden"],
    "border": ["rounded", "square"],
    "timestamps": ["off", "time", "datetime"],
    "show_tool_stream": ["on", "off"],
}

def get_visual(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {**DEFAULT_VISUAL, **(cfg.get("visual") or {})}

def validate(key: str, value: str):
    
    if key not in DEFAULT_VISUAL:
        raise ValueError(f"unknown visual key '{key}'")
    if key in CHOICES:
        if value not in CHOICES[key]:
            raise ValueError(f"{key} must be one of: {', '.join(CHOICES[key])}")
        return value
    if key == "accent":
        v = value.strip()
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("accent must be a hex color like #0d9488")
        return v
    if key == "flash":
        try:
            f = float(value)
        except ValueError:
            raise ValueError("flash must be a number of seconds")
        return max(0.5, min(30.0, f))
    return value