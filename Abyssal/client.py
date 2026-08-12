from __future__ import annotations
_A='POST'
from typing import Any,Dict,List
try:from dsk.api import APIError,AuthenticationError,DeepSeekAPI,DeepSeekError,NetworkError,RateLimitError
except ImportError:
	try:from api import APIError,AuthenticationError,DeepSeekAPI,DeepSeekError,NetworkError,RateLimitError
	except ImportError as exc:raise ImportError('Could not import DeepSeekAPI. Run this from the project directory or ensure the `dsk` package / api.py is available.')from exc
class DeepSeekClient:
	def __init__(A,token,debug=False):A.api=DeepSeekAPI(token,debug=debug)
	def verify(A):A.list_sessions()
	def create_session(A):return A.api.create_chat_session()
	def list_sessions(C):
		D=C.api._make_request(_A,'/chat_session/list',{});A=D.get('data',{}).get('biz_data',{})
		if isinstance(A,list):return A
		if isinstance(A,dict):
			for B in('chat_sessions','sessions','list','items'):
				if isinstance(A.get(B),list):return A[B]
		return[]
	def delete_session(A,session_id):A.api._make_request(_A,'/chat_session/delete',{'id':session_id})
	def rename_session(A,session_id,name):A.api._make_request(_A,'/chat_session/rename',{'id':session_id,'name':name})