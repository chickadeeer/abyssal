from __future__ import annotations

import re
from typing import List, Tuple

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _parse_hunks(patch: str) -> List[Tuple[int, List[str], List[str]]]:
    
    lines = patch.splitlines()
    hunks: List[Tuple[int, List[str], List[str]]] = []
    i = 0
    while i < len(lines):
        m = HUNK_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        old_start = int(m.group(1))
        i += 1
        old: List[str] = []
        new: List[str] = []
        while i < len(lines):
            l = lines[i]
            if HUNK_RE.match(l.strip()) or l.startswith(("--- ", "+++ ")):
                break
            if l.startswith("+"):
                new.append(l[1:])
            elif l.startswith("-"):
                old.append(l[1:])
            elif l.startswith(" "):
                old.append(l[1:])
                new.append(l[1:])
            elif l.startswith("\\"):
                pass  
            else:
                
                old.append(l)
                new.append(l)
            i += 1
        hunks.append((old_start, old, new))
    return hunks


def _find(lines: List[str], needle: List[str], approx: int) -> int:
    
    if not needle:
        return max(0, min(approx, len(lines)))

    def match_at(i: int) -> bool:
        if i < 0 or i + len(needle) > len(lines):
            return False
        return all(a.rstrip() == b.rstrip()
                   for a, b in zip(lines[i:i + len(needle)], needle))

    if match_at(approx):
        return approx
    for delta in range(1, 61):
        if match_at(approx - delta):
            return approx - delta
        if match_at(approx + delta):
            return approx + delta
    for i in range(0, max(0, len(lines) - len(needle)) + 1):
        if match_at(i):
            return i
    return -1


def apply_unified_patch(source: str, patch: str) -> Tuple[bool, str, str]:
    
    hunks = _parse_hunks(patch)
    if not hunks:
        return False, "", (
            "No diff hunks found. The 'patch' field must be a unified diff "
            "with @@ -l,c +l,c @@ headers and +/-/space line prefixes.")
    result = source.split("\n")
    offset = 0
    for idx, (old_start, old_lines, new_lines) in enumerate(hunks, 1):
        pos = _find(result, old_lines, old_start - 1 + offset)
        if pos < 0:
            return False, "", (
                f"Hunk {idx} (@@ -{old_start}) does not match the current file. "
                "Re-read the plugin with the mcp_read_plugin tool and regenerate "
                "the patch against the exact current content.")
        result[pos:pos + len(old_lines)] = new_lines
        offset += len(new_lines) - len(old_lines)
    return True, "\n".join(result), ""