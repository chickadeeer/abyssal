from __future__ import annotations
_I='preset'
_H='enabled'
_G='sonar-pulse'
_F='abyss-chime'
_E='master'
_D='file'
_C='deep-ping'
_B='blip'
_A=True
import os,subprocess,threading
from pathlib import Path
from typing import Any,Dict,List,Tuple
from.config import DEFAULT_SOUNDS,load_config
PRESETS={_F:'Abyss Chime — soft two-tone surface ping',_C:'Deep Ping — low single sonar pulse',_B:'Blip — short, bright UI tick',_G:'Sonar Pulse — descending three-tone sweep'}
_SEQUENCES={_F:[(880,140),(1318,240)],_C:[(440,280)],_B:[(1250,80)],_G:[(1568,110),(1046,110),(698,200)]}
def _sounds_cfg():
	D=load_config().get('sounds')or{};A={B:dict(A)if isinstance(A,dict)else A for(B,A)in DEFAULT_SOUNDS.items()}
	for(B,C)in D.items():
		if isinstance(C,dict)and isinstance(A.get(B),dict):A[B]={**A[B],**C}
		else:A[B]=C
	return A
def channel_settings(channel):A=_sounds_cfg();B={_H:_A,_I:_B,_D:''};C=A.get(channel)or{};return{_E:bool(A.get(_E,_A)),**B,**C}
def _play_file(path):
	C=False;A=Path(path).expanduser()
	if not A.exists():return C
	try:
		if os.name=='nt':import winsound as B;B.PlaySound(str(A),B.SND_FILENAME|B.SND_ASYNC);return _A
		for D in(('afplay',),('paplay',),('aplay',),('ffplay','-nodisp','-autoexit')):
			try:subprocess.Popen([*D,str(A)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);return _A
			except OSError:continue
	except Exception:pass
	return C
def _beep_sequence(seq):
	if os.name=='nt':
		try:
			import winsound as A
			for(B,C)in seq:A.Beep(B,C)
			return
		except Exception:pass
	try:print('\x07',flush=_A)
	except Exception:pass
def _worker(channel):
	try:
		A=channel_settings(channel)
		if not A.get(_E)or not A.get(_H):return
		B=A.get(_I)or _B
		if B=='custom':
			if A.get(_D)and _play_file(A[_D]):return
			B=_C
		_beep_sequence(_SEQUENCES.get(B,_SEQUENCES[_B]))
	except Exception:pass
def play_sound(channel):threading.Thread(target=_worker,args=(channel,),daemon=_A).start()