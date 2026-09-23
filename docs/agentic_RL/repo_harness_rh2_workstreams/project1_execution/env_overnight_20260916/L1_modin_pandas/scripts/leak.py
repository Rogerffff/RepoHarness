# 改编自 L1_moto_1/scripts/leak.py：题面/hints 是否泄漏 gold 代码或上游 PR/commit 指针
import json,re
PKG='L1_modin_pandas'
M=f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/mat'
ASG=json.load(open(f'${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}/ASSIGNMENT.json'))
def norm(s): return re.sub(r'\s+','',s or '')
PTR=re.compile(r'(github\.com/\S+/(pull|commit|issues)/\d+|#\d{4,6}|\bGH ?\d{4,6}\b|whatsnew|xref\s+#?\d+)',re.I)
out={}
for tid in ASG['tasks']:
    pub=json.load(open(f'{M}/{tid}/public.json')); val=json.load(open(f'{M}/{tid}/validation.json'))
    raw=json.load(open(f'{M}/{tid}/raw.json'))
    ps=pub['problem_statement']; hints=raw.get('hints_text') or ''
    n=norm(ps)
    added=[l[1:].strip() for l in (val.get('golden_patch') or '').split('\n') if l.startswith('+') and not l.startswith('+++')]
    added=[a for a in added if len(a.strip())>=12 and not a.strip().startswith('#')]
    hit=[a for a in added if norm(a) and norm(a) in n]
    hadded=[a for a in added if norm(a) and norm(a) in norm(hints)]
    out[tid]={'gold_added_lines':len(added),'matched_in_statement':hit,'matched_in_hints':hadded,
              'statement_ptrs':sorted(set(m[0] for m in PTR.findall(ps))),
              'hints_ptrs':sorted(set(m[0] for m in PTR.findall(hints))),
              'hints_chars':len(hints),'public_hints':pub.get('public_hints'),
              'statement_has_image':bool(re.search(r'!\[|\.png|\.jpg|user-images\.githubusercontent',ps)),
              'statement_has_url':sorted(set(re.findall(r'https?://\S+',ps)))[:6]}
    o=out[tid]
    print(f"{tid}: gold_added={o['gold_added_lines']} leak_stmt={len(hit)} leak_hints={len(hadded)} "
          f"stmt_ptrs={o['statement_ptrs'][:3]} hints_chars={o['hints_chars']} img={o['statement_has_image']} urls={len(o['statement_has_url'])}")
    for e in hit[:3]: print('     STMT-LEAK:',e[:110])
    for e in hadded[:3]: print('     HINTS-LEAK:',e[:110])
json.dump(out,open(f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/leak.json','w'),ensure_ascii=False,indent=1)
