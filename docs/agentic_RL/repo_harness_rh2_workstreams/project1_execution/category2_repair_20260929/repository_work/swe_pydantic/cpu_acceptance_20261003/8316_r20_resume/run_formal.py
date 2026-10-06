"""Pydantic剩余四题正式材料的冻结重放；额外观察不改变测试或评分。"""
from __future__ import annotations

import argparse
import asyncio
import base64
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import time
from types import SimpleNamespace

SCRIPTS = ('eval_script', 'trusted_setup_script', 'candidate_test_script', 'candidate_install_script',
           'candidate_test_after_install_script', 'pre_candidate_observation_script', 'post_candidate_observation_script')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')
    tmp.replace(path)


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def spec_record(spec):
    return dict(materials_identity=spec.grading_materials_identity,
                revision=spec.grading_revision.diagnostics(None),
                scripts={k: None if getattr(spec, k) is None else hashlib.sha256(getattr(spec, k).encode()).hexdigest()
                         for k in SCRIPTS}, hygiene=dataclasses.asdict(spec.hygiene),
                budgets={k: getattr(spec, k) for k in ('env_reset_timeout_seconds', 'apply_timeout_seconds', 'test_timeout_seconds')})


def prepare(ns, c, state):
    release = ns.release_dir
    need(sha(release / 'manifest.json') == state['manifest_sha256'], 'release manifest不符')
    manifest = json.loads((release / 'manifest.json').read_text())
    for path, f in manifest['files'].items():
        p = release / 'repo' / path
        need(p.is_file() and not p.is_symlink() and p.stat().st_size == f['size'] and sha(p) == f['sha256'], path)
    need(len(manifest['files']) == state['source_release_member_count'], 'release成员数不符')
    actual_members = {str(p.relative_to(release / 'repo')) for p in (release / 'repo').rglob('*') if p.is_file()}
    need(actual_members == set(manifest['files']), 'release成员集合不符')
    for f in c['assets']:
        p = ns.material_root / f['path']
        need(p.is_file() and not p.is_symlink() and sha(p) == f['sha256'], '本包输入不符: ' + f['path'])
    sys.path.insert(0, str(release / 'repo/rh2/src'))
    from repoharness2.adapters.slime.replay_grade import prepare_for_replay, load_context
    from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace, build_grading_spec_from_host_view
    from repoharness2.adapters.slime.sandbox_profile import rollout_profile_from_env, grader_profile_from_env
    from repoharness2.envpack.spec_vendor import derive_install_command_for_bundle
    from repoharness2.envpack.prepared_tasks import HOST_GRADING_FILE
    summary = prepare_for_replay(repo_root=release / 'repo', out_dir=ns.out / 'prepared', private_dir=ns.out / 'private',
                                 task_ids=['swe_gym_lite::' + c['instance_id']], sources=('swe_gym_lite',))
    rp = rollout_profile_from_env(os.environ, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=1)
    gp = grader_profile_from_env(os.environ)
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
                       manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=rp, grader_profile=gp,
                       artifacts_dir=ns.out / 'unused', run_id=ns.run_id)
    tid = ctx.resolve_task_id(c['instance_id'])
    view, host = ctx.rollout_views[tid], ctx.grading_views[tid]
    need(view.public_bundle_digest == c['public_bundle_digest'], '公开身份不符')
    need(host.grading.base_commit == c['base_commit'], 'base不符')
    need(list(host.grading.fail_to_pass) == c['fail_to_pass'], 'F2P不符')
    need(list(host.grading.pass_to_pass) == c['pass_to_pass'], 'P2P不符')
    need(hashlib.sha256(host.grading.test_patch.encode()).hexdigest() == c['effective_test_sha256'], '有效补丁不符')
    need(host.grading.revision.revision_id == c['revision_id'], '未激活本题修订')
    need(host.grading.revision.installation.asset_sha256 == 'sha256:' + c['install_asset_sha256'], '安装资产不符')
    need(derive_install_command_for_bundle(host.grading) == c['revised_install'], '安装字节不符')
    face = PreparedTaskFace.load(prepared_dir=summary['prepared_dir'], manifest_sha256=summary['prepared_manifest_sha256'],
                                 host_grading_path=Path(summary['private_dir']) / HOST_GRADING_FILE,
                                 host_grading_sha256=summary['host_grading_artifact_sha256'], time_budget_seconds=900,
                                 prompt_data_path=Path(summary['prepared_dir']) / 'prompts.jsonl')
    assignment = SimpleNamespace(task_id=tid, environment_package_digest=view.environment_package_digest,
                                 public_bundle_digest=view.public_bundle_digest)
    actor_spec = face.grading_spec(assignment)
    spec = build_grading_spec_from_host_view(host, image=view.public.image, image_manifest_digest=view.public.image_manifest_digest)
    need(spec_record(actor_spec) == spec_record(spec), 'actor/host spec不同')
    need(spec.grading_revision.environment_package_digest == view.environment_package_digest, '环境身份不符')
    need(spec.env_reset_timeout_seconds == 900 and spec.apply_timeout_seconds == 120 and spec.test_timeout_seconds == 1800, 'R20准备预算不符')
    need(spec.image == c['derived_id'], 'R20精确grader镜像不符')
    state['actual_grader_spec_image'] = spec.image
    need(tuple(spec.hygiene.test_files) == (c['test_file'],), '保护路径不符')
    for k in SCRIPTS:
        if getattr(spec, k) is not None:
            (ns.out / (k + '.sh')).write_text(getattr(spec, k))
    state.update(prepared=summary, spec=spec_record(spec), source_release_members_verified=state['source_release_member_count'],
                 actor_host_spec_equal=True, public_actor_evidence_scope='公开材料未变；四题实际actor开发与交付证据仍待，私有正式矩阵不能代替')
    save(ns.out / 'status.json', state)
    return ctx, spec


