from __future__ import annotations
_J='content'
_I='skill.json'
_H='history'
_G='updated_at'
_F='description'
_E=None
_D='utf-8'
_C='version'
_B=False
_A=True
import difflib,json,re,shutil
from datetime import datetime
from pathlib import Path
from typing import Any,Dict,List,Optional,Tuple
from.config import SKILLS_DIR
def _safe_name(name):return re.sub('[^A-Za-z0-9_.-]','_',(name or'').strip())[:48]
def _skill_dir(name):return SKILLS_DIR/_safe_name(name)
def _load_meta(d):
	A=d/_I
	if not A.exists():return
	try:return json.loads(A.read_text(encoding=_D))
	except Exception:return
def _save_meta(d,meta):d.mkdir(parents=_A,exist_ok=_A);(d/_I).write_text(json.dumps(meta,indent=2,ensure_ascii=_B),encoding=_D)
def _read_version(d,version):
	A=d/f"v{version}.md"
	if not A.exists():return'',_B
	try:return A.read_text(encoding=_D),_A
	except OSError:return'',_B
def list_skills():
	A=[]
	if not SKILLS_DIR.exists():return A
	for B in sorted(SKILLS_DIR.iterdir()):
		if not B.is_dir():continue
		C=_load_meta(B)
		if C:A.append(C)
	return A
def get_skill(name):
	B=_skill_dir(name);A=_load_meta(B)
	if not A:return
	C,D=_read_version(B,int(A.get(_C)or 1));A=dict(A);A[_J]=C;return A
def read_skill(name):
	A=get_skill(name)
	if not A:return _E,''
	return A,A.get(_J,'')
def write_skill(name,content,description=_E,note=''):
	G='versions';F=description;B=name;B=(B or'').strip();C=_skill_dir(B);C.mkdir(parents=_A,exist_ok=_A);A=_load_meta(C);D=datetime.now().isoformat()
	if A is _E:A={'name':B,_F:(F or'').strip(),_C:0,G:0,'created_at':D,_G:D,_H:[]}
	E=int(A.get(G)or 0)+1;(C/f"v{E}.md").write_text(content,encoding=_D)
	if F is not _E:A[_F]=F.strip()
	A[G]=E;A[_C]=E;A[_G]=D;A.setdefault(_H,[]).append({_C:E,'note':note or'updated','at':D});_save_meta(C,A);return A
def rollback_skill(name,version):
	C=name;A=version;D=_skill_dir(C);B=_load_meta(D)
	if not B:return _B,f"Skill '{C}' not found."
	G,F=_read_version(D,A)
	if not F:return _B,f"Skill '{C}' has no version v{A}."
	E=datetime.now().isoformat();B[_C]=A;B[_G]=E;B.setdefault(_H,[]).append({_C:A,'note':f"rollback to v{A}",'at':E});_save_meta(D,B);return _A,f"Skill '{C}' rolled back to v{A}."
def diff_skills(name,va,vb):
	A=name;B=_skill_dir(A);C=_load_meta(B)
	if not C:return _B,f"Skill '{A}' not found."
	D,E=_read_version(B,va);F,G=_read_version(B,vb)
	if not E:return _B,f"Skill '{A}' has no version v{va}."
	if not G:return _B,f"Skill '{A}' has no version v{vb}."
	H=difflib.unified_diff(D.splitlines(),F.splitlines(),fromfile=f"{A} v{va}",tofile=f"{A} v{vb}",lineterm='');return _A,'\n'.join(H)or'(versions are identical)'
def delete_skill(name):
	A=_skill_dir(name)
	if not A.exists():return _B
	shutil.rmtree(A,ignore_errors=_A);return _A
def skills_summary_block():
	B=list_skills()
	if not B:return''
	C=['# SKILLS LIBRARY','Reusable context written from past tasks. Read the relevant skill BEFORE starting a matching task (skill_read). When you learn something reusable, write it down with skill_write.']
	for A in B:C.append(f"- {A["name"]} (v{A.get(_C,1)}): {str(A.get(_F,""))[:120]}")
	return'\n'.join(C)