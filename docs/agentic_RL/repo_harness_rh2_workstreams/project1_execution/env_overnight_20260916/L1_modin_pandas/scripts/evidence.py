# 生成三份佐证 JSON：截断/转义不一致 ID、跨题污染对、test_patch 新建文件
import json,os,re,subprocess,collections
PKG='L1_modin_pandas'
BASE=f'docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}'
M=f'runs/env_overnight_20260916/{PKG}/mat'
REPOS='runs/env_overnight_20260916/repos'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open(f'{BASE}/ASSIGNMENT.json'))['tasks']
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S.*)$')

# ---- 1. 截断 ID 与转义不一致 ----
trunc={}
for tid in ASG:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    consts={'f2p':g['fail_to_pass'],'p2p':g['pass_to_pass']}
    p=f'{L}/{tid}/gold/offline/a1/test_output.txt'
    runtime=collections.defaultdict(set)
    if os.path.exists(p):
        for line in open(p,errors='replace'):
            m=pat.match(line.rstrip('\n'))
            if m: runtime[m.group(2).split()[0]].add(m.group(2).strip())
    rec={'truncated_constants':{},'escape_mismatch':[],'collapsed_keys':{}}
    for kind,ids in consts.items():
        for x in ids:
            if x.count('[')!=x.count(']'):
                rec['truncated_constants'].setdefault(kind,[]).append(x)
            if x not in runtime:
                # 尝试双反斜杠形态
                cand=[r for r in runtime if r.replace('\\\\','\\')==x]
                rec['escape_mismatch'].append({'kind':kind,'constant':x,
                    'runtime_candidates_after_unescape':sorted(cand)[:3],
                    'explain':'常量单反斜杠 vs 运行时双反斜杠' if cand else '运行时无同名键'})
        for x in ids:
            if x in runtime and len(runtime[x])>1:
                rec['collapsed_keys'][x]={'n_runtime_ids':len(runtime[x]),'sample':sorted(runtime[x])[:2],'kind':kind}
    rec['summary']={'n_trunc_f2p':len(rec['truncated_constants'].get('f2p',[])),
                    'n_trunc_p2p':len(rec['truncated_constants'].get('p2p',[])),
                    'n_escape_mismatch':len(rec['escape_mismatch']),
                    'n_collapsed_keys':len(rec['collapsed_keys']),
                    'hidden_extra_runtime_ids':sum(v['n_runtime_ids']-1 for v in rec['collapsed_keys'].values())}
    # 只保留前 40 条截断样例，避免文件过大
    for k in list(rec['truncated_constants']):
        rec['truncated_constants'][k]=rec['truncated_constants'][k][:40]
    trunc[tid]=rec
json.dump(trunc,open(f'{BASE}/truncated_test_ids.json','w'),ensure_ascii=False,indent=1)
print('truncated_test_ids.json 写出；摘要：')
for t,r in trunc.items(): print(' ',t,r['summary'])

# ---- 2. 跨题污染：某题 gold 是否已存在于同仓库另一题的 base ----
def repo_of(tid): return 'pandas' if 'pandas-dev' in tid else 'modin'
contam=[]
wt=f'runs/env_overnight_20260916/{PKG}/wt'
for a in ASG:
    va=json.load(open(f'{M}/{a}/validation.json'))
    patch=va.get('golden_patch') or ''
    if not patch: continue
    for b in ASG:
        if a==b or repo_of(a)!=repo_of(b): continue
        gb=json.load(open(f'{M}/{b}/grading.json'))
        # 用 git apply -R --check 判断 a 的 gold 是否已在 b 的 base 里
        d=f'{wt}/contam_{b}'
        if not os.path.isdir(d):
            subprocess.run(['git','-C',f'{REPOS}/{repo_of(b)}','worktree','add','--detach',d,gb['base_commit']],
                           capture_output=True,text=True)
        pr=subprocess.run(['git','-C',d,'apply','-R','--check','-'],input=patch,capture_output=True,text=True)
        contam.append({'gold_of':a,'base_of':b,'reverse_apply_ok':pr.returncode==0,'stderr':pr.stderr.strip()[:200]})
json.dump(contam,open(f'{BASE}/contamination_pairs.json','w'),ensure_ascii=False,indent=1)
hit=[c for c in contam if c['reverse_apply_ok']]
print(f'contamination_pairs.json 写出：检查 {len(contam)} 对，命中 {len(hit)} 对')
for c in hit: print('  HIT',c['gold_of'],'->',c['base_of'])

# ---- 3. test_patch 新建/删除文件 ----
newf={}
for tid in ASG:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    tp=g['test_patch']
    created=re.findall(r'^--- /dev/null\n\+\+\+ b/(\S+)', tp, re.M)
    deleted=re.findall(r'^--- a/(\S+)\n\+\+\+ /dev/null', tp, re.M)
    paths=sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', tp, re.M)))
    newf[tid]={'test_patch_paths':paths,'created':created,'deleted':deleted,
               'checkout_pathspec_would_cover_created':len(created)==0}
json.dump(newf,open(f'{BASE}/test_patch_new_files.json','w'),ensure_ascii=False,indent=1)
print('test_patch_new_files.json 写出：新建文件的题 =',[t for t,v in newf.items() if v['created']] or '无')
