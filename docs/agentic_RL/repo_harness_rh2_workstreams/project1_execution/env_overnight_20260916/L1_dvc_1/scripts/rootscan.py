# 216 题：gold 侧实跑失败里有多少能归因到"以 root 执行"（os.access / 权限位语义）
import json,os,glob,re,collections
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
S2='docs/agentic_RL/repo_harness_rh2_workstreams/s2'
G={}
for line in open(f'{S2}/ingest/grading_bundles_v2_v0.jsonl'):
    d=json.loads(line); G[d['instance_id']]=d
pat=re.compile(r'os\.access\([^)]*(W_OK|R_OK|X_OK)|assert.*os\.access|PermissionError|\bEACCES\b|st_mode.*0o[24]|chmod\(.*0o[04]')
hits=collections.defaultdict(list); nlog=0
for p in sorted(glob.glob(f'{L}/*/gold/offline/a1/test_output.txt')):
    tid=p.split('/')[-5]; nlog+=1
    sm_p=f'{L}/{tid}/gold/offline/a1/status_map.json'
    if not os.path.exists(sm_p): continue
    sm=json.load(open(sm_p))
    failed=[k for k,v in sm.items() if v in ('FAILED','ERROR') and '::' in k]
    if not failed: continue
    txt=open(p,errors='replace').read()
    # 在失败块里找 os.access 断言
    for blk in re.split(r'\n_{10,} (.+?) _{10,}\n', txt):
        pass
    n=len(re.findall(r'^>\s+(?:self\.)?assert\w*\(?os\.access\(', txt, re.M))
    n2=len(re.findall(r'os\.access\(', txt))
    if n: hits[tid]=(n,len(failed),n2)
print(f'有 gold 日志的题: {nlog}')
print(f'失败断言里直接出现 `> assert... os.access(` 的题: {len(hits)}')
for t,(n,f,n2) in sorted(hits.items(), key=lambda r:-r[1][0]):
    print(f'  {t:34s} 失败断言中的 os.access 行={n:3d}  该题 gold 失败用例数={f:3d}')
