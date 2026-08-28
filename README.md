# Abyssal

> **The Most Unique DeepSeek Client.**

A fully-featured terminal client for [chat.deepseek.com](https://chat.deepseek.com) built on a reverse-engineered web API. No official API key required — Abyssal authenticates directly as the web app does, giving you access to DeepSeek V4, V4 Pro, and VL2 from your terminal.

---

## Features

- **Streaming chat** with thinking mode, web search, and multimodal (vision) support
- **MCP tool integration** — connect any MCP stdio server, propose and edit plugins from within the chat
- **Cowork task scheduler** — background tasks that run on a schedule and deliver results
- **Skills library** — versioned reusable context blocks the model reads before matching tasks
- **File upload** — attach local files to completions via the DeepSeek upload API (currently broken, fix soon)
- **Autonomy modes** — from Human Driven (confirm every action) to Autonomous Decision Making
- **Full-screen settings console** — animated TUI, no config file editing required
- **Session management** — create, resume, rename, and delete chat sessions
- **Prompt library** — save and load system prompts
- **Sound notifications** — configurable per-event audio cues

---

## Models

| Name | Description |
|------|-------------|
| `default` | DeepSeek-V4 Flash — fast general chat |
| `expert` | DeepSeek-V4 Pro — deep reasoning (no search) |
| `vision` | DeepSeek-VL2 — multimodal / image input |

---

## Requirements

- Python 3.10+
- A [DeepSeek](https://chat.deepseek.com) account (free tier works)

---

## Installation

```bash
git clone https://github.com/chickadeeer/abyssal.git
cd abyssal
pip install -r requirements.txt
```

### Dependencies

```
prompt_toolkit   # Terminal UI and input handling
rich             # Styled terminal output
mcp              # MCP tool server integration
requests         # HTTP requests
wasmtime
numpy

# Optional
pyperclip        # Clipboard support (cross-platform)
pywin32          # Windows clipboard and sound support
```

---

## Setup

On first launch, Abyssal will prompt you for your auth token. To get it:

1. Log into [chat.deepseek.com](https://chat.deepseek.com)
2. Open DevTools → Console
3. Paste and run:
   ```js
   JSON.parse(localStorage.getItem("userToken")).value
   ```
4. Copy the output and paste it into Abyssal when prompted

It will be saved to `~/.abyssal-cli/.env`.

You can also set it manually:

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
--thinking        Start with thinking mode enabled
--search          Start with web search enabled
--session, -s     Resume a specific session ID
--debug           Enable debug logging
```

### Commands

| Command | Description |
|---------|-------------|
| `/settings` | Open the full interactive settings console |
| `/thinking` | Toggle thinking mode |
| `/search` | Toggle web search |
| `/exit` | Quit |

Everything else — sessions, tasks, MCP, skills, sounds, prompts, file uploads, autonomy — lives inside `/settings`.

---

## MCP Tools

Abyssal supports any MCP stdio server. Add servers via `/settings → MCP` or by editing `~/.abyssal-cli/mcp.json`:

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

The model can also propose, create, and edit MCP plugins directly from chat.

---

## Cowork Scheduler

Background tasks that run independently of your active session. Schedule prompts to run once, on an interval, daily, or weekly. Results are stored and optionally written to a file. Tasks can be chained.

Manage tasks via `/settings → Tasks` or `/task add`.

---

## Project Structure

```
Abyssal/
├── __main__.py          Entry point
├── app.py               CLI class + run loop
├── core.py              Base state, session management, prompt construction
├── chat.py              Streaming + MCP/tool execution loop
├── agent.py             Agent control block parsing + regex patterns
├── agent_actions.py     MCP proposals, system proposals, questions, commands
├── commands.py          User-facing slash command router
├── config.py            Paths, defaults, token handling
├── client.py            DeepSeekClient wrapper
├── mcp.py               MCP server manager + tool discovery + execution
├── cowork.py            Task scheduler + background execution
├── skills.py            Versioned skills library
├── settings_screen.py   Animated full-screen TUI settings console
├── task_commands.py     /task subcommands
├── files.py             /upload and /files commands
├── completion.py        prompt_toolkit tab completion
├── questions.py         Structured multi-question forms
├── patching.py          Unified diff application for MCP plugin edits
├── sounds.py            Sound notification system
└── ui.py                Rich theme + banner
```

---

## Disclaimer

Abyssal is an independent project and is not affiliated with or endorsed by DeepSeek. It reverse-engineers the web API for personal use. Use responsibly and in accordance with DeepSeek's terms of service.

---

## License

MIT
