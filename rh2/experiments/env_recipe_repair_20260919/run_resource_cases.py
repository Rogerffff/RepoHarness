"""固定Claude已修代码副本；Modin限实际核数，MONAI联合内存/shm，宿主只读采样。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import threading
import time

ROOT=Path('/work/env_recipe_repair_20260919/resources_v1')
OLD=Path('/work/full216_20260919')


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def sample(stop,run_id,out):
    rows=[]
    while not stop.is_set():
        try:
            ids=subprocess.check_output(['docker','ps','-q','--filter','label=rh2.run_id='+run_id],text=True,timeout=10).split()
            for cid in ids:
                info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True,timeout=10))[0]
                pid=info['State']['Pid'];line=Path('/proc',str(pid),'cgroup').read_text().strip().splitlines()
                rel=next(x.split('::',1)[1] for x in line if '::' in x)
                cg=Path('/sys/fs/cgroup')/rel.lstrip('/')
                facts={}
                for name in ['memory.current','memory.peak','memory.events','pids.current','pids.peak','pids.events']:
                    p=cg/name;facts[name]=p.read_text().strip() if p.exists() else None
                rows.append({'at':time.time(),'container':info['Name'],'host_config':{k:info['HostConfig'].get(k) for k in ['Memory','ShmSize','PidsLimit','NanoCpus','Init']},'state':info['State'],'cgroup':facts})
            save(out,rows)
        except (OSError,subprocess.SubprocessError,ValueError,KeyError,StopIteration) as exc:
            rows.append({'at':time.time(),'sampling_error':repr(exc)})
        stop.wait(2)
    save(out,rows)


def main():
    while not (ROOT.parent/'reference_v1/done.json').exists() or not (ROOT.parent/'pydantic_v1/done.json').exists():
        for prior in ['reference_v1','pydantic_v1']:
            if (ROOT.parent/prior/'failed.json').exists():
                raise RuntimeError('先诊断前批失败，再派发资源对照：'+prior)
        save(ROOT/'status.json',{'state':'waiting_for_two_grading_slots','at':time.time()});time.sleep(20)
    code=ROOT/'code/rh2'
    assert not code.exists()
    code.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['cp','-a','/work/claude_chainfix_20260919/code/rh2',str(code)],check=True)
    save(ROOT/'code_manifest.json',[{'path':str(p.relative_to(code)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                    for p in sorted(code.rglob('*.py'))])
    plan=json.loads((ROOT/'plan.json').read_text())
    for item in plan:
        iid=item['instance_id'];dest=ROOT/'tasks'/iid;dest.mkdir(parents=True,exist_ok=False)
        base=json.loads(subprocess.check_output(['docker','image','inspect',item['image']],text=True))[0];assert base['Id']==item['image_id']
        image=base['Id'];recipe=None
        if iid.startswith('modin'):
            ctx=dest/'context';ctx.mkdir();recipe='ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nENV MODIN_CPUS=2\n';(ctx/'Dockerfile').write_text(recipe)
            tag='rh2-envrepair/resources-v1-'+iid.lower()+':20260919'
            with (dest/'build.log').open('w') as f:
                subprocess.run(['docker','build','--pull=false','--build-arg','BASE_IMAGE='+base['RepoDigests'][0],'-t',tag,str(ctx)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
            derived=json.loads(subprocess.check_output(['docker','image','inspect',tag],text=True))[0];assert derived['RootFS']['Layers']==base['RootFS']['Layers'];image=derived['Id']
        save(dest/'image.json',{'base_id':base['Id'],'image_id':image,'recipe':recipe})
        for kind in ['noop','gold']:
            run=dest/kind;run.mkdir();run_id='er19-rv1-'+iid+'-'+kind
            env=dict(os.environ,MILES_RH2_RUN_ID=run_id)
            if iid.startswith('Project-MONAI'):
                env.update(RH2_GRADER_MEMORY_BYTES=str(8*1024**3),RH2_GRADER_SHM_BYTES=str(1024**3))
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(code/'scripts/replay_grade.py'),'run',
                 '--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                 '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                 '--derived-image',image,'--derived-image-recipe','resources-v1:'+iid,
                 '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            save(ROOT/'status.json',{'state':'grading','task':iid,'kind':kind,'at':time.time(),'command':cmd})
            stop=threading.Event();thread=threading.Thread(target=sample,args=(stop,run_id,run/'resource_samples.json'));thread.start()
            try:
                with (run/'driver.log').open('w') as f:
                    subprocess.run(cmd,cwd=code,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=4800)
            finally:
                stop.set();thread.join(30)
            row=json.loads((run/'ledger.jsonl').read_text());assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
            if iid=='modin-project__modin-6298' and row['report']['reward'] is None:
                raise RuntimeError('首题限核仍infra，保存现场先解释，不机械扩大。')
        save(dest/'done.json',{'at':time.time(),'meaning':'execution only; audit test failures and resource samples'})
    save(ROOT/'done.json',{'at':time.time(),'attempts':2*len(plan)})


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
