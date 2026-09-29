"""逐题下载固定依赖，COPY-only派生，在候选身份安装后走冻结真实评分。"""
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import time

ROOT=Path(os.environ.get('RH2_COMPAT_ROOT','/work/env_recipe_repair_20260919/compat_v1'))
OLD=Path('/work/full216_20260919')


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def call(args,log,timeout=1200):
    with log.open('w') as f:
        subprocess.run(args,check=True,timeout=timeout,stdout=f,stderr=subprocess.STDOUT)


def main():
    plans=json.loads((ROOT/'plan.json').read_text())
    for item in plans:
        iid=item['instance_id']; dest=ROOT/'tasks'/iid;dest.mkdir(parents=True,exist_ok=False)
        context=dest/'context';wheels=context/'wheels';wheels.mkdir(parents=True)
        base=json.loads(subprocess.check_output(['docker','image','inspect',item['image']],text=True))[0]
        assert base['Id']==item['image_id']
        if item.get('reuse_prepared_image'):
            derived=base
            save(dest/'image.json',{'base_id':base['Id'],'image_id':base['Id'],
                                   'reuse_prepared_image':item['reuse_prepared_image'],
                                   'reason':'same immutable prepared image; no duplicate download/build'})
        else:
            name='rh2-er19-compat-download-'+iid.lower()
            try:
                binary = [pin for pin in item['pins'] if pin not in item.get('source_pins', [])]
                groups={}
                for pin in binary:
                    index=item.get('pin_indexes',{}).get(pin,item.get('index_url','https://pypi.org/simple'))
                    groups.setdefault(index,[]).append(pin)
                for group_number,(index,pins) in enumerate(groups.items()):
                    call(['docker','run','--name',name,'--rm','--init','--memory','2g','--cpus','1','-e','PIP_NO_INDEX=0',
                          '-v',str(wheels)+':/cache',base['Id'],'/opt/miniconda3/envs/testbed/bin/python','-I','-m','pip',
                          'download','--index-url',index,'--only-binary=:all:','--no-deps','-d','/cache',
                          *pins],dest/('download_'+str(group_number)+'.log'))
                for pin in item.get('source_pins', []):
                    source_cmd = (
                        'mkdir -p /cache/source && '
                        'python -I -m pip download --index-url https://pypi.org/simple --no-deps '
                        '--no-binary=:all: -d /cache/source ' + pin + ' && '
                        'python -I -m pip wheel --no-deps --no-build-isolation -w /cache /cache/source/*.tar.gz'
                    )
                    call(['docker','run','--name',name,'--rm','--init','--memory','2g','--cpus','1','-e','PIP_NO_INDEX=0',
                          '-v',str(wheels)+':/cache',base['Id'],'bash','-c',
                          'export PATH=/opt/miniconda3/envs/testbed/bin:$PATH; ' + source_cmd],
                         dest/'source_build.log')
            finally:
                subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            save(dest/'assets_manifest.json',[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                             for p in sorted(wheels.rglob('*')) if p.is_file()])
            recipe='ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/compat-wheels/\n'
            (context/'Dockerfile').write_text(recipe)
            tag='rh2-envrepair/'+ROOT.name+'-'+iid.lower()+':20260919'
            base_ref=(base.get('RepoDigests') or base['RepoTags'])[0]
            call(['docker','build','--pull=false','--build-arg','BASE_IMAGE='+base_ref,'-t',tag,str(context)],dest/'build.log',600)
            derived=json.loads(subprocess.check_output(['docker','image','inspect',tag],text=True))[0]
            assert derived['RootFS']['Layers'][:-1]==base['RootFS']['Layers']
            save(dest/'image.json',{'base_id':base['Id'],'image_id':derived['Id'],'recipe':recipe,'base_layers_preserved':True})
        if item.get('preflight_pip_check'):
            # 只提前检查固定依赖的元数据；不能替代候选源码安装与真实评分。
            py='/opt/miniconda3/envs/testbed/bin/python'
            install=shlex.join([py,'-I','-m','pip','install','--no-index',
                               '--find-links=/opt/rh2/compat-wheels','--no-deps',*item['pins']])
            call(['docker','run','--rm','--init','--network','none','--memory','2g','--cpus','1',
                  derived['Id'],'bash','-c',install+' && '+shlex.join([py,'-I','-m','pip','check'])],
                 dest/'preflight_pip_check.log')
        # 下载/构建可先做；首轮评分等快速Pydantic批结束，控制同时活跃的评分进程。
        while not (ROOT.parent/'pydantic_v1/done.json').exists():
            if (ROOT.parent/'pydantic_v1/failed.json').exists():
                raise RuntimeError('Pydantic批中断，先检查共用执行条件后再扩大。')
            save(ROOT/'status.json',{'state':'waiting_for_grading_slot','task':iid,'at':time.time()})
            time.sleep(20)
        for prior in item.get('wait_for_batches', []):
            while not (ROOT.parent/prior/'done.json').exists():
                if (ROOT.parent/prior/'failed.json').exists():
                    raise RuntimeError('prior batch failed; inspect before dispatch: '+prior)
                save(ROOT/'status.json',{'state':'waiting_for_batch','prior':prior,'task':iid,'at':time.time()})
                time.sleep(20)
        for prior in item.get('wait_for_superseded_batches', []):
            prior_dir=ROOT.parent/prior
            while not (prior_dir/'superseded.json').exists():
                if (prior_dir/'failed.json').exists():
                    raise RuntimeError('prior batch failed without safe retirement: '+prior)
                save(ROOT/'status.json',{'state':'waiting_for_safe_retirement','prior':prior,'task':iid,'at':time.time()})
                time.sleep(20)
            retired=json.loads((prior_dir/'superseded.json').read_text())
            closed=retired['driver_close'];manager=closed['manager_close']
            assert not closed.get('halted') and not closed.get('cleanup_failures'),closed
            assert not manager.get('containers_open') and not manager.get('cleanup_failures'),closed
            prior_ledger=json.loads((prior_dir/retired['completed_run']/'ledger.jsonl').read_text())
            assert prior_ledger['cleanup']['removed'] and prior_ledger['stage_error'] is None
            run_id='er19-'+prior+'-'+prior_ledger['instance_id']+'-'+prior_ledger['candidate']['kind']
            assert not subprocess.check_output(['docker','ps','-aq','--filter','label=rh2.run_id='+run_id],text=True,timeout=30).strip()
        code=Path(item.get('code_root',str(OLD/'code/rh2')))
        for kind in item.get('cases',['noop','gold']):
            run=dest/kind;run.mkdir()
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),
                 '--code-root',str(code),'--recipe',str(ROOT/'recipes'/(iid+'.json')),'--audit-dir',str(run/'recipe')]
            if item.get('grading_label_prefix'):
                cmd+=['--grading-label-prefix',item['grading_label_prefix']]
            if item.get('bindings'):
                cmd+=['--bindings',str(ROOT/'reference_bindings_v1.json')]
            cmd+=['--','run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                  '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                  '--derived-image',derived['Id'],'--derived-image-recipe',ROOT.name+':'+iid,
                  '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            if item.get('grading_seconds'):
                cmd+=['--grading-deadline-seconds',str(item['grading_seconds'])]
            save(ROOT/'status.json',{'state':'grading','task':iid,'kind':kind,'at':time.time(),'command':cmd})
            with (run/'driver.log').open('w') as f:
                env=dict(os.environ,**item.get('environment',{}),MILES_RH2_RUN_ID='er19-'+ROOT.name+'-'+iid+'-'+kind)
                subprocess.run(cmd,cwd=code,env=env,stdout=f,stderr=subprocess.STDOUT,
                               timeout=max(4800,item.get('grading_seconds',0)+1200),check=True)
            row=json.loads((run/'ledger.jsonl').read_text());assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
            footers=[]
            for line in (run/'driver.log').read_text().splitlines():
                try:
                    value=json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value,dict) and 'manager_close' in value:
                    footers.append(value)
            assert len(footers)==1, 'missing/ambiguous driver close record'
            closed=footers[0];manager=closed['manager_close']
            save(run/'driver_close_checked.json',closed)
            assert not closed.get('halted') and not closed.get('cleanup_failures'),closed
            assert not manager.get('containers_open') and not manager.get('cleanup_failures'),closed
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
        save(dest/'done.json',{'at':time.time(),'meaning':'execution only; compare full tests and installed versions'})
    save(ROOT/'done.json',{'at':time.time(),'attempts':sum(len(x.get('cases',['noop','gold'])) for x in plans)})


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
