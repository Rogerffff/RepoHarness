"""DVC真实安装与兼容修订；已验证代表4778复用，剩余34题逐一评分。"""
from pathlib import Path
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import time
import zipfile

ROOT=Path(os.environ.get('RH2_DVC_REPAIR_ROOT','/work/env_recipe_repair_20260919/dvc_install_v1'))
OLD=Path('/work/full216_20260919')


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def backport(wheel):
    with zipfile.ZipFile(wheel) as z:
        data={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    old='networkx-2.3.dist-info/';new='networkx-2.3+rh2.1.dist-info/'
    dag='networkx/algorithms/dag.py'
    assert data[dag].count(b'from fractions import gcd')==1
    # 保留Python3.8 fractions.gcd的符号与非整数Euclid路径；不能直接换math.gcd。
    compat = b"""from math import gcd as _math_gcd


def gcd(a, b):
    if type(a) is int is type(b):
        return -_math_gcd(a, b) if (b or a) < 0 else _math_gcd(a, b)
    while b:
        a, b = b, a % b
    return a
"""
    data[dag]=data[dag].replace(b'from fractions import gcd', compat)
    meta=data.pop(old+'METADATA');assert b'Version: 2.3\n' in meta
    data[new+'METADATA']=meta.replace(b'Version: 2.3\n',b'Version: 2.3+rh2.1\n',1)
    data={n.replace(old,new):value for n,value in data.items() if not n.endswith('/RECORD')}
    record=io.StringIO();writer=csv.writer(record,lineterminator='\n')
    for name,value in sorted(data.items()):
        writer.writerow([name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode().rstrip('='),len(value)])
    writer.writerow([new+'RECORD','','']);data[new+'RECORD']=record.getvalue().encode()
    dest=ROOT/'assets/cache/networkx==2.3+rh2.1';dest.mkdir(parents=True)
    out=dest/'networkx-2.3+rh2.1-py2.py3-none-any.whl'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,value in data.items():z.writestr(name,value)
    save(ROOT/'networkx_backport.json',{'upstream_wheel':wheel.name,'upstream_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
                                      'revised_wheel':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
                                      'source_edit':{'path':dag,'before':'from fractions import gcd','after':compat.decode(),'return_semantics':'Python3.8 fractions.gcd incl negative sign; no deprecation warning emission'},
                                      'metadata_version':'2.3+rh2.1','module_version':'2.3 (upstream constant retained)',
                                      'scope':'dependency backport; no DVC source or test edit'})


def main():
    plans=json.loads((ROOT/'repair_plan.json').read_text())
    pins=sorted({pin for p in plans for pin in p['pins'] if pin!='networkx==2.3+rh2.1'}|{'networkx==2.3'})
    for pin in pins:
        cache=ROOT/'assets/cache'/pin;cache.mkdir(parents=True,exist_ok=False)
        with (cache/'download.log').open('w') as f:
            if pin.startswith('PyYAML=='):
                base='xingyaoww/sweb.eval.x86_64.iterative_s_dvc-1661:latest'
                name='rh2-er19-pyyaml-'+pin.split('==')[1].replace('.','-')
                try:
                    subprocess.run(['docker','run','--rm','--init','--name',name,'--cpus','2','--memory','2g',
                                    '-v',str(cache)+':/cache',base,'/opt/miniconda3/envs/testbed/bin/python','-I','-m','pip',
                                    'wheel','--index-url','https://pypi.org/simple','--no-deps','--no-build-isolation','-w','/cache',pin],
                                   stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
                finally:
                    subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            elif pin=='networkx==2.3':
                source=cache/'source';source.mkdir()
                subprocess.run(['/usr/bin/python3','-m','pip','download','--index-url','https://pypi.org/simple','--no-deps',
                                '--no-binary=:all:','-d',str(source),pin],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
                archive=next(source.glob('networkx*'))
                save(cache/'source.json',{'name':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})
                subprocess.run(['/usr/bin/python3','-m','pip','wheel','--no-deps','-w',str(cache),str(archive)],
                               stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
            elif pin.startswith('pygit2=='):
                # 此批使用Python3.9，宿主Python3.10下载的二进制wheel不可用于题目镜像。
                target=next(item['image'] for item in plans if pin in item['pins'])
                subprocess.run(['docker','run','--rm','--init','--memory','2g','--cpus','1',
                                '-v',str(cache)+':/cache',target,'/opt/miniconda3/envs/testbed/bin/python','-I','-m','pip',
                                'download','--index-url','https://pypi.org/simple','--no-deps','--only-binary=:all:',
                                '-d','/cache',pin],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
            else:
                subprocess.run(['/usr/bin/python3','-m','pip','download','--index-url','https://pypi.org/simple','--no-deps',
                                '--only-binary=:all:','-d',str(cache),pin],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
    backport(next((ROOT/'assets/cache/networkx==2.3').glob('*.whl')))
    save(ROOT/'assets_manifest.json',[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
                                     for p in sorted((ROOT/'assets/cache').rglob('*.whl'))])
    while not (ROOT.parent/'pydantic_v1/done.json').exists():
        if (ROOT.parent/'pydantic_v1/failed.json').exists():raise RuntimeError('先诊断前批停止')
        save(ROOT/'status.json',{'state':'waiting_for_grading_slot','at':time.time()});time.sleep(20)
    code=ROOT/'code/rh2'
    shutil.copytree('/work/claude_chainfix_20260919/code/rh2',code,ignore=shutil.ignore_patterns('.venv','__pycache__','*.pyc'))
    save(ROOT/'code_manifest.json',[{'path':str(p.relative_to(code)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                    for p in sorted(code.rglob('*.py'))])
    for item in plans:
        iid=item['instance_id'];dest=ROOT/'tasks'/iid;dest.mkdir(parents=True,exist_ok=False)
        context=dest/'context';wheels=context/'wheels';wheels.mkdir(parents=True)
        for pin in item['pins']:
            for source in (ROOT/'assets/cache'/pin).glob('*.whl'):os.link(source,wheels/source.name)
        base=json.loads(subprocess.check_output(['docker','image','inspect',item['image']],text=True))[0];assert base['Id']==item['image_id']
        recipe='ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/build-wheels/\nENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n'
        (context/'Dockerfile').write_text(recipe);tag='rh2-envrepair/dvc-install-v1-'+iid.lower()+':20260919'
        with (dest/'build.log').open('w') as f:
            subprocess.run(['docker','build','--pull=false','--build-arg','BASE_IMAGE='+base['RepoDigests'][0],'-t',tag,str(context)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
        image=json.loads(subprocess.check_output(['docker','image','inspect',tag],text=True))[0];assert image['RootFS']['Layers'][:-1]==base['RootFS']['Layers']
        save(dest/'image.json',{'base_id':base['Id'],'image_id':image['Id'],'recipe':recipe})
        for kind in ['noop','gold']:
            run=dest/kind;run.mkdir()
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),'--code-root',str(code),
                 '--recipe',str(ROOT/'recipes'/(iid+'.json')),'--audit-dir',str(run/'recipe')]
            if iid=='iterative__dvc-4185':cmd+=['--bindings',str(ROOT/'reference_bindings_v1.json')]
            cmd+=['--','run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                  '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),'--derived-image',image['Id'],
                  '--derived-image-recipe','dvc-install-v1:'+iid,'--eval-log-dir',str(run/'eval_logs'),
                  '--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            save(ROOT/'status.json',{'state':'grading','task':iid,'kind':kind,'command':cmd,'at':time.time()})
            with (run/'driver.log').open('w') as f:
                subprocess.run(cmd,cwd=code,env=dict(os.environ,MILES_RH2_RUN_ID='er19-dv1-'+iid+'-'+kind),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=4800)
            row=json.loads((run/'ledger.jsonl').read_text());assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
            # 相同配方代表若安装仍失败，先解释，不机械扩散同一失败。
            if iid in ['iterative__dvc-1661','iterative__dvc-3794']:
                assert row['install']['install_rc_last_command']==0,'代表安装仍失败：'+iid
        save(dest/'done.json',{'at':time.time(),'meaning':'execution only; installation/full tests audit required'})
    save(ROOT/'done.json',{'at':time.time(),'attempts':2*len(plans)})


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
