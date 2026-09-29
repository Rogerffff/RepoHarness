"""Dask6626 / mypy15139 CPU 接续；只编排冻结入口，不改正式材料。

root 在远端运行；本文件作者未执行它。原 actor → 已知依赖修复及复验 → 私有行为
→ 正式 noop/gold/错误候选。两类错误候选分别为 fixed_object_empty 和 unconditional_lowercase。
私有结果及正式 reward 分列，最终状态始终 pending_review。
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path('/work/swegym_cpu_preprobe_20260929')
CODE = ROOT / 'code_v1/rh2'
PY = CODE / '.venv/bin/python'
PORTS = {'dask__dask-6626': 18094, 'python__mypy-15139': 18095}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def check_diagnostic(iid, variant, cid, rc, text):
    """只确认命令完成且抵达已定位目标；保留诊断原文，不从整体rc推断修复。"""
    if rc not in (0, 1):
        raise RuntimeError(f'{variant}/{cid}: incomplete command rc={rc}')
    if re.search(r'ImportError:|ModuleNotFoundError:|ERROR collecting|INTERNALERROR|INTERNAL ERROR|no tests ran', text):
        raise RuntimeError(f'{variant}/{cid}: import/collection/internal failure')
    if cid in ('runner_before', 'runner_after_pin', 'runner_after_editable', 'pin_pytest', 'editable'):
        if rc != 0:
            raise RuntimeError(f'{cid}: inventory/install did not complete')
    elif cid == 'identity_import':
        if rc != 0 or 'PYTHON ' not in text or '/testbed/' not in text:
            raise RuntimeError('identity/import command did not complete')
    elif cid == 'issue_two_paths':
        if rc != 0 or 'PUBLIC_COMPUTE_PASS' not in text:
            raise RuntimeError('two-path compute target did not finish')
    elif cid == 'metadata_assert':
        marker = 'AssertionError: dask_set_index' if variant == 'base' else 'PUBLIC_METADATA_PASS'
        if rc != int(variant == 'base') or 'PUBLIC_COMPUTE_PASS' not in text or marker not in text:
            raise RuntimeError('metadata target differs from diagnosed behavior')
    elif cid == 'nonexample_numeric_empty':
        bad = variant != 'gold'
        marker = 'AssertionError' if bad else 'NUMERIC_EMPTY_DTYPE_PASS'
        if rc != int(bad) or 'EXPECTED ' not in text or 'ACTUAL ' not in text or marker not in text:
            raise RuntimeError('numeric-empty dtype target differs from diagnosed behavior')
    elif cid == 'issue_original':
        # 此原例是否被gold修复尚待证据，不能预设reveal具体字符串或要求rc=0。
        if len(re.findall(r'note: Revealed type is ', text)) != 2 or not re.search(r'Found \d+ errors? in 1 file|Success: no issues found in 1 source file', text):
            raise RuntimeError('mypy original CLI did not finish both reveal targets')
    elif cid.startswith('policy_'):
        if rc != 1 or 'Incompatible types in assignment' not in text or '[assignment]' not in text or 'Found 1 error in 1 file' not in text:
            raise RuntimeError('mypy policy CLI did not finish its assignment diagnostic')
    elif cid == 'public_regression':
        if not re.search(r'\b\d+ passed\b', text) or re.search(r'\b\d+ errors?\b', text):
            raise RuntimeError('public pytest did not finish a valid test segment')
        if rc == 1 and not re.search(r'\b\d+ failed\b', text):
            raise RuntimeError('public pytest nonzero lacks completed assertion failures')
    else:
        raise RuntimeError(f'unrecognized diagnostic command {cid}')


def inventory_comparison(directory):
    """从本次真实文件清单推导变化，保留完整路径；不倒签历史完整性。"""
    snapshots = {}
    for stage in ('runner_before', 'runner_after_pin', 'runner_after_editable'):
        text = (directory / 'inventory' / (stage + '.out')).read_text()
        objects = []
        for line in text.splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and 'runner_digest' in value and 'files' in value:
                objects.append(value)
        if len(objects) != 1:
            raise RuntimeError(f'{stage}: expected exactly one complete runner inventory')
        if any('error' in row for row in objects[0]['files']):
            raise RuntimeError(f'{stage}: runner file unreadable; integrity remains unknown')
        snapshots[stage] = objects[0]

    def changes(before, after):
        left = {row['path']: row for row in before['files']}
        right = {row['path']: row for row in after['files']}
        rows = []
        for path in sorted(set(left) | set(right)):
            if left.get(path) != right.get(path):
                rows.append({'path': path, 'before': left.get(path), 'after': right.get(path)})
        return rows

    old_pre = '0f3527775c70cece62a1cb6aebd15f554bceee5d03e6f54575b5af67d5068f43'
    old_post = 'a7b7f1e4d9d840b38dcc19daa1f46d09c0cb3e558d41c91f1c5e08dcfcb509cc'
    comparison = {
        'scope': 'current controlled reconstruction; historical missing file inventory remains missing',
        'snapshots': {key: {'runner_digest': value['runner_digest'], 'versions': value['versions'],
                            'files': len(value['files'])} for key, value in snapshots.items()},
        'pin_changes': changes(snapshots['runner_before'], snapshots['runner_after_pin']),
        'editable_changes': changes(snapshots['runner_after_pin'], snapshots['runner_after_editable']),
        'historical_pre_reproduced': snapshots['runner_before']['runner_digest'] == old_pre,
        'historical_post_after_pin_reproduced': snapshots['runner_after_pin']['runner_digest'] == old_post,
        'historical_post_after_editable_reproduced': snapshots['runner_after_editable']['runner_digest'] == old_post,
    }
    dump(directory / 'runner_file_comparison.json', comparison)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=list(PORTS), required=True)
    args = parser.parse_args()
    iid = args.task
    inp = ROOT / 'inputs_v1' / iid
    out = ROOT / 'results' / iid / 'followups_v1'
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, SLIME_AGENT_CC_PLATFORM_TARBALL=str(ROOT / 'cc/claude-code-linux-x64-2.1.205.tgz'))
    state = {'task': iid, 'started_at': time.time(), 'steps': [], 'status': 'running',
             'scope': 'CPU evidence only; private root behavior is not actor qualification'}

    def save():
        dump(out / 'status.json', state)

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def run(name, command, *, more_env=None, timeout=7200):
        step = {'name': name, 'command': [str(part) for part in command], 'started_at': time.time()}
        state['steps'].append(step)
        save()
        with (out / (name + '.log')).open('w') as log:
            # 独立进程组使仅停止父PID时也能向该子作业完整转发TERM，留时间给已实现的清理。
            process = subprocess.Popen(step['command'], cwd=CODE, env={**env, **(more_env or {})},
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = process.wait(timeout=timeout)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=300)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=30)
                        step['forced_kill'] = True
                step.update(rc=process.returncode, interrupted=True, finished_at=time.time())
                save()
                # 强杀/取消不能推断容器清理，主控必须读下游清理记录并查此次作业残留。
                raise
        step.update(rc=rc, finished_at=time.time())
        save()
        if rc:
            raise RuntimeError(f'{name}: rc={rc}; stop and diagnose before continuing')

    def actor(name, commands, image=None, require_expect=False):
        command_file = out / (name + '_commands.json')
        dump(command_file, commands)
        dest = out / name
        command = [PY, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                   '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task', iid,
                   '--commands', command_file, '--out-dir', dest,
                   '--attempt-id', 'cpu29-' + iid.replace('__', '-') + '-' + name,
                   '--stub-port', str(PORTS[iid]), '--wall-seconds', '1800']
        if image:
            command.extend(['--image', image])
        run(name, command, timeout=2400)
        record = json.loads((dest / 'attempt.json').read_text())
        cleanup = record.get('cleanup') or {}
        checks = record.get('checks') or {}
        if record.get('harness_exit_code') != 0 or cleanup.get('residual_after_force') != []:
            raise RuntimeError(f'{name}: actor launch/cleanup unconfirmed')
        if not checks.get('all_commands_ran'):
            raise RuntimeError(f'{name}: at least one public command not executed')
        rows = record.get('commands_result') or []
        if [row['id'] for row in rows] != [c['id'] for c in commands]:
            raise RuntimeError(f'{name}: commands missing/reordered')
        for row in rows:
            if row.get('status') in ('not_run', 'timeout') or row.get('rc') is None or row.get('rc') in (124, 137):
                raise RuntimeError(f'{name}/{row["id"]}: execution incomplete')
            size = row.get('output_bytes')
            if not isinstance(size, int) or size > 200000:
                raise RuntimeError(f'{name}/{row["id"]}: capture incomplete/truncated')
            if require_expect:
                text = (dest / 'captures' / (row['id'] + '.out')).read_text()
                check_diagnostic(iid, 'base', row['id'], row['rc'], text)
        if require_expect and not checks.get('all_match_expect'):
            raise RuntimeError(f'{name}: repaired actor command mismatch; inspect captures before more work')
        state[name] = {'all_match_expect': checks.get('all_match_expect'),
                       'interpretation': ('completed target diagnostics; read exact output before qualification'
                                          if require_expect else 'original environment result retained; repair and recheck required')}
        save()

    def behavior(name, spec):
        # helper不会因子命令rc1/124自行停止；每个variant单独调用，在matrix内及时核对。
        dest = out / name
        dest.mkdir()
        combined = {'variants': {}}
        for variant, prep in spec['variants'].items():
            body = ('import re,subprocess\n' + inspect.getsource(check_diagnostic) + '\n' +
                    'commands=' + repr(spec['commands']) + '\n' +
                    f'iid={iid!r}\nvariant={variant!r}\n' +
                    "for c in commands:\n"
                    " print('PRIVATE_COMMAND_BEGIN',c['id'],flush=True)\n"
                    " r=subprocess.run(['bash','-c',c['cmd']],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=c['timeout_s']+15)\n"
                    " print(r.stdout,flush=True)\n"
                    " print('PRIVATE_COMMAND_END',c['id'],r.returncode,flush=True)\n"
                    " check_diagnostic(iid,variant,c['id'],r.returncode,r.stdout)\n"
                    "print('PRIVATE_VARIANT_COMPLETE',variant,flush=True)\n")
            current = {**spec, 'variants': {variant: prep}, 'commands': [{
                'id': 'matrix', 'cmd': "python - <<'PY'\n" + body + 'PY',
                'timeout_s': sum(c['timeout_s'] + 15 for c in spec['commands']) + 60}]}
            path = out / (name + '_' + variant + '_spec.json')
            dump(path, current)
            vd = dest / (variant + '_run')
            run(name + '_' + variant, [PY, ROOT / 'tools_v1/private_behavior.py', path, '--out', vd], timeout=7200)
            summary = json.loads((vd / 'summary.json').read_text())
            record = summary['variants'][variant]
            clean = record.get('cleanup') or {}
            rows = record.get('commands') or []
            text = (vd / variant / 'matrix.out').read_text()
            if (record.get('status') != 'executed_interpret_separately' or
                    clean.get('rm_rc') != 0 or clean.get('query_rc') != 0 or clean.get('remaining') != [] or
                    len(rows) != 1 or rows[0].get('rc') != 0 or
                    'PRIVATE_VARIANT_COMPLETE ' + variant not in text):
                raise RuntimeError(f'{name}/{variant}: private execution requires diagnosis')
            # 把matrix中完整单命令输出拆回原路径，供库存对比与题级复核使用。
            target = dest / variant
            target.mkdir()
            for c in spec['commands']:
                begin = 'PRIVATE_COMMAND_BEGIN ' + c['id'] + '\n'
                end = 'PRIVATE_COMMAND_END ' + c['id'] + ' '
                if text.count(begin) != 1 or text.count(end) != 1:
                    raise RuntimeError(f'{name}/{variant}/{c["id"]}: command output incomplete')
                chunk = text.split(begin, 1)[1].split(end, 1)[0]
                (target / (c['id'] + '.out')).write_text(chunk)
            combined['variants'][variant] = record
            dump(dest / 'summary.json', combined)

    def grade(name, candidate, image):
        dest = out / name
        dest.mkdir()
        run(name, [PY, ROOT / 'tools_v1/replay_with_cpu_budget_v2.py', '--setup-seconds', '900',
                   '--budget-audit-dir', dest / 'budget',
                   '--code-root', CODE, '--recipe', inp / 'grader_install_recipe.json',
                   '--audit-dir', dest / 'recipe', '--', 'run',
                   '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task-ids', iid,
                   '--candidate', candidate, '--derived-image', image,
                   '--derived-image-recipe', 'cpu29-followups-v1:' + iid,
                   '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                   '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts',
                   '--ledger', dest / 'ledger.jsonl'],
            more_env={'MILES_RH2_RUN_ID': 'cpu29-follow-' + iid.replace('__', '-') + '-' + name}, timeout=5400)
        rows = [json.loads(line) for line in (dest / 'ledger.jsonl').read_text().splitlines() if line.strip()]
        if len(rows) != 1:
            raise RuntimeError(f'{name}: expected one grading row')
        row = rows[0]
        if row.get('stage_error') or not (row.get('cleanup') or {}).get('removed'):
            raise RuntimeError(f'{name}: stage/cleanup requires diagnosis')
        report, install, test = row.get('report') or {}, row.get('install') or {}, row.get('test') or {}
        if (report.get('reward') not in (0, 1) or report.get('failure_category') not in (None, 'tests_failed') or
                install.get('install_rc_last_command') != 0 or install.get('log_partial') is not False or
                test.get('segment_completed') is not True or test.get('rc') not in (0, 1) or
                row.get('reference_missing_count') != 0 or
                (row.get('verdict_diagnostics') or {}).get('apply_ok') is not True):
            raise RuntimeError(f'{name}: install/test/reference execution incomplete')
        if name in ('noop', 'gold') and report['reward'] != int(name == 'gold'):
            raise RuntimeError(f'{name}: unexpected formal control outcome')
        state.setdefault('grades', {})[name] = report
        save()
        # 不要求Dask runner不变：本题已知pytest降级须由逐文件证据归因。
        # 原安装串末条hash-r可掩盖前条失败，完整安装日志仍须人工读回。

    try:
        commands = json.loads((inp / 'public_commands.json').read_text())
        state['input_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted(inp.iterdir()) if path.is_file()}
        private_gold = inp / 'gold.patch'
        official_gold = ROOT / 'gold/v1' / (iid + '.gold.patch')
        if private_gold.read_bytes() != official_gold.read_bytes():
            raise RuntimeError('private and official gold bytes differ; do not compare unlike candidates')
        save()
        actor('actor_original', commands)
        run('build_grader', [PY, CODE / 'experiments/base_probe_20260922/build_derived.py', '--plan',
                             inp / 'grader_build_plan.json', '--out-dir', out / 'grader_build',
                             '--tag-suffix', '20260929-followups-v1'])
        grader_image = json.loads((out / 'grader_build' / iid / 'image.json').read_text())['image_id']
        run('build_actor', [PY, CODE / 'experiments/task2_swegym_dev_20260925/build_actor.py',
                            inp / 'actor_build_plan.json', '--out-dir', out / 'actor_build'])
        image_files = list((out / 'actor_build').glob('*/image.json'))
        if len(image_files) != 1:
            raise RuntimeError('expected one actor derived image')
        actor_info = json.loads(image_files[0].read_text())
        actor_image = actor_info['image_id']
        state['actor_build_pip_check'] = {'rc': actor_info.get('pip_check_rc'),
                                           'output': actor_info.get('pip_check')}
        # pip_check是全环境诊断，具体公开命令与目标调用链才判断是否阻塞，不静默称其成功。
        actor('actor_revised', commands, actor_image, require_expect=True)
        if iid == 'dask__dask-6626':
            # COPY-only grader仍保留安装前pytest；按原配方顺序获得三个真实清单。
            inv = {'image': grader_image, 'variants': {'inventory': []},
                   'files': {'private_runner_inventory.py': str(inp / 'private_runner_inventory.py')},
                   'commands': [
                       {'id': 'runner_before', 'cmd': 'python /in/private_runner_inventory.py', 'timeout_s': 120},
                       {'id': 'pin_pytest', 'cmd': 'python -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps pytest==7.4.4', 'timeout_s': 300},
                       {'id': 'runner_after_pin', 'cmd': 'python /in/private_runner_inventory.py', 'timeout_s': 120},
                       {'id': 'editable', 'cmd': 'python -m pip install --no-deps -e .', 'timeout_s': 300},
                       {'id': 'runner_after_editable', 'cmd': 'python /in/private_runner_inventory.py', 'timeout_s': 120},
                   ]}
            behavior('runner_inventory', inv)
            inv_result = json.loads((out / 'runner_inventory/summary.json').read_text())['variants']['inventory']
            if any(command['rc'] != 0 for command in inv_result['commands']):
                raise RuntimeError('runner inventory/install command failed; cannot explain digest from this run')
            inventory_comparison(out / 'runner_inventory')
            candidate = inp / 'fixed_object_empty.patch'
            candidate_name = 'fixed_object_empty'
        else:
            candidate = inp / 'unconditional_lowercase.patch'
            candidate_name = 'unconditional_lowercase'
        spec = json.loads((inp / 'private_semantic_spec.template.json').read_text())
        spec['image'] = actor_image
        spec['files'] = {name: str(inp / Path(source).name) for name, source in spec['files'].items()}
        behavior('private_behavior', spec)
        grade('noop', 'noop', grader_image)
        grade('gold', 'gold-dir:' + str(ROOT / 'gold/v1'), grader_image)
        grade(candidate_name, 'patch:' + str(candidate), grader_image)
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
