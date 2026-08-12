from __future__ import annotations
_U='result'
_T='[error]Invalid session number.[/]'
_S='accent'
_R='/settings'
_Q='Description'
_P='bold #0d9488'
_O='tool'
_N='[dim]off[/]'
_M='yes'
_L='true'
_K=False
_J='#115e59'
_I='message_id'
_H='server_id'
_G='on'
_F='assistant'
_E='user'
_D='content'
_C='role'
_B=None
_A=True
from datetime import datetime
from pathlib import Path
from typing import List,Optional
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from.import __version__
from.config import APP_NAME,CONFIG_FILE,load_token,mask,token_source
from.cowork import load_tasks
from.ui import console
try:from dsk.api import DeepSeekError
except ImportError:from api import DeepSeekError
class CommandsMixin:
	def cmd_help(D):
		A=Table(header_style=_P,border_style=_J,box=_B,padding=(0,2));A.add_column('Command',style='bold #2dd4bf',min_width=24);A.add_column(_Q)
		for(B,C)in[(_R,'Open the interactive settings menu — EVERYTHING lives here'),('/thinking [on|off]','Toggle thinking mode'),('/search [on|off]','Toggle web search'),('Enter','Send · Alt+Enter or Ctrl+J for newline')]:A.add_row(B,C)
		console.print(Panel(A,title='[accent]Commands[/]',border_style='#0d9488',padding=(1,2)));console.print('[dim]Sessions, tasks, MCP, skills, sounds, autonomy, prompts, files, export — all inside [accent]/settings[/]. Type [accent]/exit[/] to quit.[/]')
	def handle_command(A,raw,from_model=_K):
		G='[success]on[/]';D=raw.strip();B=D.split();C=B[0].lower()if B else''
		if C in('/exit','/quit','/q'):console.print('[dim]Goodbye.[/]');return _K
		if C in('/help','/h','/?'):A.cmd_help();return _A
		if C=='/version':console.print(f"{APP_NAME} [accent]v{__version__}[/]");return _A
		if C=='/thinking':A.thinking_enabled=not A.thinking_enabled if len(B)==1 else B[1].lower()in(_G,'1',_L,_M);A.cfg['thinking']=A.thinking_enabled;from.config import save_config as E;E(A.cfg);console.print(f"Thinking: {G if A.thinking_enabled else _N}");return _A
		if C in('/search','/websearch','/web'):A.search_enabled=not A.search_enabled if len(B)==1 else B[1].lower()in(_G,'1',_L,_M);A.cfg['search']=A.search_enabled;from.config import save_config as E;E(A.cfg);console.print(f"Web search: {G if A.search_enabled else _N}");return _A
		if from_model:return A._model_command_dispatch(D,C,B)
		if C in(_R,'/config'):
			from.settings_screen import SettingsScreen as H;F=H(A).run(section=B[1].lower()if len(B)>1 else _B)
			if F:F()
			A.print_status();return _A
		console.print(f"[warning]Unknown command:[/] {escape(D)} — only [accent]/settings[/], [accent]/thinking[/] and [accent]/search[/] exist. Open [accent]/settings[/] for everything else.");return _A
	def _model_command_dispatch(A,cmd,head,parts):
		L='active_prompt_name';K='system_prompt';F=cmd;C=parts;B=head;from.config import save_config as E
		if B=='/notes':A.cmd_notes(C,F);return _A
		if B in('/mcp-help','/mcphelp'):A.cmd_mcp_help();return _A
		if B=='/upload':A.cmd_upload(C);return _A
		if B=='/files':A.cmd_files(C);return _A
		if B=='/clear':console.clear();A.print_banner();A.print_status();return _A
		if B=='/status':A.print_status();return _A
		if B=='/new':A.new_session();return _A
		if B=='/sessions':A.cmd_sessions();return _A
		if B=='/use':
			if len(C)>=2 and A._session_index:A.action_use(C[1])
			return _A
		if B=='/rename':A.action_rename(F[len('/rename '):].strip());return _A
		if B=='/del':A.action_delete(C[1]if len(C)>=2 else _B);return _A
		if B=='/model':
			if len(C)==1:
				from.config import MODELS as M;D=Table(border_style=_J,header_style=_P,title='Models');D.add_column('Name',style=_S);D.add_column(_Q);D.add_column('',width=2)
				for(I,N)in M.items():D.add_row(I,N,'[success]●[/]'if I==A.model else'')
				console.print(D);return _A
			J=C[1].lower();A.model=J;A.cfg['model']=J;E(A.cfg);console.print(f"[success]✓[/] Model set to [accent]{A.model}[/]");return _A
		if B=='/system':
			if len(C)==1 or C[1].lower()=='show':
				if A.system_prompt:console.print(Panel(A.system_prompt,title='[system]System Prompt[/]',border_style=_J))
				else:console.print('[dim]No system prompt set.[/]')
			elif C[1].lower()=='clear':A.system_prompt='';A.active_prompt_name='';A.cfg.update({K:'',L:''});E(A.cfg);console.print('[success]✓[/] System prompt cleared')
			elif C[1].lower()=='set':
				G=F[len('/system set '):].strip()
				if G:A.system_prompt=G;A.active_prompt_name='';A.cfg.update({K:G,L:''});E(A.cfg);console.print('[success]✓[/] System prompt updated')
			return _A
		if B=='/task':A.cmd_task(C);return _A
		if B=='/mcp':
			O=A.mcp.list_servers();console.print(f"[mcp]MCP servers[/]: {len(O)}   [mcp]tools loaded[/]: {len(A.mcp.tools)}")
			for H in A.mcp.tools:console.print(f"  ⚙ [accent]{H["name"]}[/] [dim]({H["server"]})[/]: {H["description"][:70]}")
			return _A
		if B=='/save':A.cmd_export(C[1]if len(C)>1 else _B);return _A
		if B=='/history':A.cmd_history();return _A
		if B=='/debug':
			A.debug=not A.debug if len(C)==1 else C[1].lower()in(_G,'1',_L,_M);A.cfg['debug']=A.debug;E(A.cfg)
			if A.client:
				A.client.api.debug=A.debug
				if A.debug:A.client.api._setup_logger()
			console.print(f"Debug: {"[warning]on[/]"if A.debug else _N}");return _A
		console.print(f"[warning]Command not available to the model: {escape(B)}[/]");return _A
	def action_use(A,ident):
		try:B=A._session_index[int(ident)-1]
		except(ValueError,IndexError):console.print(_T);return
		A._apply_session(B);console.print(f"[success]✓[/] Resumed [accent]{B[:12]}…[/] ({len(A.messages)} local messages)")
	def action_rename(A,title):
		B=title
		if not B or not A.session_id:console.print('[warning]Rename needs an active session and a title.[/]');return
		A.session_title=B
		try:
			if A.client:A.client.rename_session(A.session_id,B)
		except DeepSeekError as C:console.print(f"[warning]Remote rename failed ({C}); saved locally.[/]")
		A._save_transcript();console.print(f"[success]✓[/] Renamed to [accent]{B}[/]")
	def action_delete(A,ident):
		C=ident;from rich.prompt import Confirm as E;from.config import transcript_path as F
		if C:
			try:B=A._session_index[int(C)-1]
			except(ValueError,IndexError):console.print(_T);return
		else:B=A.session_id or''
		if not B:console.print('[error]No session selected.[/]');return
		if not E.ask(f"Delete session [accent]{B[:12]}…[/]?",default=_K):return
		try:
			if A.client:A.client.delete_session(B)
		except DeepSeekError as G:console.print(f"[warning]Remote delete failed: {G}[/]")
		D=F(B)
		if D.exists():D.unlink()
		if B==A.session_id:A.session_id=_B;A.messages.clear();A.parent_message_id=_B;A._session_index=[]
		console.print('[success]✓[/] Deleted')
	def cmd_paste(C):
		A=''
		try:import win32clipboard as B;B.OpenClipboard();A=B.GetClipboardData();B.CloseClipboard()
		except Exception:
			try:import pyperclip as D;A=D.paste()
			except Exception:pass
		if A:C._next_prompt_default=A;console.print('[success]✓[/] Clipboard loaded — it will pre-fill your next prompt.')
		else:console.print('[warning]Could not read clipboard. Please paste manually.[/]')
	def cmd_copy(D):
		B=next((A for A in reversed(D.messages)if A[_C]==_F),_B)
		if not B:console.print('[dim]No assistant message to copy.[/]');return
		C=B.get(_D,'')
		try:import pyperclip as E;E.copy(C);console.print('[success]✓[/] Copied to clipboard (pyperclip).')
		except Exception:
			try:import win32clipboard as A;A.OpenClipboard();A.EmptyClipboard();A.SetClipboardText(C);A.CloseClipboard();console.print('[success]✓[/] Copied to clipboard (win32).')
			except Exception:console.print('[error]Failed to copy to clipboard.[/]')
	def cmd_retry(A):
		B=next((A for A in reversed(A.messages)if A[_C]==_E),_B)
		if not B:console.print('[dim]No user message to retry.[/]');return
		console.print(f"[info]Retrying:[/] {B[_D][:60]}...");D=len(A.messages)-1-A.messages[::-1].index(B);A.messages=A.messages[:D]
		if A.messages:
			C=next((A for A in reversed(A.messages)if A[_C]==_F),_B)
			if C:A.parent_message_id=C.get(_H)or C.get(_I)
			else:A.parent_message_id=_B
		else:A.parent_message_id=_B
		A.stream_response(B[_D])
	def cmd_edit(A,msg_number,new_text):
		C=new_text;B=msg_number-1
		if B<0 or B>=len(A.messages):console.print('[error]Message number out of range.[/]');return
		D=A.messages[B]
		if D[_C]!=_E:console.print('[warning]Can only edit user messages.[/]');return
		if not C:console.print('[warning]Empty text.[/]');return
		F=D.get(_I)or D.get(_H)
		if not F or not A.client:console.print('[error]Message ID not found for this message.[/]');return
		try:A.client.api.edit_message(A.session_id,F,C,A.thinking_enabled,A.search_enabled)
		except Exception as G:console.print(f"[error]Edit failed: {G}[/]");return
		A.messages=A.messages[:B]
		if A.messages:
			E=next((A for A in reversed(A.messages)if A[_C]==_F),_B)
			if E:A.parent_message_id=E.get(_H)or E.get(_I)
			else:A.parent_message_id=_B
		else:A.parent_message_id=_B
		A.stream_response(C)
	def cmd_undo(A):
		B=-1
		for D in range(len(A.messages)-1,-1,-1):
			if A.messages[D][_C]==_E:B=D;break
		if B==-1:console.print('[dim]Nothing to undo.[/]');return
		A.messages=A.messages[:B]
		if A.messages:
			C=next((A for A in reversed(A.messages)if A[_C]==_F),_B)
			if C:A.parent_message_id=C.get(_H)or C.get(_I)
			else:A.parent_message_id=_B
		else:A.parent_message_id=_B
		A._save_transcript();console.print('[success]✓[/] Undo successful.')
	def cmd_history(B):
		if not B.messages:console.print('[dim]No messages in this session yet.[/]');return
		for(C,A)in enumerate(B.messages,1):
			if A[_C]==_O:console.print(f"[mcp]{C}. Tool[/]: {A.get(_O)} → {str(A.get(_U,""))[:100]}");continue
			D,E=('You',_E)if A[_C]==_E else('Abyssal',_S);F=A[_D][:140].replace('\n',' ');console.print(f"[{E}]{C}. {D}[/]: {F}{"…"if len(A[_D])>140 else""}")
	def cmd_export(A,name=_B):
		C=name
		if not A.messages:console.print('[dim]Nothing to export yet.[/]');return
		C=C or datetime.now().strftime('abyssal_%Y%m%d_%H%M%S');D=Path.cwd()/f"{C}.md";E=[f"# Abyssal conversation — {A.session_title or A.session_id or"untitled"}",'',f"_Exported {datetime.now().isoformat()}_",'']
		for B in A.messages:F={_E:'**You**',_F:'**Abyssal**',_O:'**Tool**'}.get(B[_C],B[_C]);E.append(f"## {F}\n{B.get(_D,B.get(_U,""))}\n")
		D.write_text('\n'.join(E),encoding='utf-8');console.print(f"[success]✓[/] Exported → [accent]{D}[/]")
	def status_detail(A):A.print_status();B=load_tasks();C=sum(1 for A in B if A.get('status')=='pending');D=', '.join(f"{A}={_G if B else"off"}"for(A,B)in A.agent_settings.items());console.print(f"""  [dim]token[/]: {mask(load_token()or"")}  [dim](source: {token_source()})[/]
  [dim]autonomy mode[/]: {A.autonomy_mode}
  [dim]messages this session[/]: {len(A.messages)}
  [dim]next MCP reference re-injection[/]: at message {A._next_tools_reminder_at}
  [dim]scheduled tasks[/]: {len(B)} total ({C} pending)
  [dim]session notes[/]: {len(A.session_notes)}
  [dim]pending uploaded files[/]: {len(A.pending_file_ids)}
  [dim]agent settings[/]: {D}
  [dim]config[/]: {CONFIG_FILE}""")