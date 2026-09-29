"""Pydantic reserve6 两题 CPU：复用已审冻结入口；不修改原题、测试或评分。

root 在远端运行：python3 pydantic_reserve_followups_v1.py --task pydantic__pydantic-8567
每次新建 results/<iid>/reserve6_v1_<UTC+随机后缀>，禁止覆盖旧证据。
私有容器仅验证行为，不证明 actor 权限；最后 executed_pending_review 不是题目合格。
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
    'pydantic__pydantic-8567': {'port': 18120, 'core': '2.15.0', 'references': (1, 158), 'patches': {}},
    'pydantic__pydantic-9066': {'port': 18121, 'core': '2.16.3', 'references': (2, 367), 'patches': {}},
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
    """固定base/core下的精确预期；异常种类或发生阶段不同即停止，不机械记负对照。"""
    def need(ok, message):
        if not ok:
            raise RuntimeError(f'{iid}/{variant}/{cid}: {message}; rc={rc}')
    def marker_json(prefix):
        rows = [line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
        need(len(rows) == 1, 'structured result missing or repeated')
        return json.loads(rows[0])
    need(rc in (0, 1), 'unexpected return code')
    if cid == 'public_identity':
        need(rc == 0 and 'PY_CHECK ' in text, 'identity/import/core failed')
    elif cid == 'public_serializer_orders':
        actual = marker_json('SERIALIZER_ORDERS ')
        dumped = {'x': '0', 'y': True if variant == 'base' else '1'}
        need(actual == {'python': dumped, 'json': dumped, 'internal': [False, True]}, 'serializer values differ')
        need(rc == (1 if variant == 'base' else 0), 'serializer exit differs')
        need(('AssertionError: PUBLIC_SERIALIZER_ORDERS_FAILED' if variant == 'base' else
              'PUBLIC_SERIALIZER_ORDERS_PASS') in text, 'serializer final marker missing')
    elif cid == 'private_custom_plain':
        actual = marker_json('CUSTOM_PLAIN ')
        need(rc == 0, 'custom probe did not complete')
        if variant == 'base':
            need(actual == {'stage': 'constructed', 'same_object': True, 'config': {}}, 'base custom construction differs')
        else:
            need(actual.get('stage') == 'class_definition' and
                 actual.get('error') == 'PydanticSchemaGenerationError' and
                 actual.get('code') == 'schema-for-unknown-type' and
                 actual.get('message', '').startswith("Unable to generate pydantic-core schema for <class '__main__.Custom'>."),
                 'gold custom error is not the predicted class-construction failure')
    elif cid == 'public_ip_default':
        actual = marker_json('IP_DEFAULT ')
        prop = actual['schema']['properties']['ip']
        need(prop.get('type') == 'string' and prop.get('format') == 'ipvanyaddress', 'IP schema identity differs')
        if variant == 'base':
            need('default' not in prop and actual['warnings'] == [{
                'category': 'PydanticJsonSchemaWarning',
                'message': 'Default value 127.0.0.1 is not JSON serializable; excluding default from JSON schema [non-serializable-default]'}],
                'base IP warning/default differs')
            need(rc == 1 and 'AssertionError: PUBLIC_IP_DEFAULT_FAILED' in text, 'base IP not precise assertion failure')
        else:
            need(prop.get('default') == '127.0.0.1' and actual['warnings'] == [] and
                 rc == 0 and 'PUBLIC_IP_DEFAULT_PASS' in text, 'gold IP goal not satisfied')
    elif cid == 'private_dataclass_default':
        actual = marker_json('DATACLASS_DEFAULT ')
        need(rc == 0 and actual.get('warnings') == [], 'dataclass probe incomplete or unexpected warning')
        if variant == 'base':
            need(actual.get('stage') == 'schema_generated' and
                 actual.get('schema', {}).get('properties', {}).get('data', {}).get('default') == {'x': 1},
                 'base dataclass default was not encoded')
        else:
            need(actual.get('stage') == 'model_json_schema' and actual.get('error') == 'PydanticUserError' and
                 actual.get('code') == 'type-adapter-config-unused' and
                 actual.get('message', '').startswith('Cannot use `config` when the type is a BaseModel, dataclass or TypedDict.'),
                 'gold dataclass error differs from predicted config conflict')
    elif cid.startswith('public_existing'):
        need(rc == 0 and re.search(r'\b[1-9]\d* passed\b', text), 'existing tests not completed successfully')
        need(not re.search(r'\b\d+ (?:failed|errors?)\b|ERROR collecting|no tests ran', text, re.I),
             'existing tests have failures or infrastructure errors')
    else:
        raise RuntimeError('unrecognized command: ' + cid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, choices=sorted(CONFIG))
    args = parser.parse_args()
    iid, cfg = args.task, CONFIG[args.task]
    inp = ROOT / 'inputs_reserve6_v1' / iid
    run_key = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:6]
    out = ROOT / 'results' / iid / ('reserve6_v1_' + run_key)
    out.mkdir(parents=True, exist_ok=False)
    state = {'task': iid, 'started_at': time.time(), 'status': 'running', 'steps': [],
             'scope': 'CPU deterministic actor development + private root behavior + original formal references',
             'resources': {'cpus': 2, 'memory_bytes': 4 * 1024**3,
                           'basis': '本两题09-19 pydantic-install-v1记录均为2CPU/4GiB；不扩大资源'},
             'remaining': ['独立复核；正式题面/public_hints交付未由devcheck控制消息证明',
                           '公开诊断不替正式参考修订；示例拟合/退化质量限制按题判断',
                           '具体gold兼容回归需原件审阅，不因目标参考通过认证完整修复',
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
                        step['cleanup_unconfirmed'] = True
                        save()
                        os.killpg(process.pid, signal.SIGKILL)
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            step.update(rc=process.returncode, finished_at=time.time(), interrupted=True,
                                        error='process did not exit within 30 seconds after SIGKILL')
                            save()
                            raise
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
        dest = out / 'actor_original'
        run('actor_original', [PYTHON, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                              '--prepared-summary', ROOT / 'prepared/reserve6_v1/replay_summary.json', '--task', iid,
                              '--commands', inp / 'public_commands.json', '--image', base_id, '--out-dir', dest,
                              '--attempt-id', 'cpu29-reserve6-' + iid.split('-')[-1] + '-' + run_key,
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
        state['actor_interpretation'] = '公开目标精确复现，回归命令完成；不以all_match_expect替代语义核对'
        save()

    def private_variant(variant, patch, base_id, commands):
        selected = [c for c in commands if c['id'] != 'public_identity']
        selected += read_json(inp / 'private_extra_commands.json')
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
        source_path = ('pydantic/functional_validators.py' if iid.endswith('8567') else
                       'pydantic/json_schema.py')
        steps.append("python - <<'PY'\nimport hashlib,json,pathlib\n" +
                     f"p=pathlib.Path({source_path!r})\n" +
                     "data=p.read_bytes()\n" +
                     "print('PRIVATE_SOURCE_SHA256',json.dumps(dict(path=str(p),bytes=len(data)," +
                     "sha256=hashlib.sha256(data).hexdigest())))\nPY")
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
        require(all(p.get('rc') == 0 for p in record.get('preparation', [])), 'private preparation failed')
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
                             '--prepared-summary', ROOT / 'prepared/reserve6_v1/replay_summary.json', '--task-ids', iid,
                             '--candidate', candidate, '--derived-image', grader_id,
                             '--derived-image-recipe', 'cpu29-pydantic-reserve6-v1:' + iid,
                             '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                             '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts',
                             '--ledger', dest / 'ledger.jsonl'],
            more_env={'MILES_RH2_RUN_ID': 'cpu29-reserve6-' + iid.split('-')[-1] + '-' + name + '-' + run_key})
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
        endings = []
        for line in (out / ('grade_' + name + '.log')).read_text().splitlines():
            try:
                event = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(event, dict) and 'manager_close' in event:
                endings.append(event)
        require(len(endings) == 1, 'manager close receipt missing/ambiguous')
        end = endings[0]
        close, final = end.get('manager_close') or {}, end.get('final_status') or {}
        require(close.get('containers_open') == [] and close.get('supply_open') == [] and
                close.get('cleanup_failures') == [] and
                close.get('containers_created_total') == close.get('containers_removed_total') == 1 and
                end.get('cleanup_failures') == [] and final.get('exit_code') == 0 and
                final.get('grader_containers_open') == [] and final.get('cleanup_failures_total') == 0,
                'manager cleanup incomplete; stop task')
        (dest / 'manager_close_checked.json').write_text(json.dumps(end, ensure_ascii=False, indent=2) + '\n')
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
                                 'pydantic_reserve_followups_v1.py': digest(Path(__file__))}
        build = read_json(inp / 'build_plan.json')
        require(build['expected_core'] == cfg['core'], 'task/core mismatch')
        base = build['base_image']
        require('@sha256:' in base, 'base must use fixed registry digest')
        run('pull_base', ['docker', 'pull', base], timeout=2400)
        before = inspect_image(base, 'base_inspect.json')
        require(before['Id'] == build['expected_base_id'], 'base config ID mismatch')
        commands = read_json(inp / 'public_commands.json')
        actor(before['Id'], commands)
        gold = inp / 'private_gold.patch'
        require(digest(gold) == digest(ROOT / 'gold/reserve6_v1' / (iid + '.gold.patch')), 'behavior/formal gold differs')
        variants = [('base', None), ('gold', gold)] + [(name, inp / filename) for name, filename in cfg['patches'].items()]
        for name, patch in variants:
            private_variant(name, patch, before['Id'], commands)
        context = out / 'build_context'
        run('fetch_wheels', ['python3', inp / 'fetch_wheels.py', context / 'wheels'], timeout=1200)
        (context / 'Dockerfile').write_bytes((inp / 'Dockerfile.wheelhouse').read_bytes())
        tag = 'rh2-cpu29/' + iid + ':reserve6-' + run_key.lower()
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
        grade('gold', 'gold-dir:' + str(ROOT / 'gold/reserve6_v1'), after['Id'], rp)
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
