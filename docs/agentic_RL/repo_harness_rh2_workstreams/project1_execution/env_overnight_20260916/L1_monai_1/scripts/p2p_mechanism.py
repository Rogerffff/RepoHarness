"""验证 MONAI 的 F2P/P2P 生成机制：
猜想——评分命令是「跑 test_patch 触碰的整份测试文件」，名单则是
  F2P = {在 gold 通过、在 base(empty) 不通过的用例}
  P2P = {在 gold 与 base 都通过的用例}
即完全由「整文件跑两遍取差集」得到，没有 -k 子串过选那一层（mypy 才有）。
本脚本用离线 stage1 的 gold/empty status_map 重算这两个集合，与 grading bundle 对拍。
注意：stage1 是**离线**环境，与 SWE-Gym 原始构数据集时的环境不同，
所以差异本身就是「环境漂移把哪些用例挤出了名单」的证据。"""
import json,os,collections
ROOT='${REPO_ROOT}'
S=f'{ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
L=f'{ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
tb=json.load(open(f'{ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/tasks_by_repo.json'))
want=set(tb['Project-MONAI/MONAI'])
G={}
for line in open(f'{S}/ingest/grading_bundles_v2_v0.jsonl'):
    r=json.loads(line)
    if r['instance_id'] in want: G[r['instance_id']]=r
for tid in sorted(G):
    g=G[tid]; f2p=set(g['fail_to_pass']); p2p=set(g['pass_to_pass'])
    pg=f'{L}/{tid}/gold/offline/a1/status_map.json'; pe=f'{L}/{tid}/empty/offline/a1/status_map.json'
    if not (os.path.exists(pg) and os.path.exists(pe)): print(f'{tid}: NO_LOG'); continue
    sg=json.load(open(pg)); se=json.load(open(pe))
    real=lambda d:{k:v for k,v in d.items() if '::' in k}
    sg=real(sg); se=real(se)
    predF={t for t in sg if sg[t]=='PASSED' and se.get(t)!='PASSED'}
    predP={t for t in sg if sg[t]=='PASSED' and se.get(t)=='PASSED'}
    both_bad={t for t in sg if sg[t]!='PASSED' and se.get(t)!='PASSED'}
    print(f'### {tid}')
    print(f'   实际 F2P={len(f2p)} P2P={len(p2p)}   离线重算 F2P={len(predF)} P2P={len(predP)}  两侧皆非PASSED={len(both_bad)}')
    if predF!=f2p:
        print(f'   F2P 差异: 只在重算里={sorted(predF-f2p)[:4]}  只在名单里={sorted(f2p-predF)[:4]}')
    if predP!=p2p:
        print(f'   P2P 差异: 只在重算里={sorted(predP-p2p)[:4]}  只在名单里={sorted(p2p-predP)[:6]}')
    if predF==f2p and predP==p2p: print('   完全一致')
