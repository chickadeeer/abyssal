from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional




APP_NAME = "Abyssal"
APP_VERSION = "3.0.0"




CONFIG_DIR = Path.home() / ".abyssal-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = CONFIG_DIR / ".env"
HISTORY_FILE = CONFIG_DIR / "history"
CONV_DIR = CONFIG_DIR / "conversations"
PROMPTS_DIR = CONFIG_DIR / "prompts"
SKILLS_DIR = CONFIG_DIR / "skills"
MCP_CONFIG_FILE = CONFIG_DIR / "mcp.json"
TASKS_FILE = CONFIG_DIR / "tasks.json"
GLOBAL_INSTRUCTIONS_FILE = CONFIG_DIR / "global_instructions.txt"
CONSENT_FILE = CONFIG_DIR / "consent.json"
APS_GUIDE_FILE = CONFIG_DIR / "aps_guide.md"
APS_BACKUP_DIR = CONFIG_DIR / "aps_backups"


LOBEHUB_PLUGIN_PATH = Path(__file__).resolve().parent / "plugins" / "lobehub_skills.py"


OLD_CONFIG_DIR = Path.home() / ".deepseek-cli"
OLD_ENV_FILE = OLD_CONFIG_DIR / ".env"




MODELS: Dict[str, str] = {
    "default": "DeepSeek-V4 Flash — fast general chat",
    "expert":  "DeepSeek-V4 Pro — deep reasoning but no search",
    "vision":  "DeepSeek-VL2 — multimodal / image input / no search",
}
DEFAULT_SOUNDS: Dict[str, Any] = {
    "master": True,
    "notify":   {"enabled": True, "preset": "abyss-chime", "file": ""},
    "response": {"enabled": True, "preset": "blip",        "file": ""},
    "blank":    {"enabled": True, "preset": "deep-ping",   "file": ""},
}

_FIRST_RUN_SOUNDS: Dict[str, Any] = {**DEFAULT_SOUNDS, "master": False}

DEFAULT_VISUAL: Dict[str, Any] = {
    "tool_calls": "tab",
    "thinking": "panel",
    "search": "inline",
    "accent": "#0d9488",
    "border": "rounded",
    "timestamps": "off",
    "flash": 2.5,
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "thinking": False,
    "search": False,
    "debug": False,
    "model": "default",
    "provider": {"type": "deepseek"},
    "prompt_segments": [],
    "autonomy": "human-needed",
    "agent_toggles": {},
    "sounds": _FIRST_RUN_SOUNDS,
    "visual": DEFAULT_VISUAL,
    "auto_install_deps": False,
}




AUTONOMY_MODES: Dict[str, Dict[str, Any]] = {
    "human-driven": {
        "label": "Human Driven",
        "desc": "Confirms every single action — tool calls and all proposals.",
        "toggles": {"confirm-tools": True, "confirm-proposals": True},
    },
    "human-needed": {
        "label": "Human Needed",
        "desc": "Runs tools freely, but checks in at key decision points (all proposals).",
        "toggles": {"confirm-tools": False, "confirm-proposals": True},
    },
    "human-not-always-needed": {
        "label": "Human Not Always Needed",
        "desc": "Acts autonomously on routine tasks; only asks about ambiguous or destructive actions.",
        "toggles": {"confirm-tools": False, "confirm-proposals": True},
    },
    "autonomous": {
        "label": "Autonomous Decision Making",
        "desc": "Runs independently and only surfaces critical blockers. Proposals are auto-approved.",
        "toggles": {"confirm-tools": False, "confirm-proposals": False},
    },
    "custom": {
        "label": "Custom",
        "desc": "You define the rules — tune every agent toggle yourself.",
        "toggles": {},
    },
}




MCP_HELP_INTERVAL = 30
MAX_TOOL_ITERATIONS = 10000
TOOL_RESULT_MAX_CHARS = 50000




RATE_RETRY_SECONDS = 15
RATE_MAX_RETRIES = 3
BLANK_RETRY_SECONDS = 5
BLANK_MAX_RETRIES = 10




TASK_INTERVAL_CHOICES: Dict[str, int] = {
    "30min": 30,
    "1hr": 60,
    "2hr": 120,
    "6hr": 360,
    "12hr": 720,
}





