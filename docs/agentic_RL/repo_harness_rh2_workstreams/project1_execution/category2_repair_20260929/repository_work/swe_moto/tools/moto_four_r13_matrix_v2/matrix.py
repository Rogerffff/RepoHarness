"""Moto 四题固定 R13 薄编排；只调用原 prepare/export-gold/run。

每个 job 只处理一题，候选串行；不改评分、parser、参考或预算。
R13 的评分镜像由正式 registry 消费，不给 source actor 私有评分信息。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path('/work/rh2-category2-20261003')
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', choices=('5960', '6408', '6185', '7584'), required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--controls', nargs='+')
    ns = parser.parse_args()
    require(bool(re.fullmatch('moto' + ns.instance + r'-(?:bind|cpu)-[0-9a-f]{12}', ns.job)), 'job 格式不符')
    require(Path(sys.executable) == ROOT / 'runtime_cpu_v2/rh2/.venv/bin/python', '解释器不符')
    manifest = json.loads((HERE / 'manifest.json').read_text())
    require({p.name for p in HERE.iterdir()} == set(manifest['files']) | {'manifest.json'}, '编排文件集合不符')
    for name, pin in manifest['files'].items():
        require(Path(name).name == name and not (HERE / name).is_symlink(), '编排路径不符')
        require(sha(HERE / name) == pin['sha256'] and (HERE / name).stat().st_size == pin['bytes'], '编排身份不符')
    config = json.loads((HERE / 'tasks.json').read_text())
    iid = 'getmoto__moto-' + ns.instance
    tid = 'swe_gym_lite::' + iid
    task = config['tasks'][iid]
    expected = json.loads((HERE / 'expected_runtime.json').read_text())[iid]
    available = {c['name']: c for c in task['controls']}
    selected = ns.controls or list(available)
    require(len(selected) == len(set(selected)) and set(selected).issubset(available), '候选选择未知或重复')
    release = ROOT / 'releases' / config['release_id']
    repo = release / 'repo'
    require(sha(release / 'manifest.json') == config['manifest_sha256'], '发布身份不符')
    require(sha(repo / config['producer_rel'] / 'ingest_manifest_swe_revision_v1.json') == config['producer_sha256'], 'producer 不符')
    require(sha(repo / task['registry_rel'] / 'material_revisions.json') == task['registry_sha256'], 'registry 不符')
    require(sha(repo / task['registry_rel'] / 'environment_recipe.json') == task['environment_recipe_sha256'], '配方不符')
    for control in task['controls']:
        pin = control['patch']
        if pin is not None:
            p = Path(pin['path'])
            require(not p.is_symlink() and sha(p) == pin['sha256'] and p.stat().st_size == pin['bytes'], '候选补丁不符')
    out = ROOT / 'packages/swe_moto/moto_r13_v1' / ns.job
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(repo / 'rh2/src'))
    env.pop('RH2_IMAGE_OVERLAYS_PATH', None)
    env.pop('RH2_IMAGE_OVERLAYS_SHA256', None)

    def command(name, argv, *, run_id=None):
        call_env = dict(env)
        if run_id is not None:
            call_env['MILES_RH2_RUN_ID'] = run_id
        save(out / (name + '.command.json'), {'argv': argv, 'run_id': run_id, 'interpreter': sys.executable})
        print(json.dumps({'phase': name, 'state': 'started', 'job': ns.job}), flush=True)
        with (out / (name + '.stdout')).open('w') as stdout, (out / (name + '.stderr')).open('w') as stderr:
            result = subprocess.run(argv, env=call_env, stdout=stdout, stderr=stderr, check=False)
        save(out / (name + '.exit.json'), {'returncode': result.returncode})
        print(json.dumps({'phase': name, 'state': 'finished', 'rc': result.returncode}), flush=True)
        require(result.returncode == 0, name + ' 非零退出；停止后续候选，保留原件')
        return (out / (name + '.stdout')).read_text()

    command('verify_release', [sys.executable, '-B', str(release / 'verify_release.py')])
    recipe = task['environment']
    source_ref = recipe['source_image'].split(':')[0] + '@' + recipe['source_image_manifest_digest']
    refs = [source_ref]
    if recipe.get('derived_image_id'):
        refs.append(recipe['derived_image_id'])
    images = json.loads(command('image_inspect', ['docker', 'image', 'inspect', *refs]))
    source = images[0]
    require(source['Id'] == recipe['source_config_id'] and source_ref in source['RepoDigests'], '来源镜像身份不符')
    require(all(i['Architecture'] == 'amd64' and i['Os'] == 'linux' for i in images), '镜像平台不符')
    if recipe.get('derived_image_id'):
        derived = images[1]
        base_layers = source['RootFS']['Layers']
        require(derived['Id'] == recipe['derived_image_id'], '实际派生镜像不符')
        require(derived['RootFS']['Layers'][:-1] == base_layers, 'COPY-only 来源层不符')
        require({'PIP_NO_INDEX=1', 'PIP_FIND_LINKS=/opt/rh2/build-wheels'}.issubset(derived['Config']['Env']), '离线 wheel 环境不符')
    cli = [sys.executable, '-B', str(repo / 'rh2/scripts/replay_grade.py')]
    command('prepare', cli + ['prepare', '--repo-root', str(repo), '--out-dir', str(out / 'prepared'),
                             '--private-dir', str(out / 'private'), '--task-ids', tid])
    summary_path = out / 'prepared/replay_summary.json'
    summary = json.loads(summary_path.read_text())
    require(summary['task_ids'] == [tid], 'prepared 非本题唯一任务')
    save(out / 'prepared_summary.json', summary)
    sys.path.insert(0, str(repo / 'rh2/src'))
    from repoharness2.adapters.slime.prepared_task_face import (
        build_grading_spec_from_host_view,
        rollout_spec_from_view,
    )
    from repoharness2.adapters.slime.replay_grade import load_context
    from repoharness2.adapters.slime.sandbox_profile import (
        grader_profile_from_env,
        rollout_profile_from_env,
    )
    from repoharness2.envpack.spec_vendor import (
        derive_install_command_for_bundle,
        derive_test_command_for_bundle,
    )

    rollout = rollout_profile_from_env(env, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=1)
    grader = grader_profile_from_env(env)
    for profile in (rollout, grader):
        require(profile.cpus == 2 and profile.memory_bytes == 4 * 1024**3 and profile.pids_limit == 512, '资源配置不符')
    require(grader.shm_size_bytes == 64 * 1024**2, 'grader shm 不符')
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=rollout, grader_profile=grader,
        artifacts_dir=out / 'unused', run_id=ns.job)
    view = ctx.rollout_views[tid]
    gview = ctx.grading_views[tid]
    spec = build_grading_spec_from_host_view(view=gview, image=view.public.image,
                                           image_manifest_digest=view.public.image_manifest_digest)
    actor = rollout_spec_from_view(view, time_budget_seconds=1800)
    require(actor.image == task['original_actor_image'] == view.public.image and actor.grading_spec is None,
            'source actor 或私有边界不符')
    require(spec.image == task['grading_spec_image'] and spec.image_local_build_id == task['grading_spec_image_local_build_id'],
            '正式评分镜像绑定不符')
    actual = {'task_id': tid, 'image': view.public.image, 'image_manifest_digest': view.public.image_manifest_digest,
        'base_commit': view.public.base_commit, 'public_bundle_digest': view.public_bundle_digest,
        'grading_bundle_digest': gview.grading_bundle_digest, 'environment_package_digest': view.environment_package_digest,
        'install_command': derive_install_command_for_bundle(gview.grading), 'test_command': derive_test_command_for_bundle(gview.grading),
        'reference_counts': {'f2p': len(gview.grading.fail_to_pass), 'p2p': len(gview.grading.pass_to_pass)},
        'effective_test_patch_sha256': 'sha256:' + hashlib.sha256(gview.grading.test_patch.encode()).hexdigest(),
        'context': spec.grading_revision.diagnostics(None),
        'script_sha256': {name: hashlib.sha256(getattr(spec, name).encode()).hexdigest() for name in expected['script_sha256']}}
    save(out / 'consumer_readback_before_checks.json', actual)
    require(actual == expected, '正式消费与固定本地读回不符')
    budget = task['budget']
    require((spec.env_reset_timeout_seconds, spec.apply_timeout_seconds, spec.test_timeout_seconds) ==
            (budget['setup_seconds'], budget['apply_seconds'], budget['test_seconds']), '生产预算不符')
    actual.update(budgets=budget, grader_runtime_image_id=task['grader_actual_image_id'],
                  original_actor_image=actor.image, actor_executed=False, release_manifest_sha256=config['manifest_sha256'])
    save(out / 'runtime_inputs.json', actual)
    command('export_gold', cli + ['export-gold', '--ingest-dir', str(repo / config['producer_rel']),
                                  '--instance-ids', iid, '--out-dir', str(out / 'gold_input')])
    require(sha(out / 'gold_input' / (iid + '.gold.patch')) == task['gold_sha256'], '实际 gold 不符')
    save(out / 'scope.json', {'task_id': tid, 'execute': ns.execute, 'selected_controls': selected,
        'job_id': ns.job, 'release_id': config['release_id'], 'formal_cpu_accepted': False,
        'actor_executed': False, 'model_attempts': 0, 'tools_manifest_sha256': sha(HERE / 'manifest.json')})
    if not ns.execute:
        save(out / 'result.json', {'status': 'default_prepare_and_image_readback_passed_no_test_execution'})
        return 0
    rows = []
    for name in selected:
        control = available[name]
        candidate = ('noop' if name == 'noop' else 'gold-dir:' + str(out / 'gold_input') if name == 'gold'
                     else 'patch:' + control['patch']['path'])
        run_id = ns.job + '-' + name
        row_dir = out / name
        row_dir.mkdir(exist_ok=False)
        text = command('run_' + name, cli + ['run', '--prepared-summary', str(summary_path), '--task-ids', tid,
            '--candidate', candidate, '--repeat', '1', '--candidate-stage-seconds', str(budget['candidate_stage_seconds']),
            '--grading-deadline-seconds', str(budget['whole_grading_seconds']), '--cleanup-seconds', str(budget['cleanup_seconds']),
            '--image-pull-seconds', str(budget['image_pull_seconds']), '--eval-log-dir', str(row_dir / 'eval_logs'),
            '--artifacts-dir', str(row_dir / 'artifacts'), '--ledger', str(row_dir / 'ledger.jsonl'),
            '--derived-image', task['grader_actual_image_id'], '--derived-image-recipe', recipe['recipe_id']], run_id=run_id)
        ledger = [json.loads(line) for line in (row_dir / 'ledger.jsonl').read_text().splitlines() if line.strip()]
        require(len(ledger) == 1, '账本行数不符')
        row = ledger[0]
        require(row['stage_error'] is None and row['report'] is not None, '基础设施失败，不能视为题目结果')
        report = row['report']
        require(report['outcome'] in ('resolved', 'unresolved') and
                report['failure_category'] in (None, 'tests_failed') and report['reward'] in (0, 1),
                '评分基础设施/解析失败；停止后续候选，保留原件')
        require(row['image_id_actual'] == task['grader_actual_image_id'], '实际运行镜像不符')
        require(row['cleanup']['removed'] is True, '候选未移除')
        close = [json.loads(line) for line in text.splitlines() if line.startswith('{')][-1]
        require(close['rows'] == 1 and close['halted'] is None and close['aborted'] is None, '原入口未完整收口')
        require(close['final_status']['exit_code'] == 0 and not close['cleanup_failures'], '原入口清理失败')
        residual = {}
        for surface, argv in [('containers', ['ps', '-a']), ('networks', ['network', 'ls'])]:
            result = subprocess.run(['docker', *argv, '--filter', 'label=rh2.run_id=' + run_id, '--format', '{{.ID}}'],
                                    capture_output=True, text=True, check=False)
            residual[surface] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
            save(out / ('residual_' + name + '.json'), residual)
            require(result.returncode == 0 and not result.stdout.strip(), '自有资源未确认零残留')
        rows.append({'candidate': name, 'role': control['role'], 'reward': row['report']['reward'],
                     'expected_reward': control['expected_reward'],
                     'matches_expected_reward': row['report']['reward'] == control['expected_reward'], 'run_id': run_id})
        save(out / 'completed_controls.json', rows)
    save(out / 'result.json', {'status': 'selected_controls_completed_pending_raw_and_independent_review',
        'selected_controls': selected, 'rows': rows, 'formal_cpu_accepted': False, 'actor_executed': False})
    return 0 if all(row['matches_expected_reward'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