def audit_script(c):
    body = """import hashlib,importlib,os,pathlib,sys,json
import pydantic,pydantic_core
files={}
for name in SOURCE_FILES:
 p=pathlib.Path('/testbed')/name
 files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
p=pathlib.Path('/testbed')/TEST_FILE
s=p.stat()
limits={k:pathlib.Path('/sys/fs/cgroup',k).read_text().strip() for k in ('cpu.max','memory.max','pids.max')}
modules={}
for name in MODULES:
 m=importlib.import_module(name);p=pathlib.Path(m.__file__).resolve()
 modules[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
print('PYD_FORMAL_AUDIT='+json.dumps(dict(uid=os.getuid(),python=sys.executable,version=list(sys.version_info[:3]),core=pydantic_core.__version__,pydantic_file=pydantic.__file__,files=files,modules=modules,test=dict(path=TEST_FILE,sha256=hashlib.sha256((pathlib.Path('/testbed')/TEST_FILE).read_bytes()).hexdigest(),uid=s.st_uid,writable=os.access(pathlib.Path('/testbed')/TEST_FILE,os.W_OK)),cgroup=limits)))
""".replace('SOURCE_FILES', repr(c['source_files'])).replace('TEST_FILE', repr(c['test_file'])).replace('MODULES', repr(c['modules']))
    return "set -e\nsource /opt/miniconda3/bin/activate\nconda activate testbed\ncd /testbed\nPYTHONDONTWRITEBYTECODE=1 python - <<'PYD_AUDIT'\n" + body + 'PYD_AUDIT\n'


