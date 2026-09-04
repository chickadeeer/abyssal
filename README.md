# Abyssal

> **The Most Unique Terminal Client.**

A terminal client for [chat.deepseek.com](https://chat.deepseek.com) that uses a reverse-engineered web API. No official API key needed — Abyssal talks to DeepSeek the same way the web app does. Works with DeepSeek V4, V4 Pro, and VL2.

---

## What's New in 3.0.0

Version 3.0.0 is a major overhaul. Here's the short version:

- **APS overhaul** — the proposal system got a complete redesign
- **Consent system** — you control what the model can do, feature by feature
- **Scraping improvements** — you get responses faster now
- **Provider system** — modular architecture for AI models
- **Plugin system** — built-in plugin management with LobeHub Skills
- **Clipboard support** — copy/paste works properly now
- **Code blocks** — better syntax highlighting (except codeblocks don't get copied)
- **Updater** — automatic updates
- **Dependency management** — resolves packages automatically
- **Stricter security** — models propose, you approve
- **Better UI** — cleaner visuals and feedback

Check [CHANGELOG.md](CHANGELOG.md) for the full list.

---

## Features

- **Streaming chat** with thinking mode, web search, and vision
- **Abyssal Proposal System (APS)** — model proposes changes, you approve or deny
- **Consent system** — granular per-feature control
- **MCP tools** — connect any MCP stdio server
- **LobeHub Skills Marketplace** — access 100,000+ skills
- **Provider system** — modular AI provider architecture
- **Cowork scheduler** — background tasks on a schedule
- **Skills library** — versioned context blocks
- **File upload** — attach files via DeepSeek API
- **Autonomy modes** — from human-driven to autonomous
- **Settings console** — animated TUI, no config file editing
- **Session management** — create, resume, rename, delete
- **Prompt library** — save and load system prompts
- **Sound notifications** — configurable audio cues
- **Clipboard integration** — copy/paste in the CLI
- **Auto-updater** — version management and updates

---

## Models

| Name | What it's for |
|------|---------------|
| `default` | DeepSeek-V4 Flash — quick general chat |
| `expert` | DeepSeek-V4 Pro — deep reasoning (no search) |
| `vision` | DeepSeek-VL2 — images |

You can add more via the provider system.

---

## Requirements

- Python 3.10+
- A [DeepSeek](https://chat.deepseek.com) account (free works)

---

## Installation

```bash
git clone https://github.com/chickadeeer/abyssal.git
cd abyssal
pip install -r requirements.txt
```

### Dependencies

```
prompt_toolkit
rich
fastmcp
requests
wasmtime
numpy
```

---

## Setup

First time you run Abyssal, it'll ask for your auth token. Here's how to get it:

1. Log into [chat.deepseek.com](https://chat.deepseek.com)
2. Open DevTools → Console
3. Paste this:
   ```js
   JSON.parse(localStorage.getItem("userToken")).value
   ```
4. Copy what it outputs and paste it into Abyssal

It saves to `~/.abyssal-cli/.env`. You can also set it manually:

```bash
# ~/.abyssal-cli/.env
ABYSSAL_TOKEN=your_token_here
```

Or via environment variable:

```bash
export ABYSSAL_TOKEN=your_token_here
```

---

## Usage

```bash
python -m Abyssal
```

### Flags

```
--token, -t       Auth token (saved on first use)
--model, -m       Start with a specific model (default/expert/vision)
--thinking        Start with thinking mode on
--search          Start with web search on
--session, -s     Resume a specific session ID
--debug           Enable debug logging
```

---

## Commands

### Human Commands (You Only)

| Command | What it does |
|---------|--------------|
| `/settings` | Full interactive settings console |
| `/agent` | Agent autonomy and consent settings |
| `/consent` | Manage per-feature consent |
| `/thinking` | Toggle thinking mode |
| `/search` | Toggle web search |
| `/notes` | Session-scoped notes |
| `/mcp-help` | APS guide + MCP reference |
| `/prompt` | Manage prompt segments |
| `/exit` | Quit |
| `/new` | Start a new session |
| `/save` | Export conversation to markdown |
| `/history` | View conversation history |
| `/upload` | Upload files |
| `/files` | Manage pending file attachments |
| `/task` | Manage scheduled tasks |

### Consent Commands

| Command | What it does |
|---------|--------------|
| `/consent list` | Show all consent settings |
| `/consent set <feature> on/off` | Grant or revoke consent |
| `/consent clear` | Reset everything |

Features: `questions`, `mcp-proposals`, `mcp-edits`, `system-proposals`, `new-session`, `needs-input`

**Important:** The model can't run slash commands directly anymore. It proposes actions through APS, and you approve them. This is by design.

Everything else — sessions, tasks, MCP, skills, sounds, prompts, file uploads, autonomy — lives inside `/settings` or `/agent`.

---

## MCP Tools

Abyssal works with any MCP stdio server. Add servers via `/settings → MCP` or edit `~/.abyssal-cli/mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

The model can propose, create, and edit MCP plugins from chat via APS.

### MCP Plugin Proposals

When the model proposes a new plugin, you'll see:
- The code or command
- Required pip dependencies (with consent)
- A diff preview for edits

You can approve, decline, or defer.

---

## LobeHub Skills Marketplace

3.00 integrates with LobeHub Skills Marketplace — over 100,000 reusable skills.

### Search for Skills

The model can search using the `search` tool:
```
[TOOL_CALL: search]
{"query": "pdf editor"}
[/TOOL_CALL]
```

### Add Skills

When the model finds a relevant skill, it adds it automatically. Skills live in `~/.abyssal-cli/skills/` and are versioned.

### Skill Management

- `skills_list` — list installed skills
- `skill_read` — read a skill
- `skill_write` — create or update
- `skill_diff` — compare versions
- `skill_rollback` — revert to an older version

---

## Consent System

You control what the model can do. Here's what you can toggle:

| Feature | What it controls |
|---------|------------------|
| `questions` | Structured question forms |
| `mcp-proposals` | New MCP plugins |
| `mcp-edits` | Edits to existing plugins |
| `system-proposals` | System prompt changes |
| `new-session` | Model requesting new sessions |
| `needs-input` | Model pausing for your input |

### How to Manage It

```bash
/consent list          # Show current settings
/consent set questions on   # Grant consent
/consent set questions off  # Revoke consent
/consent clear         # Reset everything
```

---

## Cowork Scheduler

Background tasks that run independently of your active session. Schedule prompts to run once, on an interval, daily, or weekly. Results are stored and can be written to a file. Tasks can be chained.

Manage tasks via `/settings → Tasks` or `/task add`.

---

## Project Structure

```
Abyssal/
├── __main__.py          Entry point
├── app.py               CLI class + run loop
├── core.py              Base state, session management
├── chat.py              Streaming + MCP/tool execution
├── agent.py             Agent control block parsing
├── agent_actions.py     APS proposals, system proposals
├── commands.py          User slash command router
├── config.py            Paths, defaults, token handling
├── client.py            DeepSeekClient wrapper
├── mcp.py               MCP server manager
├── cowork.py            Task scheduler
├── skills.py            Versioned skills library
├── settings_screen.py   Animated TUI settings console
├── task_commands.py     /task subcommands
├── files.py             /upload and /files commands
├── completion.py        Tab completion
├── questions.py         Structured question forms
├── patching.py          Unified diff application
├── sounds.py            Sound notifications
├── ui.py                Rich theme + banner
├── aps_guide.py         APS protocol docs
├── clipboard.py         Clipboard integration
├── codeblocks.py        Code block handling
├── consent.py           Consent management
├── dependencies.py      Dependency management
├── updater.py           Auto-update system
├── visual.py            UI enhancements
├── plugins/             Built-in plugins
│   └── lobehub_skills.py  LobeHub Skills Marketplace
└── providers/           Modular AI providers
    ├── base.py          Base provider class
    ├── deepseek_provider.py  DeepSeek API
    ├── openai_compat.py  OpenAI-compatible
    └── __init__.py      Module init
```

Written by an Abyssal Agent :)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full list of changes between versions.

---

## Disclaimer

Abyssal isn't affiliated with or endorsed by DeepSeek. It reverse-engineers the web API for personal use. Use it responsibly and follow DeepSeek's terms of service.

---

## License

MIT
