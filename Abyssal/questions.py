from __future__ import annotations

from typing import Any, Dict, List

from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from .ui import console


def normalize_questions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    
    qs = data.get("questions")
    if isinstance(qs, dict):
        qs = [qs]
    if not isinstance(qs, list):
        raise ValueError("payload needs a 'questions' list")
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(qs, 1):
        if isinstance(q, str):
            q = {"text": q}
        if not isinstance(q, dict):
            raise ValueError(f"question {i} must be an object")
        text = str(q.get("text") or "").strip()
        if not text:
            raise ValueError(f"question {i} is missing its 'text'")
        choices = q.get("choices") or []
        if not isinstance(choices, list):
            choices = [choices]
        choices = [str(c).strip() for c in choices if str(c).strip()]
        out.append({
            "text": text,
            "choices": choices,
            "allow_text": bool(q.get("allow_text", not choices)),
            "blocking": bool(q.get("blocking", q.get("required", True))),
            "default": str(q.get("default") or "").strip(),
        })
    if not out:
        raise ValueError("'questions' list is empty")
    return out


def _ask_one(num: int, q: Dict[str, Any], allow_skip: bool) -> str:
    
    opts: List[str] = list(q["choices"])
    custom_label = "(type a custom answer)"
    skip_label = "(skip — use default)"
    if q["allow_text"]:
        opts.append(custom_label)
    if allow_skip:
        opts.append(skip_label)

    while True:
        if opts:
            console.print("  " + "   ".join(
                f"[dim]{k + 1})[/] {escape(o)}" for k, o in enumerate(opts)))
        default = q["default"] if (allow_skip and q["default"]) else None
        raw = Prompt.ask(f"[accent]Question {num}[/]", default=default).strip()

        if raw and raw.isdigit() and 1 <= int(raw) <= len(opts):
            picked = opts[int(raw) - 1]
            if picked == skip_label:
                return ""
            if picked == custom_label:
                return Prompt.ask(f"[accent]Question {num} — custom answer[/]").strip()
            return picked
        if raw in q["choices"]:
            return raw
        if raw:
            if q["allow_text"] or not q["choices"]:
                return raw
            console.print("[warning]Pick one of the choices, or a number.[/]")
            continue
        
        if allow_skip:
            return ""
        console.print("[warning]This question is blocking — an answer is required.[/]")


def ask_questions(qs: List[Dict[str, Any]]) -> str:
    
    lines: List[str] = []
    for idx, q in enumerate(qs, 1):
        tag = "[warning]blocking[/]" if q["blocking"] else "[dim]optional[/]"
        lines.append(f"[bold]Question {idx}[/] ({tag}) — {escape(q['text'])}")
        if q["choices"]:
            lines.append("   choices: " + " · ".join(escape(c) for c in q["choices"]))
        if q["default"]:
            lines.append(f"   [dim]default: {escape(q['default'])}[/]")
    console.print(Panel(
        Group(Text.from_markup("\n".join(lines))),
        title="[accent]DeepSeek asks…[/]",
        title_align="left",
        border_style="#0d9488",
        padding=(0, 1),
    ))

    
    order = sorted(range(len(qs)), key=lambda i: 0 if qs[i]["blocking"] else 1)
    answers: List[str] = [""] * len(qs)
    try:
        for i in order:
            q = qs[i]
            if not q["blocking"]:
                console.print(
                    f"[dim]Optional question {i + 1} — Enter accepts the default / skips.[/]")
            answers[i] = _ask_one(i + 1, q, allow_skip=not q["blocking"])
    except (KeyboardInterrupt, EOFError):
        pass  

    result: List[str] = []
    for i, q in enumerate(qs, 1):
        a = answers[i - 1]
        if not a:
            a = (f"(skipped — using default: {q['default']})"
                 if q["default"] else "(skipped)")
        result.append(f"Question {i}: {a}")
    return "[QUESTION_ANSWERS]\n" + "\n".join(result) + "\n[/QUESTION_ANSWERS]"