"""6114 题级薄编排：固定 R19 新37参考输入，调用原 prepare/export-gold/run。

不改评分、parser、参考或预算；源码与镜像不符时停止。输出只写本次独占目录。
SWE 派生镜像沿原 CLI --derived-image 的实际 ID 接口，不使用 R2E-only overlay。
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path('/work/rh2-category2-20261003')
RELEASE = ROOT / 'releases/cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1'
MANIFEST_SHA = '2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e'
PRODUCER_REL = 'docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest_swe40_pyd6283_moto6114_p2p_20261003_v1'
PRODUCER_SHA = 'f0154ff831d9a08fe9f2a819b08cf45068dee63657c6b8e632479a3068c9a0a7'
REGISTRY_REL = 'docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/moto6114_neptune_p2p_v2'
REGISTRY_SHA = '6aecd8d4f9eb40b0a82af7faae73121dc2a0292122876166765f9ecd4a5d8bd1'
IID = 'getmoto__moto-6114'
TID = 'swe_gym_lite::' + IID
BASE_ID = 'sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249'
IMAGE_ID = 'sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5'
SOURCE_IMAGE = 'xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6114@sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a'
NEGATIVE = ROOT / ('packages/swe_moto/preparation_v1/runs/swegym_cpu_preprobe_20260929/'
                   'task_inputs/getmoto__moto-6114/private/degenerate_first_object.patch')
NEGATIVE_SHA = '5c042121e4bf56693c71f418c139b628d108b0c1fcd67bc0af48201e471c6451'
GOLD_SHA = 'bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc'
EXACT_QWEN = RELEASE / 'repo' / REGISTRY_REL / 'source_members/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_moto/tasks/getmoto__moto-6114/neptune_name_preservation_v2/exact_qwen_a1_source.patch'
EXACT_QWEN_SHA = 'bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747'
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
    parser.add_argument('--job', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--controls', nargs='+', choices=('noop', 'gold', 'wrong_first', 'exact_qwen'), default=['noop', 'gold', 'wrong_first', 'exact_qwen'])
    ns = parser.parse_args()
    require(len(ns.controls) == len(set(ns.controls)), '候选选择重复')
    require(bool(re.fullmatch(r'moto6114-(?:bind|cpu)-[0-9a-f]{12}', ns.job)), 'job 格式不符')
    require(Path(sys.executable) == ROOT / 'runtime_cpu_v2/rh2/.venv/bin/python', '解释器不符')
    out = ROOT / 'packages/swe_moto/moto6114_r19_v1' / ns.job
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((HERE / 'manifest.json').read_text())
    actual_files = {p.name for p in HERE.iterdir() if p.is_file()}
    require(actual_files == set(manifest['files']) | {'manifest.json'}, '编排文件集合不符')
    for rel, item in manifest['files'].items():
        require(Path(rel).name == rel and not (HERE / rel).is_symlink(), '编排路径不符')
        require(sha(HERE / rel) == item['sha256'] and (HERE / rel).stat().st_size == item['bytes'], '编排文件身份不符')
    require(sha(RELEASE / 'manifest.json') == MANIFEST_SHA, '外部 release manifest 不符')
    repo = RELEASE / 'repo'
    require(sha(repo / PRODUCER_REL / 'ingest_manifest_swe_revision_v1.json') == PRODUCER_SHA, 'producer 身份不符')
    require(sha(repo / REGISTRY_REL / 'material_revisions.json') == REGISTRY_SHA, '修订 registry 不符')
    require(sha(NEGATIVE) == NEGATIVE_SHA, '反例补丁身份不符')
    require(sha(EXACT_QWEN) == EXACT_QWEN_SHA and EXACT_QWEN.stat().st_size == 6463 and not EXACT_QWEN.is_symlink(), '实际旧Qwen源码diff身份不符')
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
            result = subprocess.run(argv, env=call_env, stdout=stdout, stderr=stderr)
        save(out / (name + '.exit.json'), {'returncode': result.returncode})
        print(json.dumps({'phase': name, 'state': 'finished', 'rc': result.returncode}), flush=True)
        require(result.returncode == 0, name + ' 非零退出；停止后续候选')
        return (out / (name + '.stdout')).read_text()

    command('verify_release', [sys.executable, '-B', str(RELEASE / 'verify_release.py')])
    inspect_raw = command('image_inspect', ['docker', 'image', 'inspect', SOURCE_IMAGE, IMAGE_ID])
    base, derived = json.loads(inspect_raw)
    require(base['Id'] == BASE_ID and derived['Id'] == IMAGE_ID, '实际镜像 ID 不符')
    require(SOURCE_IMAGE in base['RepoDigests'], '来源 manifest 未匹配')
    require(all(x['Architecture'] == 'amd64' and x['Os'] == 'linux' for x in [base, derived]), '镜像平台不符')
    base_layers = base['RootFS']['Layers']
    require(derived['RootFS']['Layers'][:len(base_layers)] == base_layers, '派生镜像未保留基底层')
    require(len(derived['RootFS']['Layers']) == len(base_layers) + 1, 'COPY-only 层数不符')
    require({'PIP_NO_INDEX=1', 'PIP_FIND_LINKS=/opt/rh2/build-wheels'}.issubset(derived['Config']['Env']), '离线 wheel 环境不符')
    cli = [sys.executable, '-B', str(repo / 'rh2/scripts/replay_grade.py')]
    command('prepare', cli + ['prepare', '--repo-root', str(repo), '--out-dir', str(out / 'prepared'),
            '--private-dir', str(out / 'private'), '--task-ids', TID])
    summary_path = out / 'prepared/replay_summary.json'
    summary = json.loads(summary_path.read_text())
    require(summary['task_ids'] == [TID], 'prepared 非本题唯一任务')
    save(out / 'prepared_summary.json', summary)
    sys.path.insert(0, str(repo / 'rh2/src'))
    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view, rollout_spec_from_view
    from repoharness2.adapters.slime.replay_grade import load_context
    from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env, rollout_profile_from_env
    from repoharness2.envpack.spec_vendor import derive_install_command_for_bundle, derive_test_command_for_bundle
    rollout = rollout_profile_from_env(env, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=1)
    grader = grader_profile_from_env(env)
    for profile in [rollout, grader]:
        require(profile.cpus == 2 and profile.memory_bytes == 4 * 1024**3 and profile.pids_limit == 512, '沙箱资源不符')
    require(grader.shm_size_bytes == 64 * 1024**2, 'grader shm 不符')
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=rollout, grader_profile=grader,
        artifacts_dir=out / 'unused', run_id=ns.job)
    view = ctx.rollout_views[TID]
    gview = ctx.grading_views[TID]
    spec = build_grading_spec_from_host_view(view=gview, image=view.public.image,
                                             image_manifest_digest=view.public.image_manifest_digest)
    # SWE 沿既有实验的派生 spec 替换路径；不传 R2E-only overlay，不改公共 consumer。
    original_actor_spec = rollout_spec_from_view(view, time_budget_seconds=1800)
    actor_spec = dataclasses.replace(original_actor_spec, image=IMAGE_ID, image_manifest_digest=None, image_local_build=True)
    require(actor_spec.image == IMAGE_ID and actor_spec.image_local_build, 'SWE 派生 actor spec 未使用实际 ID')
    require(actor_spec.grading_spec is None, 'actor 暴露了私有评分面')
    expected = json.loads((HERE / 'expected_runtime.json').read_text())
    actual = dict(task_id=TID, image=view.public.image, image_manifest_digest=view.public.image_manifest_digest,
        base_commit=view.public.base_commit, public_bundle_digest=view.public_bundle_digest,
        grading_bundle_digest=gview.grading_bundle_digest, environment_package_digest=view.environment_package_digest,
        install_command=derive_install_command_for_bundle(gview.grading), test_command=derive_test_command_for_bundle(gview.grading),
        reference_counts={'f2p': len(gview.grading.fail_to_pass), 'p2p': len(gview.grading.pass_to_pass)},
        effective_test_patch_sha256='sha256:' + hashlib.sha256(gview.grading.test_patch.encode()).hexdigest(),
        context=spec.grading_revision.diagnostics(None),
        script_sha256={name: hashlib.sha256(getattr(spec, name).encode()).hexdigest() for name in expected['script_sha256']})
    save(out / 'consumer_readback_before_checks.json', actual)
    for key in ['task_id', 'image', 'image_manifest_digest', 'base_commit', 'public_bundle_digest', 'grading_bundle_digest',
                'environment_package_digest', 'install_command', 'test_command', 'reference_counts', 'effective_test_patch_sha256',
                'context', 'script_sha256']:
        require(actual[key] == expected[key], '正式消费不符：' + key)
    require(tuple(spec.hygiene.test_files) == ('tests/test_rds/test_rds_clusters.py',), '原测试恢复保护集合不符')
    require((spec.env_reset_timeout_seconds, spec.apply_timeout_seconds, spec.test_timeout_seconds) == (300, 120, 1800), '生产分段预算不符')
    actual['budgets'] = {'setup_seconds': spec.env_reset_timeout_seconds, 'apply_seconds': spec.apply_timeout_seconds,
        'test_seconds': spec.test_timeout_seconds, 'candidate_stage_seconds': 900, 'whole_grading_seconds': 1800,
        'cleanup_seconds': 120, 'image_pull_seconds': 1800}
    actual['actor_runtime_image_id'] = actor_spec.image
    actual['derived_image_recipe'] = 'moto6114_install_wave1_copy_only_20261003'
    actual['image_recipe_binding_sha256'] = sha(HERE / 'image_recipe_binding.json')
    actual['actor_image_route'] = 'existing SWE experiment dataclasses.replace; shared R2E overlay is not used'
    actual['code_manifest_sha256'] = MANIFEST_SHA
    actual['producer_manifest_sha256'] = PRODUCER_SHA
    save(out / 'runtime_inputs.json', actual)
    command('export_gold', cli + ['export-gold', '--ingest-dir', str(repo / PRODUCER_REL), '--instance-ids', IID,
                                  '--out-dir', str(out / 'gold_input')])
    require(sha(out / 'gold_input' / (IID + '.gold.patch')) == GOLD_SHA, '实际导出 gold 不符')
    save(out / 'scope.json', {'task_id': TID, 'execute': ns.execute, 'job_id': ns.job, 'release_id': RELEASE.name,
        'code_manifest_sha256': MANIFEST_SHA, 'tools_manifest_sha256': sha(HERE / 'manifest.json'),
        'original_public_unchanged': True, 'formal_cpu_accepted': False, 'model_attempts': 0, 'selected_controls': ns.controls})
    if not ns.execute:
        save(out / 'result.json', {'status': 'default_prepare_and_image_readback_passed_no_test_execution'})
        return 0
    results = []
    for name, candidate, wanted in [('noop', 'noop', 0), ('gold', 'gold-dir:' + str(out / 'gold_input'), 1),
                                   ('wrong_first', 'patch:' + str(NEGATIVE), 0), ('exact_qwen', 'patch:' + str(EXACT_QWEN), 0)]:
        if name not in ns.controls:
            continue
        run_id = ns.job + '-' + name
        row_dir = out / name
        row_dir.mkdir()
        text = command('run_' + name, cli + ['run', '--prepared-summary', str(summary_path), '--task-ids', TID,
            '--candidate', candidate, '--repeat', '1', '--candidate-stage-seconds', '900',
            '--grading-deadline-seconds', '1800', '--cleanup-seconds', '120', '--image-pull-seconds', '1800',
            '--eval-log-dir', str(row_dir / 'eval_logs'), '--artifacts-dir', str(row_dir / 'artifacts'),
            '--ledger', str(row_dir / 'ledger.jsonl'), '--derived-image', IMAGE_ID,
            '--derived-image-recipe', 'moto6114_install_wave1_copy_only_20261003'], run_id=run_id)
        rows = [json.loads(line) for line in (row_dir / 'ledger.jsonl').read_text().splitlines() if line.strip()]
        require(len(rows) == 1, '正式账本行数不符')
        row = rows[0]
        require(row['stage_error'] is None and row['report'] is not None, '正式执行出现基础设施错误')
        require(row['report']['outcome'] in ('resolved', 'unresolved') and row['report']['failure_category'] in (None, 'tests_failed') and row['report']['reward'] in (0, 1), '评分基础设施/解析失败；停止后续控制并保留原件')
        require(row['cleanup']['removed'] is True, '候选未确认移除')
        messages = [json.loads(line) for line in text.splitlines() if line.startswith('{')]
        close = messages[-1]
        require(close['rows'] == 1 and close['halted'] is None and close['aborted'] is None, '正式入口未正常收口')
        require(close['final_status']['exit_code'] == 0 and not close['cleanup_failures'], '正式入口清理失败')
        residuals = {}
        for surface, args in [('containers', ['ps', '-a']), ('networks', ['network', 'ls'])]:
            result = subprocess.run(['docker', *args, '--filter', 'label=rh2.run_id=' + run_id, '--format', '{{.ID}}'], capture_output=True, text=True)
            residuals[surface] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
            save(out / ('residual_' + name + '.json'), residuals)
            require(result.returncode == 0 and not result.stdout.strip(), '本次归属资源未确认零残留')
        results.append({'candidate': name, 'reward': row['report']['reward'], 'expected_reward': wanted,
                        'matches_expected_reward': row['report']['reward'] == wanted, 'run_id': run_id})
    save(out / 'result.json', {'status': 'selected_controls_completed_pending_raw_readback_and_independent_review', 'selected_controls': ns.controls, 'rows': results,
                              'formal_cpu_accepted': False, 'actor_executed': False})
    require(all(row['matches_expected_reward'] for row in results), '矩阵 reward 与预期不符；需分析真实失败')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
