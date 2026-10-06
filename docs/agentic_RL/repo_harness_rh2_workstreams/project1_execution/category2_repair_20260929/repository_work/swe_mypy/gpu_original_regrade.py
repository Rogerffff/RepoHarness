"""原GPU FrozenPatch的CPU窄重评分；不改旧工件、不重模型或候选矩阵。"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--job', required=True)
    ap.add_argument('--binding', type=Path, required=True)
    args = ap.parse_args()
    b = json.loads(args.binding.read_text())
    release = args.root / 'releases' / b['release_id']
    repo = release / 'repo'
    assert sha(release / 'manifest.json') == b['release_manifest_sha256']
    src = repo / 'rh2/src'
    for name, digest in b['consumer_source_sha256'].items():
        assert sha(src / name) == digest, name
    sys.path.insert(0, str(src))
    from repoharness2.adapters.slime.replay_grade import prepare_for_replay, load_context
    from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env, rollout_profile_from_env
    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
    from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest
    from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest
    from repoharness2.contracts.scoring_projection import classify_frozen_patch
    from repoharness2.grading.trusted_projection import build_trusted_scoring_projection
    from repoharness2.grading.manager import (
        SWEGradingManager, GradingManagerConfig, FrozenDeltaSource, grading_scripts_digest,
    )
    out = args.root / 'packages/swe_mypy/attempts' / args.job
    out.mkdir(parents=True, exist_ok=False)
    original = args.root / 'packages/swe_mypy' / b['original_input_dir']
    for name, digest in b['original_file_sha256'].items():
        assert sha(original / name) == digest, name
    state = {'state': 'running', 'job': args.job, 'binding': b,
             'scope': 'CPU同源可读wheel镜像下原FP窄重评分；不追溯改写GPU旧成绩/镜像/导入观测。',
             'baseline_rebuild_passed': False, 'candidate_install_steps': []}
    save(out / 'regrade_state.json', state)
    summary = prepare_for_replay(repo_root=repo, out_dir=out/'prepared', private_dir=out/'private',
                                 task_ids=[b['task_id']], sources=['swe_gym_lite'])
    # fresh prepare的时间戳必然变化；逐字段核其余清单并保留两份真实SHA，不能回填旧时间。
    old_manifest = json.loads((original/'prepared_manifest.json').read_text())
    new_manifest = json.loads((out/'prepared/prepared_manifest.json').read_text())
    assert sha(original/'prepared_manifest.json') == b['prepared_manifest_sha256']
    assert old_manifest['prepared_at_utc'] != new_manifest['prepared_at_utc']
    assert {k:v for k,v in old_manifest.items() if k != 'prepared_at_utc'} == {
        k:v for k,v in new_manifest.items() if k != 'prepared_at_utc'}
    state['prepared_identity_check'] = {
        'original_manifest_sha256': b['prepared_manifest_sha256'],
        'fresh_manifest_sha256': summary['prepared_manifest_sha256'],
        'only_changed_field': 'prepared_at_utc',
        'original_prepared_at_utc': old_manifest['prepared_at_utc'],
        'fresh_prepared_at_utc': new_manifest['prepared_at_utc'],
        'all_other_manifest_fields_equal': True,
    }
    save(out/'regrade_state.json', state)
    assert summary['host_grading_artifact_sha256'] == b['host_grading_artifact_sha256']
    gp = grader_profile_from_env({})
    rp = rollout_profile_from_env({}, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=18198)
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
                       manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=rp,
                       grader_profile=gp, artifacts_dir=out/'unused', run_id=args.job)
    view = ctx.rollout_views[b['task_id']]
    spec = build_grading_spec_from_host_view(view=ctx.grading_views[b['task_id']],
              image=view.public.image, image_manifest_digest=view.public.image_manifest_digest)
    assert spec.grading_materials_identity == b['grading_materials_identity']
    assert grading_scripts_digest(spec) == b['scripts_digest']
    spec = dataclasses.replace(spec, image=b['cpu_image_id'], image_manifest_digest=None,
             image_local_build=True, image_local_build_id=b['cpu_image_id'], env_reset_timeout_seconds=300,
             test_timeout_seconds=1800)
    baseline = BaselineWorkspaceManifestV1.model_validate_json((original/'baseline_manifest.json').read_text())
    artifact = FrozenPatchArtifactV1.model_validate_json((original/'frozen_patch.json').read_text())
    assert compute_frozen_patch_digest(artifact) == b['original_frozen_patch_digest']
    assert compute_baseline_manifest_digest(baseline) == b['original_baseline_manifest_digest']
    assert artifact.rollout_execution_id == b['original_job']
    assert artifact.runtime_image_digest == baseline.runtime_image_digest == b['original_gpu_image_id']
    assert artifact.public_bundle_digest == baseline.public_bundle_digest == view.public_bundle_digest
    classification, _ = classify_frozen_patch(artifact, baseline)
    assert classification.verdict == 'projectable'
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert not split.unsupported_shape_reasons
    assert projection.model_dump(mode='json') == json.loads((original/'projection.json').read_text())
    save(out/'projection.json', projection.model_dump(mode='json'))
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection,
                              frozen_patch_digest=compute_frozen_patch_digest(artifact))
    manager = SWEGradingManager(GradingManagerConfig(label_prefix='rh2.mypy_regrade.'+args.job,
                name_prefix='rh2-mypy-regrade', eval_log_dir=out/'eval_logs', sandbox_profile=gp))
    original_verify = manager._verify_baseline_rebuild
    original_exec = manager._exec_bash_checked
    original_observe = manager._observe
    prefix = 'set -e\nsource /opt/miniconda3/bin/activate\nconda activate testbed\ncd /testbed\n'
    probe_code = '''import hashlib, importlib, json, os, pathlib, stat, sysconfig
facts={'uid':os.getuid(),'gid':os.getgid(),'cwd':os.getcwd(),'executable':__import__('sys').executable,'modules':{},'wheels':[]}
for name in ['mypy','mypy.meet','mypy.build','mypy.checkexpr']:
 m=importlib.import_module(name);p=pathlib.Path(m.__file__)
 facts['modules'][name]={'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'loader':type(m.__loader__).__name__}
facts['meet_code_filename']=importlib.import_module('mypy.meet').is_overlapping_types.__code__.co_filename
for p in sorted(pathlib.Path('/opt/rh2/build-wheels').glob('*.whl')):
 s=p.stat();facts['wheels'].append({'name':p.name,'mode':oct(stat.S_IMODE(s.st_mode)),'uid':s.st_uid,'gid':s.st_gid,'bytes':s.st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
# 此固定旧镜像的stdlib/backport metadata finder不兼容；读取解释器purelib实际文件。
purelib=pathlib.Path(sysconfig.get_paths()['purelib'])
facts['metadata_probe_scope']='filesystem census in interpreter purelib; no distribution finder or sys.path mutation'
facts['purelib']=str(purelib)
facts['mypy_distributions']=[]
for p in sorted(purelib.glob('mypy-*.dist-info/direct_url.json')):
 metadata=p.parent/'METADATA'
 facts['mypy_distributions'].append({'path':str(p.parent),'direct_url':p.read_text(),
  'direct_url_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
  'metadata_sha256':hashlib.sha256(metadata.read_bytes()).hexdigest()})
print(json.dumps(facts,sort_keys=True))
'''
    import shlex
    probe_script = prefix + 'PYTHONDONTWRITEBYTECODE=1 python -c ' + shlex.quote(probe_code)

    async def probe(record, label):
        result = await original_exec(record, probe_script, phase='owner_'+label, timeout=90,
                    user=str(gp.candidate_exec_uid), home='/home/'+gp.candidate_exec_user)
        save(out/(label+'.exec.json'), dataclasses.asdict(result))
        assert result.exit_code == 0, label
        value = json.loads(result.stdout.splitlines()[-1])
        assert value['uid'] == gp.candidate_exec_uid == 54322
        for name, digest in b['expected_module_sha256'].items():
            assert value['modules'][name]['sha256'] == digest, name
            assert value['modules'][name]['file'] == '/testbed/'+name.replace('.', '/')+'.py', name
            assert value['modules'][name]['loader'] == 'SourceFileLoader', name
        assert value['meet_code_filename'] == '/testbed/mypy/meet.py'
        assert {x['name']: x['sha256'] for x in value['wheels']} == b['wheel_sha256']
        assert all(int(x['mode'], 8) & 0o044 == 0o044 for x in value['wheels'])
        if label != 'candidate_before_install':
            editable = [d for d in value['mypy_distributions'] if d['direct_url'] is not None
                and json.loads(d['direct_url']).get('url') == 'file:///testbed'
                and json.loads(d['direct_url']).get('dir_info',{}).get('editable') is True]
            assert editable, '真实editable安装元数据缺席；不能以cwd源码egg-info代替'
            assert any('/site-packages/' in d['path'] and d['path'].endswith('.dist-info') for d in editable)
        save(out/(label+'.json'), value)
        return value

    async def observed(record, script, *, phase, **kwargs):
        result = await original_observe(record, script, phase=phase, **kwargs)
        if phase == 'pre_candidate_observation':
            # 在同一已投影候选和UID下逐条核原配方，记录真实rc；正式脚本随后原样再跑。
            before = await probe(record, 'candidate_before_install')
            for index, command in enumerate(b['install_commands'], 1):
                step = await original_exec(record, prefix+command, phase='owner_install_'+str(index), timeout=300,
                            user=str(gp.candidate_exec_uid), home='/home/'+gp.candidate_exec_user)
                receipt = {'index': index, 'command': command, **dataclasses.asdict(step)}
                save(out/('install_step_'+str(index)+'.json'), receipt)
                state['candidate_install_steps'].append({'index':index,'command':command,'returncode':step.exit_code})
                save(out/'regrade_state.json', state)
                assert step.exit_code == 0, command
            after = await probe(record, 'candidate_after_install')
            assert before['modules'] == after['modules']
        elif phase == 'post_candidate_observation':
            await probe(record, 'candidate_after_formal_tests')
        return result

    async def observed_exec(*pos, **kwargs):
        result = await original_exec(*pos, **kwargs)
        if kwargs.get('phase') == 'baseline_rebuild':
            (out/'baseline_rebuild_census.txt').write_text(result.stdout)
        return result

    async def verify(*pos, **kwargs):
        value = await original_verify(*pos, **kwargs)
        state['baseline_rebuild_passed'] = True
        save(out/'regrade_state.json', state)
        return value

    manager._observe = observed
    manager._exec_bash_checked = observed_exec
    manager._verify_baseline_rebuild = verify

    async def run():
        try:
            manager._verify_frozen_delta_binding(spec, source)
            report = await asyncio.wait_for(manager.grade(trajectory_id=args.job, workspace=None, spec=spec,
                       frozen_delta=source, deadline_monotonic=time.monotonic()+3600), 3900)
            state['report'] = report.model_dump(mode='json')
            save(out/'report.json', state['report'])
            assert state['baseline_rebuild_passed']
            state['state'] = 'raw_regrade_completed_pending_audit'
        except BaseException as exc:
            state.update(state='stopped_pending_diagnosis', error=repr(exc))
            raise
        finally:
            closing = asyncio.create_task(manager.close())
            try:
                state['manager_close'] = await asyncio.wait_for(asyncio.shield(closing), 300)
                c=state['manager_close']
                state['cleanup_ok'] = c['containers_open']==[] and c['supply_open']==[] and c['cleanup_failures']==[]
            except BaseException as exc:
                state['cleanup_ok'] = False
                state['cleanup_error'] = repr(exc)
                closing.cancel()
            save(out/'regrade_state.json', state)
        assert state['cleanup_ok']
        for name, digest in b['original_file_sha256'].items():
            assert sha(original/name)==digest, name
        print(json.dumps({'state':state['state'],'reward':state['report']['reward'],
                          'baseline_rebuild_passed':True,'cleanup_ok':state['cleanup_ok']}))
    asyncio.run(run())


if __name__ == '__main__':
    main()
