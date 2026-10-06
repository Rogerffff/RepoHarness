"""CPU槽内串行调用冻结的真实CC公开命令检查；不生成reward或模型能力结论。"""
from __future__ import annotations
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--job',required=True)
    ap.add_argument('--release-name',required=True)
    ap.add_argument('--release-sha256',required=True)
    args=ap.parse_args()
    assert Path(args.release_name).name==args.release_name
    release=args.root/'releases'/args.release_name
    assert hashlib.sha256((release/'manifest.json').read_bytes()).hexdigest()==args.release_sha256
    manifest=json.loads((release/'manifest.json').read_text())
    src=release/'repo/rh2';python=args.root/'runtime_cpu_v2/rh2/.venv/bin/python'
    for rel in ['rh2/scripts/replay_grade.py','rh2/experiments/task2_swegym_dev_20260925/devcheck.py']:
        assert hashlib.sha256((release/'repo'/rel).read_bytes()).hexdigest()==manifest['files'][rel]['sha256']
    out=args.root/'packages/swe_mypy/attempts'/args.job;out.mkdir(parents=True,exist_ok=False)
    state={'scope':'真实CC公开开发命令；不是正式新修订reward或实际模型求解','job':args.job,'release_id':args.release_name,'release_manifest_sha256':args.release_sha256,'host_runtime':'runtime_cpu_v2/rh2/.venv/bin/python','state':'running','steps':[]}
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(src/'src'),'SLIME_AGENT_CC_PLATFORM_TARBALL':str(args.root/'cc/claude-code-linux-x64-2.1.205.tgz')}
    def save():
        (out/'actor_checks.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    def interrupted(signum,_frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def run(name,argv,timeout=2100):
        step={'name':name,'command':[str(x)for x in argv],'started_at':time.time()};state['steps'].append(step);save()
        with(out/(name+'.log')).open('wb')as log:
            proc=subprocess.Popen(argv,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                rc=proc.wait(timeout=timeout)
            except BaseException:
                if proc.poll()is None:
                    os.killpg(proc.pid,signal.SIGINT)
                    try:proc.wait(timeout=300)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=30);step['forced_kill']=True
                step.update(returncode=proc.returncode,interrupted=True,finished_at=time.time());save();raise
        step.update(returncode=rc,finished_at=time.time());save()
        if rc:raise RuntimeError(f'{name}: rc={rc}; stop and audit cleanup')
    try:
        run('verify_release',[str(python),'-B',str(release/'verify_release.py')],300)
        run('prepare',[str(python),'-B',str(src/'scripts/replay_grade.py'),'prepare','--repo-root',str(release/'repo'),'--out-dir',str(out/'prepared'),'--private-dir',str(out/'private'),'--task-ids','swe_gym_lite::python__mypy-10174,swe_gym_lite::python__mypy-15184'],300)
        images={'python__mypy-10174':'sha256:9d63f1ddcbd277fa62d49e10d800908cfec54544e890fc5fe741d2101ca8eb7e','python__mypy-15184':'sha256:76b5b2646a9eb134e6349ee8e214bb84eb6030c34a234e167351acdec5dd8c54'}
        commands_sha={'python__mypy-10174':'cd32d407102aeb902b2b79e36f3fac1912b04ea33625b34175f516f23249ad57','python__mypy-15184':'fcc47ed75d384d85b578ce43de404fcbc7dc8f453e99e4c31a287c7b12b92b94'}
        for iid,image in images.items():
            commands=args.root/'packages/swe_mypy/public_commands_v1'/(iid+'.json')
            assert hashlib.sha256(commands.read_bytes()).hexdigest()==commands_sha[iid]
            run(iid,[str(python),'-B',str(src/'experiments/task2_swegym_dev_20260925/devcheck.py'),'--prepared-summary',str(out/'prepared/replay_summary.json'),'--task',iid,'--commands',str(commands),'--image',image,'--out-dir',str(out/iid),'--attempt-id',args.job+'-'+iid.rsplit('-',1)[1],'--stub-port','18199','--wall-seconds','1800'])
        state['state']='completed_pending_individual_command_audit';save()
    except BaseException as exc:
        state.update(state='stopped_pending_diagnosis',error=repr(exc));save();raise

if __name__=='__main__':main()
