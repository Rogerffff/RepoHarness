# 对已下载的官网脚本做词法提取与 JSON5 解析，不执行 JavaScript。
import sys,re,json
from pathlib import Path
sys.path.insert(0,'/tmp/cognition-json5')
import json5
root=Path(__file__).resolve().parent.parent
sources={'frontier-code':'af0a88ae1fd72ef7.js','frontier-code-1.1':'1f3ab6ff4a7f8b56.js','swe-1-7':'03a401431ef6f66c.js','swe-2':'dc6fe6c6211d50b6.js'}
for topic,name in sources.items():
 s=(root/'web_scripts'/name).read_text();out=root/topic/'embedded';out.mkdir(exist_ok=True);manifest=[]
 for match in re.finditer(r'(?:let |,)([A-Za-z_$][\w$]*)=\[\{',s):
  start=match.end()-2;i=start;depth=0;quote=None;escape=False
  while i<len(s):
   c=s[i]
   if quote:
    if escape:escape=False
    elif c=='\\':escape=True
    elif c==quote:quote=None
   else:
    if c in '\"\'`':quote=c
    elif c=='[':depth+=1
    elif c==']':
     depth-=1
     if depth==0:break
   i+=1
  raw=s[start:i+1]
  if len(raw)<100:continue
  fn=f'array-{start}';(out/(fn+'.js.txt')).write_text(raw);record={'variable':match.group(1),'source_script':'../../web_scripts/'+name,'start_offset':start,'end_offset':i+1,'raw':fn+'.js.txt'}
  # 保留字符串原样，只转换字符串外的压缩布尔常量。模板字符串含插值时拒绝解析。
  chunks=[];k=0
  while k<len(raw):
   if raw[k] in '\"\'`':
    q=raw[k];j=k+1;esc=False
    while j<len(raw):
     if esc:esc=False
     elif raw[j]=='\\':esc=True
     elif raw[j]==q:break
     j+=1
    piece=raw[k:j+1]
    if q=='`' and '${' not in piece:
     # 静态模板里的换行与反引号；本批未使用模板插值。
     piece=json.dumps(piece[1:-1].replace('\\`','`'),ensure_ascii=False)
    chunks.append(piece);k=j+1
   elif raw[k:k+2] in ['!0','!1']:chunks.append('true' if raw[k+1]=='0' else 'false');k+=2
   else:chunks.append(raw[k]);k+=1
  try:
   obj=json5.loads(''.join(chunks));(out/(fn+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2));record['json']=fn+'.json';record['records']=len(obj);record['first_keys']=list(obj[0]) if isinstance(obj[0],dict) else []
  except Exception as e:record['parse_error']=str(e)[:180]
  manifest.append(record)
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(topic,[(x.get('records'),x.get('first_keys'),x.get('parse_error')) for x in manifest])
