from __future__ import annotations
_g='status'
_f='result'
_e='/version'
_d='/status'
_c='/clear'
_b='/history'
_a='/upload'
_Z='/system'
_Y='/websearch'
_X='/search'
_W='/thinking'
_V='/model'
_U='/sessions'
_T='show-command-results'
_S='allow-model-questions'
_R='allow-model-notes'
_Q='allow-model-pause'
_P='allow-model-new'
_O='allow-system-proposals'
_N='allow-mcp-proposals'
_M='confirm-proposals'
_L='confirm-tools'
_K='routine-auto'
_J='command-gate'
_I='model-commands'
_H='/files'
_G='/prompt'
_F='/mcp'
_E='/task'
_D='/notes'
_C=False
_B='list'
_A=True
import json,re
from typing import Any,Dict,List
COMMAND_BLOCK_RE=re.compile('\\[COMMAND:\\s*([^\\]\\n]+)\\]\\s*(.*?)\\s*\\[/COMMAND\\]',re.DOTALL)
MCP_PROPOSAL_RE=re.compile('\\[MCP_PROPOSAL\\]\\s*(\\{.*?\\})\\s*\\[/MCP_PROPOSAL\\]',re.DOTALL)
MCP_EDIT_PROPOSAL_RE=re.compile('\\[MCP_EDIT_PROPOSAL\\]\\s*(\\{.*?\\})\\s*\\[/MCP_EDIT_PROPOSAL\\]',re.DOTALL)
SYSTEM_PROPOSAL_RE=re.compile('\\[SYSTEM_PROPOSAL\\]\\s*(\\{.*?\\})\\s*\\[/SYSTEM_PROPOSAL\\]',re.DOTALL)
NEW_SESSION_RE=re.compile('\\[NEW_SESSION\\]\\s*(.*?)\\s*\\[/NEW_SESSION\\]',re.DOTALL)
NEEDS_INPUT_RE=re.compile('\\[NEEDS_INPUT\\]\\s*(.*?)\\s*\\[/NEEDS_INPUT\\]',re.DOTALL)
QUESTIONS_RE=re.compile('\\[QUESTIONS\\]\\s*(\\{.*?\\})\\s*\\[/QUESTIONS\\]',re.DOTALL)
AGENT_SETTINGS_DEFAULTS={_I:_C,_J:_A,_K:_C,_L:_C,_M:_A,_N:_A,_O:_A,_P:_A,_Q:_A,_R:_A,_S:_A,_T:_C}
SETTING_DESCRIPTIONS={_I:'Model may run existing slash commands via [COMMAND] blocks',_J:'Privileged commands need explicit human yes/no confirmation',_K:'Routine, non-destructive commands skip the gate',_L:'Confirm every MCP tool call before it runs',_M:'MCP/system/skill writes need yes/no/later approval',_N:'Model may propose new MCP plugins or edit existing ones',_O:'Model may propose system-prompt changes',_P:'Model may request a new session (/new — context lost)',_Q:'Model may pause the loop and ask the user for input',_R:'Model may write session-scoped notes (/notes)',_S:'Model may ask structured multi-question forms',_T:'Show model-command results in the UI'}
MODEL_BLOCKED_COMMANDS={'/settings','/config','/retry','/edit','/paste'}
MODEL_KNOWN_COMMANDS={'/help','/h','/?','/new',_U,'/use','/rename','/del',_V,_W,_X,_Y,'/web',_Z,_D,_E,_F,_G,_H,_a,'/save',_b,_c,_d,_e,'/exit'}
MODEL_SAFE_COMMANDS={'/help','/h','/?',_d,_e,_c,_b,'/save',_U}
def model_command_is_safe(parts):
	A=parts
	if not A:return _C
	B=A[0].lower()
	if B in MODEL_SAFE_COMMANDS:return _A
	if B==_Z:return _A
	if B in(_W,_X,_Y,'/web'):return _A
	if B==_V:return len(A)==1
	if B==_D:return _A
	if B==_E and len(A)>=2 and A[1].lower()in(_B,_f):return _A
	if B==_F and len(A)>=2 and A[1].lower()in(_g,_B,'tools'):return _A
	if B==_G and len(A)>=2 and A[1].lower()==_B:return _A
	if B==_H and len(A)>=2 and A[1].lower()==_B:return _A
	return _C
def model_command_is_routine(parts):
	B=parts
	if model_command_is_safe(B):return _A
	if not B:return _C
	A=B[0].lower();C=B[1].lower()if len(B)>1 else''
	if A==_D and C in('add',_B,'show','clear',''):return _A
	if A==_E and C in(_B,_f):return _A
	if A==_F and C in(_g,_B,'tools'):return _A
	if A==_G and C==_B:return _A
	if A==_H and C in(_B,''):return _A
	if A==_a:return _A
	return _C
def parse_command_blocks(text):
	C=[]
	for D in COMMAND_BLOCK_RE.finditer(text or''):
		A=(D.group(1)or'').strip();E=(D.group(2)or'').strip()
		if not A:continue
		B=f"{A} {E}".strip()if E else A;B='\n'.join(' '.join(A.split())for A in B.splitlines());C.append(B)
	return C
def parse_json_blocks(regex,text):
	A=[]
	for C in regex.finditer(text or''):
		try:
			B=json.loads(C.group(1))
			if isinstance(B,dict):A.append(B)
		except json.JSONDecodeError:continue
	return A
def parse_plain_blocks(regex,text):return[(A.group(1)or'').strip()for A in regex.finditer(text or'')]
def strip_model_control_blocks(text):
	A=text or''
	for B in(COMMAND_BLOCK_RE,MCP_PROPOSAL_RE,MCP_EDIT_PROPOSAL_RE,SYSTEM_PROPOSAL_RE,NEW_SESSION_RE,NEEDS_INPUT_RE,QUESTIONS_RE):A=B.sub('',A)
	return A