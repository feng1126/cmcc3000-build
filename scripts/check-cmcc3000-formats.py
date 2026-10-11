#!/usr/bin/env python3
"""Heuristic format argument audit; conditional code requires compiler review."""
import ast,re,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()/'package/mtk/drivers'
lexer=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
def comments(s):
 return lexer.sub(lambda m: ('\n'*m[0].count('\n')+' ') if m[0].startswith(('//','/*')) else m[0],s)
def arguments(s,start):
 args=[];begin=start;depth=0;quote=None;escape=False
 for i in range(start,len(s)):
  c=s[i]
  if quote:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c==quote:quote=None
   continue
  if c in '\"\'':quote=c
  elif c in '([{':depth+=1
  elif c in ')]}':
   if c==')' and depth==0:return args+[s[begin:i].strip()]
   depth-=1
  elif c==',' and depth==0:args.append(s[begin:i].strip());begin=i+1
 return []
checked=0;findings=[]
for p in root.rglob('*.c'):
 if not any(x in p.parts for x in ['warp','conninfra','mt_wifi']):continue
 s=comments(p.read_text(errors='replace'))
 for m in re.finditer(r'\b(warp_dbg|pr_info|pr_err|printk|MTWF_DBG|MTWF_LOG|osal_dbg_print|osal_info_print|osal_err_print)\s*\(',s):
  args=arguments(s,m.end())
  idx=1 if m[1]=='warp_dbg' else (4 if m[1]=='MTWF_DBG' else 0)
  if m[1]=='MTWF_LOG':
   if len(args)!=4 or not args[3].startswith('('):continue
   args=arguments(args[3],1);idx=0
  if len(args)<=idx:continue
  fmt=args[idx]
  # printk severity prefix is not a format argument.
  fmt=re.sub(r'^KERN_\w+\s*','',fmt)
  if not re.fullmatch(r'(?:"(?:\\.|[^"\\])*"\s*)+',fmt):continue
  try:f=''.join(ast.literal_eval(t) for t in re.findall(r'"(?:\\.|[^"\\])*"',fmt))
  except Exception:continue
  tokens=re.findall(r'%(?:%|[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hlztjL])?[diuoxXfFeEgGaAcspn])',f)
  expected=sum(0 if t=='%%' else 1+t.count('*') for t in tokens)
  actual=sum(6 if re.match(r'^PRINT_MAC\s*\(', a) else (4 if re.match(r'^NIPQUAD\s*\(', a) else 1) for a in args[idx+1:]);checked+=1
  if expected!=actual:findings.append((str(p.relative_to(root)),s.count('\n',0,m.start())+1,expected,actual,f))
print('Checked constant-format calls:',checked)
for x in findings:print(x)
print('Argument-count candidates (conditional code not evaluated):',len(findings))
