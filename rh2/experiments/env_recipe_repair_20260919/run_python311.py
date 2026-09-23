"""三题恢复Python3.11解释器，冻结原包版本；不屏蔽warning、不改测试。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT=Path(os.environ.get('RH2_PY311_ROOT','/work/env_recipe_repair_20260919/python311_v1'))
OLD=Path('/work/full216_20260919')
PREFIX='/opt/rh2/python311'


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def call(cmd,path,timeout=1800):
    with path.open('w') as f:
        subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,check=True)


def main():
    plans=json.loads((ROOT/'plan.json').read_text())
    for item in plans:
        iid=item['instance_id'];dest=ROOT/'tasks'/iid;dest.mkdir(parents=True)
        context=dest/'context';prefix=context/'prefix';prefix.mkdir(parents=True)
        wheels=context/'wheels';wheels.mkdir()
        req=dest/'requirements.txt';req.write_text('\n'.join(item['pins'])+'\n')
        base=json.loads(subprocess.check_output(['docker','image','inspect',item['image']],text=True))[0]
        assert base['Id']==item['image_id']
        name='rh2-er19-py311-build-'+iid.lower()
        try:
            cmd=['docker','run','--init','--name',name,'--memory','12g','--cpus','2',
                 '-v',str(prefix)+':'+PREFIX,'-v',str(dest)+':/input',base['Id'],'bash','-c',
                 '/opt/miniconda3/bin/conda create -y --solver libmamba --override-channels -c conda-forge -p '+PREFIX+
                 ' python=3.11.9 pip=24.2 && '+PREFIX+'/bin/python -I -m pip wheel --index-url https://pypi.org/simple '
                 '--no-deps -w /input/context/wheels -r /input/requirements.txt && '+PREFIX+
                 '/bin/python -I -m pip install --no-index --find-links=/input/context/wheels --no-deps -r /input/requirements.txt && '+
                 PREFIX+'/bin/python -I -m pip list --format=json > /input/installed.json && '+
                 '/opt/miniconda3/bin/conda list -p '+PREFIX+' --explicit > /input/conda-explicit.txt']
            save(ROOT/'status.json',{'at':time.time(),'state':'prepare_python311','task':iid})
            call(cmd,dest/'prepare.log',2400)
        finally:
            inspected=subprocess.run(['docker','inspect',name],text=True,capture_output=True)
            if inspected.returncode==0:
                info=json.loads(inspected.stdout)[0]
                save(dest/'builder_state.json',{'State':info['State'],
                                               'Memory':info['HostConfig']['Memory'],'NanoCpus':info['HostConfig']['NanoCpus']})
            subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        actual={x['name'].lower().replace('_','-'):x['version'] for x in json.loads((dest/'installed.json').read_text())}
        for pin in item['pins']:
            package,version=pin.split('==');assert actual[package.lower().replace('_','-')]==version,(pin,actual)
        save(dest/'assets_manifest.json',[{'path':str(p.relative_to(context)),'bytes':p.stat().st_size,
                                         'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                        for p in sorted(wheels.glob('*.whl'))])
        recipe='ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY prefix/ '+PREFIX+'/\nCOPY wheels/ /opt/rh2/build-wheels/\nENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n'
        (context/'Dockerfile').write_text(recipe)
        tag='rh2-envrepair/python311-v1-'+iid.lower()+':20260919'
        call(['docker','build','--pull=false','--build-arg','BASE_IMAGE='+base['RepoDigests'][0],'-t',tag,str(context)],dest/'build.log',600)
        image=json.loads(subprocess.check_output(['docker','image','inspect',tag],text=True))[0]
        assert image['RootFS']['Layers'][:-2]==base['RootFS']['Layers']
        save(dest/'image.json',{'base_id':base['Id'],'image_id':image['Id'],'recipe':recipe})
        for kind in ['noop','gold']:
            run=dest/kind;run.mkdir()
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),
                 '--code-root',str(OLD/'code/rh2'),'--recipe',str(ROOT/'recipes'/(iid+'.json')),'--audit-dir',str(run/'recipe'),'--',
                 'run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                 '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                 '--derived-image',image['Id'],'--derived-image-recipe','python311-v1:'+iid,
                 '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            save(ROOT/'status.json',{'at':time.time(),'state':'grading','task':iid,'kind':kind})
            env=dict(os.environ,MILES_RH2_RUN_ID='er19-py311-'+iid+'-'+kind,
                     RH2_GRADER_CANDIDATE_WRITABLE_PREFIXES='/opt/miniconda3/envs/testbed:'+PREFIX)
            with (run/'driver.log').open('w') as f:
                subprocess.run(cmd,cwd=OLD/'code/rh2',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=4800,check=True)
            row=json.loads((run/'ledger.jsonl').read_text())
            assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
        save(dest/'done.json',{'at':time.time(),'meaning':'execution only; require installed prefix and full test audit'})
    save(ROOT/'done.json',{'at':time.time(),'attempts':2*len(plans)})


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
