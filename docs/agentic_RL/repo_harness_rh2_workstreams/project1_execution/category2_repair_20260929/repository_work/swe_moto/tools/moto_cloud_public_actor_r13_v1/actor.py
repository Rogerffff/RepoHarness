"""6185/7584 原公开开发操作：固定 DevRunner/CC/桩，保留完整命令输出。

补受限镜像初态探针、trusted root exec、端口独占及完整输出取回；
不复制评分器，不 export FrozenPatch，不宣称模型自主求解或训练准入。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import socket
import sys
from pathlib import Path

ROOT = Path('/work/rh2-category2-20261003')
HERE = Path(__file__).resolve().parent
CAP = '/tmp/rh2-moto-public-r13'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', choices=('6185', '7584'), required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--prepared-summary', required=True)
    parser.add_argument('--prepared-summary-sha256', required=True)
    ns = parser.parse_args()
    assert re.fullmatch('moto' + ns.instance + r'-actor-[0-9a-f]{12}', ns.job)
    assert Path(sys.executable) == ROOT / 'runtime_cpu_v2/rh2/.venv/bin/python'
    manifest = json.loads((HERE / 'manifest.json').read_text())
    assert {p.name for p in HERE.iterdir()} == set(manifest['files']) | {'manifest.json'}
    for name, pin in manifest['files'].items():
        p = HERE / name
        assert p.is_file() and not p.is_symlink() and sha(p) == pin['sha256'] and p.stat().st_size == pin['bytes']
    config = json.loads((HERE / 'tasks.json').read_text())
    task = config['tasks']['getmoto__moto-' + ns.instance]
    release = ROOT / 'releases' / config['release_id']
    repo = release / 'repo'
    assert sha(release / 'manifest.json') == config['release_manifest_sha256']
    for rel, digest in config['code_pins'].items():
        assert sha(repo / rel) == digest
    assert sha(os.environ['SLIME_AGENT_CC_PLATFORM_TARBALL']) == config['cc_sha256']
    assert os.environ.get('RH2_SANDBOX_RELAY_PORT') == str(config['gateway_port'])
    assert not any(os.environ.get(k) for k in ('RH2_IMAGE_OVERLAYS_PATH', 'RH2_IMAGE_OVERLAYS_SHA256'))
    commands_path = HERE / task['commands_file']
    assert sha(commands_path) == task['commands_sha256']
    commands = json.loads(commands_path.read_text())
    assert len(commands) == 4 and len({c['id'] for c in commands}) == 4
    assert all(re.fullmatch(r'[A-Za-z0-9_.-]{1,40}', c['id']) and c['timeout_s'] == 240 for c in commands)
    summary_path = Path(ns.prepared_summary)
    assert summary_path.is_relative_to(ROOT / 'packages/swe_moto/moto_r13_v1')
    assert sha(summary_path) == ns.prepared_summary_sha256
    summary = json.loads(summary_path.read_text())
    assert summary['task_ids'] == [task['task_id']]
    sys.path.insert(0, str(repo / 'rh2/src'))
    from repoharness2.adapters.slime.prepared_task_face import rollout_spec_from_view
    from repoharness2.adapters.slime.replay_grade import load_context
    from repoharness2.adapters.slime.sandbox_profile import (
        grader_profile_from_env,
        rollout_profile_from_env,
    )

    profile = rollout_profile_from_env(os.environ, model_proxy_upstream_host='172.17.0.1', model_proxy_upstream_port=config['stub_port'])
    assert profile.cpus == 2 and profile.memory_bytes == 4 * 1024**3 and profile.pids_limit == 512
    out = ROOT / 'packages/swe_moto/moto_public_actor_r13_v1' / ns.job
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=profile,
        grader_profile=grader_profile_from_env(os.environ), artifacts_dir=out / 'unused', run_id=ns.job)
    view = ctx.rollout_views[task['task_id']]
    spec = rollout_spec_from_view(view, time_budget_seconds=1800)
    assert spec.image == task['original_actor_image'] and spec.grading_spec is None
    assert spec.base_commit == task['base_commit'] and view.public_bundle_digest == task['public_bundle_digest']
    assert view.environment_package_digest == task['environment_package_digest']
    source = repo / 'rh2/experiments/task2_swegym_dev_20260925/devcheck.py'
    module_spec = importlib.util.spec_from_file_location('moto_r13_original_devcheck', source)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    def full_wrap(command):
        cid = command['id']
        return (f'mkdir -p {CAP}; cd /testbed; '
            f'timeout -k 10 240 /bin/bash -c {shlex.quote(command["cmd"])} > {CAP}/{cid}.full 2>&1; '
            f'rc=$?; printf "%s\\n" "$rc" > {CAP}/{cid}.rc; wc -c < {CAP}/{cid}.full > {CAP}/{cid}.bytes; '
            f'echo RH2DC_END id={cid} rc=$rc; exit 0')

    class CompleteDevRunner(module.DevRunner):
        def start_stub(self):
            with socket.socket() as probe:
                probe.bind((self.ns.stub_host, self.ns.stub_port))
            super().start_stub()
            assert self.stub.poll() is None

        async def sh(self, script, *, user='root', timeout=120.0, env=None, input_bytes=None):
            from repoharness2.grading.manager import TRUSTED_ROOT_EXEC_PREFIX

            # 旧 DevRunner 的运行后事实段带 Git；整段以 agent 执行，防止 root 读取候选控制的 Git。
            # 原文件名保留，另记录真实角色；不把旧 post_run_facts_root.txt 当 root 权限证明。
            if user == 'root' and 'RH2_GIT_STATUS_LINES=' in script and 'git status --porcelain' in script:
                user = 'agent'
                self.rec['post_run_fact_actual_role'] = 'agent_uid_54321'
                self.save()
            argv = ['exec'] + (['-i'] if input_bytes is not None else []) + ['-u', user]
            if user != 'root':
                argv.extend(['-e', 'HOME=/home/agent'])
            for key, value in (env or {}).items():
                argv.extend(['-e', key + '=' + value])
            argv.append(self.container)
            argv.extend([*TRUSTED_ROOT_EXEC_PREFIX, script] if user == 'root' else ['/bin/bash', '-c', script])
            return await self.dk(*argv, timeout=timeout, input_bytes=input_bytes)

        async def image_facts(self):
            self.docker = module.acc_docker()
            recipe = task['environment']
            source_ref = recipe['source_image'].split(':')[0] + '@' + recipe['source_image_manifest_digest']
            inspect = await self.dk('image', 'inspect', source_ref, task['runtime_image_id'], timeout=120)
            assert inspect.exit_code == 0
            base, actual = json.loads(inspect.stdout)
            assert base['Id'] == recipe['source_config_id'] and source_ref in base['RepoDigests']
            assert actual['Id'] == recipe['derived_image_id'] == task['runtime_image_id']
            assert actual['RootFS']['Layers'][:-1] == base['RootFS']['Layers']
            assert {'PIP_NO_INDEX=1', 'PIP_FIND_LINKS=/opt/rh2/build-wheels'}.issubset(actual['Config']['Env'])
            probe = await self.dk('run', '--rm', '--network', 'none', '--cpus', '2', '--memory', str(4 * 1024**3),
                '--pids-limit', '512', '--shm-size', str(64 * 1024**2), '--label', 'rh2.run_id=' + self.ns.attempt_id,
                '--entrypoint', '/bin/bash', task['runtime_image_id'], '-c',
                'cd /testbed && echo HEAD=$(git rev-parse HEAD) && echo PORCELAIN_BEGIN && git status --porcelain; echo PORCELAIN_RC=$?', timeout=300)
            assert probe.exit_code == 0 and 'HEAD=' + task['base_commit'] in probe.stdout and 'PORCELAIN_RC=0' in probe.stdout
            self.rec['image_facts'] = {'original_public_source': source_ref, 'runtime': actual['Id'],
                'copy_only_source_layers_preserved': True, 'initial_worktree': probe.stdout, 'initial_worktree_rc': probe.exit_code}
            self.rec['scope'] = task['scope']
            self.rec['model_attempts'] = 0
            self.save()

        async def collect(self):
            cap = self.out / 'captures'
            cap.mkdir(exist_ok=True)
            rows = []
            for command in self.cmds:
                cid = command['id']
                meta = await self.sh(f'cat {CAP}/{cid}.rc; echo ---; cat {CAP}/{cid}.bytes', user='agent', timeout=60)
                assert meta.exit_code == 0
                rc_text, _, count_text = meta.stdout.partition('---')
                result = await self.sh(f'cat {CAP}/{cid}.full', user='agent', timeout=120)
                assert result.exit_code == 0
                data = result.stdout.encode()
                assert len(data) == int(count_text.strip())
                (cap / (cid + '.full')).write_bytes(data)
                rc = int(rc_text.strip())
                rows.append({'id': cid, 'rc': rc, 'status': 'rc0' if rc == 0 else 'nonzero',
                    'expect': command['expect'], 'matches_expect': (command['expect'] == 'zero') == (rc == 0),
                    'output_bytes': len(data), 'output_truncated_to': None, 'full_output_sha256': sha(cap / (cid + '.full')),
                    'pytest': module.pytest_counts(result.stdout), 'purpose': command['purpose']})
            self.rec['commands_result'] = rows
            self.save()

    module.wrap = full_wrap
    module.DevRunner = CompleteDevRunner
    os.environ['MILES_RH2_RUN_ID'] = ns.job
    rc = module.main(['--prepared-summary', str(summary_path), '--task', 'getmoto__moto-' + ns.instance,
        '--commands', str(commands_path), '--image', task['runtime_image_id'], '--out-dir', str(out),
        '--attempt-id', ns.job, '--stub-host', '172.17.0.1', '--stub-port', str(config['stub_port']),
        '--wall-seconds', '1800', '--prompt', spec.prompt])
    rec = json.loads((out / 'attempt.json').read_text())
    assert rc == 0 and rec['harness_exit_code'] == 0 and rec['termination'] == 'returned'
    checks = rec['checks']
    assert all(checks.get(k) is True for k in ('host_log_present', 'message_start_matches_stub_requests', 'result_event_present', 'log_complete', 'all_commands_ran'))
    assert len(rec['commands_result']) == 4 and all(r['rc'] in (0, 1) and r['matches_expect'] for r in rec['commands_result'])
    assert rec['container_inspect'] == task['runtime_image_id'] + ' 2000000000 4294967296'
    assert rec['cleanup']['residual_after_force'] == [] and not rec['cleanup'].get('network_failures') and not rec['cleanup'].get('relay_failures')
    request_path = out / 'stub/requests/messages_000.json'
    request = json.loads(request_path.read_text())
    text = [b.get('text') for m in request['messages'] if m.get('role') == 'user'
            for b in m.get('content', []) if isinstance(b, dict) and b.get('type') == 'text']
    assert text.count(spec.prompt) == 1
    result = {'status': 'public_commands_complete_pending_behavior_and_independent_review',
        'job_id': ns.job, 'scope': task['scope'], 'public_prompt_sha256': hashlib.sha256(spec.prompt.encode()).hexdigest(),
        'actual_request_sha256': sha(request_path), 'actual_request_prompt_exact': True,
        'commands_sha256': sha(commands_path), 'release_manifest_sha256': config['release_manifest_sha256'],
        'tools_manifest_sha256': sha(HERE / 'manifest.json'), 'actual_runtime_image_id': task['runtime_image_id'],
        'commands_result': rec['commands_result'], 'formal_cpu_accepted': False, 'model_attempts': 0,
        'frozen_patch_exported': False, 'original_record_preserved': True}
    (out / 'public_commands_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'job_id': ns.job, 'status': result['status'], 'model_attempts': 0}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
