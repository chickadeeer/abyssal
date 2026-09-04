from __future__ import annotations

from typing import Any, Dict, Union

from prompt_toolkit.completion import Completer, Completion

from .agent import AGENT_SETTINGS_DEFAULTS
from .config import AUTONOMY_MODES, COMMANDS, MODELS
from .consent import FEATURES as CONSENT_FEATURES
from .sounds import PRESETS as SOUND_PRESETS
from .visual import CHOICES as VISUAL_CHOICES

Tree = Dict[str, Union["Tree", set, list]]


def _agent_tree() -> Tree:
    return {k: {"on", "off"} for k in AGENT_SETTINGS_DEFAULTS}


def _consent_tree() -> Tree:
    return {
        "list": {},
        "reset": {},
        "set": {k: {"on", "off"} for k in CONSENT_FEATURES},
    }


def _visual_tree() -> Tree:
    set_tree: Tree = {}
    for k, choices in VISUAL_CHOICES.items():
        set_tree[k] = set(choices)
    set_tree["accent"] = {}
    set_tree["flash"] = {}
    return {"list": {}, "set": set_tree}


def _sound_channel_tree() -> Tree:
    ch: Tree = {
        "on": {}, "off": {}, "test": {},
        "preset": set(list(SOUND_PRESETS) + ["custom"]),
        "file": {},
    }
    return ch


def build_tree() -> Tree:
    return {
        "/settings": {},
        "/help": {},
        "/version": {},
        "/exit": {},
        "/thinking": {"on", "off"},
        "/search": {"on", "off"},
        "/model": set(MODELS.keys()),
        "/debug": {"on", "off"},
        "/token": {},
        "/provider": {
            "deepseek": {},
            "openai": {},
        },
        "/autonomy": set(AUTONOMY_MODES.keys()),
        "/agent": _agent_tree(),
        "/skills": {},
        "/skill": {
            "show": {}, "add": {},
            "diff": {}, "rollback": {}, "delete": {},
        },
        "/mcp": {
            "status": {}, "list": {}, "tools": {},
            "add": {}, "remove": {}, "refresh": {},
            "deps": {},
        },
        "/mcp-help": {},
        "/deps": {
            "auto": {"on", "off"},
            "check": {},
        },
        "/sessions": {},
        "/new": {},
        "/use": {},
        "/rename": {},
        "/del": {},
        "/notes": {"add": {}, "list": {}, "clear": {}},
        "/task": {
            "add": {}, "list": {}, "remove": {}, "run": {},
            "pause": {}, "result": {}, "clear": {},
        },
        "/upload": {},
        "/files": {"list": {}, "clear": {}},
        "/sounds": {"master": {"on", "off"}},
        "/sound": {
            "notify": _sound_channel_tree(),
            "response": _sound_channel_tree(),
            "blank": _sound_channel_tree(),
        },
        "/prompt": {
            "show": {}, "list": {}, "add": {}, "clear": {},
            "remove": {}, "move": {}, "edit": {},
            "tools": {"on", "off"},
            "save": {}, "load": {},
        },
        "/aps": {
            "show": {}, "edit": {}, "reset": {},
            "backups": {}, "restore": {},
        },
        "/consent": _consent_tree(),
        "/visual": _visual_tree(),
        "/status": {"detail": {}},
        "/history": {},
        "/save": {},
        "/undo": {},
        "/retry": {},
        "/copy": {},
        "/cc": {},
        "/paste": {},
        "/edit": {},
        "/update": {},
        "/clear": {},
    }


COMMAND_TREE = build_tree()


class CommandCompleter(Completer):
    

    def __init__(self, app: Any):
        self.app = app

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        tokens = text.split(" ")
        
        if len(tokens) == 1:
            for c in COMMANDS:
                if c.startswith(tokens[0]):
                    yield Completion(c, start_position=-len(tokens[0]))
            return
        
        
        node: Union[Tree, set, list] = COMMAND_TREE
        for tok in tokens[:-1]:
            if isinstance(node, dict) and tok.lower() in node:
                node = node[tok.lower()]
            else:
                return
        if isinstance(node, dict):
            candidates = list(node.keys())
        elif isinstance(node, (set, list)):
            candidates = list(node)
        else:
            return
        partial = tokens[-1]
        for cand in sorted(candidates):
            if cand.startswith(partial):
                yield Completion(cand, start_position=-len(partial))