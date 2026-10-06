"""串行编排冻结runner的新材料矩阵；身份由题级冻结binding输入，不自定义评分。"""
from __future__ import annotations
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--binding',type=Path,required=True);args=ap.parse_args()
    binding=json.loads(args.binding.read_text());iid=binding['instance_id'];assert iid in ('python__mypy-10174','python__mypy-15184')
    name=binding['release_id'];assert Path(name).name==name
    release=args.root/'releases'/name;manifest=release/'manifest.json';assert hashlib.sha256(manifest.read_bytes()).hexdigest()==binding['release_manifest_sha256']
    src=release/'repo/rh2';python=args.root/'runtime_cpu_v2/rh2/.venv/bin/python'
    out=args.root/'packages/swe_mypy/attempts'/args.job;out.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(src/'src')}
    state={'scope':'已发布新材料的真实冻结runner评分，仍需逐项回读及独立核查','state':'running','job':args.job,'binding_sha256':hashlib.sha256(args.binding.read_bytes()).hexdigest(),'binding':binding,'steps':[]}
    def save():
        (out/'revised_matrix.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    def interrupted(signum,_frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def run(step_name,argv,timeout=4800):
        step={'name':step_name,'command':[str(v)for v in argv],'started_at':time.time()};state['steps'].append(step);save()
        with(out/(step_name+'.log')).open('wb')as log:
            proc=subprocess.Popen(argv,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:rc=proc.wait(timeout=timeout)
            except BaseException:
                if proc.poll()is None:
                    os.killpg(proc.pid,signal.SIGINT)
                    try:proc.wait(timeout=300)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=30);step['forced_kill']=True
                step.update(returncode=proc.returncode,interrupted=True,finished_at=time.time());save();raise
        step.update(returncode=rc,finished_at=time.time());save()
        if rc:raise RuntimeError(f'{step_name}: rc={rc}; stop before next candidate')
    try:
        run('verify_release',[str(python),'-B',str(release/'verify_release.py')],300)
        # 只在宿主可信读回；此binding与参考内容不交给公开actor。
        readback='''import json,hashlib
from pathlib import Path
from repoharness2.envpack.swe_material_revisions import load_trusted_swe_revision_outputs
b=json.loads(Path(BINDING).read_text());r=load_trusted_swe_revision_outputs(Path(REPO)).result
p=next(p for p in r.public_bundles if p.instance_id==b['instance_id']);g=next(g for g in r.grading_bundles if g.instance_id==b['instance_id'])
assert p.digest()==b['public_digest']
assert g.digest()==b['grading_digest']
assert 'sha256:'+hashlib.sha256(g.test_patch.encode()).hexdigest()==b['effective_test_patch_sha256']
assert set(g.fail_to_pass)==set(b['fail_to_pass']) and set(g.pass_to_pass)==set(b['pass_to_pass'])
print(json.dumps({'public_digest':p.digest(),'grading_digest':g.digest(),'reference_f2p':g.fail_to_pass,'reference_p2p':g.pass_to_pass},default=list))
'''
        readback='BINDING='+repr(str(args.binding))+'\nREPO='+repr(str(release/'repo'))+'\n'+readback
        run('material_identity',[str(python),'-B','-c',readback],300)
        cli=src/'scripts/replay_grade.py'
        run('prepare',[str(python),'-B',str(cli),'prepare','--repo-root',str(release/'repo'),'--out-dir',str(out/'prepared'),'--private-dir',str(out/'private'),'--task-ids','swe_gym_lite::'+iid],300)
        image=binding['image_id'];assert image.startswith('sha256:')and len(image)==71
        for candidate in binding['candidates']:
            label=candidate['name'];assert label in ('noop','gold','bad','top_only')
            patch=candidate.get('patch')
            if patch:
                path=args.root/'packages/swe_mypy'/patch;assert not Path(patch).is_absolute()and '..'not in Path(patch).parts
                assert hashlib.sha256(path.read_bytes()).hexdigest()==candidate['patch_sha256'];value='patch:'+str(path)
            else:assert label=='noop';value='noop'
            dest=out/label;dest.mkdir();env['MILES_RH2_RUN_ID']='swe-mypy-'+args.job+'-'+label
            run(label,[str(python),'-B',str(cli),'run','--prepared-summary',str(out/'prepared/replay_summary.json'),'--task-ids',iid,'--candidate',value,'--derived-image',image,'--derived-image-recipe','mypy-install-wave1-copy-wheels-20261003','--eval-log-dir',str(dest/'eval_logs'),'--artifacts-dir',str(dest/'artifacts'),'--ledger',str(dest/'ledger.jsonl')])
            rows=[json.loads(x)for x in(dest/'ledger.jsonl').read_text().splitlines()if x];assert len(rows)==1;row=rows[0]
            assert row['stage_error']is None and row['cleanup']['removed'] and row['image_id_actual']==image
            assert row['grading_revision']is not None and row['grading_materials_identity']is not None
            state.setdefault('raw_results',{})[label]={'report':row['report'],'grading_revision':row['grading_revision'],'grading_materials_identity':row['grading_materials_identity'],'reference':row['reference'],'install':row['install'],'cleanup':row['cleanup'],'evidence_requires_audit':True};save()
        state['state']='raw_matrix_completed_pending_audit';save()
    except BaseException as exc:
        state.update(state='stopped_pending_diagnosis',error=repr(exc));save();raise

if __name__=='__main__':main()
