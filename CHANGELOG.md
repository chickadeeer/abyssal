# Changelog

## Version 3.0.1 — September 4, 2026

### What's New

**Clipboard Rewrite** (`clipboard.py`)
- Replaced the custom cross-platform clipboard implementation with `pyperclip`
- Removed ~150 lines of Windows ctypes and Unix subprocess code
- Added `pyperclip` to `requirements.txt` (file size: 56 → 91 bytes)
- Clipboard copy/paste is now simpler, more reliable, and cross-platform

**Code Block Rendering Overhaul** (`codeblocks.py`)
- **Visual change**: Clickable code block panels are temporarily disabled
- `render_group()` now returns plain Markdown instead of interactive panels
- `arm_click_listener()` and `stop_click_listener()` are now no-ops
- `/cc` command now shows "interactive code blocks disabled" message
- SGR mouse listener code remains but is bypassed with early returns

**Chat Rendering Update** (`chat.py`)
- Switched from `codeblocks.render_group()` to `rich.Markdown` for assistant responses
- Codeblock click listener calls in `stream_response()` are commented out
- Numbered, click-to-copy code block UI is removed (temporarily)

**New Prompt Stacking Command** (`commands.py`)
- Added `/prompt stack` — combine multiple prompt segments into one
- `/prompt clear` now resets session context (clears messages, resets parent ID)
- Added `stack` to help text and tab completion

**Autonomy Mode Persistence Fix** (`commands.py`)
- Fixed: autonomy mode changes now correctly persist `agent_toggles` to config
- Previously only custom mode saved toggles; now all modes save properly

**Visual Settings Enhancement** (`visual.py`, `completion.py`)
- Added `show_tool_stream` boolean to visual settings (default: True)
- Added "compact" as a `tool_calls` display option
- Tab completion updated to include both new visual settings

**Update System Improvement** (`updater.py`)
- Added `fetch_changelog()` — fetches remote changelog from `chickadeeer/abyssalinfo`
- Update notifications now display remote changelog text inline
- More informative update prompts

**Tab Completion Robustness** (`completion.py`)
- Improved prefix matching so backspacing shows valid completions
- Case-insensitive completion matching

### Files Changed

| File | 3.0.0 | 3.0.1 | Change |
|------|-------|-------|--------|
| `chat.py` | 33,634 | 34,158 | +524 |
| `clipboard.py` | 2,886 | 517 | -2,369 |
| `codeblocks.py` | 10,347 | 10,628 | +281 |
| `commands.py` | 53,429 | 55,162 | +1,733 |
| `completion.py` | 4,695 | 4,854 | +159 |
| `updater.py` | 5,166 | 5,685 | +519 |
| `visual.py` | 1,731 | 2,085 | +354 |
| `requirements.txt` | 56 | 91 | +35 |

### Underlying Impact

- **Pyperclip dependency** adds a robust cross-platform clipboard library but removes ~150 lines of custom code
- **Code blocks** are now rendered as standard Markdown without interactive copy functionality
- The codeblock listener infrastructure is still present but disabled; likely preserved for future re-enablement
- **Prompt stacking** makes it easier to combine segments without manual copy-paste

### Known Limitations

- Click-to-copy code blocks are temporarily unavailable
- The `/cc` command shows a disabled message until the feature is re-enabled

---

## Version 3.0.0 — Major Release

Here's what changed between 2.2.0 and 3.0.0. This was a big release.

---

### What's New

**The Abyssal Proposal System Got a Facelift**

The old proposal system was getting creaky. Rebuilt from the ground up to be more intuitive and give better control. Proposals for MCP plugins, system prompts, and new sessions all flow through this now, with a proper consent system backing it all.

**Consent System** (`consent.py`)
Instead of everything being all-or-nothing, you can now grant or revoke consent per feature:
- `questions` — structured question forms
- `mcp-proposals` — new MCP plugins
- `mcp-edits` — changes to existing plugins  
- `system-proposals` — prompt changes
- `new-session` — when the model wants a fresh start
- `needs-input` — model-initiated pauses

Consent sticks between sessions. Manage it with `/consent set <feature> on|off`.

**Provider System** (`providers/`)
Proper provider architecture:
- `base.py` — the blueprint for any provider
- `deepseek_provider.py` — DeepSeek integration
- `openai_compat.py` — for OpenAI-compatible APIs

Makes adding new providers easier.

**Plugin System** (`plugins/`)
Built-in plugin management with `lobehub_skills.py` hooks into the LobeHub Skills Marketplace.

**Clipboard Support** (`clipboard.py`)
Copy/paste in the CLI works across Windows, macOS, Linux.

**Code Blocks** (`codeblocks.py`)
Better parsing, syntax highlighting that actually highlights, proper handling of multi-language snippets.

