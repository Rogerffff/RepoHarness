"""读取35个DVC镜像的已装元数据与依赖满足情况；不安装、不评分。"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import time

ROOT=Path('/work/env_recipe_repair_20260919/dvc_install_v1')
SCRIPT=r'''
import importlib.metadata as m,json
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.markers import default_environment
pk={canonicalize_name(d.metadata['Name']):d.version for d in m.distributions() if d.metadata['Name']}
raw=m.requires('dvc') or []
extras={'','tests','all','testing'}
checked=[]
for text in raw:
 r=Requirement(text);env=default_environment()
 selected=not r.marker or any(r.marker.evaluate(dict(env,extra=x)) for x in extras)
 if not selected:continue
 key=canonicalize_name(r.name);v=pk.get(key)
 if key=='dvc':continue
 checked.append({'requirement':text,'installed':v,'satisfied':v is not None and v in r.specifier})
print(json.dumps({'dvc_version':m.version('dvc'),'requirements':raw,'checked':checked,'unmet':[r for r in checked if not r['satisfied']]}))
'''


def case(item):
    iid=item['instance_id'];name='rh2-er19-dvc-meta-'+iid
    try:
        r=subprocess.run(['docker','run','--rm','--init','--name',name,'--network','none','--cpus','1','--memory','1g',
                          item['image_id'],'/opt/miniconda3/envs/testbed/bin/python','-I','-c',SCRIPT],
                         text=True,capture_output=True,timeout=120)
        result={'task':iid,'image_id':item['image_id'],'rc':r.returncode,'stderr':r.stderr,
                'facts':json.loads(r.stdout) if r.returncode==0 else r.stdout,'at':time.time()}
        (ROOT/'metadata'/(iid+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(iid,'unmet',len(result['facts'].get('unmet',[])) if isinstance(result['facts'],dict) else 'error',flush=True)
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__=='__main__':
    (ROOT/'metadata').mkdir(exist_ok=True)
    plans=json.loads((ROOT/'plan.json').read_text())
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(case,plans))
    (ROOT/'metadata_done.json').write_text(json.dumps({'at':time.time(),'tasks':len(plans)})+'\n')
