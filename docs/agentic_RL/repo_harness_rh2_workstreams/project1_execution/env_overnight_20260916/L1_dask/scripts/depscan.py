import json,os,re,subprocess,sys,collections
R='runs/env_overnight_20260916/repos/dask'
M='runs/env_overnight_20260916/L1_dask/mat'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/ASSIGNMENT.json'))
def show(c,p):
    r=subprocess.run(['git','-C',R,'show',f'{c}:{p}'],capture_output=True,text=True)
    return r.stdout if r.returncode==0 else None
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    base=g['base_commit']
    ids=g['fail_to_pass']+g['pass_to_pass']
    files=sorted({x.split('::')[0] for x in ids})
    print(f'==== {tid} ver={g.get("version")} files={files}')
    for f in files:
        src=show(base,f)
        if src is None: print(f'   {f}: NOT IN BASE'); continue
        lines=src.split('\n')
        mod=[ (i+1,l.strip()) for i,l in enumerate(lines[:80]) if 'importorskip' in l or l.startswith('pytestmark')]
        for ln,l in mod: print(f'   [modlevel] {f}:{ln}: {l}')
        inline=[(i+1,l.strip()) for i,l in enumerate(lines) if 'importorskip' in l and i>=80]
        print(f'   inline importorskip count={len(inline)}')
        for ln,l in inline[:6]: print(f'      {f}:{ln}: {l}')
        net=[(i+1,l.strip()) for i,l in enumerate(lines) if 'mark.network' in l or 'mark.slow' in l or 'mark.gpu' in l]
        print(f'   marks(network/slow/gpu) count={len(net)}')
        for ln,l in net[:6]: print(f'      {f}:{ln}: {l}')
        urls=[(i+1,l.strip()) for i,l in enumerate(lines) if re.search(r'https?://|s3://|requests\.get|boto3|moto|s3fs|gcsfs|\bhdfs\b',l)]
        print(f'   net-ish refs count={len(urls)}')
        for ln,l in urls[:5]: print(f'      {f}:{ln}: {l[:120]}')
