# 静态扫描：目标测试文件（base + test_patch 新增段）里的工具链标记 / 网络 / 家目录缓存线索
import json,os,re,subprocess
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/conan'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_conan/mat'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/ASSIGNMENT.json'))
def show(c,p):
    r=subprocess.run(['git','-C',R,'show',f'{c}:{p}'],capture_output=True,text=True)
    return r.stdout if r.returncode==0 else None
PATS={'tool_mark':r'@pytest\.mark\.tool',
      'skipif':r'@pytest\.mark\.skipif',
      'conancenter':r'conancenter|center\.conan\.io|center2?\.conan',
      'http':r'https?://(?!www\.w3|schemas|localhost|127\.0\.0\.1)',
      'requests_net':r'\brequests\.(get|post|put)\b|urlopen|urlretrieve',
      'home_cache':r'expanduser|\bHOME\b|\.conan2?\b|CONAN_HOME|CONAN_USER_HOME',
      'subprocess':r'subprocess\.|os\.system|check_output',
      'which':r'\bwhich\(',
      'docker':r'\bdocker\b'}
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    base=g['base_commit']; tp=g['test_patch']
    files=sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', tp, re.M)))
    added='\n'.join(l[1:] for l in tp.split('\n') if l.startswith('+') and not l.startswith('+++'))
    rec={'files':{},'test_patch_added':{}}
    for f in files:
        src=show(base,f)
        if src is None: rec['files'][f]='MISSING_AT_BASE'; continue
        hits={}
        for name,pat in PATS.items():
            m=[(i+1,l.strip()) for i,l in enumerate(src.split('\n')) if re.search(pat,l)]
            if m: hits[name]=m[:8]
        rec['files'][f]={'lines':len(src.split('\n')),'hits':hits}
    for name,pat in PATS.items():
        m=[l.strip() for l in added.split('\n') if re.search(pat,l)]
        if m: rec['test_patch_added'][name]=m[:8]
    out[tid]=rec
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_conan/envscan.json','w'),ensure_ascii=False,indent=1)
for tid,rec in out.items():
    print(f'### {tid}')
    for f,v in rec['files'].items():
        if v=='MISSING_AT_BASE': print('   ',f,'MISSING_AT_BASE'); continue
        print(f"    {f} ({v['lines']} lines) hits={ {k:len(vv) for k,vv in v['hits'].items()} }")
        for k,vv in v['hits'].items():
            if k in ('tool_mark','conancenter','http','requests_net','docker'):
                for ln,txt in vv: print(f'        [{k}] L{ln}: {txt[:110]}')
    if rec['test_patch_added']: print('    TEST_PATCH_ADDED:', {k:len(v) for k,v in rec['test_patch_added'].items()})
