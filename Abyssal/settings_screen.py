from __future__ import annotations
_A1='_session_rows'
_A0='description'
_z='Skills'
_y='#bae6fd'
_x='#020d17'
_w='#0c4a6e'
_v='(empty)'
_u='password'
_t='builder'
_s='sounds'
_r='action'
_q='utf-8'
_p='master'
_o='result'
_n='version'
_m='desc'
_l='autonomy_mode'
_k='#5eead4'
_j='#ffffff'
_i='#e0f2fe'
_h='#22d3ee'
_g='#67e8f9'
_f='#7dd3fc'
_e='hover'
_d='autonomy'
_c='blip'
_b='status'
_a='\n'
_Z='#0e7490'
_Y='cb'
_X='confirm'
_W='#010409'
_V='file'
_U='updated'
_T='input'
_S='enabled'
_R='name'
_Q='#155e75'
_P='custom'
_O='buf'
_N='preset'
_M='lines'
_L='label'
_K='detail'
_J='items'
_I='title'
_H='sel'
_G='id'
_F='off'
_E='menu'
_D='main'
_C=False
_B=True
_A=None
import asyncio,math,random,shlex,time
from datetime import datetime
from pathlib import Path
from typing import Any,Callable,Dict,List,Optional,Tuple
from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import UIControl,UIContent
from prompt_toolkit.mouse_events import MouseEvent,MouseEventType
from prompt_toolkit.output import ColorDepth
from.import __version__
from.config import CONFIG_FILE,MODELS,PROMPTS_DIR,all_local_transcripts,load_token,mask,save_config,save_token,token_source,transcript_path
from.cowork import _schedule_label,load_tasks,save_tasks
from.ui import console
try:from.config import AUTONOMY_MODES
except ImportError:AUTONOMY_MODES={}
try:from.sounds import PRESETS as SOUND_PRESETS,play_sound
except Exception:SOUND_PRESETS,play_sound={},_A
try:from.import skills as skills_mod
except Exception:skills_mod=_A
try:from.mcp import MCP_AVAILABLE
except Exception:MCP_AVAILABLE=_C
SCROLL_UP=getattr(MouseEventType,'SCROLL_UP',_A)
SCROLL_DOWN=getattr(MouseEventType,'SCROLL_DOWN',_A)
def _hx(h):h=h.lstrip('#');return int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
def _rgb(c):return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
def _mix(a,b,t):t=max(.0,min(1.,t));return int(a[0]+(b[0]-a[0])*t),int(a[1]+(b[1]-a[1])*t),int(a[2]+(b[2]-a[2])*t)
def _clamp(v,lo,hi):return max(lo,min(hi,v))
SKY_STOPS=[(.0,_hx(_W)),(.4,_hx('#03111f')),(.7,_hx('#062a44')),(1.,_hx('#094463'))]
ART=['  ▄▄▄▄   ▄▄                            ▄▄ ','▄██▀▀██▄ ██                            ██ ','███  ███ ████▄ ██ ██ ▄█▀▀▀ ▄█▀▀▀  ▀▀█▄ ██ ','███▀▀███ ██ ██ ██▄██ ▀███▄ ▀███▄ ▄█▀██ ██ ','███  ███ ████▀  ▀██▀ ▄▄▄█▀ ▄▄▄█▀ ▀█▄██ ██ ','                 ██                       ','               ▀▀▀']
def _sky_at(f):
	for C in range(len(SKY_STOPS)-1):
		A,D=SKY_STOPS[C];B,E=SKY_STOPS[C+1]
		if f<=B:F=(f-A)/(B-A)if B>A else .0;return _mix(D,E,F)
	return SKY_STOPS[-1][1]
class Canvas:
	def __init__(A,w,h):A.w=max(10,w);A.h=max(5,h);A.bg=[[_hx(_W)]*A.w for B in range(A.h)];A.ch=[[' ']*A.w for B in range(A.h)];A.fg=[[_A]*A.w for B in range(A.h)]
	def set_bg(A,x,y,c):
		if 0<=x<A.w and 0<=y<A.h:A.bg[y][x]=c
	def put(A,x,y,char,color,bold=_B):
		if 0<=x<A.w and 0<=y<A.h:A.ch[y][x]=char;A.fg[y][x]=color,bold
	def text(A,x,y,s,color,bold=_B):
		if not 0<=y<A.h:return
		for(C,D)in enumerate(s):
			B=x+C
			if 0<=B<A.w:A.ch[y][B]=D;A.fg[y][B]=color,bold
	def blend_rect(A,x0,y0,x1,y1,c,t):
		for B in range(max(0,y0),min(A.h,y1+1)):
			for C in range(max(0,x0),min(A.w,x1+1)):A.bg[B][C]=_mix(A.bg[B][C],c,t)
	def box(A,x0,y0,x1,y1,color,heavy=_C):
		B=color;C,D=('━','┃')if heavy else('─','│');A.put(x0,y0,'╭',B);A.put(x1,y0,'╮',B);A.put(x0,y1,'╰',B);A.put(x1,y1,'╯',B)
		for E in range(x0+1,x1):A.put(E,y0,C,B);A.put(E,y1,C,B)
		for F in range(y0+1,y1):A.put(x0,F,D,B);A.put(x1,F,D,B)
	def fragments(A):
		H=[]
		for C in range(A.h):
			F=[];D=_A;B=[]
			for E in range(A.w):
				I=A.fg[C][E];J=_rgb(A.bg[C][E])
				if I is _A:G=f"bg:{J}"
				else:K,L=I;G=f"{K}{" bold"if L else""} bg:{J}"
				if G!=D:
					if B:F.append((D or'',''.join(B)))
					D,B=G,[A.ch[C][E]]
				else:B.append(A.ch[C][E])
			if B:F.append((D or'',''.join(B)))
			H.append(F)
		return H
class Item:
	def __init__(A,label,kind=_r,value=_A):A.label=label;A.kind=kind;A.get_value=value;A.on_activate=_A;A.on_left=_A
	def value_text(A):
		try:return A.get_value()if A.get_value else''
		except Exception:return'?'