def validate(ns, c, candidate, row, spec, report, extra):
    from repoharness2.envpack.swegym_parsers import lookup_parser
    from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest
    checks = dict(stage_ok=row.get('stage_error') is None, candidate_removed=(row.get('cleanup') or {}).get('removed') is True,
                  actual_image=row.get('image_id_actual') == c['derived_id'],
                  projectable=(row.get('classification') or {}).get('verdict') == 'projectable',
                  material_identity=row.get('grading_materials_identity') == spec.grading_materials_identity)
    checks['r20_persisted_budgets'] = row.get('budgets') == dict(candidate_stage_seconds=900.0, cleanup_seconds=120.0, env_reset_timeout_seconds=900, grading_deadline_seconds=3600.0, image_pull_seconds=1800.0)
    checks['r20_persisted_policy'] = row.get('preparation_budget_policy') == dict(policy_sha256='d417dbb8d3140e6a0082f2f12cda02fd492feb14db9375ace3d69222e48acdab', request_id='swe-pydantic8316-control-protect-timeout-support-v1-20261003', request_input_sha256='f6f157c22f2c5ad9a630795ad35011b2fbbd5affcc85dae4c9c1f7cd978bf498')
    rep = row.get('report') or {}
    checks.update(reward=rep.get('reward') == candidate['expected_reward'],
                  ordinary_outcome=rep.get('outcome') == ('resolved' if candidate['expected_reward'] else 'unresolved'),
                  ordinary_failure=rep.get('failure_category') == (None if candidate['expected_reward'] else 'tests_failed'),
                  no_infra=not rep.get('infra_failure_detail') and not rep.get('execution_failure_stage'),
                  reference_totals=rep.get('f2p_total') == len(c['fail_to_pass']) and rep.get('p2p_total') == len(c['pass_to_pass']),
                  binary_semantics=rep.get('grading_semantics') == 'swe_f2p_p2p' and report.get('reward_scale_version') == 'binary_v1')
    install = row.get('install') or {}
    checks.update(install_all_zero=install.get('install_rc_last_command') == 0 and install.get('install_failed_commands') == [] and install.get('install_skipped') is False,
                  candidate_complete=install.get('candidate_segment_completed') is True and install.get('candidate_exec_exit_code') == 0,
                  test_rc=install.get('test_rc') == (0 if candidate['expected_reward'] else 1),
                  log_complete=(row.get('log') or {}).get('partial') is False and install.get('log_partial') is False)
    log_path = Path((row.get('log') or {}).get('path', '/nonexistent'))
    states = {}
    if log_path.is_file():
        text = log_path.read_text()
        checks['log_digest'] = 'sha256:' + sha(log_path) == (row.get('log') or {}).get('sha256')
        checks['log_bytes'] = log_path.stat().st_size == (report.get('eval_log_ref') or {}).get('byte_size')
        checks['unique_test_markers'] = text.count('>>>>> Start Test Output') == text.count('>>>>> End Test Output') == 1
        # 使用来源parser，随后按真实参考ID逐项核；不引入摘要别名。
        parser = lookup_parser('pydantic/pydantic')
        start_marker, end_marker = '>>>>> Start Test Output', '>>>>> End Test Output'
        need(start_marker in text and end_marker in text.split(start_marker, 1)[1], '真实测试标记缺失')
        segment = text.split(start_marker, 1)[1].split(end_marker, 1)[0]
        states = parser(segment)
        need(states is not None, '来源parser未给结果')
        states = {k: str(getattr(v, 'value', v)) for k, v in states.items()}
        refs = c['fail_to_pass'] + c['pass_to_pass']
        checks['all_references_accounted'] = all(states.get(k) in ('PASSED', 'FAILED') for k in refs)
        checks['required_statuses'] = all(states.get(k) == v for k, v in candidate['required_statuses'].items())
        checks['no_collect_error'] = 'ERROR collecting' not in segment and 'no tests ran' not in segment
    else:
        checks['full_log'] = False
    diag = json.loads(Path(row['diagnostics_ref']).read_text()) if row.get('diagnostics_ref') else {}
    verdict = diag.get('verdict') or {}
    checks['reference_parser_complete'] = verdict.get('apply_ok') is True and not verdict.get('reference_missing') and not verdict.get('reference_skipped') and verdict.get('num_parsed_tests', 0) >= len(c['fail_to_pass']) + len(c['pass_to_pass'])
    checks['reference_missing_zero'] = row.get('reference_missing_count') == 0
    checks['runner_unchanged'] = row.get('runner_integrity_changed') is False
    revision = row.get('grading_revision') or {}
    checks['revision_parsed'] = revision.get('state') == 'parsed' and revision.get('revision_id') == c['revision_id']
    checks['revision_environment'] = revision.get('environment_package_digest') == spec.grading_revision.environment_package_digest
    for part in revision.get('partitions', {}).values():
        result = part.get('result') or {}
        checks['partitions_complete'] = checks.get('partitions_complete', True) and not any(result.get(x) for x in ('missing', 'skipped', 'unaccounted')) and set(result.get('success', []) + result.get('failure', [])) == set(part.get('references', []))
    frozen_paths = list((ns.out / candidate['name'] / 'artifacts').rglob('frozen_patch.json'))
    checks['one_frozen_export'] = len(frozen_paths) == 1
    if len(frozen_paths) == 1:
        frozen = FrozenPatchArtifactV1.model_validate_json(frozen_paths[0].read_text())
        baseline = json.loads((frozen_paths[0].parent / 'baseline_manifest.json').read_text())
        checks['frozen_projection'] = compute_frozen_patch_digest(frozen) == (row.get('projection') or {}).get('frozen_patch_digest')
        checks['frozen_image'] = frozen.runtime_image_digest == c['derived_id']
        checks['baseline_public'] = baseline['public_bundle_digest'] == c['public_bundle_digest']
        source_hashes = {e['path']: e.get('content_digest') for e in baseline['entries']}
        for e in frozen.model_dump()['entries']:
            if e.get('content_b64') is not None:
                source_hashes[e['path']] = 'sha256:' + hashlib.sha256(base64.b64decode(e['content_b64'])).hexdigest()
        checks['candidate_source_sha'] = all(source_hashes.get(k) == 'sha256:' + h for k, h in candidate['source_sha256'].items())
    if extra and extra.get('exit_code') == 0:
        lines = [x.removeprefix('PYD_FORMAL_AUDIT=') for x in extra['stdout'].splitlines() if x.startswith('PYD_FORMAL_AUDIT=')]
        need(len(lines) == 1, '源码/core观察缺唯一JSON')
        obs = json.loads(lines[0])
        checks['runtime_identity'] = obs['uid'] == 54322 and obs['python'] == '/opt/miniconda3/envs/testbed/bin/python' and obs['version'][:2] == [3, 8] and obs['core'] == c['core'] and obs['pydantic_file'] == '/testbed/pydantic/__init__.py'
        checks['imported_source'] = all(v['path'].startswith('/testbed/') and candidate['source_sha256'].get(v['path'].removeprefix('/testbed/')) == v['sha256'] for v in obs['modules'].values())
        checks['protected_effective_test'] = obs['test']['sha256'] == c['effective_test_file_sha256'] and obs['test']['uid'] == 0 and not obs['test']['writable']
        quota, period = map(int, obs['cgroup']['cpu.max'].split())
        checks['resource_limits'] = quota == 2 * period and int(obs['cgroup']['memory.max']) == 4294967296 and int(obs['cgroup']['pids.max']) == 512
    else:
        obs = None
        checks['runtime_observation'] = False
    return dict(checks=checks, automated_checks_passed=all(checks.values()), states=states,
                referenced_states={k: states.get(k) for k in c['fail_to_pass'] + c['pass_to_pass']},
                report=rep, source_observation=obs, revision=revision,
                scope='作者自动核对；需非作者读取真实原件与失败原因')


