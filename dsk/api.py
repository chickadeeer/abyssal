_X='action'
_W='search_enabled'
_V='thinking_enabled'
_U='ref_file_ids'
_T='prompt'
_S='chat_session_id'
_R='default'
_Q='Invalid challenge response format'
_P='challenge'
_O='target_path'
_N='/chat/create_pow_challenge'
_M='API rate limit exceeded'
_L='content-type'
_K='disabled'
_J='status'
_I='POST'
_H='Invalid or expired authentication token'
_G='x-ds-pow-response'
_F='authorization'
_E='utf-8'
_D='biz_data'
_C='data'
_B=False
_A=None
import json,logging
from pathlib import Path
import threading
from typing import Any,Dict,Generator,List,Literal,Optional
import requests
from.pow import DeepSeekPOW
ThinkingMode=Literal['detailed','simple',_K]
SearchMode=Literal['enabled',_K]
class DeepSeekError(Exception):0
class AuthenticationError(DeepSeekError):0
class RateLimitError(DeepSeekError):0
class NetworkError(DeepSeekError):0
class CloudflareError(DeepSeekError):0
class APIError(DeepSeekError):
	def __init__(A,message,status_code=_A):super().__init__(message);A.status_code=status_code
class POWCache:
	def __init__(A,api):A.api=api;A._lock=threading.Lock();A._cached=_A;A._thread=_A
	def _compute(A):
		try:
			B=A.api._get_pow_challenge();C=A.api.pow_solver.solve_challenge(B)
			with A._lock:A._cached=C
		except Exception:
			with A._lock:A._cached=_A
	def get(A):
		with A._lock:B=A._cached;A._cached=_A
		if B is _A:C=A.api._get_pow_challenge();B=A.api.pow_solver.solve_challenge(C)
		A._thread=threading.Thread(target=A._compute,daemon=True);A._thread.start();return B
