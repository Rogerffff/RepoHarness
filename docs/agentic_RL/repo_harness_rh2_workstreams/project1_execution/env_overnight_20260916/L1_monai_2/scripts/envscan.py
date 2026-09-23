"""对每题的 test_patch 目标测试文件做静态环境依赖扫描（下载/权重/数据/GPU/多进程/大张量）。"""
import json,os,re,subprocess,sys
PKG='L1_monai_2'
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/MONAI'
M=f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/mat'
ASG=json.load(open(f'${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}/ASSIGNMENT.json'))
PATTERNS=[
 ('DOWNLOAD', r'download_url|download_and_extract|testing_data_config|url=|\.tar\.gz|\.zip"|huggingface|torch\.hub|load_state_dict_from_url|hub_dir|model_zoo'),
 ('NET',      r'requests\.|urlopen|urlretrieve|http://(?!www\.apache)|https://(?!www\.apache)'),
 ('GPU',      r'cuda|skip_if_no_cuda|device="cuda"|DEVICES'),
 ('MP',       r'DataLoader|num_workers|multiprocessing|spawn|torch\.distributed|DistCall|dist\.'),
 ('SKIPDEC',  r'@skip_if|@unittest\.skip|SkipIfBeforePyTorchVersion|SkipIfNoModule|skip_if_quick|optional_import'),
 ('NDARRAYS', r'TEST_NDARRAYS\w*|TEST_DEVICES|TEST_TORCH'),
 ('BIGTENSOR',r'\b\d{3,}\s*,\s*\d{3,}\b|ones\(\(\s*\d{2,}'),
 ('TMPFILE',  r'tempfile|TemporaryDirectory|subprocess'),
]
def show(commit,path):
    p=subprocess.run(['git','-C',R,'show',f'{commit}:{path}'],capture_output=True,text=True)
    return p.stdout if p.returncode==0 else None
tids=sys.argv[1:] or ASG['tasks']
for tid in tids:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    base=g['base_commit']
    tps=sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', g['test_patch'], re.M)))
    print(f'##### {tid} base={base[:8]}')
    for path in tps:
        src=show(base,path)
        if src is None: print(f'  {path}: FILE_MISSING_AT_BASE'); continue
        lines=src.split('\n')
        print(f'  --- {path} ({len(lines)} 行)')
        for name,pat in PATTERNS:
            hits=[(i+1,l.strip()[:120]) for i,l in enumerate(lines) if re.search(pat,l)]
            if hits:
                print(f'     [{name}] {len(hits)} 处: '+ '; '.join(f'{n}:{t}' for n,t in hits[:4]))
