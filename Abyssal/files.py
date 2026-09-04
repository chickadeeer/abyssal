from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from rich.table import Table

from .ui import console


class FileCommandsMixin:
    

    def cmd_upload(self, parts: List[str]) -> None:
        
        if len(parts) < 2:
            console.print("[warning]Usage: /upload <path>[/]")
            return
        if not self.provider:
            console.print("[error]Not authenticated.[/]")
            return
        if not getattr(self.provider, "supports_uploads", False):
            console.print(
                f"[error]The '{self.provider.name}' provider does not support uploads. "
                f"Switch with /provider deepseek.[/]")
            return
        raw_path = " ".join(parts[1:]).strip()
        path = Path(raw_path).expanduser()
        if not path.exists():
            console.print(f"[error]File not found: {path}[/]")
            return
        if not path.is_file():
            console.print(f"[error]Not a file: {path}[/]")
            return
        try:
            with console.status(f"[accent]Uploading {path.name}…[/]", spinner="dots"):
                file_id = self.provider.upload_file(
                    str(path),
                    model_type=self.model,
                    thinking_enabled=self.thinking_enabled,
                )
        except Exception as e:
            console.print(f"[error]Upload failed: {e}[/]")
            return
        self.pending_file_ids.append(file_id)
        self.uploaded_files.append({
            "id": file_id,
            "path": str(path),
            "name": path.name,
            "uploaded_at": datetime.now().isoformat(),
        })
        console.print(
            f"[success]✓[/] Uploaded [accent]{path.name}[/] → "
            f"[dim]{file_id}[/] · attached to next completion"
        )

    def cmd_files(self, parts: List[str]) -> None:
        
        sub = parts[1].lower() if len(parts) > 1 else "list"
        if sub == "clear":
            n = len(self.pending_file_ids)
            self.pending_file_ids = []
            console.print(f"[success]✓[/] Cleared {n} pending file attachment(s)")
            return
        if sub != "list":
            console.print("[warning]Usage: /files [list|clear][/]")
            return
        if not self.pending_file_ids and not self.uploaded_files:
            console.print("[dim]No uploaded files this session.[/]")
            return
        table = Table(
            title="Uploaded Files",
            border_style="#115e59",
            header_style="bold #0d9488",
        )
        table.add_column("Pending", width=8)
        table.add_column("File ID", style="accent")
        table.add_column("Name")
        table.add_column("Path", style="dim")
        pending = set(self.pending_file_ids)
        for item in self.uploaded_files:
            table.add_row(
                "[success]yes[/]" if item["id"] in pending else "[dim]sent[/]",
                item["id"],
                item.get("name", ""),
                item.get("path", ""),
            )
        console.print(table)
        console.print(
            "[dim]Pending files are attached to the next completion. "
            "Use /files clear to remove pending attachments.[/]"
        )