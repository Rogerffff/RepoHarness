"""固定 R5 原材料单反例对照；评分未知，不作修订准入判定。"""
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
    parser.add_argument('--instance', choices=('5960', '6408'), required=True)
    parser.add_argument('--job', required=True)
    ns = parser.parse_args()
    require(bool(re.fullmatch('moto' + ns.instance + r'-oldnegative-[0-9a-f]{12}', ns.job)), 'job 格式不符')
    require(Path(sys.executable) == ROOT / 'runtime_cpu_v2/rh2/.venv/bin/python', '解释器不符')
    manifest = json.loads((HERE / 'manifest.json').read_text())
    require({p.name for p in HERE.iterdir()} == set(manifest['files']) | {'manifest.json'}, '工具集合不符')
    for name, pin in manifest['files'].items():
        p = HERE / name
        require(Path(name).name == name and p.is_file() and not p.is_symlink(), '工具路径不符')
        require(sha(p) == pin['sha256'] and p.stat().st_size == pin['bytes'], '工具身份不符')
    config = json.loads((HERE / 'tasks.json').read_text())
    task = config['tasks'][ns.instance]
    tid = task['task_id']
    expected = json.loads((HERE / 'expected_original.json').read_text())[tid]
    require(task['expected_reward'] is None and expected['grading_revision'] is None, '原对照范围不符')
    release = ROOT / 'releases' / config['release_id']
    repo = release / 'repo'
    require(sha(release / 'manifest.json') == config['release_manifest_sha256'], 'R5 身份不符')
    patch = Path(task['patch']['path'])
    require(patch.is_file() and not patch.is_symlink(), '反例路径不符')
    require(sha(patch) == task['patch']['sha256'] and patch.stat().st_size == task['patch']['bytes'], '反例身份不符')
    out = ROOT / 'packages/swe_moto/moto_original_negative_r5_v1' / ns.job
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(repo / 'rh2/src'))
    env.pop('RH2_IMAGE_OVERLAYS_PATH', None)
    env.pop('RH2_IMAGE_OVERLAYS_SHA256', None)

    def command(name, argv, *, run_id=None):
        call_env = dict(env)
        if run_id:
            call_env['MILES_RH2_RUN_ID'] = run_id
        save(out / (name + '.command.json'), {'argv': argv, 'run_id': run_id, 'interpreter': sys.executable})
        print(json.dumps({'phase': name, 'state': 'started', 'job': ns.job}), flush=True)
        with (out / (name + '.stdout')).open('w') as stdout, (out / (name + '.stderr')).open('w') as stderr:
            result = subprocess.run(argv, env=call_env, stdout=stdout, stderr=stderr, check=False)
        save(out / (name + '.exit.json'), {'returncode': result.returncode})
        print(json.dumps({'phase': name, 'state': 'finished', 'rc': result.returncode}), flush=True)
        require(result.returncode == 0, name + ' 非零；保留原件，不自动重跑')
        return (out / (name + '.stdout')).read_text()

    command('verify_release', [sys.executable, '-B', str(release / 'verify_release.py')])
    source_ref = expected['image'].split(':')[0] + '@' + expected['image_manifest_digest']
    images = json.loads(command('image_inspect', ['docker', 'image', 'inspect', source_ref, expected['image']]))
    require(len(images) == 2 and all(image['Id'] == task['source_config_id'] and
            source_ref in image['RepoDigests'] and image['Architecture'] == 'amd64' and
            image['Os'] == 'linux' for image in images), '原来源 manifest/tag 镜像身份不符')
    cli = [sys.executable, '-B', str(repo / 'rh2/scripts/replay_grade.py')]
    command('prepare', cli + ['prepare', '--repo-root', str(repo), '--out-dir', str(out / 'prepared'),
                             '--private-dir', str(out / 'private'), '--task-ids', tid])
    summary_path = out / 'prepared/replay_summary.json'
    summary = json.loads(summary_path.read_text())
    require(summary['task_ids'] == [tid], 'prepared 非本题唯一输入')
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
    require(all(p.cpus == 2 and p.memory_bytes == 4 * 1024**3 and p.pids_limit == 512
                for p in (rollout, grader)) and grader.shm_size_bytes == 64 * 1024**2, '资源不符')
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=rollout, grader_profile=grader,
        artifacts_dir=out / 'unused', run_id=ns.job)
    view = ctx.rollout_views[tid]
    gview = ctx.grading_views[tid]
    spec = build_grading_spec_from_host_view(view=gview, image=view.public.image,
                                           image_manifest_digest=view.public.image_manifest_digest)
    actor = rollout_spec_from_view(view, time_budget_seconds=1800)
    require(actor.image == view.public.image and actor.grading_spec is None and spec.grading_revision is None,
            '原公开/私有边界或原材料不符')
    require(spec.image == view.public.image and spec.image_local_build_id is None, '原评分非来源镜像')
    actual = {'base_commit': view.public.base_commit, 'public_bundle_digest': view.public_bundle_digest,
        'grading_bundle_digest': gview.grading_bundle_digest, 'environment_package_digest': view.environment_package_digest,
        'image': view.public.image, 'image_manifest_digest': view.public.image_manifest_digest,
        'effective_test_patch_sha256': 'sha256:' + hashlib.sha256(gview.grading.test_patch.encode()).hexdigest(),
        'install_command': derive_install_command_for_bundle(gview.grading),
        'test_command': derive_test_command_for_bundle(gview.grading),
        'f2p': list(gview.grading.fail_to_pass), 'p2p': list(gview.grading.pass_to_pass), 'grading_revision': None,
        'spec_budget': {'setup': spec.env_reset_timeout_seconds, 'apply': spec.apply_timeout_seconds,
                        'test': spec.test_timeout_seconds}}
    save(out / 'consumer_readback_before_checks.json', actual)
    require(actual == expected, '远端原材料与固定本地读回不符')
    save(out / 'scope.json', {'task_id': tid, 'job_id': ns.job, 'candidate': task['candidate_name'],
        'release_manifest_sha256': config['release_manifest_sha256'], 'tools_manifest_sha256': sha(HERE / 'manifest.json'),
        'expected_reward': None, 'original_material_only': True, 'formal_cpu_accepted': False,
        'actor_executed': False, 'model_attempts': 0, 'whole_grading_seconds': 1800,
        'whole_grading_seconds_origin': 'explicit diagnostic outer deadline; original CLI default is 3600'})
    row_dir = out / task['candidate_name']
    row_dir.mkdir(exist_ok=False)
    text = command('run_' + task['candidate_name'], cli + ['run', '--prepared-summary', str(summary_path), '--task-ids', tid,
        '--candidate', 'patch:' + str(patch), '--repeat', '1', '--candidate-stage-seconds', '900',
        '--grading-deadline-seconds', '1800', '--cleanup-seconds', '120', '--image-pull-seconds', '1800',
        '--eval-log-dir', str(row_dir / 'eval_logs'), '--artifacts-dir', str(row_dir / 'artifacts'),
        '--ledger', str(row_dir / 'ledger.jsonl')], run_id=ns.job)
    rows = [json.loads(line) for line in (row_dir / 'ledger.jsonl').read_text().splitlines() if line.strip()]
    require(len(rows) == 1, '账本行数不符')
    row = rows[0]
    require(row['stage_error'] is None and row['report'] is not None, '基础设施失败不算原评分结果')
    report = row['report']
    require(report['outcome'] in ('resolved', 'unresolved') and
            report['failure_category'] in (None, 'tests_failed') and report['reward'] in (0, 1),
            '原评分未形成正常语义结果；保留基础设施/解析失败，不预报旧得分')
    # 原 source 分支没有 ledger actual ID；不为补此字段切换诊断性 local override。
    require(row['image_ref'] == expected['image'] and row['image_digest_expected'] == expected['image_manifest_digest'] and
            row['image_local_build'] is False and row['image_id_actual'] is None and row['overlay'] is None and
            row['derived_image_recipe'] is None and row['grading_revision'] is None, '原 source 评分账本身份不符')
    require(row['cleanup']['removed'] is True, '候选未收口')
    close = [json.loads(line) for line in text.splitlines() if line.startswith('{')][-1]
    require(close['rows'] == 1 and close['halted'] is None and close['aborted'] is None and
            close['final_status']['exit_code'] == 0 and not close['cleanup_failures'], '原入口未完整收口')
    residual = {}
    for surface, argv in [('containers', ['ps', '-a']), ('networks', ['network', 'ls'])]:
        check = subprocess.run(['docker', *argv, '--filter', 'label=rh2.run_id=' + ns.job, '--format', '{{.ID}}'],
                               capture_output=True, text=True, check=False)
        residual[surface] = {'returncode': check.returncode, 'stdout': check.stdout, 'stderr': check.stderr}
        save(out / 'residual.json', residual)
        require(check.returncode == 0 and not check.stdout.strip(), '自有资源未确认零残留')
    save(out / 'result.json', {'status': 'original_counterexample_completed_pending_raw_readback',
        'reward_observed': row['report']['reward'], 'expected_reward': None, 'original_material_only': True,
        'formal_cpu_accepted': False, 'actor_executed': False, 'model_attempts': 0})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