class DeepSeekAPI:
	BASE_URL='https://chat.deepseek.com/api/v0'
	def __init__(A,auth_token,debug=_B):
		B=auth_token
		if not B or not isinstance(B,str):raise AuthenticationError('Invalid auth token provided')
		A.auth_token=B;A.pow_solver=DeepSeekPOW();A.pow_cache=POWCache(A);A.debug=debug;A.logger=_A
		if A.debug:A._setup_logger()
		A.cookies={};C=Path(__file__).parent/'cookies.json'
		try:
			with open(C,'r',encoding=_E)as D:E=json.load(D);A.cookies=E.get('cookies',{})
		except(FileNotFoundError,json.JSONDecodeError):pass
	def _setup_logger(A):
		A.logger=logging.getLogger('DeepSeekAPI');A.logger.setLevel(logging.DEBUG);A.logger.propagate=_B
		if not A.logger.handlers:B=logging.FileHandler('debug.txt',mode='a',encoding=_E);C=logging.Formatter('%(asctime)s | %(levelname)-7s | %(message)s',datefmt='%Y-%m-%d %H:%M:%S');B.setFormatter(C);A.logger.addHandler(B)
		A.logger.debug('='*60);A.logger.debug('DeepSeekAPI logger started (debug=True)')
	def _log(A,message):
		if A.debug and A.logger:A.logger.debug(message)
	def _safe_headers(B,headers):
		A=headers.copy()
		if _F in A:A[_F]='Bearer [REDACTED]'
		if _G in A:A[_G]='[REDACTED]'
		return A
	def _get_headers(C,pow_response=_A):
		A=pow_response;B={'accept':'*/*','accept-language':'en-US,en;q=0.9',_F:f"Bearer {C.auth_token}",_L:'application/json','origin':'https://chat.deepseek.com','referer':'https://chat.deepseek.com/','user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36','x-client-bundle-id':'com.deepseek.chat','x-client-locale':'en_US','x-client-platform':'web','x-client-version':'2.3.0','x-client-timezone-offset':'-14400'}
		if A:B[_G]=A
		return B
	def _make_request(B,method,endpoint,json_data):
		D=json_data;C=method;E=f"{B.BASE_URL}{endpoint}";F=B._get_headers();B._log(f"REQUEST  {C} {E}");B._log(f"HEADERS  {json.dumps(B._safe_headers(F),indent=2)}");B._log(f"BODY     {json.dumps(D,indent=2,ensure_ascii=_B)}")
		try:
			A=requests.request(method=C,url=E,headers=F,json=D,cookies=B.cookies,timeout=30);B._log(f"RESPONSE status={A.status_code}")
			try:H=A.json();B._log(f"BODY     {json.dumps(H,indent=2,ensure_ascii=_B)}")
			except Exception:B._log(f"BODY     {A.text[:2000]}")
			if A.status_code==401:raise AuthenticationError(_H)
			elif A.status_code==429:raise RateLimitError(_M)
			elif A.status_code>=500:raise APIError(f"Server error: {A.text}",A.status_code)
			elif A.status_code!=200:raise APIError(f"Request failed: {A.text}",A.status_code)
			return A.json()
		except requests.exceptions.RequestException as G:B._log(f"NETWORK ERROR: {G}");raise NetworkError(f"Network error: {str(G)}")
	def _get_pow_challenge(A):
		try:B=A._make_request(_I,_N,{_O:'/api/v0/chat/completion'});return B[_C][_D][_P]
		except KeyError:raise APIError(_Q)
	def _get_pow_for_path(A,target_path):
		B=A._make_request(_I,_N,{_O:target_path})
		try:C=B[_C][_D][_P]
		except KeyError:raise APIError(_Q)
		return A.pow_solver.solve_challenge(C)
	def create_chat_session(C):
		B='chat_session'
		try:
			D=C._make_request(_I,'/chat_session/create',{'character_id':_A});A=D[_C][_D]
			if B in A:return A[B]['id']
			return A['id']
		except KeyError:raise APIError('Invalid session creation response')
	def upload_file(A,file_path,model_type=_R,thinking_enabled=_B):
		H=file_path;import mimetypes as J;C=Path(H)
		if not C.exists():raise FileNotFoundError(f"File not found: {H}")
		I=C.stat().st_size;K=J.guess_type(str(C))[0]or'application/octet-stream';L=A._get_pow_for_path('/api/v0/file/upload_file');D=A._get_headers(L);D.pop(_L,_A);D['x-file-size']=str(I);D['x-model-type']=model_type;D['x-thinking-enabled']='1'if thinking_enabled else'0';M=f"{A.BASE_URL}/file/upload_file";A._log(f"UPLOAD   {C.name} ({I} bytes)")
		try:
			with open(C,'rb')as N:B=requests.post(M,headers=D,files={'file':(C.name,N,K)},cookies=A.cookies,timeout=120)
		except requests.exceptions.RequestException as O:raise NetworkError(f"Upload network error: {O}")
		A._log(f"UPLOAD   status={B.status_code}")
		try:E=B.json();A._log(f"BODY     {json.dumps(E,indent=2)}")
		except Exception:raise APIError('Upload failed: non-JSON response')
		if B.status_code==401:raise AuthenticationError(_H)
		elif B.status_code==429:raise RateLimitError('Rate limit exceeded during upload')
		elif B.status_code!=200:raise APIError(f"Upload failed: {B.text}",B.status_code)
		F=E.get(_C,{}).get(_D,{})
		if F.get(_J)!='SUCCESS':raise APIError(f"Upload not successful: {F.get("error_code")} — {E}")
		G=F.get('id')
		if not G:raise APIError(f"No file id in upload response: {E}")
		A._log(f"UPLOAD   file_id={G} tokens={F.get("token_usage")}");return G
	def _stream_response(B,endpoint,json_data):
		o='queries';n='search';m='APPEND';l='fragments';k='response';d=json_data;c='TOOL_SEARCH';W='results';V='response/fragments/-1/content';U='RESPONSE';T='response_message_id';R='thinking';N='THINK';M='text';D='type';C='content'
		try:
			p=B.pow_cache.get();e=B._get_headers(p);f=f"{B.BASE_URL}{endpoint}";B._log(f"REQUEST  POST {f}  (streaming)");B._log(f"HEADERS  {json.dumps(B._safe_headers(e),indent=2)}");B._log(f"BODY     {json.dumps(d,indent=2,ensure_ascii=_B)}");I=requests.post(f,headers=e,json=d,cookies=B.cookies,stream=True,timeout=_A);B._log(f"RESPONSE status={I.status_code} (stream started)")
			if I.status_code!=200:
				q=I.text;B._log(f"BODY     {q[:2000]}")
				if I.status_code==401:raise AuthenticationError(_H)
				elif I.status_code==429:raise RateLimitError(_M)
				else:raise APIError(f"Request failed: {I.status_code}",I.status_code)
			F=_A;g=_A;O=_A;J=_A
			for G in I.iter_lines():
				if not G:continue
				if isinstance(G,bytes):G=G.decode(_E)
				B._log(f"STREAM   {G}")
				if G.startswith('event: '):O=G[7:];continue
				if not G.startswith('data: '):continue
				X=G[6:]
				if not X or X=='[DONE]':continue
				try:L=json.loads(X)
				except json.JSONDecodeError:continue
				if O=='ready'or T in L:
					if T in L:g=L[T]
					O=_A;continue
				if O in('close','finish'):h={D:'meta',T:g,'finish_reason':'stop'};B._log(f"YIELD    {h}");yield h;return
				O=_A;E=L.get('v');Y=L.get('p');Z=L.get('o')
				if isinstance(E,dict)and k in E:
					S=E[k]
					if isinstance(S.get(C),str)and S[C]:F='response/content';J=U;A={D:M,C:S[C]};B._log(f"YIELD    {A}");yield A
					for i in S.get(l,[]):
						K=i.get(D);H=i.get(C)or''
						if K==N and H:J=N;F=V;A={D:R,C:H};B._log(f"YIELD    {A}");yield A
						elif K==U and H:J=U;F=V;A={D:M,C:H};B._log(f"YIELD    {A}");yield A
						elif K==c:J=c
					continue
				if Y is not _A:
					F=Y
					if Z==m and isinstance(E,str):
						if F and F.endswith(C):
							if J==N:A={D:R,C:E}
							else:A={D:M,C:E}
							B._log(f"YIELD    {A}");yield A
					elif Z=='SET':
						if Y.endswith(W)and isinstance(E,list):A={D:n,W:E};B._log(f"YIELD    {A}");yield A
					elif Z=='BATCH'and isinstance(E,list):
						for a in E:
							b=a.get('p');r=a.get('o');P=a.get('v')
							if b==l and r==m and isinstance(P,list):
								for Q in P:
									K=Q.get(D);H=Q.get(C)or'';J=K
									if K==N and H:F=V;A={D:R,C:H};B._log(f"YIELD    {A}");yield A
									elif K==U and H:F=V;A={D:M,C:H};B._log(f"YIELD    {A}");yield A
									elif K==c:s=Q.get(o)or[];A={D:n,_J:Q.get(_J,'WIP'),o:[A.get('query')for A in s],W:Q.get(W)or[]};B._log(f"YIELD    {A}");yield A
							elif b and b.endswith(C)and isinstance(P,str):
								if J==N:A={D:R,C:P}
								else:A={D:M,C:P}
								B._log(f"YIELD    {A}");yield A
					continue
				if isinstance(E,str)and F and F.endswith(C):
					if J==N:A={D:R,C:E}
					else:A={D:M,C:E}
					B._log(f"YIELD    {A}");yield A
		except requests.exceptions.RequestException as j:B._log(f"NETWORK ERROR during streaming: {j}");raise NetworkError(f"Network error during streaming: {str(j)}")
	def chat_completion(B,chat_session_id,prompt,parent_message_id=_A,model_type=_R,thinking_enabled=_B,search_enabled=_B,ref_file_ids=_A):A=ref_file_ids;C={_S:chat_session_id,'parent_message_id':parent_message_id,'model_type':_A if A else model_type,_T:prompt,_U:A or[],_V:thinking_enabled,_W:search_enabled,_X:_A,'preempt':_B};return B._stream_response('/chat/completion',C)
	def edit_message(A,chat_session_id,message_id,prompt,thinking_enabled=_B,search_enabled=_B):B={_S:chat_session_id,'message_id':message_id,_U:[],_T:prompt,_W:search_enabled,_V:thinking_enabled,_X:_A};return A._stream_response('/chat/edit_message',B)