"""扫描 stage1 全部题目的 status_map.json，找出键不像 pytest nodeid 的伪条目。
机制：rh2/src/repoharness2/envpack/swegym_parsers.py 的 parse_log_pytest 对
任何以 FAILED/PASSED/SKIPPED/ERROR/XFAIL 开头的行都记一条
`status_map[line.split()[1]] = line.split()[0]`，不校验第二个 token 是不是 nodeid。
于是被测程序自己打印的日志（dvc 的 `ERROR: Could not ...`）、pytest 的 SKIPPED 摘要行
（`SKIPPED [1] file:line: reason`，不含 nodeid）都会进 status_map。"""
import json,glob,os,collections
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
tot=collections.Counter(); ntask=0; nbad=0
for d in sorted(glob.glob(f'{L}/*')):
    tid=os.path.basename(d)
    p=f'{d}/gold/offline/a1/status_map.json'
    if not os.path.exists(p): continue
    ntask+=1
    sm=json.load(open(p))
    bogus={t:s for t,s in sm.items() if '::' not in t}
    if bogus:
        nbad+=1
        print(f'{tid:45s} {bogus}')
        for t,s in bogus.items(): tot[(t,s)]+=1
print(f'--- {nbad}/{ntask} 个有 gold 日志的题产生了伪条目 ---')
for k,v in tot.most_common(20): print(' ',k,v)
