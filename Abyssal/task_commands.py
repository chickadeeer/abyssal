from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import List, Optional

from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .config import MODELS, TASK_INTERVAL_CHOICES
from .cowork import (
    _ask_datetime,
    _ask_time,
    _fmt_dt,
    _schedule_label,
    find_task,
    load_tasks,
    new_task,
    save_tasks,
)
from .ui import console


class TaskCommandsMixin:
    

    def cmd_task(self, parts: List[str]) -> None:
        sub = parts[1].lower() if len(parts) > 1 else "list"

        if sub == "add":
            self._task_add()
        elif sub == "list":
            self._task_list()
        elif sub in ("remove", "rm", "delete"):
            self._task_action(parts, "remove")
        elif sub == "run":
            self._task_action(parts, "run")
        elif sub == "pause":
            self._task_action(parts, "pause")
        elif sub == "result":
            self._task_action(parts, "result")
        elif sub == "clear":
            tasks = load_tasks()
            keep = [t for t in tasks if t.get("status") not in ("done", "failed")]
            removed = len(tasks) - len(keep)
            save_tasks(keep)
            console.print(f"[success]✓[/] Cleared {removed} finished task(s)")
        else:
            console.print(
                "[warning]Usage: /task [add|list|remove <id>|run <id>|"
                "pause <id>|result <id>|clear][/]"
            )

    def _task_add(self) -> None:
        console.print(Panel(
            Text("Answer the prompts to schedule a new task. Ctrl+C aborts.", style="dim"),
            title="[accent]New Cowork task[/]",
            border_style="#0d9488",
        ))

        try:
            prompt = Prompt.ask("[accent]Prompt to run[/]").strip()
            if not prompt:
                console.print("[warning]Empty prompt — nothing scheduled.[/]")
                return

            model = Prompt.ask(
                "[accent]Model[/]",
                choices=[*MODELS.keys(), "custom"],
                default=self.model if self.model in MODELS else "custom",
            )

            if model == "custom":
                model = Prompt.ask("Custom model_type", default=self.model)

            thinking = Confirm.ask("Thinking mode?", default=self.thinking_enabled)
            search = Confirm.ask("Web search?", default=self.search_enabled)
            mcp_enabled = Confirm.ask("Flag task as MCP-enabled?", default=bool(self.mcp.tools))

            selected_tools: List[str] = []

            if mcp_enabled and self.mcp.tools:
                console.print("[accent]Available MCP tools:[/]")
                for i, t in enumerate(self.mcp.tools, 1):
                    console.print(f"  {i}. [bold]{t['name']}[/] - {t['description'][:60]}")

                while True:
                    try:
                        choice = Prompt.ask("Add tool (name or number), or type 'mcpdone' to finish").strip()
                    except (KeyboardInterrupt, EOFError):
                        break

                    if choice.lower() in ("mcpdone", "done", ""):
                        break

                    found = None

                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(self.mcp.tools):
                            found = self.mcp.tools[idx]["name"]
                    else:
                        for t in self.mcp.tools:
                            if t["name"] == choice:
                                found = choice
                                break

                    if found:
                        if found not in selected_tools:
                            selected_tools.append(found)
                            console.print(f"[success]✓ Added {found}[/]")
                    else:
                        console.print("[warning]Tool not found.[/]")

            use_sys = Confirm.ask(
                "Use the current chat system prompt for this task?",
                default=bool(self.system_prompt),
            )

            schedule = Prompt.ask(
                "[accent]Schedule[/]",
                choices=["30min", "1hr", "2hr", "6hr", "12hr", "daily", "weekly", "once"],
                default="once",
            )

            schedule_type = "interval"
            interval_minutes: Optional[int] = 60
            run_at: Optional[datetime] = None

            if schedule in TASK_INTERVAL_CHOICES:
                schedule_type, interval_minutes = "interval", TASK_INTERVAL_CHOICES[schedule]
            elif schedule == "daily":
                schedule_type, interval_minutes = "daily", None
                tm = _ask_time("Time each day (HH:MM)", "09:00")
                if not tm:
                    console.print("[error]Invalid time — cancelled.[/]")
                    return
                run_at = datetime.combine(datetime.now().date(), tm)
            elif schedule == "weekly":
                schedule_type, interval_minutes = "weekly", None
                run_at = _ask_datetime("First run (YYYY-MM-DD HH:MM)")
                if not run_at:
                    console.print("[error]Invalid date — cancelled.[/]")
                    return
            else:  
                schedule_type, interval_minutes = "once", None
                run_at = _ask_datetime(
                    "Run at (YYYY-MM-DD HH:MM)",
                    default=(datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"),
                )
                if not run_at:
                    console.print("[error]Invalid date — cancelled.[/]")
                    return

            output_file = Prompt.ask("Output file (blank to skip)", default="").strip()
            chain_raw = Prompt.ask("Chain next task id when done (blank for none)", default="").strip()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Task creation cancelled.[/]")
            return

        chain_id = ""
        if chain_raw:
            target = find_task(load_tasks(), chain_raw)
            if target:
                chain_id = target["id"]
            else:
                console.print("[warning]Chain target not found — continuing without chain.[/]")

        task = new_task(
            prompt=prompt,
            model=model,
            thinking=thinking,
            search=search,
            mcp_enabled=mcp_enabled,
            schedule_type=schedule_type,
            interval_minutes=interval_minutes,
            run_at=run_at,
            output_file=output_file,
            chain_task_id=chain_id,
            system_prompt=self.system_prompt if use_sys else "",
            selected_tools=selected_tools,
        )

        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)

        console.print(
            f"[success]✓[/] Task [accent]{task['id'][:8]}[/] scheduled — "
            f"{_schedule_label(task)} · next run {_fmt_dt(task.get('next_run'))}"
        )

    def _task_list(self) -> None:
        tasks = load_tasks()

        if not tasks:
            console.print("[dim]No scheduled tasks. Use [accent]/task add[/] to create one.[/]")
            return

        table = Table(
            title="Cowork Tasks",
            border_style="#115e59",
            header_style="bold #0d9488",
        )
        table.add_column("ID", style="accent")
        table.add_column("Prompt")
        table.add_column("Model")
        table.add_column("Schedule")
        table.add_column("Next run", style="dim")
        table.add_column("Last run", style="dim")
        table.add_column("Status")

        status_style = {
            "pending": "dim",
            "running": "yellow",
            "done": "success",
            "failed": "error",
            "paused": "warning",
        }

        for t in tasks:
            status = t.get("status", "pending")
            style = status_style.get(status, "dim")
            p = t.get("prompt", "")
            chain = " ⛓" if t.get("chain_task_id") else ""
            out = " 📄" if t.get("output_file") else ""

            table.add_row(
                t.get("id", "")[:8],
                (p[:40] + ("…" if len(p) > 40 else "")) + chain + out,
                t.get("model", "default"),
                _schedule_label(t),
                _fmt_dt(t.get("next_run")),
                _fmt_dt(t.get("last_run")),
                f"[{style}]{status}[/]",
            )

        console.print(table)
        console.print(
            "[dim]/task run <id> now · /task pause <id> pause/resume · "
            "/task result <id> output · ⛓ chains · 📄 output file[/]"
        )

    def _task_action(self, parts: List[str], action: str) -> None:
        if len(parts) < 3:
            console.print(f"[warning]Usage: /task {action} <id>[/]")
            return

        tasks = load_tasks()
        task = find_task(tasks, parts[2])

        if not task:
            console.print(f"[error]Task '{parts[2]}' not found (or id is ambiguous).[/]")
            return

        if action == "remove":
            tasks = [t for t in tasks if t["id"] != task["id"]]

            
            for t in tasks:
                if t.get("chain_task_id") == task["id"]:
                    t["chain_task_id"] = ""

            save_tasks(tasks)
            console.print(f"[success]✓[/] Removed task [accent]{task['id'][:8]}[/]")

        elif action == "run":
            if not self.taskman:
                console.print("[error]Scheduler not running yet.[/]")
                return
            console.print(f"[info]Running task {task['id'][:8]} now…[/]")
            threading.Thread(
                target=self.taskman.execute_task,
                args=(task["id"],),
                daemon=True,
            ).start()

        elif action == "pause":
            if task.get("status") == "paused":
                task["status"] = "pending"
                save_tasks(tasks)
                console.print(f"[success]✓[/] Resumed [accent]{task['id'][:8]}[/]")
            else:
                task["status"] = "paused"
                save_tasks(tasks)
                console.print(
                    f"[success]✓[/] Paused [accent]{task['id'][:8]}[/] "
                    f"(skipped by scheduler)"
                )

        elif action == "result":
            res = task.get("result")
            if not res:
                console.print("[dim]No result recorded for this task yet.[/]")
                return

            try:
                body = Markdown(res) if len(res) < 20000 else Text(res)
            except Exception:
                body = Text(res)

            console.print(Panel(
                body,
                title=f"[accent]Result — {task['id'][:8]}[/]",
                title_align="left",
                border_style="#0d9488",
                padding=(0, 1),
            ))