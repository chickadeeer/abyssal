from __future__ import annotations
_N='next_run'
_M='#0d9488'
_L='failed'
_K='chain_task_id'
_J='paused'
_I='pending'
_H='done'
_G='pause'
_F='run'
_E='remove'
_D='result'
_C='dim'
_B='status'
_A='id'
import threading
from datetime import datetime,timedelta
from typing import List,Optional
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm,Prompt
from rich.table import Table
from rich.text import Text
from.config import MODELS,TASK_INTERVAL_CHOICES
from.cowork import _ask_datetime,_ask_time,_fmt_dt,_schedule_label,find_task,load_tasks,new_task,save_tasks
from.ui import console
class TaskCommandsMixin:
	def cmd_task(B,parts):
		F='list';C=parts;A=C[1].lower()if len(C)>1 else F
		if A=='add':B._task_add()
		elif A==F:B._task_list()
		elif A in(_E,'rm','delete'):B._task_action(C,_E)
		elif A==_F:B._task_action(C,_F)
		elif A==_G:B._task_action(C,_G)
		elif A==_D:B._task_action(C,_D)
		elif A=='clear':D=load_tasks();E=[A for A in D if A.get(_B)not in(_H,_L)];G=len(D)-len(E);save_tasks(E);console.print(f"[success]✓[/] Cleared {G} finished task(s)")
		else:console.print('[warning]Usage: /task [add|list|remove <id>|run <id>|pause <id>|result <id>|clear][/]')
	def _task_add(A):
		a='[error]Invalid date — cancelled.[/]';Z='interval';Q='once';P='weekly';O='daily';N='name';M='custom';G=None;console.print(Panel(Text('Answer the prompts to schedule a new task. Ctrl+C aborts.',style=_C),title='[accent]New Cowork task[/]',border_style=_M))
		try:
			R=Prompt.ask('[accent]Prompt to run[/]').strip()
			if not R:console.print('[warning]Empty prompt — nothing scheduled.[/]');return
			K=Prompt.ask('[accent]Model[/]',choices=[*MODELS.keys(),M],default=A.model if A.model in MODELS else M)
			if K==M:K=Prompt.ask('Custom model_type',default=A.model)
			b=Confirm.ask('Thinking mode?',default=A.thinking_enabled);c=Confirm.ask('Web search?',default=A.search_enabled);S=Confirm.ask('Flag task as MCP-enabled?',default=bool(A.mcp.tools));L=[]
			if S and A.mcp.tools:
				console.print('[accent]Available MCP tools:[/]')
				for(d,H)in enumerate(A.mcp.tools,1):console.print(f"  {d}. [bold]{H[N]}[/] - {H["description"][:60]}")
				while True:
					try:D=Prompt.ask("Add tool (name or number), or type 'mcpdone' to finish").strip()
					except(KeyboardInterrupt,EOFError):break
					if D.lower()in('mcpdone',_H,''):break
					B=G
					if D.isdigit():
						T=int(D)-1
						if 0<=T<len(A.mcp.tools):B=A.mcp.tools[T][N]
					else:
						for H in A.mcp.tools:
							if H[N]==D:B=D;break
					if B:
						if B not in L:L.append(B);console.print(f"[success]✓ Added {B}[/]")
					else:console.print('[warning]Tool not found.[/]')
			e=Confirm.ask('Use the current chat system prompt for this task?',default=bool(A.system_prompt));I=Prompt.ask('[accent]Schedule[/]',choices=['30min','1hr','2hr','6hr','12hr',O,P,Q],default=Q);E=Z;F=60;C=G
			if I in TASK_INTERVAL_CHOICES:E,F=Z,TASK_INTERVAL_CHOICES[I]
			elif I==O:
				E,F=O,G;U=_ask_time('Time each day (HH:MM)','09:00')
				if not U:console.print('[error]Invalid time — cancelled.[/]');return
				C=datetime.combine(datetime.now().date(),U)
			elif I==P:
				E,F=P,G;C=_ask_datetime('First run (YYYY-MM-DD HH:MM)')
				if not C:console.print(a);return
			else:
				E,F=Q,G;C=_ask_datetime('Run at (YYYY-MM-DD HH:MM)',default=(datetime.now()+timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M'))
				if not C:console.print(a);return
			f=Prompt.ask('Output file (blank to skip)',default='').strip();V=Prompt.ask('Chain next task id when done (blank for none)',default='').strip()
		except(KeyboardInterrupt,EOFError):console.print('\n[dim]Task creation cancelled.[/]');return
		W=''
		if V:
			X=find_task(load_tasks(),V)
			if X:W=X[_A]
			else:console.print('[warning]Chain target not found — continuing without chain.[/]')
		J=new_task(prompt=R,model=K,thinking=b,search=c,mcp_enabled=S,schedule_type=E,interval_minutes=F,run_at=C,output_file=f,chain_task_id=W,system_prompt=A.system_prompt if e else'',selected_tools=L);Y=load_tasks();Y.append(J);save_tasks(Y);console.print(f"[success]✓[/] Task [accent]{J[_A][:8]}[/] scheduled — {_schedule_label(J)} · next run {_fmt_dt(J.get(_N))}")
	def _task_list(J):
		C=load_tasks()
		if not C:console.print('[dim]No scheduled tasks. Use [accent]/task add[/] to create one.[/]');return
		A=Table(title='Cowork Tasks',border_style='#115e59',header_style='bold #0d9488');A.add_column('ID',style='accent');A.add_column('Prompt');A.add_column('Model');A.add_column('Schedule');A.add_column('Next run',style=_C);A.add_column('Last run',style=_C);A.add_column('Status');F={_I:_C,'running':'yellow',_H:'success',_L:'error',_J:'warning'}
		for B in C:D=B.get(_B,_I);G=F.get(D,_C);E=B.get('prompt','');H=' ⛓'if B.get(_K)else'';I=' 📄'if B.get('output_file')else'';A.add_row(B.get(_A,'')[:8],E[:40]+('…'if len(E)>40 else'')+H+I,B.get('model','default'),_schedule_label(B),_fmt_dt(B.get(_N)),_fmt_dt(B.get('last_run')),f"[{G}]{D}[/]")
		console.print(A);console.print('[dim]/task run <id> now · /task pause <id> pause/resume · /task result <id> output · ⛓ chains · 📄 output file[/]')
	def _task_action(F,parts,action):
		E=parts;C=action
		if len(E)<3:console.print(f"[warning]Usage: /task {C} <id>[/]");return
		B=load_tasks();A=find_task(B,E[2])
		if not A:console.print(f"[error]Task '{E[2]}' not found (or id is ambiguous).[/]");return
		if C==_E:
			B=[B for B in B if B[_A]!=A[_A]]
			for G in B:
				if G.get(_K)==A[_A]:G[_K]=''
			save_tasks(B);console.print(f"[success]✓[/] Removed task [accent]{A[_A][:8]}[/]")
		elif C==_F:
			if not F.taskman:console.print('[error]Scheduler not running yet.[/]');return
			console.print(f"[info]Running task {A[_A][:8]} now…[/]");threading.Thread(target=F.taskman.execute_task,args=(A[_A],),daemon=True).start()
		elif C==_G:
			if A.get(_B)==_J:A[_B]=_I;save_tasks(B);console.print(f"[success]✓[/] Resumed [accent]{A[_A][:8]}[/]")
			else:A[_B]=_J;save_tasks(B);console.print(f"[success]✓[/] Paused [accent]{A[_A][:8]}[/] (skipped by scheduler)")
		elif C==_D:
			D=A.get(_D)
			if not D:console.print('[dim]No result recorded for this task yet.[/]');return
			try:H=Markdown(D)if len(D)<20000 else Text(D)
			except Exception:H=Text(D)
			console.print(Panel(H,title=f"[accent]Result — {A[_A][:8]}[/]",title_align='left',border_style=_M,padding=(0,1)))