def _toggle(label,get,set_,msg=''):
	B=label;A=get;C=Item(B,'toggle',value=lambda:'ON'if A()else'OFF')
	def D(s):set_(not A());s.flash(msg or f"{B} → {"on"if A()else _F}");s.rebuild_top()
	C.on_activate=D;return C
def _cycle(label,options,get,set_):
	D=label;B=get;A=options;C=Item(D,'cycle',value=lambda:f"‹ {B()} ›")
	def E(s,direction):C=B();E=A.index(C)if C in A else 0;set_(A[(E+direction)%len(A)]);s.flash(f"{D} → {B()}");s.rebuild_top()
	C.on_activate=lambda s:E(s,1);C.on_left=lambda s:E(s,-1);return C
def _action(label,fn,value=_A):A=Item(label,_r,value=value);A.on_activate=fn;return A
def _input(label,fn,password=_C,initial=''):
	A=label;B=Item(A,_T)
	def C(s):s.begin_input(A,fn,password=password,initial=initial)
	B.on_activate=C;return B
def _label(label,value=''):A=value;return Item(label,_L,value=(lambda:A)if A else _A)
class SceneControl(UIControl):
	def __init__(A,screen):super().__init__();A.screen=screen
	def is_focusable(A):return _B
	def create_content(C,width,height):
		A=height;B=C.screen.render(width,A)
		def D(i):
			if 0<=i<len(B):return FormattedText(B[i])
			return FormattedText([])
		return UIContent(get_line=D,line_count=A,show_cursor=_C)
class SceneWindow(Window):
	def __init__(A,screen,**B):super().__init__(**B);A.screen=screen
	def is_focusable(A):return _B
	def mouse_handler(B,mouse_event):
		A=mouse_event
		try:B.screen.on_mouse(A.position.x,A.position.y,A.event_type)
		except Exception:pass