async def execute(ns, c, ctx, spec, state):
    from repoharness2.adapters.slime.replay_grade import DerivedImage, ReplayBudgets, ReplayGrader, CandidateInput, final_exit_status
    from repoharness2.grading.manager import SWEGradingManager, GradingManagerConfig, run_docker
    calls = 0
    async def docker(*args, **kwargs):
        nonlocal calls
        need(args and args[0] != 'pull', 'run槽禁止隐式拉镜像')
        calls += 1
        dest = ns.out / 'docker_calls' / f'{calls:04d}'
        dest.mkdir(parents=True)
        if kwargs.get('input_bytes') is not None:
            (dest / 'stdin.bin').write_bytes(kwargs['input_bytes'])
        record = dict(argv=list(args), started_at=time.time())
        save(dest / 'call.json', record)
        try:
            r = await run_docker(*args, **kwargs)
            (dest / 'stdout.full').write_text(r.stdout)
            (dest / 'stderr.full').write_text(r.stderr)
            record.update(exit_code=r.exit_code)
            return r
        finally:
            record['finished_at'] = time.time()
            save(dest / 'call.json', record)
    for image in (c['base_id'], c['derived_id']):
        r = await asyncio.wait_for(docker('image', 'inspect', image), 30)
        need(r.exit_code == 0 and json.loads(r.stdout)[0]['Id'] == image, '镜像不在缓存或ID不符')
    extras, reports = {}, {}
    script = audit_script(c)
    (ns.out / 'supplemental_observation.sh').write_text(script)
    class ObservedManager(SWEGradingManager):
        async def grade(self, *args, **kwargs):
            report = await super().grade(*args, **kwargs)
            reports[report.report_id] = report.model_dump(mode='json')
            return report

        async def _observe(self, record, script, *, phase, timeout, user=None, home=None):
            facts = await super()._observe(record, script, phase=phase, timeout=timeout, user=user, home=home)
            if phase == 'post_candidate_observation':
                try:
                    r = await asyncio.wait_for(self._exec_bash(record, audit, user=user, home=home), 30)
                    extras[record.trajectory_id] = dict(exit_code=r.exit_code, stdout=r.stdout, stderr=r.stderr, user=user)
                except TimeoutError:
                    extras[record.trajectory_id] = dict(error='supplemental_observation_timeout')
            return facts
    audit = 'timeout -k 2 25 /bin/bash -c ' + shlex.quote(script)
    prefix = 'rh2.pydantic.acceptance.' + ns.run_id
    manager = ObservedManager(GradingManagerConfig(label_prefix=prefix, name_prefix='rh2-pydantic-grade',
                                                   eval_log_dir=ns.out / 'eval_logs', sandbox_profile=ctx.grader_profile), docker=docker)
    aborted = None
    try:
        await manager.startup()
        for candidate in c['candidates']:
            name = candidate['name']
            state['current'] = name
            save(ns.out / 'status.json', state)
            dest = ns.out / name
            dest.mkdir()
            patch = None if name == 'noop' else (ns.material_root / candidate['patch']).read_text()
            case_ctx = dataclasses.replace(ctx, run_id=ns.run_id, artifacts_dir=dest / 'artifacts', docker=docker,
                                           derived_image=DerivedImage(ref=c['derived_id'], recipe='pydantic_v1_public_8_wheelhouse:' + c['instance_id']), qualifications={})
            replay = ReplayGrader(case_ctx, manager, ledger_path=dest / 'ledger.jsonl', budgets=ReplayBudgets())
            candidate_input = CandidateInput(kind='noop' if name == 'noop' else ('gold' if name == 'gold' else 'contrast'),
                                             origin='pydantic-formal:' + name, patch_text=patch)
            row = await replay.replay_one(c['instance_id'], candidate_input, attempt=1)
            full = reports.get((row.get('report') or {}).get('report_id'), {})
            extra = next(reversed(extras.values())) if extras else None
            extras.clear()
            save(dest / 'report.json', full)
            save(dest / 'supplemental_observation.json', extra)
            review = validate(ns, c, candidate, row, spec, full, extra)
            save(dest / 'review.json', review)
            state['rows'].append(dict(candidate=name, reward=(row.get('report') or {}).get('reward'), checks=review['checks'], passed=review['automated_checks_passed']))
            save(ns.out / 'status.json', state)
            need(not replay.cleanup_failures and not manager.cleanup_failures, '清理失败，停止本矩阵')
            need(review['automated_checks_passed'], name + ': 自动核对失败；保存原件，停止进一步候选')
    except BaseException as exc:
        aborted = repr(exc)
        raise
    finally:
        closed = await asyncio.wait_for(asyncio.shield(manager.close()), 300)
        end = final_exit_status(halted=None, manager_close=closed, aborted=aborted)
        residual = {}
        for kind, args, fmt in [('containers', ('ps', '-a'), '{{.Names}}'), ('networks', ('network', 'ls'), '{{.Name}}')]:
            r = await asyncio.wait_for(docker(*args, '--filter', 'label=rh2.run_id=' + ns.run_id, '--format', fmt), 30)
            residual[kind] = dict(rc=r.exit_code, stdout=r.stdout, stderr=r.stderr)
        state['cleanup'] = dict(manager_close=closed, final_status=end, residual=residual)
        save(ns.out / 'status.json', state)
        need(end['exit_code'] == 0 and all(r['rc'] == 0 and not r['stdout'].strip() for r in residual.values()), '收尾异常或存在本run残留')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', choices=('8316',), required=True)
    ap.add_argument('--release-dir', type=Path, required=True)
    ap.add_argument('--material-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--execute', action='store_true')
    ns = ap.parse_args()
    os.umask(0o077)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['MILES_RH2_RUN_ID'] = ns.run_id
    need(re.fullmatch(r'pyd8316-formal-[a-z0-9-]{4,40}', ns.run_id), 'run_id不符')
    ns.out = ns.out.resolve()
    need(not ns.out.is_relative_to(ns.release_dir.resolve()), '不能写release')
    ns.out.mkdir(parents=True, exist_ok=False)
    for x in ('RH2_SANDBOX_CPUS', 'RH2_GRADER_CPUS'):
        os.environ[x] = '2'
    for x in ('RH2_SANDBOX_MEMORY_BYTES', 'RH2_GRADER_MEMORY_BYTES'):
        os.environ[x] = str(4294967296)
    inputs = Path(__file__).parent / 'formal_inputs.json'
    meta = json.loads(inputs.read_text())
    need(ns.release_dir.name == meta['source_release'], '发布目录与冻结输入ID不符')
    c = meta['tasks'][ns.task]
    state = dict(scope='正式受信材料CPU重放；不代表独立验收或模型探针', status='preparing',
                 source_release=meta['source_release'], manifest_sha256=meta['manifest_sha256'],
                 source_release_member_count=meta['source_release_member_count'], task=c['instance_id'], run_id=ns.run_id,
                 wrapper_sha256=sha(Path(__file__)), input_sha256=sha(inputs), runtime=sys.executable,
                 execute=ns.execute, rows=[], started_at=time.time())
    save(ns.out / 'status.json', state)
    try:
        ctx, spec = prepare(ns, c, state)
        if ns.execute:
            async def run():
                task = asyncio.current_task()
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, task.cancel)
                await execute(ns, c, ctx, spec, state)
            asyncio.run(run())
        state['status'] = 'formal_matrix_executed_pending_non_author_review' if ns.execute else 'static_prepare_join_passed'
    except BaseException as exc:
        state.update(status='stopped_needs_analysis', error=repr(exc))
        raise
    finally:
        state['finished_at'] = time.time()
        save(ns.out / 'status.json', state)
        print(json.dumps({k: state[k] for k in ('task', 'status')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
