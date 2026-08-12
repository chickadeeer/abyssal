from __future__ import annotations
_I='session_id'
_H='parent_message_id'
_G='messages'
_F='#115e59'
_E='system_prompt'
_D='updated_at'
_C='title'
_B=None
_A=False
import json
from datetime import datetime
from typing import Any,Dict,List,Optional
from prompt_toolkit.key_binding import KeyBindings
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from.agent import AGENT_SETTINGS_DEFAULTS
from.client import DeepSeekClient,DeepSeekError
from.config import AUTONOMY_MODES,MCP_HELP_INTERVAL,MODELS,all_local_transcripts,load_config,load_token,mask,save_config,save_token,token_source,transcript_path
from.cowork import load_tasks,vault_root
from.mcp import MCPManager
from.skills import list_skills,skills_summary_block
from.ui import console,print_banner
class BaseCLI:
	def __init__(A,token=_B,debug=_A,model=_B,resume_session=_B):
		D='enter';C='human-needed';B=token;A.cfg=load_config();A.debug=debug or A.cfg.get('debug',_A);A.model=model or A.cfg.get('model','default');A.thinking_enabled=A.cfg.get('thinking',_A);A.search_enabled=A.cfg.get('search',_A);A.system_prompt=A.cfg.get(_E,'');A.active_prompt_name=A.cfg.get('active_prompt_name','');A.client=_B;A.session_id=_B;A.session_title='';A.parent_message_id=_B;A.messages=[];A._session_index=[];A._resume_target=resume_session;A._cancelled=_A;A._next_prompt_default='';A.mcp=MCPManager();A.taskman=_B;A._next_tools_reminder_at=MCP_HELP_INTERVAL;A.autonomy_mode=A.cfg.get('autonomy',C)
		if A.autonomy_mode not in AUTONOMY_MODES:A.autonomy_mode=C
		A.agent_settings=dict(AGENT_SETTINGS_DEFAULTS);A.agent_settings.update(A.cfg.get('agent_toggles',{}));E=AUTONOMY_MODES[A.autonomy_mode]
		if A.autonomy_mode!='custom':A.agent_settings.update(E.get('toggles',{}))
		A.session_notes=[];A._mcp_rejected_plugins=set();A._exit_requested=_A;A.pending_file_ids=[];A.uploaded_files=[]
		if B:save_token(B.strip())
		A.kb=KeyBindings()
		@A.kb.add('c-j')
		@A.kb.add('escape',D)
		def F(event):event.app.current_buffer.insert_text('\n')
		@A.kb.add(D)
		def G(event):event.app.current_buffer.validate_and_handle()
		@A.kb.add('c-v')
		def H(event):
			C=event
			try:import win32clipboard as A;A.OpenClipboard();B=A.GetClipboardData();A.CloseClipboard();C.app.current_buffer.insert_text(B)
			except Exception:
				try:import pyperclip as D;B=D.paste();C.app.current_buffer.insert_text(B)
				except Exception:pass
		A.prompt_session=_B
	def print_banner(A):print_banner()
	def status_line(A):
		K='status';J='[success]on[/]';F='[dim]off[/]';B=[f"[accent]session[/]: {A.session_id[:8]}…"if A.session_id else'[dim]no session[/]',f"[accent]model[/]: {A.model}",f"[accent]thinking[/]: {J if A.thinking_enabled else F}",f"[search]web[/]: {J if A.search_enabled else F}"];L=AUTONOMY_MODES.get(A.autonomy_mode,{});B.append(f"[dim]auto: {L.get("label",A.autonomy_mode)}[/]")
		if A.mcp.tools:B.append(f"[mcp]mcp[/]: {len(A.mcp.tools)} tools")
		G=len(list_skills())
		if G:B.append(f"[dim]skills: {G}[/]")
		if A.pending_file_ids:B.append(f"[accent]files[/]: {len(A.pending_file_ids)} pending")
		if A.active_prompt_name:B.append(f"[system]prompt[/]: {A.active_prompt_name}")
		elif A.system_prompt:B.append('[system]prompt[/]: custom')
		if A.session_notes:B.append(f"[dim]notes: {len(A.session_notes)}[/]")
		H=load_tasks();C=sum(1 for A in H if A.get(K)=='pending');D=sum(1 for A in H if A.get(K)=='running')
		if C>0 or D>0:
			E=[]
			if C>0:E.append(f"{C} pending")
			if D>0:E.append(f"{D} running")
			B.append(f"[warning]{", ".join(E)} tasks[/]")
		I=vault_root()
		if I:B.append(f"[dim]vault: {I}[/]")
		B.append(f"debug: {"[warning]on[/]"if A.debug else F}");return Text.from_markup('  │  '.join(B))
	def print_status(A):console.print(Rule(A.status_line(),style=_F))
	def authenticate(B):
		for E in range(3):
			A=load_token()
			if not A:
				console.print('[info]No ABYSSAL_TOKEN / DEEPSEEK_TOKEN found in env or .env files.[/]');A=Prompt.ask('[accent]Paste your Abyssal auth token[/]').strip()
				if not A:console.print('[error]A token is required.[/]');continue
				C=save_token(A);console.print(f"[success]✓[/] Token saved to [accent]{C}[/] (mode 600)")
			D=DeepSeekClient(A,debug=B.debug);B.client=D;console.print(f"[success]✓[/] Authenticated  [dim](source: {token_source()}, {mask(A)})[/]");return True
		return _A
	def new_session(A,quiet=_A):
		if not A.client:return _A
		with console.status('[accent]Creating session…[/]',spinner='dots'):
			try:A.session_id=A.client.create_session()
			except DeepSeekError as B:console.print(f"[error]Failed to create session: {B}[/]");return _A
		A.parent_message_id=_B;A.messages.clear();A.session_title='';A._next_tools_reminder_at=MCP_HELP_INTERVAL;A.session_notes=[];A._mcp_rejected_plugins=set()
		if not quiet:console.print(f"[success]✓[/] New session [accent]{A.session_id[:12]}…[/]")
		return True
	def _apply_session(A,session_id):B=session_id;A.session_id=B;C=json.loads(transcript_path(B).read_text(encoding='utf-8'))if transcript_path(B).exists()else{};A.messages=C.get(_G,[]);A.parent_message_id=C.get(_H);A.session_title=C.get(_C,'');A._next_tools_reminder_at=len(A.messages)+MCP_HELP_INTERVAL;A.session_notes=[];A._mcp_rejected_plugins=set()
	def _save_transcript(A):
		if not A.session_id:return
		B={_I:A.session_id,_C:A.session_title,'model':A.model,_E:A.system_prompt,_H:A.parent_message_id,_G:A.messages,_D:datetime.now().isoformat()}
		try:transcript_path(A.session_id).write_text(json.dumps(B,indent=2,ensure_ascii=_A),encoding='utf-8')
		except OSError:pass
	def cmd_sessions(G):
		L='dim';I='updated';F='id'
		if not G.client:return
		with console.status('[accent]Fetching sessions…[/]',spinner='dots'):
			try:M=G.client.list_sessions()
			except DeepSeekError as N:console.print(f"[error]Could not list sessions: {N}[/]");return
		O=all_local_transcripts();B=Table(title='Chat Sessions',border_style=_F,header_style='bold #0d9488');B.add_column('#',style=L,width=4);B.add_column('ID',style='accent');B.add_column('Title');B.add_column('Updated',style=L);B.add_column('',width=2);C,J=[],set()
		for D in M:
			E=str(D.get(F)or D.get(_I)or'')
			if not E:continue
			J.add(E);C.append({F:E,_C:D.get(_C)or D.get('name')or'',I:D.get(_D)or D.get('create_time')or''})
		for(E,K)in O.items():
			if E not in J:C.append({F:E,_C:K.get(_C,'')+' [dim](local only)[/]',I:K.get(_D,'')})
		C.sort(key=lambda r:str(r[I]),reverse=True);G._session_index=[A[F]for A in C]
		if not C:console.print('[dim]No sessions yet. Type a message to start one.[/]');return
		for(P,H)in enumerate(C,1):
			A=H[I]
			if isinstance(A,(int,float)):A=datetime.fromtimestamp(A/1000 if A>1e12 else A).strftime('%Y-%m-%d %H:%M')
			elif isinstance(A,str)and A:A=A[:16].replace('T',' ')
			Q='[success]●[/]'if H[F]==G.session_id else'';B.add_row(str(P),H[F][:16]+'…',H[_C][:48]or'[dim]untitled[/]',str(A),Q)
		console.print(B);console.print('[dim]Resume / rename / delete from /settings → Sessions[/]')
	def _agent_protocol_block(B):
		D='allow-mcp-proposals';E=B.agent_settings;C=AUTONOMY_MODES.get(B.autonomy_mode,{})
		def A(key):return'ENABLED'if E.get(key)else'disabled'
		return'\n'.join(['# AGENT CONTROL PROTOCOL','You are running inside Abyssal. The human user controls your capabilities from the /settings screen; you can never change these settings yourself.','',f"AUTONOMY MODE: {C.get("label",B.autonomy_mode)} — {C.get("desc","")}",'','HARD LIMITS (always in force, no exceptions):','- You can NEVER message, prompt, or reply to yourself, and you can never act as the user.','- You can NOT switch models mid-conversation. If a different model is needed, the user must start a new session (/new) — all current context will be lost.','- You can never run /settings, /retry, /edit, or /paste.','',f"Model-initiated slash commands: {A("model-commands")}. When enabled, you may request any existing CLI slash command by outputting exactly:",'[COMMAND: /some-command arguments]','[/COMMAND]','One command per block, then wait for its [COMMAND_RESULT]. Depending on the autonomy mode, privileged or destructive commands may require explicit user confirmation. /notes add <text> stores a session-scoped note (wiped on /new).','',f"MCP plugin proposals: {A(D)}. Propose a brand-new MCP plugin server with a JSON block. YOU MUST USE THE OFFICIAL MCP SDK IMPORT: `from mcp.server.fastmcp import FastMCP`. Do NOT use `from fastmcp import FastMCP`. The 'code' field is a JSON string — escape newlines as \\n so multi-line Python works. The script MUST end with `if __name__ == \"__main__\": mcp.run()`. If you omit `mcp.run()` or use the wrong import, the server will crash with 'Connection closed'.",'[MCP_PROPOSAL]','{"name": "plugin_name", "reason": "why this helps", "code": "from mcp.server.fastmcp import FastMCP\\n\\nmcp = FastMCP(\\"MyPlugin\\")\\n\\n@mcp.tool()\\ndef my_tool(arg: str) -> str:\\n    return arg\\n\\nif __name__ == \\"__main__\\":\\n    mcp.run()"}','[/MCP_PROPOSAL]','',f"MCP plugin edits: {A(D)}. WORK SURGICALLY: first call the mcp_read_plugin tool to see the full numbered source, then send a MINIMAL unified diff in the 'patch' field — only rewrite the whole file in 'code' for tiny plugins. The user sees the resulting diff and approves it:",'[MCP_EDIT_PROPOSAL]','{"name": "existing_plugin_name", "reason": "why this edit is needed", "patch": "@@ -12,7 +12,7 @@\\n context line\\n-old line\\n+new line"}','[/MCP_EDIT_PROPOSAL]','',f"System-prompt proposals: {A("allow-system-proposals")}. JSON block:",'[SYSTEM_PROPOSAL]','{"reason": "why", "prompt": "the full proposed system prompt"}','[/SYSTEM_PROPOSAL]','',f"Structured questions: {A("allow-model-questions")}. Ask several questions at once; mark each blocking (must answer) or optional (has a default, can be skipped). Blocking questions surface first. Answers come back as 'Question N: answer' lines.",'[QUESTIONS]','{"questions": [{"text": "Which style?", "choices": ["dark", "light"], "blocking": true}, {"text": "Site title?", "allow_text": true, "blocking": false, "default": "My Site"}]}','[/QUESTIONS]','','SKILLS: reusable knowledge you or the user wrote. Call skills_list / skill_read BEFORE a matching task (e.g. read a frontend-design skill before building a webpage). Write skills with skill_write {"name", "content", "description", "note"} — especially AFTER finishing a task where a skill would have helped: write it now so it exists next time. Skills are versioned: skill_diff compares versions and skill_rollback reverts if a newer version made things worse.','',f"Human-input pause: {A("allow-model-pause")}. To suspend the loop and ask the user:",'[NEEDS_INPUT] your clear question or decision request [/NEEDS_INPUT]','',f"New-session request: {A("allow-model-new")}. A clean slate loses ALL context:",'[NEW_SESSION] reason [/NEW_SESSION]'])
	def build_final_prompt(A,user_prompt):
		C=user_prompt
		if A.parent_message_id is _B and not A.messages:
			B=[]
			if A.system_prompt:B.append(A.system_prompt.strip())
			B.append(A._agent_protocol_block());D=A.mcp.get_short_block()
			if D:B.append(D)
			E=skills_summary_block()
			if E:B.append(E)
			if B:return f"<system>\n"+'\n'.join(B)+f"\n</system>\n{C}"
		return C
	def _maybe_attach_tools_reminder(A,prompt):
		B=prompt
		if len(A.messages)>=A._next_tools_reminder_at:A._next_tools_reminder_at=len(A.messages)+MCP_HELP_INTERVAL;console.print(f"[mcp]ⓘ Re-injecting MCP tool reference (every {MCP_HELP_INTERVAL} messages)[/]");return B+'\n<tools_reminder>\n'+A.mcp.get_help_block()+'\n</tools_reminder>'
		return B