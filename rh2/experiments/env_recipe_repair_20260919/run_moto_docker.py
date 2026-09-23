"""7105的真实Docker能力：先运行嵌套容器，再在真实RH2侧车配置下noop/gold。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import threading
import time

from rootless_docker_service import call, load, start, stop

ROOT=Path(os.environ.get('RH2_MOTO_DOCKER_ROOT','/work/env_recipe_repair_20260919/moto_docker_v1'))
OLD=Path('/work/full216_20260919')
IID='getmoto__moto-7105'


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    assets=ROOT/'assets';assets.mkdir()
    manifests=[];archives=[]
    for tag in ['docker:28.1.1-dind-rootless','busybox:latest','amazonlinux:latest']:
        with (assets/(tag.replace(':','_')+'.pull.log')).open('w') as f:
            subprocess.run(['docker','pull',tag],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
        image=json.loads(call(['docker','image','inspect',tag]).stdout)[0]
        manifests.append({'tag':tag,'image_id':image['Id'],'repo_digests':image['RepoDigests']})
        if tag.startswith('docker:'):
            service_image=image['Id']
        else:
            archive=assets/(tag.split(':')[0]+'.tar')
            subprocess.run(['docker','save','-o',str(archive),tag],check=True,timeout=300)
            archives.append(archive)
            manifests[-1].update(archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    save(ROOT/'assets_manifest.json',manifests)
    evidence=ROOT/'capability';evidence.mkdir()
    name='rh2-er19-docker-preflight'
    try:
        start(name,'none',service_image,evidence)
        load(name,archives,evidence)
        p=call(['docker','exec',name,'docker','-H','tcp://127.0.0.1:2375','run','--rm',
                '--add-host','host.docker.internal:host-gateway','busybox:latest','sh','-c',
                'id; cat /etc/hosts; echo RH2_NESTED_EXEC_OK'])
        (evidence/'nested_exec.log').write_text(p.stdout+p.stderr)
        assert 'RH2_NESTED_EXEC_OK' in p.stdout
    finally:
        stop(name,evidence)
    image=json.loads((ROOT.parent/'install_wave1/tasks'/IID/'image.json').read_text())['image_id']
    for kind in ['noop','gold']:
        run=ROOT/'runs'/kind;run.mkdir(parents=True)
        run_id='er19-'+ROOT.name+'-'+kind;name='rh2-er19-docker-service-'+kind
        ev=run/'service';ev.mkdir();finish=threading.Event();errors=[]

        def serve():
            started=False
            try:
                for _ in range(600):
                    if finish.is_set():return
                    p=call(['docker','ps','--filter','label=rh2.run_id='+run_id,'--format','{{.ID}} {{.Names}}'])
                    candidates=[l.split()[0] for l in p.stdout.splitlines() if ' rh2-grading-' in l]
                    if candidates:break
                    time.sleep(.5)
                else:raise RuntimeError('no grader container for isolated service')
                started=True
                start(name,'container:'+candidates[0],service_image,ev)
                load(name,archives,ev)
                # 只有资产就绪才允许可信准备继续。临时marker在本题grader容器内。
                call(['docker','exec','--user','0',candidates[0],'touch','/tmp/rh2-docker-ready'])
                finish.wait(4700)
            except BaseException as exc:
                errors.append(repr(exc));save(ev/'error.json',{'error':repr(exc)})
            finally:
                if started:
                    try:stop(name,ev)
                    except BaseException as exc:errors.append(repr(exc))

        thread=threading.Thread(target=serve);thread.start()
        cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),'--code-root',str(OLD/'code/rh2'),
             '--recipe',str(ROOT/'recipe.json'),'--audit-dir',str(run/'recipe'),'--','run',
             '--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',IID,
             '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
             '--derived-image',image,'--derived-image-recipe','offline-wheels+isolated-rootless-'+ROOT.name,
             '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
        save(ROOT/'status.json',{'at':time.time(),'state':'grading','kind':kind})
        try:
            with (run/'driver.log').open('w') as f:
                subprocess.run(cmd,cwd=OLD/'code/rh2',env=dict(os.environ,MILES_RH2_RUN_ID=run_id),
                               stdout=f,stderr=subprocess.STDOUT,timeout=4800,check=True)
        finally:
            finish.set();thread.join(180)
        assert not thread.is_alive() and not errors,errors
        row=json.loads((run/'ledger.jsonl').read_text())
        assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
        print('GRADED',kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
    save(ROOT/'done.json',{'at':time.time(),'attempts':2,'meaning':'execution only; full tests and two-container resource scope require audit'})


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