**Visual Enhancements** (`visual.py`)
New UI components, better terminal rendering, status displays that don't look like an afterthought.

**Updater System** (`updater.py`)
Checks for updates automatically, handles version management, can self-update.

**Dependency Management** (`dependencies.py`)
Automatic dependency resolution, tracks what's installed, plays nice with virtual environments.

---

### Big Changes

**Security & Autonomy**

Models can't run slash commands anymore. Full stop. They propose changes via APS, you approve them. Command gating is tighter, separation between human and model is crystal clear.

**MCP System**

Plugin proposals now include a `dependencies` field. If a plugin needs pip packages, they're shown and installed with your consent. Error handling is better, proper path management. `mcp_read_plugin` lets you peek at source code before editing.

**Configuration**

`/settings` is more granular. Config persists across sessions, defaults are saner, organized by category.

**APS Guide** (`aps_guide.py`)

Instead of scattered protocol blocks, there's a dedicated guide injected into the system prompt.

**Command System** (`commands.py`)

Grew from 19KB to 53KB. More comprehensive command handling, better validation, better help. New commands: `/agent`, `/consent`, `/prompt list`.

**UI & Sound**

Better colors, panel styling, responsive interface. Sound system got love too.

**Agent Actions** (`agent_actions.py`)

Refactored from 29KB to 20KB. Yanked out model command execution, simplified APS handling, cleaned up consent integration.

**Core System** (`core.py`)

Trimmed from 20KB to 17KB. Leaner core logic, better error handling, session management.

---

### New Files

| File | What it does |
|------|--------------|
| `aps_guide.py` | APS protocol docs |
| `clipboard.py` | Clipboard integration |
| `codeblocks.py` | Code block handling |
| `consent.py` | Consent management |
| `dependencies.py` | Dependency stuff |
| `updater.py` | Auto-update system |
| `visual.py` | UI enhancements |
| `plugins/lobehub_skills.py` | LobeHub integration |
| `providers/base.py` | Provider base class |
| `providers/deepseek_provider.py` | DeepSeek API |
| `providers/openai_compat.py` | OpenAI-compatible |
| `providers/__init__.py` | Module init |

### Removed Files

| File | Why it's gone |
|------|---------------|
| `settings_screen.py` | Replaced by new UI + `/agent` commands |

### File Size Changes (2.2.0 → 3.0.0)

| File | 2.2.0 | 3.0.0 | Difference |
|------|-------|-------|------------|
| `agent.py` | 7,159 | 3,491 | -3,668 |
| `agent_actions.py` | 29,558 | 20,374 | -9,184 |
| `app.py` | 5,371 | 6,227 | +856 |
| `chat.py` | 33,524 | 33,634 | +110 |
| `commands.py` | 19,438 | 53,429 | +33,991 |
| `completion.py` | 1,073 | 4,695 | +3,622 |
| `config.py` | 12,597 | 14,279 | +1,682 |
| `core.py` | 20,423 | 17,384 | -3,039 |
| `cowork.py` | 16,150 | 16,005 | -145 |
| `files.py` | 3,357 | 3,579 | +222 |
| `mcp.py` | 18,117 | 19,354 | +1,237 |
| `sounds.py` | 3,283 | 3,560 | +277 |
| `ui.py` | 2,476 | 2,976 | +500 |
| `settings_screen.py` | 70,761 | — | GONE |

---

### Security Stuff

- Models can't execute commands anymore
- Consent-based permissions for everything
- Better input sanitization
- MCP plugins get dependency verification
- Sessions are properly isolated

### UX Improvements

- UI feels less clunky
- Status indicators that actually indicate something
- Help system that's actually helpful
- Error messages you can act on
- Progress bars for long ops
- Clipboard integration so you're not retyping stuff
- Sound notifications that don't annoy you

### Bug Fixes

- MCP tool execution doesn't crap out as much
- Failed proposals give useful error messages now
- Consent system handles edge cases without dying
- Clipboard works on all platforms (finally)
- Dependency resolution is less finicky
- Malformed JSON doesn't crash everything

---

## Upgrading from 2.2.0

A few things to keep in mind:

1. **Config**: Some settings moved or got renamed.
2. **Commands**: The model can't run them anymore — it proposes, you approve.
3. **Consent**: You'll need to grant consent for features you want the model to use.
4. **Plugins**: Existing ones should work, but might need tweaks.
5. **Skills**: The ones in `~/.abyssal-cli/skills/` are still fine.

## Upgrading from 3.0.0

1. **Clipboard**: The new `pyperclip` dependency will be installed automatically.
2. **Visual**: Code blocks are now plain Markdown. The interactive click-to-copy feature is temporarily disabled.
3. **Prompts**: `/prompt stack` is available for combining segments.

---

**Written by an Abyssal Agent**