COMMANDS = [
    "/settings", "/help", "/version", "/exit",
    "/model", "/thinking", "/search", "/debug", "/token", "/provider",
    "/autonomy", "/agent",
    "/skills", "/skill",
    "/mcp", "/mcp-help", "/deps",
    "/sessions", "/new", "/use", "/rename", "/del",
    "/notes", "/task",
    "/upload", "/files",
    "/sounds", "/sound",
    "/prompt", "/aps", "/consent", "/visual",
    "/status", "/history", "/save", "/undo", "/retry", "/copy", "/cc",
    "/paste", "/edit",
    "/update", "/clear",
]




def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    CONV_DIR.mkdir(exist_ok=True)
    PROMPTS_DIR.mkdir(exist_ok=True)
    SKILLS_DIR.mkdir(exist_ok=True)
    APS_BACKUP_DIR.mkdir(exist_ok=True)


def load_config() -> Dict[str, Any]:
    ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cfg = {**DEFAULT_CONFIG, **raw}
            
            if "sounds" not in raw:
                cfg["sounds"] = {**DEFAULT_SOUNDS, "master": False}
            
            if "prompt_segments" not in raw and raw.get("system_prompt"):
                cfg["prompt_segments"] = [
                    {"text": str(raw["system_prompt"]), "show_tools": True}
                ]
            return cfg
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg: Dict[str, Any]) -> None:
    ensure_dirs()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def _default_mcp_config() -> Dict[str, Any]:
    
    return {
        "mcpServers": {
            "lobehub-skills": {
                "command": sys.executable,
                "args": [str(LOBEHUB_PLUGIN_PATH)],
                "env": {},
                "dependencies": ["requests"],
            }
        }
    }


def load_mcp_config() -> Dict[str, Any]:
    ensure_dirs()
    if MCP_CONFIG_FILE.exists():
        try:
            with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    cfg = _default_mcp_config()
    save_mcp_config(cfg)
    return cfg


def save_mcp_config(cfg: Dict[str, Any]) -> None:
    ensure_dirs()
    with open(MCP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)





def _parse_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_token() -> Optional[str]:
    for key in ("ABYSSAL_TOKEN", "DEEPSEEK_TOKEN"):
        tok = os.environ.get(key)
        if tok:
            return tok
    for path in (Path.cwd() / ".env", ENV_FILE, OLD_ENV_FILE):
        env = _parse_env_file(path)
        for key in ("ABYSSAL_TOKEN", "DEEPSEEK_TOKEN"):
            tok = env.get(key)
            if tok:
                return tok
    return None


def token_source() -> str:
    for key in ("ABYSSAL_TOKEN", "DEEPSEEK_TOKEN"):
        if os.environ.get(key):
            return f"environment:{key}"
    cwd_env = _parse_env_file(Path.cwd() / ".env")
    for key in ("ABYSSAL_TOKEN", "DEEPSEEK_TOKEN"):
        if cwd_env.get(key):
            return f"./.env:{key}"
    home_env = _parse_env_file(ENV_FILE)
    for key in ("ABYSSAL_TOKEN", "DEEPSEEK_TOKEN"):
        if home_env.get(key):
            return f"{ENV_FILE}:{key}"
    old_env = _parse_env_file(OLD_ENV_FILE)
    for key in ("ABYSSAL_TOKEN", "DEEPSEEK_TOKEN"):
        if old_env.get(key):
            return f"{OLD_ENV_FILE}:{key}"
    return "none"


def save_token(token: str) -> Path:
    ensure_dirs()
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = [
            l for l in ENV_FILE.read_text(encoding="utf-8").splitlines()
            if not l.startswith("ABYSSAL_TOKEN=")
            and not l.startswith("DEEPSEEK_TOKEN=")
        ]
    lines.append(f"ABYSSAL_TOKEN={token}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass
    os.environ["ABYSSAL_TOKEN"] = token
    return ENV_FILE


def mask(token: str) -> str:
    return token[:8] + "…" + token[-4:] if len(token) > 16 else "****"





def transcript_path(session_id: str) -> Path:
    return CONV_DIR / f"{session_id}.json"


def all_local_transcripts() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for p in CONV_DIR.glob("*.json"):
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            if t:
                out[p.stem] = t
        except Exception:
            pass
    return out