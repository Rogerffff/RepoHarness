"""5706 症状诊断 v2：复用已验 actor 身份/回归，只补跑一条公开症状命令。

root远端运行：python3 pydantic5706_symptom_followup_v2.py --task pydantic__pydantic-5706
每次新建 results/pydantic__pydantic-5706/symptom_v2_<UTC+随机后缀>。
固定core0.31.0异常不同于题面core0.25.0；P5不解除，原材料不修改。
随后私有三方、8公开wheel层、原正式三方；executed_pending_review不等于合格。
"""
import argparse
import hashlib
import inspect
import json
import os
import re
import signal
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path('/work/swegym_cpu_preprobe_20260929')
CODE = ROOT / 'code_v1/rh2'
PYTHON = CODE / '.venv/bin/python'
CONFIG = {
    'pydantic__pydantic-5662': {'port': 18096, 'core': '0.27.0', 'references': (1, 127), 'patches': {
        'all_nonmodels_equal': 'private_degenerate_all_nonmodels_equal.patch',
        'any_only': 'private_any_only.patch'}},
    'pydantic__pydantic-6283': {'port': 18097, 'core': '0.42.0', 'references': (1, 38), 'patches': {
        'validate_construct': 'private_degenerate_validate_construct.patch'}},
    'pydantic__pydantic-5706': {'port': 18098, 'core': '0.31.0', 'references': (2, 273), 'patches': {
        'sequence_list': 'private_source_only_sequence_list.patch'}},
}
# 已逐字核对本批 frozen_code_v1；启动前只核这些直接入口，不导入历史项目。
FROZEN = {
    'experiments/task2_swegym_dev_20260925/devcheck.py': '75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160',
    'experiments/env_recipe_repair_20260919/replay_with_install_recipe.py': 'fc570d892f9189292e8502e8bb69351e723d56f340f71a8298455c58ab761dc9',
    'scripts/replay_grade.py': 'd36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3',
    'src/repoharness2/adapters/slime/sandbox_profile.py': '5adce65d22a0bb056f4834d4ce94b8f79222a087e70f8d7fef2a4194bc9afb1b',
}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_behavior_result(iid, variant, cid, rc, text):
    """只认已定位行为；v2仅修正5706固定core0.31的诊断异常预期。"""
    if rc not in (0, 1):
        raise RuntimeError(f'{variant}/{cid}: unexpected rc={rc}, not a behavior rejection')
    if cid == 'public_identity':
        if rc != 0 or 'PY_CHECK ' not in text:
            raise RuntimeError('identity/import/core check failed')
        return
    if cid == 'public_comparison':
        lines = [x[len('COMPARISONS '):] for x in text.splitlines() if x.startswith('COMPARISONS ')]
        if len(lines) != 1:
            raise RuntimeError('comparison target did not finish')
        actual = json.loads(lines[0])
        expected = dict(any=False, true_matcher=False, false_matcher=False,
                        unknown_matcher=False, dict=False, object=False)
        if variant == 'gold':
            expected.update(any=True, true_matcher=True)
        elif variant == 'any_only':
            expected['any'] = True
        elif variant == 'all_nonmodels_equal':
            expected = {k: True for k in expected}
        wanted_rc = 0 if variant == 'gold' else 1
        if actual != expected or rc != wanted_rc:
            raise RuntimeError(f'comparison differs from diagnosed case: {actual}, rc={rc}')
        marker = 'AssertionError' if variant == 'all_nonmodels_equal' else 'PUBLIC_COMPARISON_DELEGATION_FAILED'
        if rc == 1 and marker not in text:
            raise RuntimeError('nonzero comparison lacks the expected assertion')
        return
    if cid == 'public_root_original':
        expected_rc = 1 if variant == 'base' else 0
        marker = 'PUBLIC_ROOT_CONSTRUCTION_EQUALITY_FAILED' if variant == 'base' else 'ROOT_EQUAL True'
        if rc != expected_rc or marker not in text:
            raise RuntimeError('RootModel target differs from expected behavior')
        return
    if cid == 'private_no_validation':
        bad = variant == 'validate_construct'
        if rc != int(bad) or (bad and ('ValidationError' not in text or 'int_parsing' not in text)):
            raise RuntimeError('construct nonvalidation control failed unexpectedly')
        if not bad and 'PUBLIC_CONSTRUCT_NO_VALIDATION_OK' not in text:
            raise RuntimeError('construct nonvalidation control did not complete')
        return
    if cid == 'public_original_symptoms':
        expected = ('JSON_EXPECTED_CORE031_ERROR NotImplementedError Cannot check isinstance when '
                    'validating from json,use a JsonOrPython validator instead.')
        if rc != 0 or 'BASE_CORE031_PUBLIC_SYMPTOMS_CONFIRMED' not in text or expected not in text:
            raise RuntimeError('Sequence base symptoms not precisely reproduced')
        return
    if cid == 'public_sequence_regression':
        bad = variant == 'sequence_list'
        if rc != int(bad) or 'SEQUENCE_REGRESSION_FAILURES ' not in text:
            raise RuntimeError('Sequence regression control incomplete')
        if bad:
            for marker in ('tuple:container_or_value', 'range:rejected', 'deque:container_or_value'):
                if marker not in text:
                    raise RuntimeError('Sequence regression differs from historical source-only candidate')
        return
    if cid.startswith('public_existing') or cid == 'public_shared_construct':
        bad = ((iid.endswith('5662') and variant == 'all_nonmodels_equal') or
               (iid.endswith('6283') and variant == 'validate_construct' and cid == 'public_existing_root_tests') or
               (iid.endswith('5706') and variant == 'sequence_list'))
        if rc != int(bad) or not re.search(r'\b\d+ passed\b', text):
            raise RuntimeError('public pytest did not produce the expected completed behavior result')
        if re.search(r'\b\d+ errors?\b|ERROR collecting|no tests ran', text, re.I):
            raise RuntimeError('pytest collection/execution infrastructure requires diagnosis')
        if bad and not re.search(r'\b\d+ failed\b', text):
            raise RuntimeError('expected pytest assertion rejection was not recorded')
        return
    raise RuntimeError(f'unrecognized command: {cid}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, choices=['pydantic__pydantic-5706'])
    args = parser.parse_args()
    iid, cfg = args.task, CONFIG[args.task]
    inp = ROOT / 'inputs_extra/5706_symptom_v2'
    run_key = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:6]
    out = ROOT / 'results' / iid / ('symptom_v2_' + run_key)
    out.mkdir(parents=True, exist_ok=False)
    state = {'task': iid, 'started_at': time.time(), 'status': 'running', 'steps': [],
             'scope': 'CPU deterministic actor development + private root behavior + original formal references',
             'resources': {'cpus': 2, 'memory_bytes': 4 * 1024**3,
                           'basis': '三题09-19 install-v1均在2CPU/4GiB有效完成；不无依据扩至8GiB'},
             'remaining': ['独立复核；正式题面/public_hints交付未由devcheck控制消息证明',
                           '公开诊断不替正式参考修订；示例拟合/退化质量限制按题判断',
                           '5706支持/拒绝目标歧义与误奖分开，后检不解除P5',
                           'GPU入口、模型与预算均未在本脚本处理']}
    env = dict(os.environ, SLIME_AGENT_CC_PLATFORM_TARBALL=str(ROOT / 'cc/claude-code-linux-x64-2.1.205.tgz'),
               RH2_SANDBOX_CPUS='2', RH2_SANDBOX_MEMORY_BYTES=str(4 * 1024**3),
               RH2_GRADER_CPUS='2', RH2_GRADER_MEMORY_BYTES=str(4 * 1024**3))

    def save():
        (out / 'status.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def run(name, command, timeout=4800, more_env=None):
        step = {'name': name, 'command': [str(x) for x in command], 'started_at': time.time()}
        state['steps'].append(step)
        save()
        with (out / (name + '.log')).open('w') as log:
            process = subprocess.Popen(step['command'], cwd=CODE, env={**env, **(more_env or {})},
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = process.wait(timeout=timeout)
            except BaseException:
                # 给已有driver/private helper机会运行finally；强杀后绝不继续题内候选。
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=180)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        step['cleanup_unconfirmed'] = True
                step.update(rc=process.returncode, finished_at=time.time(), interrupted=True)
                save()
                raise
        step.update(rc=rc, finished_at=time.time())
        save()
        require(rc == 0, f'{name} rc={rc}; stop this task and preserve evidence')

    def inspect_image(ref, filename):
        result = subprocess.run(['docker', 'image', 'inspect', ref], capture_output=True, text=True, timeout=60)
        (out / filename).write_text(result.stdout + result.stderr)
        require(result.returncode == 0, 'image inspection failed')
        images = json.loads(result.stdout)
        require(len(images) == 1, 'image inspection not unique')
        return images[0]

    def actor(base_id, commands):
        dest = out / 'actor_symptom_v2'
        run('actor_symptom_v2', [PYTHON, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                              '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task', iid,
                              '--commands', inp / 'actor_symptom_commands.json', '--image', base_id, '--out-dir', dest,
                              '--attempt-id', 'cpu29-symptom-v2-' + iid.split('-')[-1] + '-' + run_key,
                              '--stub-port', str(cfg['port']), '--wall-seconds', '1800'], timeout=2400)
        a = read_json(dest / 'attempt.json')
        cleanup = a.get('cleanup') or {}
        require(a.get('harness_exit_code') == 0 and a.get('termination') == 'returned', 'actor incomplete')
        require(cleanup.get('residual_after_force') == [] and cleanup.get('container_rm') == 0 and
                cleanup.get('network_failures') == [] and cleanup.get('relay_failures') == [] and
                cleanup.get('stub_rc') == 0, 'actor cleanup unknown')
        require(read_json(dest / 'prelaunch.json').get('ok') is True and
                read_json(dest / 'activation_check.json').get('ok') is True, 'actor prelaunch/activation failed')
        require((a.get('launch_facts', {}).get('harness_log') or {}).get('log_complete') is True,
                'actor tool stream incomplete')
        rows = a.get('commands_result') or []
        require([r['id'] for r in rows] == [c['id'] for c in commands], 'actor commands missing/reordered')
        for row in rows:
            text = (dest / 'captures' / (row['id'] + '.out')).read_text()
            require(row.get('output_bytes', 200001) <= 200000, 'actor capture truncated')
            check_behavior_result(iid, 'base', row['id'], row.get('rc'), text)
        state['actor_interpretation'] = '本轮仅补验core0.31精确症状；原identity及公开回归引用先前已验原件；P5未解除'
        save()

    def private_variant(variant, patch, base_id, commands):
        selected = [c for c in commands if c['id'] != 'public_identity']
        if iid.endswith('6283'):
            selected += read_json(inp / 'private_nonvalidation_commands.json')
        if iid.endswith('5706') and variant != 'base':
            selected = [c for c in selected if c['id'] != 'public_original_symptoms']
        # 单一命令内部逐步核对；helper不解释rc，因此这里遇到异常就中止后续命令。
        body = ('import json,re,subprocess\n' + inspect.getsource(check_behavior_result) + '\n' +
                'commands=' + repr(selected) + '\n' +
                f'iid={iid!r}\nvariant={variant!r}\n' +
                "for c in commands:\n"
                " print('PRIVATE_COMMAND_BEGIN',c['id'],flush=True)\n"
                " r=subprocess.run(['bash','-c',c['cmd']],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=c['timeout_s']+15)\n"
                " print(r.stdout,flush=True)\n"
                " print('PRIVATE_COMMAND_END',c['id'],r.returncode,flush=True)\n"
                " check_behavior_result(iid,variant,c['id'],r.returncode,r.stdout)\n"
                "print('PRIVATE_VARIANT_COMPLETE',variant,flush=True)\n")
        steps = ([] if patch is None else ['git apply /in/candidate.patch'])
        steps += [next(c['cmd'] for c in commands if c['id'] == 'public_identity')]
        # 收集先验失败属于环境，不能等到正式行为失败后才解释为候选被拒绝。
        for c in selected:
            if c['cmd'].startswith('python -m pytest '):
                steps.append(c['cmd'].replace('python -m pytest ', 'python -m pytest --collect-only ', 1))
        spec = {'image': base_id, 'cpus': 2, 'memory': '4g', 'variants': {variant: steps},
                'files': {} if patch is None else {'candidate.patch': str(patch)},
                'commands': [{'id': 'private_matrix', 'cmd': "python - <<'PY'\n" + body + 'PY',
                              'timeout_s': sum(c['timeout_s'] + 15 for c in selected) + 60}]}
        sp = out / (variant + '_private_spec.json')
        sp.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
        dest = out / ('private_' + variant)
        run('private_' + variant, [PYTHON, ROOT / 'tools_v1/private_behavior.py', sp, '--out', dest], timeout=2400)
        s = read_json(dest / 'summary.json')
        require(s.get('image_id_actual') == base_id and set(s['variants']) == {variant}, 'private identity differs')
        record = s['variants'][variant]
        clean = record.get('cleanup') or {}
        require(record.get('status') == 'executed_interpret_separately' and
                clean.get('rm_rc') == 0 and clean.get('query_rc') == 0 and clean.get('remaining') == [],
                'private preparation/execution/cleanup unknown')
        require(len(record.get('commands', [])) == 1 and record['commands'][0].get('rc') == 0,
                'private matrix requires diagnosis; no further variants')
        require('PRIVATE_VARIANT_COMPLETE ' + variant in (dest / variant / 'private_matrix.out').read_text(),
                'private matrix lacks completion marker')

    def grade(name, candidate, grader_id, recipe):
        dest = out / ('grade_' + name)
        dest.mkdir()
        run('grade_' + name, [PYTHON, ROOT / 'tools_v1/replay_with_cpu_budget_v2.py', '--setup-seconds', '900',
                   '--budget-audit-dir', dest / 'budget',
                             '--code-root', CODE, '--recipe', recipe, '--audit-dir', dest / 'recipe', '--', 'run',
                             '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task-ids', iid,
                             '--candidate', candidate, '--derived-image', grader_id,
                             '--derived-image-recipe', 'cpu29-pydantic5706-symptom-v2:' + iid,
                             '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                             '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts',
                             '--ledger', dest / 'ledger.jsonl'],
            more_env={'MILES_RH2_RUN_ID': 'cpu29-symptom-v2-' + iid.split('-')[-1] + '-' + name + '-' + run_key})
        rows = [json.loads(x) for x in (dest / 'ledger.jsonl').read_text().splitlines() if x.strip()]
        require(len(rows) == 1, 'grading row missing/ambiguous')
        row = rows[0]
        report, install, test = row.get('report') or {}, row.get('install') or {}, row.get('test') or {}
        require(row.get('stage_error') is None and (row.get('cleanup') or {}).get('removed') is True,
                'grading stage/cleanup failure')
        require(install.get('install_rc_last_command') == 0 and install.get('log_partial') is False and
                test.get('segment_completed') is True and test.get('rc') in (0, 1), 'install/test segment incomplete')
        require(report.get('reward') in (0, 1) and report.get('failure_category') in (None, 'tests_failed') and
                not report.get('execution_failure_stage') and not report.get('infra_failure_detail'), 'invalid grading execution')
        require(row.get('reference_missing_count') == 0 and row.get('runner_integrity_changed') is False and
                (row.get('verdict_diagnostics') or {}).get('apply_ok') is True, 'reference/integrity unknown')
        require((report.get('f2p_total'), report.get('p2p_total')) == cfg['references'], 'frozen reference totals changed')
        obs = row.get('observations') or {}
        require(obs.get('RH2_OBS_IMPORT_PATH') == '/testbed/pydantic/__init__.py' and
                obs.get('RH2_OBS_CPU29_CORE') == cfg['core'], 'grader candidate source/core not confirmed')
        if name in ('noop', 'gold'):
            require(report['reward'] == (1 if name == 'gold' else 0), 'control outcome unexpected; review before more candidates')
        state.setdefault('grades', {})[name] = report
        save()

    try:
        save()
        for rel, sha in FROZEN.items():
            require(digest(CODE / rel) == sha, 'frozen entry changed: ' + rel)
        manifest = read_json(inp / 'input_manifest.json')
        for item in manifest['artifacts']:
            require(digest(inp / Path(item['path']).name) == item['sha256'], 'input snapshot changed: ' + item['path'])
        state['input_hashes'] = {f.name: digest(f) for f in inp.iterdir() if f.is_file()}
        state['entry_hashes'] = {**FROZEN, 'private_behavior.py': digest(ROOT / 'tools_v1/private_behavior.py'),
                                 'pydantic5706_symptom_followup_v2.py': digest(Path(__file__))}
        build = read_json(inp / 'build_plan.json')
        require(build['expected_core'] == cfg['core'], 'task/core mismatch')
        base = build['base_image']
        require('@sha256:' in base, 'base must use fixed registry digest')
        run('pull_base', ['docker', 'pull', base], timeout=2400)
        before = inspect_image(base, 'base_inspect.json')
        require(before['Id'] == build['expected_base_id'], 'base config ID mismatch')
        commands = read_json(inp / 'public_commands.json')
        # 明确引用已清理的历史 actor，不重跑已完成 identity/两组回归。
        prior_receipt = read_json(inp / 'prior_actor_evidence.json')
        prior = ROOT / prior_receipt['remote_run']
        for rel, sha in prior_receipt['files'].items():
            require(digest(prior / rel) == sha, 'prior actor evidence changed: ' + rel)
        prior_state = read_json(prior / 'status.json')
        old_actor = read_json(prior / 'actor_original/attempt.json')
        require(prior_state.get('status') == 'stopped_needs_diagnosis' and
                prior_state.get('error') == "RuntimeError('Sequence base symptoms not precisely reproduced')",
                'prior stop differs from diagnosed matcher error')
        require(old_actor.get('image') == before['Id'] and
                old_actor.get('base_commit') == '70e7e99ca1861ad71520cc8fcf1a2fb913abbc10' and
                old_actor.get('harness_exit_code') == 0 and old_actor.get('termination') == 'returned',
                'prior actor identity/execution mismatch')
        old_clean = old_actor.get('cleanup') or {}
        require(old_clean.get('container_rm') == 0 and old_clean.get('stub_rc') == 0 and
                all(old_clean.get(k) == [] for k in ('network_failures', 'relay_failures',
                     'labeled_containers_left', 'labeled_networks_left', 'residual_after_force')),
                'prior actor cleanup unknown')
        old_commands = {c['id']: c for c in old_actor['commands']}
        old_results = {c['id']: c for c in old_actor['commands_result']}
        for cid in ('public_identity', 'public_sequence_regression', 'public_existing_sequence_tests'):
            current = next(c for c in commands if c['id'] == cid)
            require(current == old_commands[cid] and old_results[cid]['rc'] == 0,
                    'reused public command or result differs: ' + cid)
            check_behavior_result(iid, 'base', cid, 0,
                                  (prior / 'actor_original/captures' / (cid + '.out')).read_text())
        state['reused_actor_evidence'] = prior_receipt
        save()
        symptom_commands = read_json(inp / 'actor_symptom_commands.json')
        require(symptom_commands == [next(c for c in commands if c['id'] == 'public_original_symptoms')],
                'actor continuation must execute only revised public symptom command')
        actor(before['Id'], symptom_commands)
        gold = inp / 'private_gold.patch'
        require(digest(gold) == digest(ROOT / 'gold/v1' / (iid + '.gold.patch')), 'behavior/formal gold differs')
        variants = [('base', None), ('gold', gold)] + [(name, inp / filename) for name, filename in cfg['patches'].items()]
        for name, patch in variants:
            private_variant(name, patch, before['Id'], commands)
        context = out / 'build_context'
        run('fetch_wheels', ['python3', inp / 'fetch_wheels.py', context / 'wheels'], timeout=1200)
        (context / 'Dockerfile').write_bytes((inp / 'Dockerfile.wheelhouse').read_bytes())
        tag = 'rh2-cpu29/' + iid + ':symptom-v2-' + run_key.lower()
        run('build_grader', ['docker', 'build', '--pull=false', '--network=none', '--build-arg', 'BASE_IMAGE=' + base,
                             '-t', tag, context], timeout=1200)
        after = inspect_image(tag, 'grader_inspect.json')
        require(after['RootFS']['Layers'][:len(before['RootFS']['Layers'])] == before['RootFS']['Layers'], 'base layers changed')
        state['images'] = {'base': before['Id'], 'grader': after['Id'], 'base_repo_digests': before['RepoDigests']}
        recipe = read_json(inp / 'install_recipe.json')
        require(recipe['instance_id'] == iid, 'recipe task mismatch')
        # 仅增加候选身份诊断，不改变安装或测试/评分；冻结wrapper支持此字段。
        recipe['post_observation_append'] = recipe.get('post_observation_append', '') + (
            '\npython -c "import pydantic_core; print(\'RH2_OBS_CPU29_CORE=\' + pydantic_core.__version__)"\n')
        rp = out / 'observed_install_recipe.json'
        rp.write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
        grade('noop', 'noop', after['Id'], rp)
        grade('gold', 'gold-dir:' + str(ROOT / 'gold/v1'), after['Id'], rp)
        for name, filename in cfg['patches'].items():
            grade(name, 'patch:' + str(inp / filename), after['Id'], rp)
        state['status'] = 'executed_pending_review'
    except BaseException as exc:
        state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        state['finished_at'] = time.time()
        save()


if __name__ == '__main__':
    main()
