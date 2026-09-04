# Changelog

## Version 3.00

Here's what I changed between 2.20 and 3.00. This one's a big release.

---

## What's New

### The Abyssal Proposal System Got a Facelift

The old proposal system was getting creaky. I rebuilt it from the ground up to be more intuitive and give you better control. Proposals for MCP plugins, system prompts, and new sessions all flow through this now, and there's a proper consent system backing it all.

**Consent System** (`consent.py`)
This is the big one. Instead of everything being all-or-nothing, you can now grant or revoke consent per feature:
- `questions` — structured question forms
- `mcp-proposals` — new MCP plugins
- `mcp-edits` — changes to existing plugins  
- `system-proposals` — prompt changes
- `new-session` — when the model wants a fresh start
- `needs-input` — model-initiated pauses

Consent sticks between sessions, and you manage it with `/consent set <feature> on|off`.

### Provider System (`providers/`)

I finally cleaned up how models get plugged in. No more scattered API calls. There's a proper provider architecture now with:
- `base.py` — the blueprint for any provider
- `deepseek_provider.py` — DeepSeek integration
- `openai_compat.py` — for OpenAI-compatible APIs

Makes adding new providers way easier.

### Plugin System (`plugins/`)

Built-in plugin management with one standout: `lobehub_skills.py` hooks into the LobeHub Skills Marketplace. Plugins load dynamically and you manage them via `/mcp`.

### Clipboard Support (`clipboard.py`)

Copy/paste in the CLI actually works now. Works across Windows, macOS, Linux.

### Code Blocks (`codeblocks.py`)

Better parsing, syntax highlighting that actually highlights, and proper handling of multi-language snippets. No more code block soup.

### Visual Enhancements (`visual.py`)

New UI components, better terminal rendering, status displays that don't look like an afterthought.

### Updater System (`updater.py`)

Checks for updates automatically, handles version management, can self-update. No more wondering if you're on the latest version.

### Dependency Management (`dependencies.py`)

Automatic dependency resolution, tracks what's installed, plays nice with virtual environments.

---

## Big Changes

### Security & Autonomy

**Models can't run slash commands anymore.** Full stop. They propose changes via APS, you approve them. It's cleaner, safer, and stops the model from doing anything sketchy. Command gating is tighter, and the separation between what the human does and what the model does is crystal clear.

### MCP System

Plugin proposals now include a `dependencies` field. If a plugin needs pip packages, I show you what they are and install them with your consent. Error handling is better, and there's a proper path management system now. `mcp_read_plugin` lets you peek at source code before editing.

### Configuration

`/settings` is more granular now. Config persists across sessions, defaults are saner, and settings are organized by category so you can actually find stuff.

### APS Guide (`aps_guide.py`)

Instead of scattered protocol blocks, there's now a dedicated guide that gets injected into the system prompt. The model always knows the rules.

### Command System (`commands.py`)

This file blew up from 19KB to 53KB. Way more comprehensive command handling, better validation, better help. New commands: `/agent`, `/consent`, `/prompt list`.

### UI & Sound

Better colors, better panel styling, more responsive interface. Sound system got some love too — better notifications and platform support.

### Agent Actions (`agent_actions.py`)

Refactored down from 29KB to 20KB. I yanked out the model command execution stuff, simplified the APS handling, and cleaned up the consent integration.

### Core System (`core.py`)

Trimmed from 20KB to 17KB. Leaner core logic, better error handling, session management that doesn't make you want to throw your computer out the window.

---

## New Files

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

## Removed Files

| File | Why it's gone |
|------|---------------|
| `settings_screen.py` | Replaced by new UI + `/agent` commands |

## File Size Changes

| File | v2.20 | v3.00 | Difference |
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

## Security Stuff

- Models can't execute commands anymore
- Consent-based permissions for everything
- Better input sanitization
- MCP plugins get dependency verification
- Sessions are properly isolated

## UX Improvements

- UI feels less clunky
- Status indicators that actually indicate something
- Help system that's actually helpful
- Error messages you can act on
- Progress bars for long ops
- Clipboard integration so you're not retyping stuff
- Sound notifications that don't annoy you

## Bug Fixes

- MCP tool execution doesn't crap out as much
- Failed proposals give useful error messages now
- Consent system handles edge cases without dying
- Clipboard works on all platforms (finally)
- Dependency resolution is less finicky
- Malformed JSON doesn't crash everything

## Documentation Updates

- APS guide is now in the system prompt
- Help system is better
- Command references are up to date
- Error messages actually tell you what went wrong

## What's Next

- Claude and Gemini providers
- Better plugin ecosystem
- More skills marketplace integration
- Smarter auto-updates
- Performance stuff

---

## Upgrading from 2.20

A few things to keep in mind:

1. **Config**: Some settings moved or got renamed.
2. **Commands**: The model can't run them anymore — it proposes, you approve.
3. **Consent**: You'll need to grant consent for features you want the model to use.
4. **Plugins**: Existing ones should work, but might need tweaks.
5. **Skills**: The ones in `~/.abyssal-cli/skills/` are still fine.

If something breaks, check the docs or file an issue.

Written by an Abyssal Agent :)