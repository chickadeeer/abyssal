from __future__ import annotations

import asyncio
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import load_mcp_config, save_mcp_config
from .dependencies import ensure_dependencies
from .ui import console




try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False




TOOL_CALL_RE = re.compile(
    r"\[TOOL_CALL:\s*([A-Za-z0-9_.\-]+)\s*\]\s*(\{.*?\})?\s*\[/TOOL_CALL\]",
    re.DOTALL,
)


def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    calls = []
    for m in TOOL_CALL_RE.finditer(text or ""):
        name = m.group(1).strip()
        raw_args = (m.group(2) or "{}").strip()
        try:
            args = json.loads(raw_args)
            if not isinstance(args, dict):
                args = {"_raw": raw_args}
        except json.JSONDecodeError:
            args = {"_raw": raw_args}
        calls.append({"name": name, "arguments": args})
    return calls





class MCPManager:
    
    BUILTIN_TOOL_NAMES = [
        "mcp_help",
        "deepseek_upload_file",
        "mcp_read_plugin",
        "skills_list",
        "skill_read",
        "skill_write",
        "skill_rollback",
        "skill_diff",
    ]

    def __init__(self) -> None:
        self.tools: List[Dict[str, Any]] = []
        self.tool_index: Dict[str, str] = {}  
        self.config = load_mcp_config()

    
    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        return self.config.get("mcpServers", {})

    def add_server(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        self.config.setdefault("mcpServers", {})[name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
            "dependencies": [d for d in (dependencies or []) if (d or "").strip()],
        }
        save_mcp_config(self.config)

    def set_dependencies(self, name: str, dependencies: List[str]) -> bool:
        if name not in self.config.get("mcpServers", {}):
            return False
        self.config["mcpServers"][name]["dependencies"] = list(dependencies)
        save_mcp_config(self.config)
        return True

    def remove_server(self, name: str) -> bool:
        if name in self.config.get("mcpServers", {}):
            del self.config["mcpServers"][name]
            save_mcp_config(self.config)
            return True
        return False

    def get_plugin_path(self, name: str) -> Optional[Path]:
        
        cfg = self.config.get("mcpServers", {}).get(name)
        if not cfg:
            return None
        cmd = cfg.get("command", "")
        args = cfg.get("args", []) or []
        if cmd == sys.executable and args:
            p = Path(args[0])
            if p.exists() and p.suffix == ".py":
                return p
        return None

    
    def _ensure_server_deps(self, server_cfg: Dict[str, Any]) -> None:
        deps = server_cfg.get("dependencies") or []
        if deps:
            ensure_dependencies(deps, console)

    
    async def _load_tools_from_server(
        self,
        name: str,
        server_cfg: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        
        if not MCP_AVAILABLE:
            return []
        self._ensure_server_deps(server_cfg)
        params = StdioServerParameters(
            command=server_cfg["command"],
            args=server_cfg.get("args", []),
            env=server_cfg.get("env") or None,
        )
        tools: List[Dict[str, Any]] = []
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    for tool in result.tools:
                        tools.append({
                            "server": name,
                            "name": tool.name,
                            "description": (tool.description or "").strip(),
                            "input_schema": getattr(tool, "inputSchema", {}) or {},
                        })
        except Exception as e:
            console.print(f"[warning]MCP server '{name}' failed: {e}[/]")
            traceback.print_exc()
        return tools

    async def refresh_tools(self) -> List[Dict[str, Any]]:
        self.tools = []
        self.tool_index = {}
        for name, cfg in self.list_servers().items():
            for t in await self._load_tools_from_server(name, cfg):
                self.tools.append(t)
                self.tool_index[t["name"]] = name
        return self.tools

    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        server_name = self.tool_index.get(tool_name)
        if server_name is None:
            raise KeyError(f"Unknown tool '{tool_name}'")
        cfg = self.config["mcpServers"][server_name]
        self._ensure_server_deps(cfg)
        
        params = StdioServerParameters(
            command=cfg["command"],
            args=cfg.get("args", []),
            env=cfg.get("env") or None,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                texts = []
                for c in getattr(result, "content", []) or []:
                    if getattr(c, "type", "") == "text":
                        texts.append(getattr(c, "text", ""))
                return "\n".join(t for t in texts if t) or str(getattr(result, "content", ""))

    
    @staticmethod
    def _schema_lines(schema: Dict[str, Any]) -> List[str]:
        props = (schema or {}).get("properties", {}) or {}
        required = set((schema or {}).get("required", []) or [])
        lines = []
        for pname, pdef in props.items():
            typ = pdef.get("type", "any")
            desc = pdef.get("description", "")
            flag = ", required" if pname in required else ""
            lines.append(f"    • {pname} ({typ}{flag}): {desc}")
        return lines or ["    (no arguments)"]

    @staticmethod
    def _example_call(name: str, schema: Dict[str, Any]) -> str:
        required = (schema or {}).get("required", []) or []
        example = {p: "…" for p in required}
        return (
            f"[TOOL_CALL: {name}]\n"
            f"{json.dumps(example, ensure_ascii=False)}\n"
            f"[/TOOL_CALL]"
        )

    def _builtin_reference(self) -> List[str]:
        upload_schema = {
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or ~ path to a local file to upload.",
                }
            },
            "required": ["path"],
        }
        read_plugin_schema = {
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of a Python-based MCP plugin to read.",
                }
            },
            "required": ["name"],
        }
        skill_write_schema = {
            "properties": {
                "name": {"type": "string", "description": "Skill name."},
                "content": {"type": "string", "description": "Full skill content (markdown)."},
                "description": {"type": "string", "description": "One-line description."},
                "note": {"type": "string", "description": "Version note."},
            },
            "required": ["name", "content"],
        }
        skill_name_schema = {
            "properties": {"name": {"type": "string", "description": "Skill name."}},
            "required": ["name"],
        }
        skill_rollback_schema = {
            "properties": {
                "name": {"type": "string", "description": "Skill name."},
                "version": {"type": "integer", "description": "Version number to re-activate."},
            },
            "required": ["name", "version"],
        }
        skill_diff_schema = {
            "properties": {
                "name": {"type": "string", "description": "Skill name."},
                "version_a": {"type": "integer", "description": "First version."},
                "version_b": {"type": "integer", "description": "Second version."},
            },
            "required": ["name", "version_a", "version_b"],
        }
        questions_note = (
            "Ask the user structured multi-question forms with the [QUESTIONS]{json}[/QUESTIONS] "
            "block (see the APS guide) — it is optional, only for clean structured input."
        )
        lines = [
            "## Built-in",
            "",
            "Note: external MCP servers run in ephemeral mode (process starts and stops per call).",
            "",
            "### mcp_help",
            "Shows this reference: every MCP tool, its argument schema, and server commands.",
            "Example:",
            self._example_call("mcp_help", {}),
            "",
            "### deepseek_upload_file",
            "Uploads a local file from the user's machine (DeepSeek provider only). "
            "The returned file id is attached to the next completion request.",
            "arguments:",
            *self._schema_lines(upload_schema),
            "example:",
            self._example_call("deepseek_upload_file", upload_schema),
            "",
            "### mcp_read_plugin",
            "Reads the FULL numbered source of an existing Python MCP plugin. ALWAYS call this "
            "before proposing an [MCP_EDIT_PROPOSAL], then send only a minimal unified diff "
            "in the 'patch' field.",
            "arguments:",
            *self._schema_lines(read_plugin_schema),
            "example:",
            self._example_call("mcp_read_plugin", read_plugin_schema),
            "",
            "### skills_list",
            "Lists every skill in the library (name, active version, description).",
            "example:",
            self._example_call("skills_list", {}),
            "",
            "### skill_read",
            "Reads the ACTIVE version of a skill. Read the relevant skill BEFORE a matching task.",
            "arguments:",
            *self._schema_lines(skill_name_schema),
            "example:",
            self._example_call("skill_read", skill_name_schema),
            "",
            "### skill_write",
            "Creates a skill or appends a new version. Use it after finishing a task where a "
            "skill would have helped — self-improve for next time.",
            "arguments:",
            *self._schema_lines(skill_write_schema),
            "example:",
            self._example_call("skill_write", skill_write_schema),
            "",
            "### skill_rollback",
            "Re-activates an older version of a skill when a newer version made things worse.",
            "arguments:",
            *self._schema_lines(skill_rollback_schema),
            "example:",
            self._example_call("skill_rollback", skill_rollback_schema),
            "",
            "### skill_diff",
            "Shows a unified diff between two versions of a skill.",
            "arguments:",
            *self._schema_lines(skill_diff_schema),
            "example:",
            self._example_call("skill_diff", skill_diff_schema),
            "",
            f"note: {questions_note}",
            "",
        ]
        return lines

    def get_short_block(self) -> str:
        
        names = ", ".join(
            [t["name"] for t in self.tools] + self.BUILTIN_TOOL_NAMES
        )
        return (
            "# TOOL USE\n"
            "You have MCP tools available. To call one, output exactly this block "
            "in your response and wait for the result:\n"
            "[TOOL_CALL: <tool_name>]\n"
            '{"argument": "value"}\n'
            "[/TOOL_CALL]\n"
            f"Available tools: {names}.\n"
            "Arguments must be valid JSON. One tool call per response.\n"
            "Each server runs in ephemeral mode (process starts and stops per call). "
            "Call mcp_help for the full reference."
        )

    def _help_header_lines(self) -> List[str]:
        return [
            "# MCP TOOL REFERENCE",
            "",
            "To use a tool, output exactly one block per response and wait for its result:",
            "",
            "[TOOL_CALL: <tool_name>]",
            '{"argument": "value"}',
            "[/TOOL_CALL]",
            "",
            "Rules:",
            "- Arguments must be valid JSON matching the schema below.",
            "- Do not repeat an identical call unless the previous one failed.",
            '- The built-in tool "mcp_help" (arguments {}) re-displays this reference.',
            '- The built-in tool "deepseek_upload_file" uploads a local file and attaches it to the next request.',
            '- Before editing an MCP plugin, call "mcp_read_plugin" and propose a minimal unified diff.',
            "",
            *self._builtin_reference(),
        ]

    def get_help_block(self) -> str:
        
        lines = self._help_header_lines()
        if not self.tools:
            lines.append("(No external MCP tools loaded. Use /mcp refresh.)")
            return "\n".join(lines)
        by_server: Dict[str, List[Dict[str, Any]]] = {}
        for t in self.tools:
            by_server.setdefault(t["server"], []).append(t)
        for server, tools in by_server.items():
            cfg = self.list_servers().get(server, {})
            cmd = cfg.get("command", "?")
            args = " ".join(cfg.get("args", []) or [])
            deps = ", ".join(cfg.get("dependencies") or []) or "none"
            lines.append(f"## MCP server: {server}")
            lines.append(f"command: `{cmd} {args}`".rstrip())
            lines.append(f"dependencies: {deps}")
            lines.append("")
            for t in tools:
                lines.append(f"### {t['name']}")
                if t["description"]:
                    lines.append(t["description"])
                lines.append("arguments:")
                lines.extend(self._schema_lines(t["input_schema"]))
                lines.append("example:")
                lines.append(self._example_call(t["name"], t["input_schema"]))
                lines.append("")
        return "\n".join(lines)

    def get_help_block_for_tools(self, tool_names: List[str]) -> str:
        
        lines = self._help_header_lines()
        filtered_tools = [t for t in self.tools if t["name"] in tool_names]
        if not filtered_tools:
            lines.append("(No matching external MCP tools found.)")
            return "\n".join(lines)
        by_server: Dict[str, List[Dict[str, Any]]] = {}
        for t in filtered_tools:
            by_server.setdefault(t["server"], []).append(t)
        for server, tools in by_server.items():
            cfg = self.list_servers().get(server, {})
            cmd = cfg.get("command", "?")
            args = " ".join(cfg.get("args", []) or [])
            lines.append(f"## MCP server: {server}")
            lines.append(f"command: `{cmd} {args}`".rstrip())
            lines.append("")
            for t in tools:
                lines.append(f"### {t['name']}")
                if t["description"]:
                    lines.append(t["description"])
                lines.append("arguments:")
                lines.extend(self._schema_lines(t["input_schema"]))
                lines.append("example:")
                lines.append(self._example_call(t["name"], t["input_schema"]))
                lines.append("")
        return "\n".join(lines)

    def get_full_block(self) -> str:
        
        return self.get_help_block()