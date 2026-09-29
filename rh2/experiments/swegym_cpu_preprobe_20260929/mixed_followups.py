"""本批五题逐题CPU编排；只调用code_v1冻结入口，不改题面、测试或评分语义。

远端调用：python mixed_followups.py --task <ID> [--attempt mixed_v1]
私有root行为不是actor权限证明。状态executed_pending_review不授予训练资格。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
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
TASKS = {
    'Project-MONAI__MONAI-2446': (18099, 'degenerate_array_no_shuffle.patch'),
    'Project-MONAI__MONAI-5932': (18100, 'degenerate_reverse_order.patch'),
    'conan-io__conan-11594': (18101, 'degenerate_drop_config.patch'),
    'getmoto__moto-5406': (18102, 'degenerate_constant_east2.patch'),
    'getmoto__moto-6114': (18103, 'degenerate_first_object.patch'),
}
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


class Campaign:
    def __init__(self, iid, attempt):
        self.iid, self.attempt = iid, attempt
        self.port, self.mutant = TASKS[iid]
        self.inp = ROOT / 'inputs_v1' / iid
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
        required = ['public_commands.json', 'recovery.json', 'buildplan.json', 'private/gold.patch',
                    'private/' + self.mutant, 'private/behavior_commands.json', 'private/patch_validation.json']
        if self.iid.endswith('2446'):
            required += ['private/historical_recipe.json', 'wheel_manifest.json', 'Dockerfile.recovery']
        elif self.iid.endswith('6114'):
            required += ['wheel_manifest.json', 'Dockerfile.recovery']
        elif self.iid.startswith('conan'):
            required += ['private/reference_bindings.json']
        for rel in required:
            require(rel in manifests and digest(self.inp / rel) == manifests[rel]['sha256'], f'input hash mismatch: {rel}')
        self.validations = {x['patch']: x for x in load(self.inp / 'private/patch_validation.json')}
        self.recovery = load(self.inp / 'recovery.json')
        views = [json.loads(line) for line in (ROOT / 'prepared/v1/rollout_task_views.jsonl').read_text().splitlines() if line.strip()]
        matches = [x['public'] for x in views if x['instance_id'] == self.iid]
        require(len(matches) == 1, 'prepared public view missing/ambiguous')
        self.public = matches[0]
        require(self.recovery['source_image'].split('@')[-1] == self.public['image_manifest_digest'],
                'recovery source manifest differs from prepared task')
        self.plan = load(self.inp / 'buildplan.json')
        self.commands = load(self.inp / 'public_commands.json')
        self.gold = ROOT / 'gold/v1' / (self.iid + '.gold.patch')
        require(self.gold.read_bytes() == (self.inp / 'private/gold.patch').read_bytes(), 'gold/v1 disagrees with validated gold')
        self.state['inputs'] = {rel: manifests[rel]['sha256'] for rel in required}
        self.state['private_runner_sha256'] = digest(ROOT / 'tools_v1/private_behavior.py')
        self.state['code_sha256'] = FROZEN
        self.save()

    def actor(self, name, image, *, require_expected):
        dest = self.out / name
        self.run(name, [PY, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                       '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task', self.iid,
                       '--commands', self.inp / 'public_commands.json', '--image', image, '--out-dir', dest,
                       '--attempt-id', 'cpu29-' + self.iid.lower().replace('__', '-') + '-' + self.attempt + '-' + name,
                       '--stub-port', self.port, '--wall-seconds', '1800'], timeout=2160)
        rec = load(dest / 'attempt.json')
        cleanup = rec.get('cleanup') or {}
        require(rec.get('harness_exit_code') == 0 and rec.get('result') == 'ran', 'actor harness incomplete')
        require(cleanup.get('residual_after_force') == [] and not cleanup.get('network_failures')
                and not cleanup.get('relay_failures'), 'actor cleanup unconfirmed')
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
            self.verify_target_evidence(dest)

    def verify_target_evidence(self, dest):
        # nonzero只能在目标已执行的证据存在时作为base复现，不能用import/工具错误充数。
        cap = dest / 'captures'
        requirements = {
            'Project-MONAI__MONAI-2446': ('public_smartcache', ['SMARTCACHE_RESULTS=', 'public input ownership/shuffle requirement failed']),
            'Project-MONAI__MONAI-5932': ('short_first', ['SyntaxError', 'num_epochs']),
            'conan-io__conan-11594': ('real_cmake', ['RUN_TESTS', 'unknown target']),
            'getmoto__moto-5406': ('us_east_2', ['ARN_OBSERVATION=', 'us-east-1', 'us-east-2']),
            'getmoto__moto-6114': ('target_identity', ['EXPECTED_TARGET', 'DBClusterNotFound']),
        }
        cid, tokens = requirements[self.iid]
        text = (cap / (cid + '.out')).read_text()
        require(all(t in text for t in tokens), 'base nonzero lacks task-specific behavior evidence: ' + cid)

    def build_known_repair(self, base):
        dest = self.out / 'dependency_build'
        dest.mkdir()
        wheels = dest / 'wheels'
        wheels.mkdir()
        if self.iid.endswith('2446'):
            pins, wheel_dir = ['nibabel==4.0.2'], '/opt/rh2/compat-wheels'
        else:
            require(self.iid.endswith('6114'), 'no authorized historical dependency build for task')
            pins, wheel_dir = ['setuptools==72.1.0', 'wheel==0.43.0', 'packaging==24.1'], '/opt/rh2/build-wheels'
        manifest = load(self.inp / 'wheel_manifest.json')
        name = 'cpu29-download-' + self.iid.lower().replace('__', '-') + '-' + self.attempt
        try:
            self.run('download_wheels', ['docker', 'run', '--name', name, '--rm', '--cpus', '1', '--memory', '2g',
                     '--network', 'bridge', '--label', 'rh2.cpu29.owner=' + name, '--entrypoint',
                     '/opt/miniconda3/envs/testbed/bin/python', '-e', 'PIP_NO_INDEX=0', '-v', str(wheels) + ':/cache',
                     base['Id'], '-I', '-m', 'pip', 'download', '--index-url', 'https://pypi.org/simple',
                     '--only-binary=:all:', '--no-deps', '-d', '/cache', *pins], timeout=1200)
        finally:
            rm = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True, timeout=120)
            left = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=^/' + name + '$', '--format', '{{.Names}}'],
                                  capture_output=True, text=True, timeout=60)
            write(dest / 'download_cleanup.json', {'rm_rc': rm.returncode, 'query_rc': left.returncode,
                                                  'remaining': left.stdout.split(), 'stderr': rm.stderr})
            require(left.returncode == 0 and not left.stdout.strip(), 'download cleanup unconfirmed')
        require({p.name for p in wheels.iterdir()} == {x['name'] for x in manifest}, 'unexpected/missing wheel files')
        for item in manifest:
            f = wheels / item['name']
            require(digest(f) == item['sha256'] and f.stat().st_size == item['bytes'], 'historical wheel mismatch')
        dockerfile = 'ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ ' + wheel_dir + '/\n'
        if self.iid.endswith('2446'):
            # 历史compat只COPY；本次actor需要同一解释器预装NiBabel。grader仍消费原compat安装配方。
            dockerfile += 'RUN /opt/miniconda3/envs/testbed/bin/python -I -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps nibabel==4.0.2\n'
        else:
            dockerfile += 'ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n'
        require(dockerfile == (self.inp / 'Dockerfile.recovery').read_text(), 'reviewed Dockerfile changed')
        (dest / 'Dockerfile').write_text(dockerfile)
        tag = 'rh2-cpu29/' + self.iid.lower().replace('__', '-') + ':' + self.attempt
        self.run('build_dependencies', ['docker', 'build', '--pull=false', '--network=none', '--force-rm',
                                       '--build-arg', 'BASE_IMAGE=' + self.recovery['source_image'], '-t', tag, dest], timeout=1200)
        built = self.inspect(tag)
        require(built['RootFS']['Layers'][:len(base['RootFS']['Layers'])] == base['RootFS']['Layers'], 'base layers changed')
        write(dest / 'image.json', {'base': base, 'derived': built, 'pins': pins, 'dockerfile_sha256': digest(dest / 'Dockerfile'),
                                   'meaning': 'dependency restoration only; actual actor revalidation follows'})
        return built['Id']

    def private_behavior(self, image):
        variants, files = {}, {}
        identity = next(x['cmd'] for x in self.commands if x['id'] == 'identity')
        for name, patch in [('base', None), ('gold', 'gold.patch'), ('degenerate', self.mutant)]:
            validation = self.validations[patch or 'gold.patch']
            checks = [(validation['path'], validation['source_sha256'])]
            steps = ['git config --global --add safe.directory /testbed', identity, hash_check(checks)]
            if patch:
                files[patch] = str(self.inp / 'private' / patch)
                steps += ['git apply --check ' + shlex.quote('/in/' + patch), 'git apply ' + shlex.quote('/in/' + patch),
                          hash_check([(validation['path'], validation['applied_sha256'])])]
            variants[name] = steps
        spec = {'image': image, 'cpus': 2, 'memory': '4g', 'variants': variants, 'files': files,
                'commands': load(self.inp / 'private/behavior_commands.json')}
        specpath = self.out / 'private_behavior_spec.json'
        write(specpath, spec)
        self.run('private_behavior', [PY, ROOT / 'tools_v1/private_behavior.py', specpath, '--out', self.out / 'private_behavior'], timeout=3600)
        summary = load(self.out / 'private_behavior/summary.json')
        require(set(summary.get('variants', {})) == set(variants), 'missing private variants')
        for name, rec in summary['variants'].items():
            require(rec.get('status') == 'executed_interpret_separately', 'private execution incomplete')
            require(all(x['rc'] == 0 for x in rec['preparation']), 'private prep failed')
            cleanup = rec.get('cleanup') or {}
            require(cleanup.get('query_rc') == 0 and cleanup.get('remaining') == [], 'private cleanup unconfirmed')
            require(len(rec['commands']) == len(spec['commands']) and all(x['rc'] not in (124, 137) for x in rec['commands']),
                    'private behavior incomplete/timed out')
            if name == 'gold':
                require(all(x['rc'] == 0 for x in rec['commands']), 'gold public behavior failed; diagnose before formal scoring')
        # base/退化候选的目标失败是数据，不自动改变评分；最终仍需读取具体行为日志。
        self.state['private_behavior'] = str(self.out / 'private_behavior/summary.json')
        self.save()

    def grade(self, kind, image):
        dest = self.out / ('grade_' + kind)
        dest.mkdir()
        run_id = 'cpu29-' + self.iid.lower().replace('__', '-') + '-' + self.attempt + '-' + kind
        patchname = {'gold': 'gold.patch', 'degenerate': self.mutant}.get(kind)
        candidate = 'noop' if kind == 'noop' else ('gold-dir:' + str(ROOT / 'gold/v1') if kind == 'gold'
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
        cmd += ['run', '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task-ids', self.iid,
                '--candidate', candidate, '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '1800',
                '--cleanup-seconds', '120', '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts',
                '--ledger', dest / 'ledger.jsonl']
        if self.plan['mode'] == 'rebuild_dependency_image':
            cmd += ['--derived-image', image, '--derived-image-recipe', 'cpu29-' + self.attempt + ':' + self.iid]
        name = 'grade_' + kind
        self.run(name, cmd, timeout=3180, more_env={'MILES_RH2_RUN_ID': run_id})
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
        require(install.get('install_rc_last_command') == 0 and install.get('log_partial') is False, 'install/log incomplete')
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
        require(not footer.get('halted') and not footer.get('aborted') and not footer.get('cleanup_failures')
                and not footer.get('manager_close', {}).get('containers_open')
                and footer.get('final_status', {}).get('exit_code') == 0, 'driver cleanup/status unconfirmed')
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
        self.run('pull_public_tag', ['docker', 'pull', self.public['image']], timeout=3600)
        require(self.inspect(self.public['image'])['Id'] == base['Id'], 'public tag no longer matches pinned source')
        write(self.out / 'original_image.json', base)
        known_repair = self.plan['mode'] == 'rebuild_dependency_image'
        self.actor('actor_original', base['Id'], require_expected=not known_repair)
        image = base['Id']
        if known_repair:
            image = self.build_known_repair(base)
            self.actor('actor_revised', image, require_expected=True)
        # Conan若缺CMake/Ninja在actor阶段停止，候选新pin没有历史验收，不自动套15422或新策略。
        self.private_behavior(image)
        for kind in ['noop', 'gold', 'degenerate']:
            self.grade(kind, image)
        if self.iid.endswith('5406'):
            self.state['remaining'].append('完整题面Stream/SSE/TableClass组合尚未核；本次先核ARN核心与East1反例')
        self.state['status'] = 'executed_pending_review'


def hash_check(entries):
    code = 'from pathlib import Path\nimport hashlib,json\nchecks=' + repr(entries) + '\n'
    code += "for path,expected in checks:\n actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()\n print('SOURCE_SHA',path,actual)\n assert actual==expected,(path,actual,expected)\n"
    return 'python -c ' + shlex.quote(code)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', choices=TASKS, required=True)
    ap.add_argument('--attempt', default='mixed_v1')
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
