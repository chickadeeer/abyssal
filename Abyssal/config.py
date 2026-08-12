from __future__ import annotations
_S='human-needed'
_R='default'
_Q='file'
_P='preset'
_O='enabled'
_N='confirm-proposals'
_M='confirm-tools'
_L='routine-auto'
_K='command-gate'
_J='model-commands'
_I='.env'
_H='toggles'
_G='desc'
_F='label'
_E='DEEPSEEK_TOKEN'
_D='ABYSSAL_TOKEN'
_C='utf-8'
_B=False
_A=True
import json,os
from pathlib import Path
from typing import Any,Dict,Optional
APP_NAME='Abyssal'
APP_VERSION='2.2.0'
CONFIG_DIR=Path.home()/'.abyssal-cli'
CONFIG_FILE=CONFIG_DIR/'config.json'
ENV_FILE=CONFIG_DIR/_I
HISTORY_FILE=CONFIG_DIR/'history'
CONV_DIR=CONFIG_DIR/'conversations'
PROMPTS_DIR=CONFIG_DIR/'prompts'
SKILLS_DIR=CONFIG_DIR/'skills'
MCP_CONFIG_FILE=CONFIG_DIR/'mcp.json'
TASKS_FILE=CONFIG_DIR/'tasks.json'
GLOBAL_INSTRUCTIONS_FILE=CONFIG_DIR/'global_instructions.txt'
OLD_CONFIG_DIR=Path.home()/'.deepseek-cli'
OLD_ENV_FILE=OLD_CONFIG_DIR/_I
MODELS={_R:'DeepSeek-V4 Flash — fast general chat','expert':'DeepSeek-V4 Pro — deep reasoning but no search','vision':'DeepSeek-VL2 — multimodal / image input / no search'}
DEFAULT_SOUNDS={'master':_A,'notify':{_O:_A,_P:'abyss-chime',_Q:''},'response':{_O:_A,_P:'blip',_Q:''},'blank':{_O:_A,_P:'deep-ping',_Q:''}}
DEFAULT_CONFIG={'thinking':_B,'search':_B,'debug':_B,'model':_R,'system_prompt':'','active_prompt_name':'','autonomy':_S,'agent_toggles':{},'sounds':DEFAULT_SOUNDS}
DEFAULT_MCP_CONFIG={'mcpServers':{}}
AUTONOMY_MODES={'human-driven':{_F:'Human Driven',_G:'Confirms every single action — tool calls, commands, and proposals.',_H:{_J:_A,_K:_A,_L:_B,_M:_A,_N:_A}},_S:{_F:'Human Needed',_G:'Runs tools freely, but checks in at key decision points (privileged commands and all proposals).',_H:{_J:_A,_K:_A,_L:_B,_M:_B,_N:_A}},'human-not-always-needed':{_F:'Human Not Always Needed',_G:'Acts autonomously on routine tasks; only asks about ambiguous or destructive actions.',_H:{_J:_A,_K:_A,_L:_A,_M:_B,_N:_A}},'autonomous':{_F:'Autonomous Decision Making',_G:'Runs independently and only surfaces critical blockers. Proposals are auto-approved.',_H:{_J:_A,_K:_B,_L:_A,_M:_B,_N:_B}},'custom':{_F:'Custom',_G:'You define the rules — tune every agent toggle yourself.',_H:{}}}
MCP_HELP_INTERVAL=30
MAX_TOOL_ITERATIONS=10000
TOOL_RESULT_MAX_CHARS=50000
RATE_RETRY_SECONDS=15
RATE_MAX_RETRIES=3
BLANK_RETRY_SECONDS=5
BLANK_MAX_RETRIES=3
TASK_INTERVAL_CHOICES={'30min':30,'1hr':60,'2hr':120,'6hr':360,'12hr':720}
COMMANDS=['/settings','/thinking','/search']
def ensure_dirs():CONFIG_DIR.mkdir(exist_ok=_A);CONV_DIR.mkdir(exist_ok=_A);PROMPTS_DIR.mkdir(exist_ok=_A);SKILLS_DIR.mkdir(exist_ok=_A)
def load_config():
	ensure_dirs()
	if CONFIG_FILE.exists():
		try:
			with open(CONFIG_FILE,'r',encoding=_C)as A:return{**DEFAULT_CONFIG,**json.load(A)}
		except Exception:pass
	return DEFAULT_CONFIG.copy()
def save_config(cfg):
	ensure_dirs()
	with open(CONFIG_FILE,'w',encoding=_C)as A:json.dump(cfg,A,indent=2)
def load_mcp_config():
	ensure_dirs()
	if MCP_CONFIG_FILE.exists():
		try:
			with open(MCP_CONFIG_FILE,'r',encoding=_C)as A:return json.load(A)
		except Exception:pass
	return DEFAULT_MCP_CONFIG.copy()
def save_mcp_config(cfg):
	ensure_dirs()
	with open(MCP_CONFIG_FILE,'w',encoding=_C)as A:json.dump(cfg,A,indent=2)
def _parse_env_file(path):
	B={}
	if not path.exists():return B
	try:
		for A in path.read_text(encoding=_C).splitlines():
			A=A.strip()
			if not A or A.startswith('#')or'='not in A:continue
			C,E,D=A.partition('=');B[C.strip()]=D.strip().strip('"').strip("'")
	except OSError:pass
	return B
def load_token():
	for B in(_D,_E):
		A=os.environ.get(B)
		if A:return A
	for C in(Path.cwd()/_I,ENV_FILE,OLD_ENV_FILE):
		D=_parse_env_file(C)
		for B in(_D,_E):
			A=D.get(B)
			if A:return A
def token_source():
	for A in(_D,_E):
		if os.environ.get(A):return f"environment:{A}"
	B=_parse_env_file(Path.cwd()/_I)
	for A in(_D,_E):
		if B.get(A):return f"./.env:{A}"
	C=_parse_env_file(ENV_FILE)
	for A in(_D,_E):
		if C.get(A):return f"{ENV_FILE}:{A}"
	D=_parse_env_file(OLD_ENV_FILE)
	for A in(_D,_E):
		if D.get(A):return f"{OLD_ENV_FILE}:{A}"
	return'none'
def save_token(token):
	B=token;ensure_dirs();A=[]
	if ENV_FILE.exists():A=[A for A in ENV_FILE.read_text(encoding=_C).splitlines()if not A.startswith('ABYSSAL_TOKEN=')and not A.startswith('DEEPSEEK_TOKEN=')]
	A.append(f"ABYSSAL_TOKEN={B}");ENV_FILE.write_text('\n'.join(A)+'\n',encoding=_C)
	try:ENV_FILE.chmod(384)
	except OSError:pass
	os.environ[_D]=B;return ENV_FILE
def mask(token):A=token;return A[:8]+'…'+A[-4:]if len(A)>16 else'****'
def transcript_path(session_id):return CONV_DIR/f"{session_id}.json"
def all_local_transcripts():
	A={}
	for B in CONV_DIR.glob('*.json'):
		try:
			C=json.loads(B.read_text(encoding=_C))
			if C:A[B.stem]=C
		except Exception:pass
	return A