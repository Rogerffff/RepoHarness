"""首两题的有界 CPU 对照作业。只编排已冻结入口，不改变生产实现或评分规则。"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path('/work/swegym_cpu_preprobe_20260929')
CODE = ROOT / 'code_v1/rh2'
PY = CODE / '.venv/bin/python'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', choices=['dask__dask-7656', 'pydantic__pydantic-8793'], required=True)
    args = ap.parse_args()
    iid = args.task
    inp = ROOT / 'inputs_v1' / iid
    out = ROOT / 'results' / iid / 'calibration_v1'
    out.mkdir(parents=True, exist_ok=False)
    state = {'task': iid, 'started_at': time.time(), 'steps': [], 'status': 'running'}
    env = dict(os.environ, SLIME_AGENT_CC_PLATFORM_TARBALL=str(ROOT / 'cc/claude-code-linux-x64-2.1.205.tgz'))

    def save():
        (out / 'status.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def run(name, cmd, *, cwd=CODE, more_env=None):
        step = {'name': name, 'command': [str(x) for x in cmd], 'started_at': time.time()}
        state['steps'].append(step)
        save()
        with (out / (name + '.log')).open('w') as log:
            result = subprocess.run([str(x) for x in cmd], cwd=cwd, env={**env, **(more_env or {})},
                                    stdout=log, stderr=subprocess.STDOUT)
        step.update(rc=result.returncode, finished_at=time.time())
        save()
        if result.returncode:
            raise RuntimeError(f'{name} exited {result.returncode}; preserve evidence and stop this task')

    def inspect(ref):
        return json.loads(subprocess.check_output(['docker', 'image', 'inspect', ref], timeout=60))[0]

    def grade(name, candidate, image_id, recipe):
        dest = out / name
        dest.mkdir()
        run_id = 'cpu29-cal-' + iid.replace('__', '-') + '-' + name
        run(name, [PY, CODE / 'experiments/env_recipe_repair_20260919/replay_with_install_recipe.py',
                   '--code-root', CODE, '--recipe', recipe, '--audit-dir', dest / 'recipe', '--', 'run',
                   '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task-ids', iid,
                   '--candidate', candidate, '--derived-image', image_id,
                   '--derived-image-recipe', 'cpu29-calibration-v1:' + iid,
                   '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                   '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts', '--ledger', dest / 'ledger.jsonl'],
            more_env={'MILES_RH2_RUN_ID': run_id})
        rows = [json.loads(line) for line in (dest / 'ledger.jsonl').read_text().splitlines() if line.strip()]
        if len(rows) != 1:
            raise RuntimeError('expected exactly one grading row')
        row = rows[0]
        if row.get('stage_error') or not row.get('cleanup', {}).get('removed'):
            raise RuntimeError('grading stage/cleanup requires diagnosis before more candidates')
        # 不把 0/1 当作质量验收；完整日志、参考状态和误奖仍需主审/复核读回。
        if (row.get('report') or {}).get('reward') is None:
            raise RuntimeError('no valid grade; diagnose this environment before next candidate')
        return row

    try:
        if iid.startswith('dask'):
            run('build_grader', [PY, CODE / 'experiments/base_probe_20260922/build_derived.py', '--plan',
                                 inp / 'grader_build_plan.json', '--out-dir', out / 'grader_build', '--tag-suffix', '20260929-v1'])
            grader_image = json.loads((out / 'grader_build' / iid / 'image.json').read_text())['image_id']
            run('build_actor', [PY, CODE / 'experiments/task2_swegym_dev_20260925/build_actor.py',
                                inp / 'actor_build_plan.json', '--out-dir', out / 'actor_build'])
            built = next((out / 'actor_build').glob('*/image.json'))
            actor_image = json.loads(built.read_text())['image_id']
            commands = json.loads((inp / 'public_commands.json').read_text())
            commands.extend(json.loads((inp / 'public_environment_check.json').read_text()))
            cp = out / 'public_commands.json'
            cp.write_text(json.dumps(commands, ensure_ascii=False, indent=2) + '\n')
            actor_out = out / 'actor_revised'
            run('actor_revised', [PY, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                                  '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task', iid,
                                  '--commands', cp, '--image', actor_image, '--out-dir', actor_out,
                                  '--attempt-id', 'cpu29-dask7656-revised-v1', '--stub-port', '18093', '--wall-seconds', '1800'])
            actor_record = json.loads((actor_out / 'attempt.json').read_text())
            if actor_record.get('harness_exit_code') != 0 or actor_record.get('cleanup', {}).get('residual_after_force'):
                raise RuntimeError('actor revised run incomplete or cleanup unconfirmed')
            spec = json.loads((inp / 'private_semantic_spec.template.json').read_text())
            spec['image'] = actor_image
            spec['files'] = {key: str(inp / Path(value).name) for key, value in spec['files'].items()}
            candidates = [('opaque', inp / 'opaque_dataclass.patch'), ('wrong_result_type', inp / 'wrong_result_type.patch')]
            recipe = inp / 'grader_install_recipe.json'
        else:
            buildplan = json.loads((inp / 'build_plan.json').read_text())
            context = out / 'context'
            run('fetch_wheels', ['python3', inp / 'fetch_wheels.py', context / 'wheels'])
            (context / 'Dockerfile').write_bytes((inp / 'Dockerfile.wheelhouse').read_bytes())
            base = buildplan['base_image']
            run('pull_base', ['docker', 'pull', base])
            before = inspect(base)
            if before['Id'] != buildplan['expected_base_id']:
                raise RuntimeError('immutable source image disagrees with recorded config ID')
            tag = 'rh2-cpu29/' + iid + ':wheelhouse-v1'
            run('build_grader', ['docker', 'build', '--pull=false', '--network=none', '--build-arg', 'BASE_IMAGE=' + base,
                                 '-t', tag, context])
            after = inspect(tag)
            if after['RootFS']['Layers'][:len(before['RootFS']['Layers'])] != before['RootFS']['Layers']:
                raise RuntimeError('base layers not preserved')
            grader_image = after['Id']
            (out / 'image.json').write_text(json.dumps({'base_id': before['Id'], 'base_repo_digests': before['RepoDigests'],
                                                       'image_id': grader_image, 'base_layers_preserved': True}, indent=2) + '\n')
            actor_image = before['Id']  # 原actor已经实测；wheelhouse只改变grader安装准备。
            commands = json.loads((inp / 'public_commands.json').read_text())
            commands = [c for c in commands if c['id'] in ('public_required', 'public_defaults', 'public_existing_tests')]
            experiments = json.loads((inp / 'private_quality_experiments.json').read_text())['experiments']
            boundary = next(x for x in experiments if x['id'] == 'ellipsis_existing_default_boundary')
            commands.append({'id': 'private_ellipsis_boundary', 'cmd': boundary['cmd'], 'timeout_s': 90})
            spec = {'image': actor_image, 'variants': {'base': [], 'gold': ['git apply /in/gold.patch'],
                                                     'forced_required': ['git apply /in/forced_required.patch']},
                    'files': {'gold.patch': str(inp / 'private_gold.patch'),
                              'forced_required.patch': str(inp / 'private_degenerate_force_required.patch')}, 'commands': commands}
            candidates = [('forced_required', inp / 'private_degenerate_force_required.patch')]
            recipe = inp / 'install_recipe.json'
        specpath = out / 'private_behavior_spec.json'
        specpath.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
        run('private_behavior', [PY, ROOT / 'tools_v1/private_behavior.py', specpath, '--out', out / 'private_behavior'])
        grade('noop', 'noop', grader_image, recipe)
        grade('gold', 'gold-dir:' + str(ROOT / 'gold/v1'), grader_image, recipe)
        for name, patch in candidates:
            grade(name, 'patch:' + str(patch), grader_image, recipe)
        state['status'] = 'executed_pending_review'
    except BaseException as exc:
        state['status'] = 'stopped_needs_diagnosis'
        state['error'] = repr(exc)
        raise
    finally:
        state['finished_at'] = time.time()
        save()


if __name__ == '__main__':
    main()
