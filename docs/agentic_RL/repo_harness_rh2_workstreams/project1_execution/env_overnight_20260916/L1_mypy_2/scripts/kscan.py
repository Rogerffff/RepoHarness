import json,subprocess,re,collections,os
R='runs/env_overnight_20260916/repos/mypy'
PKG='docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2'
PRE=json.load(open('runs/env_overnight_20260916/L1_mypy_2/prescan.json'))
ids=json.load(open(f'{PKG}/ASSIGNMENT.json'))['tasks']
cache={}
def cases_at(commit):
    if commit in cache: return cache[commit]
    p=subprocess.run(['git','-C',R,'grep','-n','-E','^\\[case ',commit,'--','test-data/unit/'],capture_output=True,text=True)
    m=collections.defaultdict(list)   # case name -> [(file,line)]
    for line in p.stdout.split('\n'):
        mm=re.match(r'^[0-9a-f]+:(test-data/unit/[^:]+):(\d+):\[case (\w+)',line)
        if mm: m[mm.group(3)].append((mm.group(1),int(mm.group(2))))
    cache[commit]=m
    return m
out={}
for tid in ids:
    r=PRE[tid]; base=r['base_commit']
    allc=cases_at(base)
    tp=set(r['test_patch_paths'])
    sel=[]
    seen=set()
    for x in r['f2p']+r['p2p']:
        name=x.split('::')[-1]
        if name in seen: continue
        seen.add(name); sel.append((x,name))
    rows=[]
    for x,name in sel:
        over=sorted(k for k in allc if name in k and k!=name)
        loc=allc.get(name,[])
        homes=sorted(set(f for f,_ in loc))
        # is the file hosting the case protected (in test_patch)?
        prot=[f in tp for f in homes]
        rows.append({'id':x,'case':name,'over_select':over,'home_files_in_base':homes,
                     'home_protected':prot,'dup_in_base':len(loc)>1})
    out[tid]={'rows':rows,'test_patch_paths':sorted(tp)}
json.dump(out,open('runs/env_overnight_20260916/L1_mypy_2/kscan.json','w'),ensure_ascii=False,indent=1)
for tid in ids:
    o=out[tid]; flags=[]
    for row in o['rows']:
        if row['over_select']: flags.append(f"OVER {row['case']} -> {row['over_select']}")
        if row['dup_in_base']: flags.append(f"DUPNAME {row['case']} -> {row['home_files_in_base']}")
        if row['home_files_in_base'] and not any(row['home_protected']):
            flags.append(f"UNPROT_HOME {row['case']} in {row['home_files_in_base']}")
        if not row['home_files_in_base']:
            flags.append(f"NEW(only via test_patch) {row['case']}")
    print(f'### {tid}')
    for f in flags: print('   ',f)
