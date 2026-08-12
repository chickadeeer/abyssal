from __future__ import annotations
_E='allow_text'
_D='text'
_C='blocking'
_B='choices'
_A='default'
from typing import Any,Dict,List
from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from.ui import console
def normalize_questions(data):
	C=data.get('questions')
	if isinstance(C,dict):C=[C]
	if not isinstance(C,list):raise ValueError("payload needs a 'questions' list")
	D=[]
	for(E,A)in enumerate(C,1):
		if isinstance(A,str):A={_D:A}
		if not isinstance(A,dict):raise ValueError(f"question {E} must be an object")
		F=str(A.get(_D)or'').strip()
		if not F:raise ValueError(f"question {E} is missing its 'text'")
		B=A.get(_B)or[]
		if not isinstance(B,list):B=[B]
		B=[str(A).strip()for A in B if str(A).strip()];D.append({_D:F,_B:B,_E:bool(A.get(_E,not B)),_C:bool(A.get(_C,A.get('required',True))),_A:str(A.get(_A)or'').strip()})
	if not D:raise ValueError("'questions' list is empty")
	return D
def _ask_one(num,q,allow_skip):
	C=allow_skip;B=list(q[_B]);E='(type a custom answer)';F='(skip — use default)'
	if q[_E]:B.append(E)
	if C:B.append(F)
	while True:
		if B:console.print('  '+'   '.join(f"[dim]{A+1})[/] {escape(B)}"for(A,B)in enumerate(B)))
		G=q[_A]if C and q[_A]else None;A=Prompt.ask(f"[accent]Question {num}[/]",default=G).strip()
		if A and A.isdigit()and 1<=int(A)<=len(B):
			D=B[int(A)-1]
			if D==F:return''
			if D==E:return Prompt.ask(f"[accent]Question {num} — custom answer[/]").strip()
			return D
		if A in q[_B]:return A
		if A:
			if q[_E]or not q[_B]:return A
			console.print('[warning]Pick one of the choices, or a number.[/]');continue
		if C:return''
		console.print('[warning]This question is blocking — an answer is required.[/]')
def ask_questions(qs):
	C=qs;D=[]
	for(H,A)in enumerate(C,1):
		I='[warning]blocking[/]'if A[_C]else'[dim]optional[/]';D.append(f"[bold]Question {H}[/] ({I}) — {escape(A[_D])}")
		if A[_B]:D.append('   choices: '+' · '.join(escape(A)for A in A[_B]))
		if A[_A]:D.append(f"   [dim]default: {escape(A[_A])}[/]")
	console.print(Panel(Group(Text.from_markup('\n'.join(D))),title='[accent]DeepSeek asks…[/]',title_align='left',border_style='#0d9488',padding=(0,1)));J=sorted(range(len(C)),key=lambda i:0 if C[i][_C]else 1);F=['']*len(C)
	try:
		for B in J:
			A=C[B]
			if not A[_C]:console.print(f"[dim]Optional question {B+1} — Enter accepts the default / skips.[/]")
			F[B]=_ask_one(B+1,A,allow_skip=not A[_C])
	except(KeyboardInterrupt,EOFError):pass
	G=[]
	for(B,A)in enumerate(C,1):
		E=F[B-1]
		if not E:E=f"(skipped — using default: {A[_A]})"if A[_A]else'(skipped)'
		G.append(f"Question {B}: {E}")
	return'[QUESTION_ANSWERS]\n'+'\n'.join(G)+'\n[/QUESTION_ANSWERS]'