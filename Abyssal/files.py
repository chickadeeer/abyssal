from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any,Dict,List
from rich.table import Table
from.ui import console
class FileCommandsMixin:
	def cmd_upload(B,parts):
		D=parts
		if len(D)<2:console.print('[warning]Usage: /upload <path>[/]');return
		if not B.client:console.print('[error]Not authenticated.[/]');return
		E=' '.join(D[1:]).strip();A=Path(E).expanduser()
		if not A.exists():console.print(f"[error]File not found: {A}[/]");return
		if not A.is_file():console.print(f"[error]Not a file: {A}[/]");return
		try:
			with console.status(f"[accent]Uploading {A.name}…[/]",spinner='dots'):C=B.client.api.upload_file(str(A),model_type=B.model,thinking_enabled=B.thinking_enabled)
		except Exception as F:console.print(f"[error]Upload failed: {F}[/]");return
		B.pending_file_ids.append(C);B.uploaded_files.append({'id':C,'path':str(A),'name':A.name,'uploaded_at':datetime.now().isoformat()});console.print(f"[success]✓[/] Uploaded [accent]{A.name}[/] → [dim]{C}[/] · attached to next completion")
	def cmd_files(A,parts):
		F='list';D=parts;E=D[1].lower()if len(D)>1 else F
		if E=='clear':G=len(A.pending_file_ids);A.pending_file_ids=[];console.print(f"[success]✓[/] Cleared {G} pending file attachment(s)");return
		if E!=F:console.print('[warning]Usage: /files [list|clear][/]');return
		if not A.pending_file_ids and not A.uploaded_files:console.print('[dim]No uploaded files this session.[/]');return
		B=Table(title='Uploaded Files',border_style='#115e59',header_style='bold #0d9488');B.add_column('Pending',width=8);B.add_column('File ID',style='accent');B.add_column('Name');B.add_column('Path',style='dim');H=set(A.pending_file_ids)
		for C in A.uploaded_files:B.add_row('[success]yes[/]'if C['id']in H else'[dim]sent[/]',C['id'],C.get('name',''),C.get('path',''))
		console.print(B);console.print('[dim]Pending files are attached to the next completion. Use /files clear to remove pending attachments.[/]')