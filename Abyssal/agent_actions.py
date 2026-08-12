from __future__ import annotations
_b='allow-mcp-proposals'
_a='command'
_Z='prompt'
_Y='content'
_X='/notes'
_W='/model'
_V='command-gate'
_U='#115e59'
_T='utf-8'
_S='confirm-proposals'
_R='dim italic'
_Q='(no reason given)'
_P='reason'
_O='dim'
_N='server'
_M='#0d9488'
_L='off'
_K='add'
_J='name'
_I='clear'
_H='left'
_G='list'
_F='no'
_E='yes'
_D='later'
_C='\n'
_B=True
_A=False
import asyncio,difflib,re,sys,uuid
from typing import Any,Dict,List,Tuple
from rich.console import Group
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm,Prompt
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text
from.agent import AGENT_SETTINGS_DEFAULTS,MODEL_BLOCKED_COMMANDS,MODEL_KNOWN_COMMANDS,SETTING_DESCRIPTIONS,model_command_is_routine,model_command_is_safe,strip_model_control_blocks
from.config import CONFIG_DIR,MODELS,PROMPTS_DIR,TOOL_RESULT_MAX_CHARS,save_config
from.cowork import _schedule_label,find_task,load_tasks
from.mcp import MCP_AVAILABLE
from.patching import apply_unified_patch
from.questions import ask_questions,normalize_questions
from.ui import console
class AgentMixin:
	def cmd_settings(F,parts):
		I='[dim]off[/]';H='[success]on[/]';A=parts[1:]
		if A and A[0].lower()=='set':A=A[1:]
		if not A:
			from rich.table import Table;B=Table(title='Agent Settings (session-scoped)',border_style=_U,header_style='bold #0d9488');B.add_column('Key',style='accent');B.add_column('Value');B.add_column('Meaning')
			for D in AGENT_SETTINGS_DEFAULTS:J=F.agent_settings.get(D,_A);B.add_row(D,H if J else I,SETTING_DESCRIPTIONS.get(D,''))
			console.print(B);console.print('[dim]Prefer the interactive menu: type /settings[/]');return
		if len(A)!=2:console.print('[warning]Usage: /settings [set] <key> <on|off>[/]');return
		C,G=A[0].lower(),A[1].lower()
		if C not in AGENT_SETTINGS_DEFAULTS:console.print(f"[error]Unknown setting '{C}'.[/] Run [accent]/settings[/] for the list.");return
		if G in('on','1','true',_E):E=_B
		elif G in(_L,'0','false',_F):E=_A
		else:console.print('[warning]Value must be on or off.[/]');return
		F.agent_settings[C]=E;console.print(f"[success]✓[/] [accent]{C}[/] = {H if E else I} (this session only)")
	def cmd_notes(A,parts,cmd):
		C=parts;B=C[1].lower()if len(C)>1 else _G
		if B==_K:
			D=cmd.partition(_K)[2].strip()
			if not D:console.print('[warning]Usage: /notes add <text>[/]');return
			A.session_notes.append(D);console.print(f"[success]✓[/] Note saved [dim]({len(A.session_notes)} this session)[/]")
		elif B==_I:E=len(A.session_notes);A.session_notes=[];console.print(f"[success]✓[/] Cleared {E} session note(s)")
		elif B in(_G,'show'):
			if not A.session_notes:console.print('[dim]No session notes.[/]');return
			for(F,G)in enumerate(A.session_notes,1):console.print(f"[dim]{F}.[/] {escape(G)}")
		else:console.print('[warning]Usage: /notes [list | add <text> | clear][/]')
	def cmd_mcp_help(A):console.print(Panel(Markdown(A._agent_protocol_block()),title='[accent]Agent protocol[/]',title_align=_H,border_style=_M,padding=(0,1)));console.print(Panel(Markdown(A.mcp.get_help_block()),title='[mcp]MCP tool reference[/]',title_align=_H,border_style='#14b8a6',padding=(0,1)))
	def _command_needs_confirm(A,parts):
		B=parts
		if not A.agent_settings.get(_V):return _A
		if model_command_is_safe(B):return _A
		if A.agent_settings.get('routine-auto')and model_command_is_routine(B):return _A
		return _B
	def _execute_model_command(B,cmd_line):
		C=cmd_line;C=C.strip();D=C.split();A=D[0].lower()if D else''
		if not A.startswith('/'):return _A,f'Only slash commands are allowed (got "{A}").'
		if A in MODEL_BLOCKED_COMMANDS:return _A,f"{A} cannot be run by the model. The model can never message itself, inject user input, or change its own settings."
		if A==_W and len(D)>1:return _A,'Model switching mid-conversation is not allowed. The user must start a new session (/new) — all current context will be lost.'
		if A==_X:
			if not B.agent_settings.get('allow-model-notes'):return _A,'Session notes are disabled. The user can enable them with /settings → Autonomy & Agent.'
			if len(D)>=2 and D[1].lower()not in(_K,_G,'show',_I):return _A,'Unknown /notes subcommand. Use: /notes [list | add <text> | clear].'
		if B._command_needs_confirm(D):
			try:E=Confirm.ask(f"[mcp]Model wants to run[/] [accent]{escape(C)}[/] — allow?",default=_A)
			except(KeyboardInterrupt,EOFError):E=_A
			if not E:return _A,f"The user declined to run: {C}"
		if A not in MODEL_KNOWN_COMMANDS:return _A,f"Unknown command '{A}'. Only existing slash commands are allowed."
		try:F=B.handle_command(C,from_model=_B)
		except Exception as G:return _A,f"Command {A} failed: {G}"
		if not F:B._exit_requested=_B;return _B,'The session is ending (/exit was approved).'
		if not B.session_id and A in('/del','/new','/use'):B.new_session(quiet=_B)
		return _B,B._describe_command_result(C,D)
	def _describe_command_result(B,cmd_line,parts):
		O='status';N='(none)';I='result';E=parts;A=E[0].lower();C=E[1].lower()if len(E)>1 else''
		if A=='/status':return B.status_line().plain
		if A==_W:return f"Current model: {B.model}. Available: "+'; '.join(f"{A} ({B})"for(A,B)in MODELS.items())
		if A=='/thinking':return f"thinking={"on"if B.thinking_enabled else _L}"
		if A in('/search','/websearch','/web'):return f"web_search={"on"if B.search_enabled else _L}"
		if A=='/system':
			if C=='set':return'System prompt updated (applies to new conversations).'
			if C==_I:return'System prompt cleared.'
			return f"Current system prompt: {B.system_prompt or N}"
		if A==_X:
			if C==_K:return f"Note saved ({len(B.session_notes)} total this session)."
			if C==_I:return'Session notes cleared.'
			if not B.session_notes:return'No session notes.'
			return'Session notes:\n'+_C.join(f"- {A}"for A in B.session_notes)
		if A=='/history':
			if not B.messages:return'No messages in this session yet.'
			J=[]
			for(P,F)in enumerate(B.messages[-40:],1):Q=F.get('role');R=strip_model_control_blocks(str(F.get(_Y)or F.get(I)or''))[:300];J.append(f"{P}. [{Q}] {R}")
			return _C.join(J)
		if A=='/sessions':
			if not B._session_index:return'No sessions listed.'
			return'Sessions (most recent first):\n'+_C.join(f"- {A}"for A in B._session_index[:20])
		if A=='/task':
			if C==I and len(E)>=3:D=find_task(load_tasks(),E[2]);return str(D.get(I)or'(no result recorded)')if D else'Task not found.'
			if C in(_G,''):
				K=load_tasks()
				if not K:return'No scheduled tasks.'
				return'Scheduled tasks:\n'+_C.join(f"- {A.get("id","")[:8]} [{A.get(O,"pending")}] {_schedule_label(A)} :: {str(A.get(_Z,""))[:80]}"for A in K)
			return f"/task {C} executed."
		if A=='/mcp':
			if C in(O,_G,'tools',''):
				G=B.mcp.list_servers()
				if not G and not B.mcp.tools:return'No MCP servers configured; no tools loaded.'
				H=[f"MCP servers: {len(G)}; tools loaded: {len(B.mcp.tools)}"]
				for(S,L)in G.items():H.append(f"- server {S}: {L.get(_a)} {" ".join(L.get("args")or[])}")
				for D in B.mcp.tools:H.append(f"- tool {D[_J]} ({D[_N]}): {D["description"][:100]}")
				return _C.join(H)
			return f"/mcp {C} executed."
		if A=='/prompt':
			if C==_G:M=[A.stem for A in sorted(PROMPTS_DIR.glob('*.txt'))];return'Saved prompts: '+(', '.join(M)if M else N)
			return f"/prompt {C} executed."
		if A=='/files':
			if C==_I:return'Pending file attachments cleared.'
			if not B.pending_file_ids:return'No pending file attachments.'
			return'Pending file attachments:\n'+_C.join(f"- {A}"for A in B.pending_file_ids)
		if A=='/upload':return'Upload command executed.'
		if A=='/new':return'New session started. Previous context is gone.'
		if A=='/save':return'Conversation exported to markdown in the working directory.'
		if A in('/help','/h','/?'):return'Help shown to the user. User commands: /settings, /thinking, /search, /exit.'
		if A in('/del','/use','/rename','/undo','/copy','/debug','/token','/clear','/version'):return f"{A} executed successfully."
		return f"{A} executed."
	@staticmethod
	def _command_result_prompt(results):
		A=[]
		for(D,E,B)in results:
			C=B[:TOOL_RESULT_MAX_CHARS]
			if len(B)>TOOL_RESULT_MAX_CHARS:C+='\n…(output truncated)'
			A.append(f'[COMMAND_RESULT command="{D}" status="{"ok"if E else"blocked"}"]\n{C}\n[/COMMAND_RESULT]')
		return _C.join(A)+'\nThese slash commands were executed for you. Continue the task. Remember: you can never message yourself and you cannot switch models mid-conversation.'
	@staticmethod
	def _render_diff_panel(old_code,new_code,title):
		C=old_code.splitlines(keepends=_B);D=new_code.splitlines(keepends=_B);E=difflib.unified_diff(C,D,fromfile='before',tofile='after',lineterm='');B=Text()
		for A in E:
			if A.startswith('+++')or A.startswith('---'):B.append(A.rstrip()+_C,style='bold dim')
			elif A.startswith('@@'):B.append(A.rstrip()+_C,style='cyan')
			elif A.startswith('+'):B.append(A.rstrip()+_C,style='bold green')
			elif A.startswith('-'):B.append(A.rstrip()+_C,style='bold red')
			else:B.append(A.rstrip()+_C,style=_O)
		return Panel(B,title=title,title_align=_H,border_style=_M,padding=(0,1))
	def _handle_questions(A,data):
		if not A.agent_settings.get('allow-model-questions'):return _A,'Structured questions are disabled. The user can enable them in /settings → Autonomy & Agent (allow-model-questions).'
		try:B=normalize_questions(data)
		except ValueError as C:return _A,f"Your [QUESTIONS] block was invalid: {C}. Send a single JSON object with a 'questions' list; each item needs 'text' and may have 'choices', 'allow_text', 'blocking' and 'default'."
		return _B,ask_questions(B)
	def _handle_mcp_proposal(B,prop):
		D=prop;A=str(D.get(_J)or'').strip()or f"plugin_{uuid.uuid4().hex[:6]}";M=re.sub('[^A-Za-z0-9_.-]','_',A)[:48]or'plugin';N=str(D.get(_P)or _Q).strip();F=str(D.get('code')or'');E=str(D.get(_a)or'').strip();C=D.get('args')or[]
		if not isinstance(C,list):C=[str(C)]
		if A in B._mcp_rejected_plugins:return _A,f"MCP plugin '{A}' was already declined by the user this session. Do not propose it again unless the user asks for it."
		if not B.agent_settings.get(_b):return _A,'MCP plugin proposals are disabled (/settings → Autonomy & Agent → allow-mcp-proposals).'
		if not MCP_AVAILABLE:return _A,'MCP SDK is not installed in this environment (pip install mcp), so the proposal cannot be loaded.'
		H=[Text(N,style=_R)]
		if F:H.append(Syntax(F,'python',line_numbers=_B,word_wrap=_B))
		elif E:H.append(Text(f"command: {E} {" ".join(str(A)for A in C)}",style=_O))
		O=B.agent_settings.get(_S,_B)
		if O:
			console.print(Panel(Group(*H),title=f"[mcp]Proposed NEW MCP plugin: {escape(A)}[/]",title_align=_H,border_style=_M,padding=(0,1)))
			try:G=Prompt.ask('Approve this NEW MCP plugin?',choices=[_E,_F,_D])
			except(KeyboardInterrupt,EOFError):G=_D
		else:G=_E;console.print(f"[mcp]Autonomous mode — auto-approving NEW plugin [accent]{escape(A)}[/]")
		if G==_D:return _A,f"The user deferred MCP plugin '{A}'. You may propose it again later in this session."
		if G==_F:B._mcp_rejected_plugins.add(A);return _A,f"The user declined MCP plugin '{A}'. Do not propose it again this session."
		if F:
			J=CONFIG_DIR/'plugins';J.mkdir(exist_ok=_B);K=J/f"{M}.py"
			try:K.write_text(F,encoding=_T)
			except OSError as I:return _A,f"Could not write plugin file: {I}"
			E,C=sys.executable,[str(K)]
		if not E:return _A,"The proposal needs either a 'code' field or a 'command' field."
		B.mcp.add_server(A,E,[str(A)for A in C])
		try:
			with console.status('[mcp]Loading proposed MCP plugin…[/]',spinner='dots'):asyncio.run(B.mcp.refresh_tools())
		except Exception as I:B.mcp.remove_server(A);return _A,f"MCP plugin '{A}' failed to load and was removed: {I}"
		B._next_tools_reminder_at=min(B._next_tools_reminder_at,len(B.messages)+1);L=[B[_J]for B in B.mcp.tools if B[_N]==A]
		if L:return _B,f"MCP plugin '{A}' approved and loaded. Tools: {", ".join(L)}."
		return _B,f"MCP plugin '{A}' approved and registered, but it exposed no tools (check the server output)."
	def _handle_mcp_edit_proposal(B,prop):
		L='patch';D=prop;A=str(D.get(_J)or'').strip();M=str(D.get(_P)or _Q).strip();E=str(D.get('code')or'');H=str(D.get(L)or'')
		if not A:return _A,"MCP_EDIT_PROPOSAL requires a 'name' field identifying the plugin to edit."
		if not E and not H:return _A,"MCP_EDIT_PROPOSAL requires either a 'patch' field (preferred: a unified diff against the current source, obtained via mcp_read_plugin) or a 'code' field with the complete updated source."
		if not B.agent_settings.get(_b):return _A,'MCP plugin proposals (including edits) are disabled (/settings → Autonomy & Agent → allow-mcp-proposals).'
		if A in B._mcp_rejected_plugins:return _A,f"MCP plugin '{A}' was already declined by the user this session. Do not propose edits to it unless the user asks."
		F=B.mcp.get_plugin_path(A)
		if F is None:return _A,f"Cannot edit '{A}': it is not a Python-based plugin managed by this CLI, or the source file could not be located."
		try:I=F.read_text(encoding=_T)
		except OSError as C:return _A,f"Could not read current plugin source for '{A}': {C}"
		if H:
			N,O,P=apply_unified_patch(I,H)
			if not N:return _A,P
			E=O;J=L
		else:J='full rewrite'
		Q=B._render_diff_panel(I,E,title=f"[mcp]Proposed EDIT ({J}): {escape(A)} ({F.name})[/]");R=B.agent_settings.get(_S,_B)
		if R:
			console.print(Q);console.print(Text(f"Reason: {M}",style=_R))
			try:G=Prompt.ask('Apply this edit to the MCP plugin?',choices=[_E,_F,_D])
			except(KeyboardInterrupt,EOFError):G=_D
		else:G=_E;console.print(f"[mcp]Autonomous mode — auto-applying edit to [accent]{escape(A)}[/]")
		if G==_D:return _A,f"The user deferred the edit to '{A}'. You may propose it again later in this session."
		if G==_F:B._mcp_rejected_plugins.add(A);return _A,f"The user declined the edit to '{A}'. Do not propose edits to it again this session."
		try:F.write_text(E,encoding=_T)
		except OSError as C:return _A,f"Could not write updated plugin source for '{A}': {C}"
		try:
			with console.status(f"[mcp]Reloading edited plugin '{A}'…[/]",spinner='dots'):asyncio.run(B.mcp.refresh_tools())
		except Exception as C:return _A,f"Plugin '{A}' was updated on disk but failed to reload: {C}. The file has been written; you may need to fix and re-propose."
		B._next_tools_reminder_at=min(B._next_tools_reminder_at,len(B.messages)+1);K=[B[_J]for B in B.mcp.tools if B[_N]==A]
		if K:return _B,f"Edit to '{A}' applied and reloaded. Tools: {", ".join(K)}."
		return _B,f"Edit to '{A}' applied and reloaded, but it currently exposes no tools."
	def _handle_system_proposal(A,prop):
		D=str(prop.get(_P)or _Q).strip();B=str(prop.get(_Z)or'').strip()
		if not B:return _A,"SYSTEM_PROPOSAL needs a non-empty 'prompt' field."
		if not A.agent_settings.get('allow-system-proposals'):return _A,'System-prompt proposals are disabled (/settings → Autonomy & Agent → allow-system-proposals).'
		E=A.agent_settings.get(_S,_B)
		if E:
			F=Group(Text(f"Reason: {D}",style=_R),Rule(style=_O),Text(B));console.print(Panel(F,title='[system]Proposed system prompt[/]',title_align=_H,border_style=_U,padding=(0,1)))
			try:C=Prompt.ask('Apply this system prompt?',choices=[_E,_F,_D])
			except(KeyboardInterrupt,EOFError):C=_D
		else:C=_E;console.print('[system]Autonomous mode — auto-applying system prompt change[/]')
		if C==_D:return _A,'The user deferred the system-prompt change. You may ask again later.'
		if C==_F:return _A,'The user declined the system-prompt change.'
		A.system_prompt=B;A.active_prompt_name='';A.cfg.update({'system_prompt':B,'active_prompt_name':''});save_config(A.cfg);return _B,'System prompt updated (it applies automatically to new conversations). Note: the model can never switch models mid-conversation.'
	def _handle_new_session_request(A,reason):
		if not A.agent_settings.get('allow-model-new'):return _A,'New-session requests are disabled (/settings → Autonomy & Agent → allow-model-new).'
		if A.agent_settings.get(_V):
			try:B=Confirm.ask(f"[mcp]Model requests a NEW session[/] [dim]({reason or"no reason given"}). Current context will be lost.[/] Allow?",default=_A)
			except(KeyboardInterrupt,EOFError):B=_A
			if not B:return _A,'The user declined to start a new session. Continue in this one.'
		if not A.new_session():return _A,'Failed to create a new session.'
		return _B,'New session created. All previous context is gone; the agent protocol has been re-stated.'
	def _handle_needs_input(E,question,prior_feedback):
		D=prior_feedback;C=question;console.print(Panel(Text((C or'The model needs your input.').strip(),style='warning'),title='[warning]Model paused — human input needed[/]',title_align=_H,border_style='yellow',padding=(0,1)))
		try:A=Prompt.ask('[accent]Your answer[/]').strip()
		except(KeyboardInterrupt,EOFError):A=''
		E.messages.append({'role':'user',_Y:A or'(no answer given)','message_id':None});B=[]
		if D:B.append(D)
		B.append(f'[HUMAN_RESPONSE to="{(C or"")[:120]}"]\n{A or"(The user gave no answer.)"}\n[/HUMAN_RESPONSE]');return _C.join(B)