class SettingsScreen:
	REFRESH=.08
	def __init__(A,cli):A.cli=cli;A.scene=_D;A.sel=0;A.sections=A._main_sections();A.stack=[];A.input_state=_A;A.confirm_state=_A;A.detail_state=_A;A.flash_msg='';A.flash_until=.0;A._click=[];A._rects=[];A._grid_cols=3;A._t0=time.time();A._legacy=_A;A._quit_after=_C;A._pending_flash='';A.app=_A;B=random.Random(20250917);A._stars=[(B.random(),B.random()*.5,B.random()*6.28,.6+B.random()*2.2)for A in range(70)];A._clouds=[dict(y=.14,speed=4.2,scale=1.5,seed=.1),dict(y=.26,speed=2.6,scale=1.,seed=.55),dict(y=.08,speed=5.5,scale=.8,seed=.8),dict(y=.33,speed=1.8,scale=1.9,seed=.35)]
	def run(A,section=_A):
		D=section
		if D:
			B={'general':0,_d:1,'skills':2,'mcp':3,'sessions':4,'tasks':5,'files':6,_s:7,'prompts':8,'tools':9,'about':10}.get(D.lower())
			if B is not _A and B<len(A.sections):A.sections[B][2]()
		while _B:
			G=SceneControl(A);E=SceneWindow(A,content=G,always_hide_cursor=_B);H=Layout(E,focused_element=E);A.app=Application(layout=H,key_bindings=A._build_kb(),full_screen=_B,mouse_support=_B,refresh_interval=A.REFRESH,color_depth=ColorDepth.DEPTH_24_BIT)
			try:A.app.run()
			except Exception as C:console.print(f"[error]Settings screen error: {C}[/]");return
			F,A._legacy=A._legacy,_A;I,A._quit_after=A._quit_after,_C
			if F is _A:return
			try:F()
			except Exception as C:A._pending_flash=f"Error: {C}"
			if I:return
			if A._pending_flash:A.flash(A._pending_flash,4.);A._pending_flash=''
	def flash(A,msg,secs=2.5):A.flash_msg=msg;A.flash_until=time.time()+secs
	def _now_flash(A):return A.flash_msg if time.time()<A.flash_until else''
	def quit(A):
		if A.app:A.app.exit()
	def run_blocking(A,fn,quit_after=_C):A._legacy=fn;A._quit_after=quit_after;A.quit()
	def push(A,title,builder):B=builder;C=B();A.stack.append({_I:title,_t:B,_J:C,_H:0});A.scene=_E
	def rebuild_top(B):
		if B.stack:A=B.stack[-1];A[_J]=A[_t]();A[_H]=_clamp(A[_H],0,max(0,len(A[_J])-1))
	def _back_or_quit(A):
		if A.scene==_T:A.input_state=_A;A.scene=_E
		elif A.scene==_X:A.confirm_state=_A;A.scene=_E
		elif A.scene==_K:A.detail_state=_A;A.scene=_E if A.stack else _D
		elif A.scene==_E:
			if A.stack:A.stack.pop()
			A.scene=_E if A.stack else _D
		else:A.quit()
	def begin_input(A,label,cb,password=_C,initial=''):A.input_state={_L:label,_O:initial or'',_u:password,_Y:cb};A.scene=_T
	def begin_confirm(A,label,cb):A.confirm_state={_L:label,_Y:cb};A.scene=_X
	def open_detail(A,title,text):A.detail_state={_I:title,_M:text.splitlines()or[_v],_F:0};A.scene=_K
	def _input_commit(A):
		B=A.input_state
		if not B:return
		A.input_state=_A;A.scene=_E if A.stack else _D;C=B[_O].strip()
		try:B[_Y](A,C)
		except Exception as D:A.flash(f"Error: {D}",4.)
	def on_mouse(A,x,y,etype):
		B=etype
		if B in(SCROLL_UP,SCROLL_DOWN)and A.scene==_K and A.detail_state:C=A.detail_state;E=len(C[_M]);C[_F]=_clamp(C[_F]+(3 if B is SCROLL_DOWN else-3),0,max(0,E-1));return
		D=B==MouseEventType.MOUSE_MOVE;F=B==MouseEventType.MOUSE_UP
		if not(D or F):return
		for(G,H,I,J,K)in A._click:
			if G<=x<=I and H<=y<=J:K(_e if D else'click');return
	def _build_kb(A):
		H='down';G='enter';E='escape';B=KeyBindings();C=Condition(lambda:A.scene==_T);D=Condition(lambda:A.scene==_X);I=Condition(lambda:A.scene in(_D,_E,_K))
		@B.add('c-c')
		def J(event):A.quit()
		@B.add(E,filter=C)
		def K(event):A.input_state=_A;A.scene=_E if A.stack else _D
		@B.add(G,filter=C)
		def L(event):A._input_commit()
		@B.add('backspace',filter=C)
		def M(event):
			if A.input_state:A.input_state[_O]=A.input_state[_O][:-1]
		@B.add('<any>',filter=C)
		def N(event):
			if not A.input_state:return
			C=event.data
			if C=='\t':return
			for B in C:
				if B.isprintable()or B==' ':A.input_state[_O]+=B
		@B.add('y',filter=D)
		def O(event):
			B=A.confirm_state;A.confirm_state=_A;A.scene=_E if A.stack else _D
			if B:
				try:B[_Y]()
				except Exception as C:A.flash(f"Error: {C}",4.)
		@B.add('n',filter=D)
		@B.add(E,filter=D)
		def P(event):A.confirm_state=_A;A.scene=_E if A.stack else _D
		@B.add(E,filter=I)
		def Q(event):A._back_or_quit()
		@B.add('up',filter=Condition(lambda:A.scene in(_D,_E)))
		def R(event):A._nav(-A._grid_cols if A.scene==_D else-1)
		@B.add(H,filter=Condition(lambda:A.scene in(_D,_E)))
		def S(event):A._nav(A._grid_cols if A.scene==_D else 1)
		@B.add('left',filter=Condition(lambda:A.scene in(_D,_E)))
		def T(event):
			if A.scene==_E and A.stack:
				B=A.stack[-1];C=B[_J][B[_H]]if B[_J]else _A
				if C and C.on_left:C.on_left(A);return
			A._nav(-1)
		@B.add('right',filter=Condition(lambda:A.scene in(_D,_E)))
		def U(event):A._nav(1)
		@B.add('tab',filter=Condition(lambda:A.scene in(_D,_E)))
		def V(event):A._nav(1)
		@B.add('s-tab',filter=Condition(lambda:A.scene in(_D,_E)))
		def W(event):A._nav(-1)
		@B.add(G,filter=Condition(lambda:A.scene in(_D,_E)))
		def X(event):A._activate_current()
		@B.add('up',filter=Condition(lambda:A.scene==_K))
		def Y(event):
			if A.detail_state:A.detail_state[_F]=max(0,A.detail_state[_F]-1)
		@B.add(H,filter=Condition(lambda:A.scene==_K))
		def Z(event):
			if A.detail_state:B=A.detail_state;B[_F]=_clamp(B[_F]+1,0,max(0,len(B[_M])-1))
		@B.add('pageup',filter=Condition(lambda:A.scene==_K))
		def a(event):
			if A.detail_state:A.detail_state[_F]=max(0,A.detail_state[_F]-10)
		@B.add('pagedown',filter=Condition(lambda:A.scene==_K))
		def b(event):
			if A.detail_state:B=A.detail_state;B[_F]=_clamp(B[_F]+10,0,max(0,len(B[_M])-1))
		for F in'123456789':
			@B.add(F,filter=Condition(lambda:A.scene in(_D,_E)))
			def c(event,d=F):
				B=int(d)-1
				if A.scene==_D:
					if B<len(A.sections):A.sel=B;A._activate_current()
				elif A.stack:
					C=A.stack[-1]
					if B<len(C[_J]):C[_H]=B;A._activate_current()
		return B
	def _nav(A,delta):
		D=delta
		if A.scene==_D:B=len(A.sections);A.sel=(A.sel+D)%B if B else 0
		elif A.stack:
			C=A.stack[-1];B=len(C[_J])
			if B:C[_H]=(C[_H]+D)%B
	def _activate_current(A):
		if A.scene==_D:
			if A.sections:A.sections[A.sel][2]()
		elif A.stack:
			B=A.stack[-1]
			if B[_J]:
				C=B[_J][B[_H]]
				if C.on_activate:C.on_activate(A)
				elif C.kind==_L:A.flash('—')
	def render(A,w,h):
		A._click=[];A._rects=[]
		try:
			B=Canvas(w,h);C=time.time()-A._t0
			if w<58 or h<16:B.text(2,h//2,'◈ Please enlarge the terminal window ◈',_f);return B.fragments()
			A._draw_sky(B);A._draw_stars(B,C,w,h);A._draw_sun(B,C,w,h);A._draw_clouds(B,C,w,h);A._draw_mountains(B,C,w,h)
			if A.scene==_D:A._draw_main(B,C,w,h)
			elif A.scene==_K and A.detail_state:A._draw_detail(B,C,w,h)
			elif A.stack:A._draw_menu(B,C,w,h)
			A._draw_footer(B,C,w,h);return B.fragments()
		except Exception as D:B=Canvas(w,h);B.text(2,2,f"render error: {D}",'#f87171');return B.fragments()
	def _draw_sky(C,cv):
		for A in range(cv.h):B=_sky_at(A/max(1,cv.h-1));cv.bg[A]=[B]*cv.w
	def _draw_stars(D,cv,t,w,h):
		E=_hx('#bfe3ff')
		for(F,G,H,I)in D._stars:
			A,B=int(F*w),int(G*h);C=.5+.5*math.sin(t*I+H)
			if C>.55 and 0<=A<w and 0<=B<h:J=_rgb(_mix(cv.bg[B][A],E,.25+.55*C));cv.put(A,B,'·',J,bold=_C)
	def _draw_sun(L,cv,t,w,h):
		D,E=int(w*.82),int(h*.14);G=.5+.5*math.sin(t*1.4);C=3.5;H=C+2.5+G*.8;J=_hx(_g);I=_hx('#ecfeff')
		for A in range(max(0,E-8),min(h,E+8)):
			for B in range(max(0,D-14),min(w,D+14)):
				F=math.sqrt((B-D)**2+((A-E)*2.8)**2)
				if F<=C:cv.bg[A][B]=I;cv.put(B,A,' ',_rgb(I))
				elif F<=H:K=(1-(F-C)/(H-C))*(.3+.22*G);cv.bg[A][B]=_mix(cv.bg[A][B],J,K)
	def _draw_clouds(F,cv,t,w,h):
		G=_hx('#41607f')
		for B in F._clouds:
			H=int(B['y']*h);E=w+40;I=int((B['seed']*E+t*B['speed'])%E)-20;A=B['scale'];J=[(0,0,int(11*A)),(-1,int(2*A),int(9*A)),(1,int(1*A),int(10*A))]
			for(K,L,M)in J:
				C=H+K
				if not 0<=C<h:continue
				N=_mix(cv.bg[C][0],G,.3)
				for O in range(L,M):
					D=I+O
					if 0<=D<w:cv.bg[C][D]=_mix(cv.bg[C][D],N,.55)
	def _draw_mountains(K,cv,t,w,h):
		G='col';F='amp';H=[dict(base=.58,amp=2.4,f1=.045,f2=.013,drift=.7,col=(11,44,66),edge=(24,104,138)),dict(base=.7,amp=3.1,f1=.06,f2=.02,drift=1.5,col=(6,27,42),edge=(15,78,106)),dict(base=.84,amp=3.8,f1=.082,f2=.028,drift=2.6,col=(2,10,18),edge=(9,54,78))]
		for A in H:
			for B in range(w):
				E=B+t*A['drift'];D=int(h*A['base']+A[F]*math.sin(E*A['f1'])+A[F]*1.6*math.sin(E*A['f2']+1.7))
				for C in range(_clamp(D,0,h-1),h):cv.bg[C][B]=A[G]
				if 0<=D<h:cv.bg[D][B]=_mix(A['edge'],A[G],.35+.15*math.sin(t+B*.15))
		I=_hx(_W)
		for C in range(int(h*.93),h):
			J=(C-h*.93)/max(1.,h*.07)
			for B in range(w):cv.bg[C][B]=_mix(cv.bg[C][B],I,.5*J)
	def _draw_main(A,cv,t,w,h):
		Y='#a5f3fc';G=cv;Z=max(len(A.rstrip())for A in ART);a=(w-Z)//2;J=max(2,int(h*.08));b=.5+.5*math.sin(t*1.8)
		for(F,c)in enumerate(ART):d=_mix(_hx(_h),_hx(Y),.25+.35*b);e=_mix(d,_hx('#075985'),F/(len(ART)+2));G.text(a,J+F,c.rstrip(),_rgb(e))
		P='◈  S Y S T E M   C O N S O L E  ◈';G.text((w-len(P))//2,J+len(ART)+1,P,_Q,bold=_C);f=[A[0]for A in A.sections];D=_clamp(max(len(A)for A in f)+8,20,28);E,K,I=3,3,2;Q=len(A.sections);H=max(1,min(Q,(w-6)//(D+K)));A._grid_cols=H;R=math.ceil(Q/H);g=H*D+(H-1)*K;i=(w-g)//2;L=J+len(ART)+3
		if L+R*(E+I)>h-3:E=2;I=1
		for(F,(S,j,r))in enumerate(A.sections):
			k,l=divmod(F,H);B=i+l*(D+K);C=L+k*(E+I);M=F==A.sel;m=.5+.5*math.sin(t*1.1+F*.9)
			if M:N=.5+.5*math.sin(t*4.5);T=_rgb(_mix(_hx('#0ea5e9'),_hx(Y),N));U=_rgb(_mix(_hx(_i),_hx(_j),N*.6));G.blend_rect(B,C,B+D-1,C+E-1,_hx(_w),.42+.14*N)
			else:T=_rgb(_mix(_hx('#164e63'),_hx('#0891b2'),m*.35));U=_f;G.blend_rect(B,C,B+D-1,C+E-1,_hx('#082f49'),.3)
			G.box(B,C,B+D-1,C+E-1,T,heavy=M);V=f" {F+1} ▸ {S} "if M else f" {F+1}  {S} ";n=B+max(1,(D-len(V))//2);o=C+(E-1)//2;G.text(n,o,V[:D-2],U,bold=_B);A._rects.append((B,C,B+D-1,C+E-1));p=F
			def q(kind,idx=p,desc=j):
				if kind==_e:A.sel=idx
				else:A.sel=idx;A._activate_current()
			A._click.append((B,C,B+D-1,C+E-1,q))
		W=L+R*(E+I)+1;O=A._now_flash()
		if O:G.text((w-len(O))//2,W,O,_k)
		elif A.sections:X='— '+A.sections[A.sel][1]+' —';G.text((w-len(X))//2,W,X,'#38bdf8',bold=_C)
	def _draw_menu(D,cv,t,w,h):
		B=cv;F=D.stack[-1];G=F[_J];C=min(w-6,92);X=max(3,h-10);J=min(X,len(G)+4);A=(w-C)//2;E=(h-J)//2-1;B.blend_rect(A,E,A+C-1,E+J-1,_hx(_x),.82);L=.5+.5*math.sin(t*2.2);B.box(A,E,A+C-1,E+J-1,_rgb(_mix(_hx(_Z),_hx(_h),.35+.3*L)));S=f" ◈ {F[_I].upper()} ◈ ";B.text(A+(C-len(S))//2,E,S,_rgb(_mix(_hx(_g),_hx(_i),L)),bold=_B);P=0;K=J-3
		if len(G)>K:P=_clamp(F[_H]-K//2,0,len(G)-K)
		for(Y,Q)in enumerate(range(P,min(len(G),P+K))):
			T=G[Q];H=E+2+Y;M=Q==F[_H];Z=T.label;I=T.value_text()
			if M:B.blend_rect(A+1,H,A+C-2,H,_hx(_w),.55);U='▸ ';V=_rgb(_mix(_hx(_y),_hx(_j),L))
			else:U='  ';V='#93c5fd'
			B.text(A+3,H,U,_h);B.text(A+5,H,Z[:C-len(I)-10],V,bold=M)
			if I:
				R=_k if I=='ON'else'#475569'if I=='OFF'else _f
				if M:R=_rgb(_mix(_hx(R),_hx(_j),.3*L))
				B.text(A+C-3-len(I),H,I,R,bold=M)
			def a(kind,i=Q):
				if kind==_e:F[_H]=i
				else:F[_H]=i;D._activate_current()
			D._click.append((A+2,H,A+C-3,H,a))
		if len(G)>K:B.text(A+C-4,E+1,f"{F[_H]+1}/{len(G)}",_Q,bold=_C)
		N=E+J-2;W=D._now_flash()
		if D.scene==_T and D.input_state:O=D.input_state;b='•'*len(O[_O])if O[_u]else O[_O];c='▌'if int(t*2.5)%2==0 else' ';d=f"{O[_L]}: {b}{c}";B.text(A+3,N,d[:C-6],_i)
		elif D.scene==_X and D.confirm_state:e=f"{D.confirm_state[_L]}  (y / n)";B.text(A+3,N,e[:C-6],'#fbbf24')
		elif W:B.text(A+3,N,W[:C-6],_k)
		else:f='↑↓ move · ←→ adjust · Enter select · Esc back';B.text(A+3,N,f,_Q,bold=_C)
	def _draw_detail(L,cv,t,w,h):
		D=cv;C=L.detail_state;E=min(w-6,100);G=h-6;A,B=(w-E)//2,2;D.blend_rect(A,B,A+E-1,B+G-1,_hx(_x),.86);D.box(A,B,A+E-1,B+G-1,_Z);I=f" ◈ {C[_I].upper()} ◈ ";D.text(A+(E-len(I))//2,B,I,_g);F=C[_M];H=G-4;C[_F]=_clamp(C[_F],0,max(0,len(F)-H))
		for J in range(H):
			K=C[_F]+J
			if K>=len(F):break
			D.text(A+3,B+2+J,F[K][:E-6],_y,bold=_C)
		if len(F)>H:D.text(A+E-8,B+1,f"{C[_F]+1}-{min(len(F),C[_F]+H)}/{len(F)}",_Q,bold=_C)
		D.text(A+3,B+G-2,'↑↓ scroll · PgUp/PgDn page · Esc back',_Q,bold=_C)
	def _draw_footer(F,cv,t,w,h):
		A=h-1
		for D in range(w):cv.bg[A][D]=_hx(_W)
		E=f"ABYSSAL v{__version__}";B=time.strftime('%H:%M:%S');C='◄ ► ▲ ▼  navigate   ·   Enter open   ·   Esc back   ·   mouse hover';cv.text(2,A,E,_Z,bold=_C);cv.text((w-len(C))//2,A,C,_Q,bold=_C);cv.text(w-len(B)-2,A,B,_Z,bold=_C)
	def _main_sections(A):return[('GENERAL','Model · thinking · web search · debug · token',lambda:A.push('General',A._menu_general)),('AUTONOMY','How independently DeepSeek acts',lambda:A.push('Autonomy & Agent',A._menu_autonomy)),('SKILLS','Contextual knowledge library',lambda:A.push(_z,A._menu_skills)),('MCP','Servers & tools',lambda:A.push('MCP Servers & Tools',A._menu_mcp)),('SESSIONS','List · resume · rename · delete',A._open_sessions),('TASKS','Cowork scheduled background tasks',lambda:A.push('Cowork Tasks',A._menu_tasks)),('FILES','Uploads & pending attachments',lambda:A.push('Files & Uploads',A._menu_files)),('SOUNDS','Notification · response · blank response',lambda:A.push('Sounds',A._menu_sounds)),('PROMPTS','System prompt & prompt library',lambda:A.push('System Prompt',A._menu_prompts)),('TOOLS','History · export · undo · retry · copy',lambda:A.push('Conversation Tools',A._menu_convtools)),('ABOUT','Version · paths · token',lambda:A.push('About',A._menu_about))]
	def _menu_general(B):
		A=B.cli
		def C():return A.model if A.model in MODELS else list(MODELS.keys())[0]
		def D(v):A.model=v;A.cfg['model']=v;save_config(A.cfg)
		def E(v):A.thinking_enabled=v;A.cfg['thinking']=v;save_config(A.cfg)
		def F(v):A.search_enabled=v;A.cfg['search']=v;save_config(A.cfg)
		def G(v):
			A.debug=v;A.cfg['debug']=v;save_config(A.cfg)
			if getattr(A,'client',_A):
				A.client.api.debug=v
				if v:A.client.api._setup_logger()
		def H(s,value):
			B=value
			if not B:s.flash('Empty token — nothing changed');return
			def C():
				save_token(B);A.client=_A
				if A.authenticate()and not A.session_id:A.new_session(quiet=_B)
			s.run_blocking(C)
		I=[_cycle('Model',list(MODELS.keys()),C,D),_toggle('Thinking mode',lambda:A.thinking_enabled,E),_toggle('Web search',lambda:A.search_enabled,F),_toggle('Debug logging',lambda:A.debug,G),_input('Auth token (paste new)',H,password=_B),_label('Token',f"{mask(load_token()or"")} · {token_source()}")];return I
	def _menu_autonomy(E):
		D='agent_toggles';A=E.cli;B=[]
		if AUTONOMY_MODES:
			C=[AUTONOMY_MODES[A][_L]for A in AUTONOMY_MODES];F=list(AUTONOMY_MODES.keys())
			def G():return AUTONOMY_MODES.get(getattr(A,_l,'human-needed'),{}).get(_L,'—')
			def H(label):
				B=F[C.index(label)];A.autonomy_mode=B;A.cfg[_d]=B
				if B!=_P:A.agent_settings.update(AUTONOMY_MODES[B].get('toggles',{}))
				A.cfg[D]=dict(A.agent_settings);save_config(A.cfg)
			B.append(_cycle('Autonomy mode',C,G,H));I=AUTONOMY_MODES.get(getattr(A,_l,''),{});B.append(_label('Behavior',I.get(_m,'')[:64]))
		for J in list(A.agent_settings.keys()):
			def K(key=J):
				B=key
				def C():return bool(A.agent_settings.get(B))
				def E(v):
					A.agent_settings[B]=v
					if AUTONOMY_MODES and A.autonomy_mode!=_P:A.autonomy_mode=_P;A.cfg[_d]=_P
					A.cfg[D]=dict(A.agent_settings);save_config(A.cfg)
				return _toggle(B,C,E)
			B.append(K())
		return B
	def _menu_skills(B):
		if skills_mod is _A:return[_label('Skills module not installed','')]
		C=[]
		for A in skills_mod.list_skills():
			D=A[_R]
			def E(s=A,name=D):B.push(f"Skill · {name}",lambda name=name:B._menu_skill(name))
			C.append(_action(f"{D}  —  v{A.get(_n,1)}",lambda s_=_A,f=E:f(),value=lambda s=A:str(s.get(_A0,''))[:40]))
		def F(s):s.begin_input('New skill name',B._skill_name_cb)
		C.append(_action('＋ Create a new skill',F));return C
	def _skill_name_cb(A,s,name):
		if not name:return
		A._draft={_R:name};s.begin_input('One-line description',A._skill_desc_cb)
	def _skill_desc_cb(A,s,desc):A._draft[_m]=desc;A._draft[_M]=[];s.flash("Enter content lines — finish with a lone '.'");s.begin_input('skill│',A._skill_line_cb)
	def _skill_line_cb(A,s,line):
		if line.strip()=='.':
			B=_a.join(A._draft[_M]).strip()
			if not B:s.flash('Empty content — nothing saved');return
			C=skills_mod.write_skill(A._draft[_R],B,description=A._draft.get(_m),note='written from settings console');s.flash(f"Saved skill '{C[_R]}' v{C[_n]}");A.rebuild_top();return
		A._draft[_M].append(line);s.begin_input('skill│',A._skill_line_cb)
	def _menu_skill(C,name):
		A=name;B=[]
		def D(s):
			B,C=skills_mod.read_skill(A)
			if B:s.open_detail(f"{A} · v{B.get(_n)}",(B.get(_A0)or'')+'\n\n'+C)
		B.append(_action('View content',D))
		def E(s):s.begin_input('Diff — version A #',lambda sc,va:sc.begin_input('Diff — version B #',lambda sc2,vb:C._do_skill_diff(A,va,vb)))
		B.append(_action('Diff two versions',E))
		def F(s):s.begin_input('Roll back to version #',lambda sc,v:C._do_skill_rollback(A,v))
		B.append(_action('Roll back to an older version',F))
		def G(s):s.begin_confirm(f"Delete skill '{A}' and ALL versions?",lambda:(skills_mod.delete_skill(A),C.flash(f"Deleted '{A}'"),C._back_or_quit()))
		B.append(_action('Delete skill',G));return B
	def _do_skill_diff(A,name,va,vb):
		try:C,B=skills_mod.diff_skills(name,int(va),int(vb))
		except ValueError:A.flash('Version numbers must be integers');return
		if C:A.open_detail(f"{name} · v{va} → v{vb}",B)
		else:A.flash(B)
	def _do_skill_rollback(A,name,v):
		try:B,C=skills_mod.rollback_skill(name,int(v))
		except ValueError:A.flash('Version must be a number');return
		A.flash(C,4.)
		if B:A.rebuild_top()
	def _menu_mcp(B):
		A=B.cli;C=[_label('Status',f"{len(A.mcp.list_servers())} servers · {len(A.mcp.tools)} tools · sdk {"ok"if MCP_AVAILABLE else"MISSING"}")]
		def D(s):
			if not MCP_AVAILABLE:s.flash('MCP SDK missing — pip install mcp');return
			def C():C=asyncio.run(A.mcp.refresh_tools());A._next_tools_reminder_at=min(A._next_tools_reminder_at,len(A.messages)+1);B._pending_flash=f"Loaded {len(C)} MCP tools"
			s.run_blocking(C)
		C.append(_action('Refresh / reconnect servers',D))
		def E(s):s.begin_input('Server name',lambda sc,n:sc.begin_input('Command (python, npx…)',lambda sc2,cmd:sc2.begin_input('Arguments (space separated)',lambda sc3,a:B._mcp_add_done(n,cmd,a))))
		C.append(_action('Add a server',E))
		if A.mcp.list_servers():C.append(_action('Remove a server…',lambda s:B.push('Remove MCP server',B._menu_mcp_remove)))
		return C
	def _mcp_add_done(A,name,cmd,args):
		B=name
		if not B or not cmd:A.flash('Name and command are required');return
		try:C=shlex.split(args or'')
		except ValueError:C=(args or'').split()
		A.cli.mcp.add_server(B,cmd,C);A.flash(f"Added '{B}' — run Refresh to load its tools",4.);A.rebuild_top()
	def _menu_mcp_remove(A):
		B=A.cli;C=[]
		for(D,E)in B.mcp.list_servers().items():
			def F(name=D):A.begin_confirm(f"Remove MCP server '{name}'?",lambda name=name:(B.mcp.remove_server(name),A.flash(f"Removed '{name}'"),A._back_or_quit(),A.rebuild_top()))
			C.append(_action(D,lambda s=_A,f=F:f(),value=lambda cfg=E:f"{cfg.get("command")} {" ".join(cfg.get("args")or[])}"[:34]))
		return C or[_label('No servers configured','')]
	def _open_sessions(C):
		def A():
			I='updated_at';E=C.cli;D=[]
			try:F=E.client.list_sessions()if E.client else[]
			except Exception:F=[]
			G=set()
			for A in F:
				B=str(A.get(_G)or A.get('session_id')or'')
				if not B:continue
				G.add(B);D.append({_G:B,_I:A.get(_I)or A.get(_R)or'',_U:str(A.get(I)or A.get('create_time')or'')[:16]})
			for(B,H)in all_local_transcripts().items():
				if B not in G:D.append({_G:B,_I:(H.get(_I)or'')+' (local)',_U:str(H.get(I,''))[:16]})
			D.sort(key=lambda r:r[_U],reverse=_B);C._session_rows=D
		def B():A();C.push('Sessions',C._menu_sessions)
		C.run_blocking(B)
	def _menu_sessions(A):
		E=A.cli;B=[]
		def F(s):s.run_blocking(lambda:E.new_session(),quit_after=_B)
		B.append(_action('＋ New session',F))
		for(G,C)in enumerate(getattr(A,_A1,[])):
			D=C[_G]
			def H(sid=D):A.cli._apply_session(sid);A.flash(f"Resumed {sid[:12]}…");A.quit()
			B.append(_action(f"{G+1}. {C[_I][:38]or D[:12]}",lambda s=_A,f=H:f(),value=lambda r=C:r[_U]))
		def I(s):s.begin_input('New title for current session',A._session_rename_cb)
		B.append(_action('Rename current session',I));B.append(_action('Delete a session…',lambda s:A.push('Delete session',A._menu_sessions_delete)));return B
	def _session_rename_cb(C,s,title):
		B=title
		if not B:return
		A=C.cli
		def D():
			A.session_title=B
			try:
				if A.client and A.session_id:A.client.rename_session(A.session_id,B)
			except Exception:pass
			A._save_transcript();C._pending_flash=f"Renamed to '{B}'"
		s.run_blocking(D)
	def _menu_sessions_delete(A):
		C=[]
		for B in getattr(A,_A1,[]):
			D=B[_G]
			def E(sid=D):A.begin_confirm(f"Delete session {sid[:12]}…?",lambda sid=sid:A._session_delete(sid))
			C.append(_action(f"{B[_I][:36]or D[:12]}",lambda s=_A,f=E:f(),value=lambda r=B:r[_U]))
		return C or[_label('No sessions','')]
	def _session_delete(B,sid):
		C=sid;A=B.cli
		def D():
			try:
				if A.client:A.client.delete_session(C)
			except Exception:pass
			D=transcript_path(C)
			if D.exists():D.unlink()
			if C==A.session_id:A.session_id=_A;A.messages.clear();A.parent_message_id=_A
			B._session_rows=[A for A in B._session_rows if A[_G]!=C];B._pending_flash='Session deleted'
		B.run_blocking(D)
	def _menu_tasks(A):
		E=A.cli;B=[]
		def F(s):s.run_blocking(lambda:E.cmd_task(['/task','add']))
		B.append(_action('＋ Add a task (guided)',F))
		for C in load_tasks():
			D=C.get(_G,'')[:8]
			def G(t=C):A.push(f"Task · {D if _C else t.get(_G,"")[:8]}",lambda t=t:A._menu_task(t[_G]))
			B.append(_action(f"{D}  {str(C.get("prompt",""))[:36]}",lambda s=_A,f=G:f(),value=lambda t=C:f"{t.get(_b)} · {_schedule_label(t)}"))
		def H(s):s.begin_confirm('Clear all finished tasks?',lambda:(save_tasks([A for A in load_tasks()if A.get(_b)not in('done','failed')]),A.flash('Cleared finished tasks'),A.rebuild_top()))
		B.append(_action('Clear finished tasks',H));return B
	def _menu_task(A,tid):
		B=tid;D=A.cli;C=[]
		def E():return next((A for A in load_tasks()if A[_G]==B),_A)
		def F(s):
			def C():
				import threading as C
				if D.taskman:C.Thread(target=D.taskman.execute_task,args=(B,),daemon=_B).start()
				A._pending_flash='Task started in background'
			s.run_blocking(C)
		C.append(_action('Run now',F))
		def G(s):
			D='paused';F=E()
			if not F:return
			C=load_tasks()
			for A in C:
				if A[_G]==B:A[_b]='pending'if A.get(_b)==D else D
			save_tasks(C);s.flash('Task toggled');s.rebuild_top()
		C.append(_action('Pause / resume',G))
		def H(s):A=E();s.open_detail(f"Result · {B[:8]}",str((A or{}).get(_o)or'(no result yet)'))
		C.append(_action('Show last result',H))
		def I(s):
			def C():
				E='chain_task_id';C=[A for A in load_tasks()if A[_G]!=B]
				for D in C:
					if D.get(E)==B:D[E]=''
				save_tasks(C);A._pending_flash='Task removed'
			s.begin_confirm('Remove this task?',lambda:(A.run_blocking(C),A._back_or_quit(),A._back_or_quit()))
		C.append(_action('Remove task',I));return C
	def _menu_files(D):
		A=D.cli;B=[_label('Pending attachments',str(len(A.pending_file_ids)))]
		def E(s):s.begin_input('Path to file',lambda sc,p:sc.run_blocking(lambda:A.cmd_upload(['/upload',p])))
		B.append(_action('Upload a file',E))
		def F(s):A.pending_file_ids=[];s.flash('Pending attachments cleared');s.rebuild_top()
		B.append(_action('Clear pending attachments',F));G=set(A.pending_file_ids)
		for C in getattr(A,'uploaded_files',[]):B.append(_label(C.get(_R,C.get(_G,'?'))[:40],'pending'if C.get(_G)in G else'sent'))
		return B
	def _sounds_cfg(A):return A.cli.cfg.setdefault(_s,{_p:_B,'notify':{_S:_B,_N:'abyss-chime',_V:''},'response':{_S:_B,_N:_c,_V:''},'blank':{_S:_B,_N:'deep-ping',_V:''}})
	def _menu_sounds(A):
		if play_sound is _A:return[_label('Sounds module not installed','')]
		B=A._sounds_cfg()
		def G(v):B[_p]=v;save_config(A.cli.cfg)
		C=[_toggle('Master sounds',lambda:bool(B.get(_p,_B)),G)]
		for(D,E)in(('notify','Notification / completion'),('response','Response'),('blank','Blank response')):
			def H(ch=D,label=E):A.push(f"Sound · {label}",lambda ch=ch:A._menu_sound_ch(ch))
			I=B.get(D,{});F=I.get(_N,_c);J='custom file'if F==_P else F;C.append(_action(f"{E} sound ›",lambda s=_A,f=H:f(),value=lambda shown=J:shown))
		return C
	def _menu_sound_ch(B,ch):
		C=B._sounds_cfg();A=C.setdefault(ch,{_S:_B,_N:_c,_V:''})
		def D(v):A[_S]=v;save_config(B.cli.cfg)
		E=list(SOUND_PRESETS.keys())+[_P]
		def F():return A.get(_N,_c)
		def G(v):A[_N]=v;save_config(B.cli.cfg)
		def H(s,path):
			if path:A[_N]=_P;A[_V]=str(Path(path).expanduser());save_config(B.cli.cfg);s.flash('Custom sound file set')
		def I(s):play_sound(ch);s.flash('Playing…')
		return[_toggle('Enabled',lambda:bool(A.get(_S,_B)),D),_cycle('Preset',E,F,G),_input('Custom audio file path…',H),_action('Test this sound',I)]
	def _menu_prompts(C):
		E='system_prompt';D='active_prompt_name';A=C.cli;B=[]
		def H(s):s.open_detail('System prompt',A.system_prompt or'(none set)')
		B.append(_action('Show current system prompt',H))
		def I(s,text):
			B=text
			if not B:return
			A.system_prompt=B;A.active_prompt_name='';A.cfg.update({E:B,D:''});save_config(A.cfg);s.flash('System prompt updated')
		B.append(_input('Set system prompt',I))
		def J(s):s.begin_confirm('Clear the system prompt?',lambda:(setattr(A,E,''),A.cfg.update({E:'',D:''}),save_config(A.cfg),s.flash('Cleared'),s.rebuild_top()))
		B.append(_action('Clear system prompt',J));G=[A.stem for A in sorted(PROMPTS_DIR.glob('*.txt'))]
		for F in G:
			def K(n=F):B=PROMPTS_DIR/f"{n}.txt";A.system_prompt=B.read_text(encoding=_q);A.active_prompt_name=n;A.cfg.update({E:A.system_prompt,D:n});save_config(A.cfg);C.flash(f"Loaded '{n}'");C.rebuild_top()
			B.append(_action(f"Load '{F}'",lambda s=_A,f=K:f(),value=lambda n=F:'active'if A.active_prompt_name==n else''))
		def L(s):s.begin_input('Save current prompt as',lambda sc,n:((PROMPTS_DIR/f"{n}.txt").write_text(A.system_prompt,encoding=_q),setattr(A,D,n),A.cfg.__setitem__(D,n),save_config(A.cfg),sc.flash(f"Saved '{n}'"),sc.rebuild_top())if n and A.system_prompt else sc.flash('Nothing to save'))
		B.append(_action('Save current as…',L))
		def M(s):C.push('Delete prompt',C._menu_prompts_delete)
		if G:B.append(_action('Delete a prompt…',M))
		return B
	def _menu_prompts_delete(A):
		B=[]
		for C in sorted(PROMPTS_DIR.glob('*.txt')):
			def D(p=C):A.begin_confirm(f"Delete prompt '{p.stem}'?",lambda p=p:(p.unlink(),A.flash(f"Deleted '{p.stem}'"),A._back_or_quit(),A.rebuild_top()))
			B.append(_action(C.stem,lambda s=_A,f=D:f()))
		return B or[_label('No saved prompts','')]
	def _menu_convtools(E):
		G='History';F='content';D='role';A=E.cli;B=[]
		def H(s):B=[f"version     : {__version__}",f"session     : {A.session_id or"—"}",f"model       : {A.model}",f"thinking    : {A.thinking_enabled}   search: {A.search_enabled}",f"messages    : {len(A.messages)}",f"notes       : {len(A.session_notes)}",f"mcp tools   : {len(A.mcp.tools)}",f"token       : {mask(load_token()or"")} ({token_source()})",f"config      : {CONFIG_FILE}"];s.open_detail('Status',_a.join(B))
		B.append(_action('Status (detailed)',H))
		def I(s):
			C=[]
			for(E,B)in enumerate(A.messages[-40:],1):H=str(B.get(F)or B.get(_o)or'')[:200];C.append(f"{E}. [{B.get(D)}] {H}")
			s.open_detail(G,_a.join(C)or _v)
		B.append(_action(G,I))
		def J(s,name):
			def B():
				H=name or datetime.now().strftime('abyssal_%Y%m%d_%H%M%S');C=Path.cwd()/f"{H}.md";G=[f"# Abyssal — {A.session_title or"untitled"}",'']
				for B in A.messages:I={'user':'**You**','assistant':'**Abyssal**','tool':'**Tool**'}.get(B[D],B[D]);G.append(f"## {I}\n{B.get(F,B.get(_o,""))}\n")
				C.write_text(_a.join(G),encoding=_q);E._pending_flash=f"Exported → {C}"
			s.run_blocking(B)
		B.append(_input('Export conversation (file name)',J))
		def C(cmd,quit_after=_B):return lambda s:s.run_blocking(lambda:A.handle_command(cmd),quit_after=quit_after)
		B.append(_action('Retry last message',C('/retry')));B.append(_action('Undo last exchange',C('/undo',_C)));B.append(_action('Copy last response',C('/copy',_C)));B.append(_action('Paste clipboard → next prompt',C('/paste')))
		def K(s):s.begin_input('Edit — message #',lambda sc,n:sc.begin_input('New text',lambda sc2,txt:sc2.run_blocking(lambda:A.handle_command(f"/edit {n} {txt}"))))
		B.append(_action('Edit an earlier message',K));return B
	def _menu_about(C):B='n/a';A=C.cli;return[_label('Abyssal',f"v{__version__} — the most unique terminal client"),_label('Config',str(CONFIG_FILE)),_label('Token',f"{mask(load_token()or"")} · {token_source()}"),_label('Autonomy',str(getattr(A,_l,B))),_label('MCP tools',str(len(A.mcp.tools))),_label(_z,str(len(skills_mod.list_skills()))if skills_mod else B),_label('Messages this session',str(len(A.messages)))]