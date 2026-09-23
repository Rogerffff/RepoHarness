# 本包新增：扫 F2P/P2P 所在测试文件在 base 上的可选依赖 skip / 网络 / 编译扩展线索
import json,os,re,subprocess
PKG='L1_modin_pandas'
M=f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/mat'
REPOS='${REPO_ROOT}/runs/env_overnight_20260916/repos'
ASG=json.load(open(f'${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}/ASSIGNMENT.json'))
PAT={
 'importorskip': re.compile(r'importorskip\(\s*["\']([\w\.\-]+)'),
 'skip_if_no': re.compile(r'skip_if_no\(\s*["\']([\w\.\-]+)'),
 'mark_network': re.compile(r'@pytest\.mark\.network'),
 'mark_single_cpu': re.compile(r'@pytest\.mark\.single_cpu'),
 'mark_slow': re.compile(r'@pytest\.mark\.slow'),
 'datapath': re.compile(r'\bdatapath\b'),
 'url': re.compile(r'https?://(?!www\.apache\.org|localhost|127\.0\.0\.1)[\w\.\-]+'),
 's3': re.compile(r's3_(base|resource|public_bucket|storage_options)|boto3|s3fs|moto'),
 'subprocess': re.compile(r'subprocess\.(Popen|run|check)'),
 'tmpfile_big': re.compile(r'10\*\*[6-9]|1_000_000|np\.random\.rand\(10\*\*'),
}
def show(repo,commit,path):
    p=subprocess.run(['git','-C',f'{REPOS}/{repo}','show',f'{commit}:{path}'],capture_output=True,text=True)
    return p.stdout if p.returncode==0 else None
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    repo='pandas' if 'pandas-dev' in tid else 'modin'
    base=g['base_commit']
    files=sorted({x.split('::')[0] for x in g['fail_to_pass']+g['pass_to_pass']})
    agg={}
    for f in files:
        src=show(repo,base,f)
        if src is None: agg.setdefault('FILE_MISSING',[]).append(f); continue
        for k,p in PAT.items():
            hits=p.findall(src)
            if hits:
                vals=sorted({h if isinstance(h,str) else h[0] for h in hits}) if k not in ('mark_network','mark_single_cpu','mark_slow','datapath','subprocess','tmpfile_big') else [str(len(hits))]
                agg.setdefault(k,{})[f]=vals[:12]
    out[tid]={'files':files,'signals':agg}
    print(f"### {tid} files={files}")
    for k,v in agg.items(): print(f"    {k}: {v}")
json.dump(out,open(f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/optdeps.json','w'),ensure_ascii=False,indent=1)
