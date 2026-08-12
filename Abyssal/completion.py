from __future__ import annotations
from typing import Any,Dict,List
from prompt_toolkit.completion import Completer,Completion
from.config import COMMANDS
ARG_OPTIONS={'/thinking':['on','off'],'/search':['on','off'],'/settings':['general','autonomy','skills','mcp','sessions','tasks','files','sounds','prompts','tools','about']}
class CommandCompleter(Completer):
	def __init__(A,app):A.app=app
	def get_completions(F,document,complete_event):
		A=document.text_before_cursor
		if not A.startswith('/'):return
		if' 'not in A:
			for B in COMMANDS:
				if B.startswith(A):yield Completion(B,start_position=-len(A))
			return
		E,G,C=A.partition(' ')
		for D in ARG_OPTIONS.get(E,[]):
			if D.startswith(C):yield Completion(D,start_position=-len(C))