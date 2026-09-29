"""按166镜像实测声明扩展mypy/Moto离线安装；仅COPY资产，宿主内核不变。"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import json
import os
import subprocess
import threading
import time

ROOT=Path('/work/env_recipe_repair_20260919/install_wave1')
OLD=Path('/work/full216_20260919')
STOP=threading.Event()


def capture(args):
    return subprocess.check_output(args,text=True,timeout=120)


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def case(plan):
    if STOP.is_set():
        return
    iid=plan['instance_id'];dest=ROOT/'tasks'/iid
    dest.mkdir(parents=True,exist_ok=False)
    try:
        context=ROOT/'assets'/'contexts'/iid
        (context/'wheels').mkdir(parents=True)
        for pkg,version in plan['pins'].items():
            files=list((ROOT/'assets'/'cache'/(pkg+'=='+version)).glob('*.whl'))
            assert len(files)==1,(pkg,version,files)
            os.link(files[0],context/'wheels'/files[0].name)
        recipe='ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/build-wheels/\nENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n'
        (context/'Dockerfile').write_text(recipe)
        base=json.loads(capture(['docker','image','inspect',plan['image']]))[0]
        assert base['Id']==plan['image_id']
        tag='rh2-envrepair/install-wave1-'+iid.lower()+':20260919'
        with (dest/'build.log').open('w') as log:
            subprocess.run(['docker','build','--pull=false','--force-rm','--build-arg','BASE_IMAGE='+base['RepoDigests'][0],
                            '-t',tag,str(context)],stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
        derived=json.loads(capture(['docker','image','inspect',tag]))[0]
        assert derived['RootFS']['Layers'][:-1]==base['RootFS']['Layers']
        save(dest/'image.json',{'base_id':base['Id'],'base_digest':base['RepoDigests'][0],'image_id':derived['Id'],
                               'recipe':recipe,'pins':plan['pins'],'base_layers_preserved':True})
        kinds=['noop'] if plan['action'].endswith('material_repair') else ['noop','gold']
        for kind in kinds:
            if STOP.is_set():
                return
            run=dest/kind;run.mkdir()
            py=str(OLD/'code/rh2/.venv/bin/python')
            command=[py,str(OLD/'code/rh2/scripts/replay_grade.py'),'run',
                     '--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),
                     '--task-ids',iid,'--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                     '--derived-image',derived['Id'],'--derived-image-recipe','install-wave1:'+iid,
                     '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            save(dest/'status.json',{'kind':kind,'command':command,'at':time.time()})
            with (run/'driver.log').open('w') as log:
                subprocess.run(command,cwd=OLD/'code/rh2',env=dict(os.environ,MILES_RH2_RUN_ID='er19-iw1-'+iid+'-'+kind),
                               check=True,timeout=4800,stdout=log,stderr=subprocess.STDOUT)
            row=json.loads((run/'ledger.jsonl').read_text())
            assert row['cleanup']['removed'] and row['stage_error'] is None,row.get('stage_error')
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
        save(dest/'done.json',{'at':time.time(),'attempts':len(kinds),'meaning':'execution only; audit separately'})
    except BaseException as exc:
        STOP.set()
        save(dest/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise


def main():
    plans=json.loads((ROOT/'plan.json').read_text())
    pins=sorted({k+'=='+v for p in plans for k,v in p['pins'].items()})
    for pin in pins:
        dest=ROOT/'assets'/'cache'/pin;dest.mkdir(parents=True,exist_ok=False)
        with (dest/'download.log').open('w') as log:
            subprocess.run(['/usr/bin/python3','-m','pip','download','--index-url','https://pypi.org/simple',
                            '--only-binary=:all:','--no-deps','--python-version','3.9','-d',str(dest),pin],
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    assets=[{'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in (ROOT/'assets/cache').rglob('*.whl')]
    save(ROOT/'assets_manifest.json',assets)
    # 代表批失败需先解释，不能把同一错误机械扩到75题。
    prior=ROOT.parent/'round2b/evidence'
    while not (prior/'dependency_batch_done.json').exists():
        if (prior/'dependency_batch_failed.json').exists():
            raise RuntimeError('代表批中断；停止扩大运行。')
        time.sleep(30)
    active=[p for p in plans if p['action']!='reuse_round2b_evidence']
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(case,p) for p in active]
        for future in as_completed(futures):
            future.result()
    save(ROOT/'done.json',{'at':time.time(),'new_tasks':len(active),'meaning':'execution finished; installation/log/reference audit required'})


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
