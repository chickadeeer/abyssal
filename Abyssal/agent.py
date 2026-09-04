from __future__ import annotations

import json
import re
from typing import Any, Dict, List




MCP_PROPOSAL_RE = re.compile(
    r"\[MCP_PROPOSAL\]\s*(\{.*?\})\s*\[/MCP_PROPOSAL\]",
    re.DOTALL,
)
MCP_EDIT_PROPOSAL_RE = re.compile(
    r"\[MCP_EDIT_PROPOSAL\]\s*(\{.*?\})\s*\[/MCP_EDIT_PROPOSAL\]",
    re.DOTALL,
)
SYSTEM_PROPOSAL_RE = re.compile(
    r"\[SYSTEM_PROPOSAL\]\s*(\{.*?\})\s*\[/SYSTEM_PROPOSAL\]",
    re.DOTALL,
)
NEW_SESSION_RE = re.compile(
    r"\[NEW_SESSION\]\s*(.*?)\s*\[/NEW_SESSION]",
    re.DOTALL,
)
NEEDS_INPUT_RE = re.compile(
    r"\[NEEDS_INPUT\]\s*(.*?)\s*\[/NEEDS_INPUT]",
    re.DOTALL,
)
QUESTIONS_RE = re.compile(
    r"\[QUESTIONS\]\s*(\{.*?\})\s*\[/QUESTIONS]",
    re.DOTALL,
)




AGENT_SETTINGS_DEFAULTS: Dict[str, bool] = {
    "confirm-tools": False,
    "confirm-proposals": True,
    "allow-mcp-proposals": True,
    "allow-system-proposals": True,
    "allow-model-new": True,
    "allow-model-pause": True,
    "allow-model-questions": True,
}
SETTING_DESCRIPTIONS: Dict[str, str] = {
    "confirm-tools": "Confirm every MCP tool call before it runs",
    "confirm-proposals": "MCP/system/skill writes need yes/no/later approval",
    "allow-mcp-proposals": "Model may propose new MCP plugins or edit existing ones",
    "allow-system-proposals": "Model may propose prompt-segment changes",
    "allow-model-new": "Model may request a new session (/new — context lost)",
    "allow-model-pause": "Model may pause the loop and ask the user for input",
    "allow-model-questions": "Model may show structured multi-question forms",
}


def parse_json_blocks(regex: "re.Pattern", text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in regex.finditer(text or ""):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                out.append(data)
        except json.JSONDecodeError:
            continue
    return out


def parse_plain_blocks(regex: "re.Pattern", text: str) -> List[str]:
    return [(m.group(1) or "").strip() for m in regex.finditer(text or "")]


def strip_model_control_blocks(text: str) -> str:
    
    out = text or ""
    for pat in (
        MCP_PROPOSAL_RE,
        MCP_EDIT_PROPOSAL_RE,
        SYSTEM_PROPOSAL_RE,
        NEW_SESSION_RE,
        NEEDS_INPUT_RE,
        QUESTIONS_RE,
    ):
        out = pat.sub("", out)
    return out