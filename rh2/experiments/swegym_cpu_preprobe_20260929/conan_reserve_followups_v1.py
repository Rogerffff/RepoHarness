"""reserve6 Conan13230/13721 CPU编排；只调用code_v1冻结入口，不改题面、测试或评分语义。

远端调用：python conan_reserve_followups_v1.py --task <ID> [--attempt reserve6-v1]
私有root行为不是actor权限证明。状态executed_pending_review不授予训练资格。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import inspect
import json
import os
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path('/work/swegym_cpu_preprobe_20260929')
CODE = ROOT / 'code_v1/rh2'
PY = CODE / '.venv/bin/python'
TASKS = {'conan-io__conan-13230': (18106, 'android_only.patch'),
         'conan-io__conan-13721': (18107, 'realpath_name.patch')}
FROZEN = {
    'scripts/replay_grade.py': 'd36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3',
    'experiments/task2_swegym_dev_20260925/devcheck.py': '75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160',
    'experiments/env_recipe_repair_20260919/replay_with_install_recipe.py': 'fc570d892f9189292e8502e8bb69351e723d56f340f71a8298455c58ab761dc9',
    'src/repoharness2/adapters/slime/replay_grade.py': '011dd5f5e22c642f3a1f8661fa9103d8d493e17a3e5b989fd276b9af3af02e8f',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def check_observation(iid, variant, cid, rc, text):
    # 此函数也原样进入私有matrix；任何未知异常、超时或未执行测试都停止本题。
    if rc != 0 or re.search(r'ModuleNotFoundError:|ImportError:|ERROR collecting|INTERNALERROR|no tests ran', text):
        raise RuntimeError(f'{variant}/{cid}: command incomplete rc={rc}')
    if cid == 'identity':
        if 'PUBLIC_IDENTITY_COMPLETE' not in text:
            raise RuntimeError('identity did not finish')
        return
    if cid == 'public_regression':
        count = 34 if iid.endswith('13230') else 6
        if not re.search(r'\b' + str(count) + r' passed\b', text) or re.search(r'\b\d+ (?:failed|errors?|skipped)\b', text):
            raise RuntimeError('public old module count/outcome changed')
        return
    if cid != 'public_profiles' or 'PUBLIC_PROFILE_DIAGNOSTIC_COMPLETE' not in text:
        raise RuntimeError('unknown/missing public diagnostic')
    lines = [line.split('=', 1)[1] for line in text.splitlines() if line.startswith('PROFILE_OBSERVATIONS=')]
    if len(lines) != 1:
        raise RuntimeError('missing/duplicate observations')
    rows = json.loads(lines[0])
    if iid.endswith('13230'):
        if [x['mode'] for x in rows] != ['issue_exact', 'explicit_sdk_diagnostic']:
            raise RuntimeError('both profile cases must execute')
        if variant == 'gold':
            valid = all(x['outcome'] == 'deliberate_flags_exception' and x['flags'] == [] for x in rows)
        else:
            valid = (rows[0]['outcome'] == 'wrong_branch_sdk_lookup' and rows[0]['flags'] is None and
                     rows[1]['outcome'] == 'deliberate_flags_exception' and
                     rows[1]['flags'] == ['-isysroot /public-diagnostic-sdk', '-arch x86_64'])
        if not valid:
            raise RuntimeError(f'{variant}: profile payload differs from registered target: {rows}')
    else:
        if [x['requested'] for x in rows] != ['alpha', 'beta'] or any(x['symlink_target'] != '_generator' for x in rows):
            raise RuntimeError('both requested symlink names must execute')
        expected = {'base': ['', ''], 'gold': ['alpha', 'beta'], 'degenerate': ['_generator', '_generator']}[variant]
        if [x['rendered'] for x in rows] != expected:
            raise RuntimeError(f'{variant}: rendered profile names differ: {rows}')


class Campaign:
    def __init__(self, iid, attempt):
        self.iid, self.attempt = iid, attempt
        self.port, self.mutant = TASKS[iid]
        self.inp = ROOT / 'inputs_reserve6_v1' / iid
        self.out = ROOT / 'results' / iid / attempt
        self.out.mkdir(parents=True, exist_ok=False)
        self.state = {'task': iid, 'attempt': attempt, 'started_at': time.time(), 'steps': [],
                      'status': 'running', 'scope': 'CPU deterministic; no solver, no qualification',
                      'remaining': ['全部新失败与skip的人工归因', '独立复核', '公共GPU入口与预算'],
                      'private_scope': 'root behavior only; not actor permissions'}
        self.env = dict(os.environ, SLIME_AGENT_CC_PLATFORM_TARBALL=str(ROOT / 'cc/claude-code-linux-x64-2.1.205.tgz'),
                        RH2_SANDBOX_CPUS='2', RH2_SANDBOX_MEMORY_BYTES=str(4 * 1024**3),
                        RH2_GRADER_CPUS='2', RH2_GRADER_MEMORY_BYTES=str(4 * 1024**3))
        self.save()

    def save(self):
        write(self.out / 'status.json', self.state)

    def run(self, name, args, *, timeout=3600, more_env=None):
        step = {'name': name, 'command': list(map(str, args)), 'started_at': time.time(), 'timeout_s': timeout}
        self.state['steps'].append(step)
        self.save()
        proc = None
        try:
            with (self.out / (name + '.log')).open('w') as log:
                proc = subprocess.Popen(step['command'], cwd=CODE, env={**self.env, **(more_env or {})},
                                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    rc = proc.wait(timeout=timeout)
                except BaseException:
                    # 给冻结driver机会落清理证据；未确认清理时不派下个步骤。
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=180)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait(timeout=30)
                    raise
            step['rc'] = rc
            require(rc == 0, f'{name} rc={rc}; stop and inspect preserved evidence')
        except BaseException as exc:
            step['error'] = repr(exc)
            raise
        finally:
            step['finished_at'] = time.time()
            self.save()

    def docker_json(self, *args):
        return json.loads(subprocess.check_output(['docker', *args], text=True, timeout=60))

    def inspect(self, ref):
        return self.docker_json('image', 'inspect', ref)[0]

    def verify_inputs(self):
        for rel, expected in FROZEN.items():
            require(digest(CODE / rel) == expected, f'frozen source changed: {rel}')
        manifests = {x['path']: x for x in load(self.inp / 'input_manifest.json')}
        required = ['public_commands.json', 'public_repro.py', 'recovery.json', 'buildplan.json', 'private/gold.patch',
                    'private/' + self.mutant, 'private/behavior_commands.json', 'private/patch_validation.json']
        required += ['private/reference_bindings.json', 'private/evidence_binding.json']
        for rel in required:
            require(rel in manifests and digest(self.inp / rel) == manifests[rel]['sha256'], f'input hash mismatch: {rel}')
        self.validations = {x['patch']: x for x in load(self.inp / 'private/patch_validation.json')}
        self.recovery = load(self.inp / 'recovery.json')
        views = [json.loads(line) for line in (ROOT / 'prepared/reserve6_v1/rollout_task_views.jsonl').read_text().splitlines() if line.strip()]
        matches = [x['public'] for x in views if x['instance_id'] == self.iid]
        require(len(matches) == 1, 'prepared public view missing/ambiguous')
        self.public = matches[0]
        require(self.recovery['source_image'].split('@')[-1] == self.public['image_manifest_digest'],
                'recovery source manifest differs from prepared task')
        self.plan = load(self.inp / 'buildplan.json')
        self.commands = load(self.inp / 'public_commands.json')
        self.gold = ROOT / 'gold/reserve6_v1' / (self.iid + '.gold.patch')
        require(self.gold.read_bytes() == (self.inp / 'private/gold.patch').read_bytes(), 'gold/v1 disagrees with validated gold')
        self.state['inputs'] = {rel: manifests[rel]['sha256'] for rel in required}
        self.state['private_runner_sha256'] = digest(ROOT / 'tools_v1/private_behavior.py')
        self.state['code_sha256'] = FROZEN
        self.save()

    def actor(self, name, image, *, require_expected):
        dest = self.out / name
        self.run(name, [PY, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                       '--prepared-summary', ROOT / 'prepared/reserve6_v1/replay_summary.json', '--task', self.iid,
                       '--commands', self.inp / 'public_commands.json', '--image', image, '--out-dir', dest,
                       '--attempt-id', 'cpu29-' + self.iid.lower().replace('__', '-') + '-' + self.attempt + '-' + name,
                       '--stub-port', self.port, '--wall-seconds', '1800'], timeout=2160)
        rec = load(dest / 'attempt.json')
        cleanup = rec.get('cleanup') or {}
        require(rec.get('harness_exit_code') == 0 and rec.get('result') == 'ran', 'actor harness incomplete')
        require(cleanup.get('residual_after_force') == [] and not cleanup.get('network_failures')
                and not cleanup.get('relay_failures') and cleanup.get('container_rm') == 0
                and cleanup.get('stub_rc') == 0 and cleanup.get('labeled_containers_left') == []
                and cleanup.get('labeled_networks_left') == [], 'actor cleanup unconfirmed')
        checks = rec.get('checks') or {}
        for field in ['host_log_present', 'message_start_matches_stub_requests', 'result_event_present',
                      'log_complete', 'all_commands_ran']:
            require(checks.get(field) is True, 'actor evidence incomplete: ' + field)
        rows = rec.get('commands_result') or []
        require(len(rows) == len(self.commands), 'actor command count mismatch')
        require(all(x.get('rc') is not None and x['rc'] not in (124, 137) for x in rows), 'actor command timeout/not run')
        self.state.setdefault('actor_results', {})[name] = {'attempt': str(dest / 'attempt.json'),
                                                         'all_match_expect': checks.get('all_match_expect'),
                                                         'commands': rows}
        self.save()
        if require_expected:
            require(all(x.get('matches_expect') is True for x in rows), 'actor public behavior/dependency mismatch; manual diagnosis required')
            for row in rows:
                text = (dest / 'captures' / (row['id'] + '.out')).read_text()
                require(row.get('output_bytes', 200001) <= 200000, 'actor capture truncated')
                check_observation(self.iid, 'base', row['id'], row['rc'], text)

    def private_behavior(self, image):
        identity = next(x['cmd'] for x in self.commands if x['id'] == 'identity')
        commands = load(self.inp / 'private/behavior_commands.json')
        for variant, patch in [('base', None), ('gold', 'gold.patch'), ('degenerate', self.mutant)]:
            val = self.validations[patch or 'gold.patch']
            steps = ['git config --global --add safe.directory /testbed', identity,
                     hash_check([(val['path'], val['source_sha256'])])]
            files = {}
            if patch:
                files[patch] = str(self.inp / 'private' / patch)
                steps += ['git apply --check /in/' + patch, 'git apply /in/' + patch,
                          hash_check([(val['path'], val['applied_sha256'])])]
            body = ('import json,re,subprocess\n' + inspect.getsource(check_observation) + '\n' +
                    'iid=' + repr(self.iid) + '\nvariant=' + repr(variant) + '\ncommands=' + repr(commands) + '\n' +
                    "for c in commands:\n print('PRIVATE_BEGIN',c['id'],flush=True)\n" +
                    " r=subprocess.run(['bash','-c',c['cmd']],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=c['timeout_s']+10)\n" +
                    " print(r.stdout,flush=True)\n print('PRIVATE_END',c['id'],r.returncode,flush=True)\n" +
                    " check_observation(iid,variant,c['id'],r.returncode,r.stdout)\n" +
                    "print('PRIVATE_VARIANT_COMPLETE',variant,flush=True)\n")
            spec = {'image': image, 'cpus': 2, 'memory': '4g', 'variants': {variant: steps}, 'files': files,
                    'commands': [{'id': 'matrix', 'cmd': 'python -c ' + shlex.quote(body), 'timeout_s': 1000}]}
            path = self.out / ('private_' + variant + '_spec.json')
            write(path, spec)
            dest = self.out / ('private_' + variant)
            self.run('private_' + variant, [PY, ROOT / 'tools_v1/private_behavior.py', path, '--out', dest], timeout=2400)
            rec = load(dest / 'summary.json')['variants'][variant]
            clean = rec.get('cleanup') or {}
            require(rec.get('status') == 'executed_interpret_separately' and all(x['rc'] == 0 for x in rec['preparation']), 'private prep incomplete')
            require(clean.get('rm_rc') == 0 and clean.get('query_rc') == 0 and clean.get('remaining') == [], 'private cleanup unconfirmed')
            rows = rec.get('commands') or []
            output = (dest / variant / 'matrix.out').read_text()
            require(len(rows) == 1 and rows[0]['rc'] == 0 and output.count('PRIVATE_VARIANT_COMPLETE ' + variant) == 1,
                    'private command failed/timed out or unknown target; stop before formal')
            for c in commands:
                require(output.count('PRIVATE_BEGIN ' + c['id']) == 1 and output.count('PRIVATE_END ' + c['id']) == 1,
                        'private commands incomplete')
            self.state.setdefault('private_results', {})[variant] = str(dest / 'summary.json')
            self.save()

    def grade(self, kind, image):
        dest = self.out / ('grade_' + kind)
        dest.mkdir()
        run_id = 'cpu29-' + self.iid.lower().replace('__', '-') + '-' + self.attempt + '-' + kind
        patchname = {'gold': 'gold.patch', 'degenerate': self.mutant}.get(kind)
        candidate = 'noop' if kind == 'noop' else ('gold-dir:' + str(ROOT / 'gold/reserve6_v1') if kind == 'gold'
                                                  else 'patch:' + str(self.inp / 'private' / self.mutant))
        wrapper = ROOT / 'tools_v1/replay_with_cpu_budget_v2.py'
        common = [PY, wrapper, '--setup-seconds', '900', '--budget-audit-dir', dest / 'budget', '--code-root', CODE]
        cmd = common + ['--mode', 'direct']
        if self.iid.endswith('2446') or self.iid.startswith('conan'):
            cmd = common + ['--audit-dir', dest / 'recipe', '--grading-label-prefix', run_id]
            if self.iid.endswith('2446'):
                cmd += ['--recipe', self.inp / 'private/historical_recipe.json']
            else:
                binding = self.inp / 'private/reference_bindings.json'
                require(self.iid in load(binding).get('tasks', {}), 'Conan bindings missing task map')
                cmd += ['--bindings', binding]
            cmd += ['--']
        if self.plan['mode'] == 'use_original_no_repair':
            require(self.inspect(self.public['image'])['Id'] == image, 'original image tag changed before grade')
        cmd += ['run', '--prepared-summary', ROOT / 'prepared/reserve6_v1/replay_summary.json', '--task-ids', self.iid,
                '--candidate', candidate, '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                '--cleanup-seconds', '120', '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts',
                '--ledger', dest / 'ledger.jsonl']
        if self.plan['mode'] == 'rebuild_dependency_image':
            cmd += ['--derived-image', image, '--derived-image-recipe', 'cpu29-' + self.attempt + ':' + self.iid]
        name = 'grade_' + kind
        self.run(name, cmd, timeout=5400, more_env={'MILES_RH2_RUN_ID': run_id})
        lines = [json.loads(x) for x in (dest / 'ledger.jsonl').read_text().splitlines() if x.strip()]
        require(len(lines) == 1, 'expected exactly one grading record')
        row = lines[0]
        require(row.get('stage_error') is None and row.get('cleanup', {}).get('removed') is True, 'grade stage/cleanup incomplete')
        report = row.get('report') or {}
        require(report.get('reward') in (0, 1) and not report.get('execution_failure_stage')
                and not report.get('infra_failure_detail'), 'formal grading did not complete valid target execution')
        require(row.get('reference_missing_count') == 0 and not (row.get('verdict_diagnostics') or {}).get('reference_skipped'),
                'reference missing/skipped; cannot interpret reward')
        install = row.get('install') or {}
        require(install.get('install_rc_last_command') == 0 and install.get('log_partial') is False
                and not install.get('install_failed_commands')
                and (row.get('verdict_diagnostics') or {}).get('apply_ok') is True, 'apply/install/log incomplete')
        test = row.get('test') or {}
        require(test.get('segment_completed') is True and test.get('rc') is not None, 'test segment incomplete')
        require(not row.get('runner_integrity_changed'), 'runner integrity changed')
        require((row.get('observations') or {}).get('RH2_OBS_IMPORT_PATH', '').startswith('/testbed/'),
                'grader actual package import is not recorded from candidate workspace')
        if self.plan['mode'] == 'rebuild_dependency_image':
            require(row.get('image_id_actual') == image, 'grader image does not match dependency build')
        projection = row.get('projection') or {}
        if patchname:
            validation = self.validations[patchname]
            require(projection.get('included_paths') == [validation['path']], 'unexpected projected source paths')
            patches = list((dest / 'artifacts').rglob('frozen_patch.json'))
            require(len(patches) == 1, 'missing/ambiguous frozen artifact')
            entries = [x for x in load(patches[0])['entries'] if x['path'] == validation['path']]
            require(len(entries) == 1, 'expected source bytes absent from frozen patch')
            actual = hashlib.sha256(base64.b64decode(entries[0]['content_b64'], validate=True)).hexdigest()
            require(actual == validation['applied_sha256'], 'frozen source differs from actually validated candidate')
            write(dest / 'frozen_source_checked.json', {'path': validation['path'], 'sha256': actual, 'patch': patchname})
        else:
            require(projection.get('included_paths') == [], 'noop unexpectedly changed projected files')
        footers = []
        for line in (self.out / (name + '.log')).read_text().splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and 'manager_close' in obj:
                footers.append(obj)
        require(len(footers) == 1, 'driver cleanup footer missing/ambiguous')
        footer = footers[0]
        close, final = footer.get('manager_close') or {}, footer.get('final_status') or {}
        require(not footer.get('halted') and not footer.get('aborted') and not footer.get('cleanup_failures')
                and close.get('containers_created_total') == close.get('containers_removed_total') == 1
                and close.get('containers_open') == [] and close.get('supply_open') == []
                and close.get('cleanup_failures') == [] and final.get('exit_code') == 0
                and final.get('grader_containers_open') == [] and final.get('cleanup_failures_total') == 0,
                'driver cleanup/status unconfirmed')
        write(dest / 'driver_close_checked.json', footer)
        self.state.setdefault('formal_results', {})[kind] = {'reward': report['reward'], 'test_rc': test['rc'], 'ledger': str(dest / 'ledger.jsonl')}
        self.save()
        # 正负控制异常先停；退化得1是待审查的误收证据，不阻止该题完成取证。
        if kind in ('noop', 'gold'):
            require(report['reward'] == (1 if kind == 'gold' else 0), kind + ' control changed; diagnose')
        if report['reward'] == 1:
            require(test['rc'] == 0, 'reward=1 but complete test command failed; diagnose before next candidate')

    def execute(self):
        self.verify_inputs()
        source = self.recovery['source_image']
        self.run('pull_original', ['docker', 'pull', source], timeout=3600)
        base = self.inspect(source)
        # 正式candidate入口仍取prepared公开tag；另拉并核同一ID，不凭tag名字相信内容。
        tag_info = subprocess.run(['docker', 'image', 'inspect', self.public['image']], capture_output=True, text=True, timeout=60)
        if tag_info.returncode:
            # 官方prepared仍消费公开tag；只将已按immutable digest拉取的同一镜像建立本地别名。
            self.run('alias_original', ['docker', 'tag', base['Id'], self.public['image']], timeout=60)
        require(self.inspect(self.public['image'])['Id'] == base['Id'], 'public tag conflicts with immutable source')
        write(self.out / 'original_image.json', base)
        require(self.plan['mode'] == 'use_original_no_repair', 'new dependency repair requires evidence and separately versioned input')
        self.actor('actor_original', base['Id'], require_expected=True)
        image = base['Id']
        self.private_behavior(image)
        for kind in ['noop', 'gold', 'degenerate']:
            self.grade(kind, image)
        self.state['status'] = 'executed_pending_review'


def hash_check(entries):
    code = 'from pathlib import Path\nimport hashlib,json\nchecks=' + repr(entries) + '\n'
    code += "for path,expected in checks:\n actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()\n print('SOURCE_SHA',path,actual)\n assert actual==expected,(path,actual,expected)\n"
    return 'python -c ' + shlex.quote(code)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', choices=TASKS, required=True)
    ap.add_argument('--attempt', default='reserve6-v1')
    ns = ap.parse_args()
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,15}', ns.attempt.replace('_', '-')) is not None,
            'attempt must be a short lowercase identifier')
    # 保持Docker tag/attempt-id兼容，旧结果目录不覆盖。
    ns.attempt = ns.attempt.replace('_', '-')
    campaign = Campaign(ns.task, ns.attempt)

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        campaign.execute()
    except BaseException as exc:
        campaign.state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        campaign.state['finished_at'] = time.time()
        campaign.save()


if __name__ == '__main__':
    main()
