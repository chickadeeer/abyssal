from __future__ import annotations
_A=False
import re
from typing import List,Tuple
HUNK_RE=re.compile('^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@')
def _parse_hunks(patch):
	C=patch.splitlines();F=[];B=0
	while B<len(C):
		G=HUNK_RE.match(C[B].strip())
		if not G:B+=1;continue
		H=int(G.group(1));B+=1;D=[];E=[]
		while B<len(C):
			A=C[B]
			if HUNK_RE.match(A.strip())or A.startswith(('--- ','+++ ')):break
			if A.startswith('+'):E.append(A[1:])
			elif A.startswith('-'):D.append(A[1:])
			elif A.startswith(' '):D.append(A[1:]);E.append(A[1:])
			elif A.startswith('\\'):0
			else:D.append(A);E.append(A)
			B+=1
		F.append((H,D,E))
	return F
def _find(lines,needle,approx):
	C=lines;B=needle;A=approx
	if not B:return max(0,min(A,len(C)))
	def D(i):
		if i<0 or i+len(B)>len(C):return _A
		return all(A.rstrip()==B.rstrip()for(A,B)in zip(C[i:i+len(B)],B))
	if D(A):return A
	for E in range(1,61):
		if D(A-E):return A-E
		if D(A+E):return A+E
	for F in range(0,max(0,len(C)-len(B))+1):
		if D(F):return F
	return-1
def apply_unified_patch(source,patch):
	D=_parse_hunks(patch)
	if not D:return _A,'',"No diff hunks found. The 'patch' field must be a unified diff with @@ -l,c +l,c @@ headers and +/-/space line prefixes."
	A=source.split('\n');E=0
	for(H,(F,B,G))in enumerate(D,1):
		C=_find(A,B,F-1+E)
		if C<0:return _A,'',f"Hunk {H} (@@ -{F}) does not match the current file. Re-read the plugin with the mcp_read_plugin tool and regenerate the patch against the exact current content."
		A[C:C+len(B)]=G;E+=len(G)-len(B)
	return True,'\n'.join(A),''