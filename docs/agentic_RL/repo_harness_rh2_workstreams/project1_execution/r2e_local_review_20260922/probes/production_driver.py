"""隔离审查探针：复用已有 R2E 夹具镜像，执行完整 ReplayGrader 生产入口。"""
from __future__ import annotations

import asyncio
import difflib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path.cwd().parent  # 从仓库的 rh2/ 下执行；不把本机私有路径写进可复用探针。
# 每次复跑使用独立临时目录；历史 evidence 不回写。
import tempfile
OUT = Path(tempfile.mkdtemp(prefix='r2e-production-review-'))
sys.path.insert(0, str(ROOT / 'rh2/tests'))
sys.path.insert(0, str(ROOT / 'rh2/tests/grading'))
modspec = importlib.util.spec_from_file_location('r2e_fixture_data', ROOT / 'rh2/tests/grading/test_r2e_docker.py')
fx = importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(fx)

from repoharness2.adapters.slime.replay_grade import CandidateInput, ReplayBudgets, ReplayContext, ReplayGrader
from repoharness2.adapters.slime.sandbox_profile import GraderSandboxProfile, RolloutSandboxProfile
from repoharness2.envpack.environment_overlay import EnvironmentOverlayFacts, EnvironmentOverlayV1
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager, run_docker


def patch(content: str) -> str:
    old = 'def feature():\n    return "broken"\n'
    return ''.join(difflib.unified_diff(old.splitlines(keepends=True), content.splitlines(keepends=True), fromfile='a/pkg/core.py', tofile='b/pkg/core.py'))


async def main():
    image = fx.R2E_FIXTURE_IMAGE
    checked = await run_docker('image', 'inspect', '-f', '{{.Id}}', image)
    assert checked.exit_code == 0, checked.stderr
    image_id = checked.stdout.strip()
    checked = await run_docker('run', '--rm', '--network', 'none', image_id, 'git', '-C', '/testbed', 'rev-parse', 'HEAD')
    assert checked.exit_code == 0, checked.stderr
    head = checked.stdout.strip()
    cases = [
        ('noop', None, False, 60),
        ('fixed', patch(fx.SRC_FIXED), False, 60),
        ('drift', patch(fx.SRC_FIXED), True, 60),
        ('timeout', patch('import time\nprint("PRODUCTION_TIMEOUT_STARTED", flush=True)\ntime.sleep(60)\n' + fx.SRC_FIXED), False, 8),
    ]
    outputs = []
    for label, patch_text, drift, seconds in cases:
        case_dir = OUT / label
        case_dir.mkdir(exist_ok=True)
        hidden = {**fx.HIDDEN_FILES, 'runner.py': fx.RUNNER + '# expected drift\n'} if drift else None
        bundle = fx._bundle(head, hidden=hidden)
        task_id = 'r2e_gym_subset::' + bundle.instance_id
        public = SimpleNamespace(base_commit=head, image=image, image_manifest_digest='sha256:' + 'e' * 64, workdir='/testbed')
        rollout = SimpleNamespace(task_id=task_id, public=public, public_bundle_digest='sha256:' + 'd' * 64)
        grading = SimpleNamespace(task_id=task_id, instance_id=bundle.instance_id, source='r2e_gym_subset', grading=bundle)
        overlay = EnvironmentOverlayV1(
            task_id=task_id, base_image_ref=image, base_image_manifest_digest=public.image_manifest_digest,
            derived_image_ref=image, derived_image_id=image_id, recipe_id='existing-fixture-v1',
            recipe_sha256='sha256:' + 'c' * 64, built_at_utc=datetime.now(timezone.utc),
            facts=EnvironmentOverlayFacts(interpreter_relocated=True, testbed_owner='root', git_scrubbed=True,
                hidden_tests_location='/rh2_private/r2e_tests', hidden_tests_tree_sha256=bundle.hidden_tests_tree_sha256),
        )
        calls = []

        async def docker(*args, input_bytes=None):
            result = await run_docker(*args, input_bytes=input_bytes)
            info = {'args': list(args), 'rc': result.exit_code}
            if args[0] == 'exec' and 'RH2_PREFLIGHT_' in args[-1]:
                info['stdout'] = result.stdout
                info['stderr'] = result.stderr
            calls.append(info)
            return result

        rollout_profile = RolloutSandboxProfile(model_proxy_upstream_host='10.0.0.1', model_proxy_upstream_port=18001)
        grader_profile = GraderSandboxProfile()
        context = ReplayContext(manifest=None, rollout_views={task_id: rollout}, grading_views={task_id: grading},
            rollout_profile=rollout_profile, grader_profile=grader_profile, run_id='production-review-' + label,
            artifacts_dir=case_dir / 'artifacts', docker=docker, image_overlays={task_id: overlay})
        manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=case_dir / 'logs', sandbox_profile=grader_profile), docker=docker)
        grader = ReplayGrader(context, manager, ledger_path=case_dir / 'ledger.jsonl',
            budgets=ReplayBudgets(candidate_stage_seconds=60, grading_deadline_seconds=seconds, cleanup_seconds=10))
        try:
            row = await grader.replay_one(task_id, CandidateInput(kind='noop' if patch_text is None else 'gold', origin='review-fixture', patch_text=patch_text))
        finally:
            close = await manager.close()
        (case_dir / 'calls.json').write_text(json.dumps(calls, ensure_ascii=False, indent=2))
        summary = {'case': label, 'image_id': image_id, 'stage_error': row['stage_error'], 'report': row['report'],
            'candidate': row['candidate'], 'test': row['test'], 'log': row['log'], 'cleanup': row['cleanup'],
            'manager_close': close, 'preflight': [c for c in calls if 'stdout' in c],
            'container_run_images': [c['args'][-3] for c in calls if c['args'][0] == 'run']}
        outputs.append(summary)
        expected = {'noop': ('unresolved', 0.0), 'fixed': ('resolved', 1.0),
                    'drift': ('failed_to_grade', None), 'timeout': ('failed_to_grade', None)}[label]
        assert (row['report']['outcome'], row['report']['reward']) == expected
        assert row['stage_error'] is None and row['cleanup']['removed']
        assert not close['containers_open'] and not close['cleanup_failures']
        assert summary['container_run_images'] == [image_id, image_id]
        assert row['report']['grading_semantics'] == 'r2e_expected_map'
        log_text = Path(row['log']['path']).read_text()
        if label == 'drift':
            assert row['test'] is None and '>>>>> Start Test Output' not in log_text
            assert 'RH2_SETUP_ERROR=hidden_tests_tree_mismatch:' in log_text
        elif label == 'timeout':
            assert row['log']['partial'] and row['test']['segment_completed'] is False
            assert 'PRODUCTION_TIMEOUT_STARTED' in log_text and '>>>>> End Test Output' not in log_text
        else:
            assert row['test']['rc'] == 1 and row['test']['segment_completed'] is True
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    (OUT / 'results.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2))


asyncio.run(main())
