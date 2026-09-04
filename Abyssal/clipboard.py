

from __future__ import annotations
import pyperclip

def copy(text: str) -> bool:
    
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False

def paste() -> str:
    
    try:
        return pyperclip.paste()
    except Exception:
        return ""