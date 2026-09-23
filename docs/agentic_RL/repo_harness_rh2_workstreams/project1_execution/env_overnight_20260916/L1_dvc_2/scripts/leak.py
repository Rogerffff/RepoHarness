import json,re
M='runs/env_overnight_20260916/L1_dvc_2/mat'
B='docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
ASG=json.load(open(f'{B}/L1_dvc_2/ASSIGNMENT.json'))
def norm(s): return re.sub(r'\s+','',s)
URL=re.compile(r'(github\.com/\S+|https?://\S+)')
for tid in ASG['tasks']:
    pub=json.load(open(f'{M}/{tid}/public.json')); val=json.load(open(f'{M}/{tid}/validation.json'))
    raw=json.load(open(f'{M}/{tid}/raw.json'))
    ps=pub['problem_statement']; nps=norm(ps)
    hints=raw.get('hints_text') or ''
    added=[l[1:].strip() for l in (val.get('golden_patch') or '').split('\n')
           if l.startswith('+') and not l.startswith('+++')]
    added=[a for a in added if len(a.strip())>=12 and not a.strip().startswith('#')]
    hit=[a for a in added if norm(a) and norm(a) in nps]
    hint_hit=[a for a in added if norm(a) and norm(a) in norm(hints)]
    urls_ps=sorted(set(URL.findall(ps)))
    urls_h=sorted(set(URL.findall(hints)))
    # duplicated problem statement halves
    n=len(ps); dup = n>40 and n%2==0 and ps[:n//2]==ps[n//2:]
    print(f'{tid} gold_added={len(added)} ps_match={len(hit)} hints_match={len(hint_hit)} dup_ps={dup}')
    for e in hit[:4]: print('    PS-LEAK:',e[:120])
    for e in hint_hit[:4]: print('    HINT-LEAK:',e[:120])
    if urls_ps: print('    ps_urls:',urls_ps[:6])
    if urls_h: print('    hint_urls:',urls_h[:6])
