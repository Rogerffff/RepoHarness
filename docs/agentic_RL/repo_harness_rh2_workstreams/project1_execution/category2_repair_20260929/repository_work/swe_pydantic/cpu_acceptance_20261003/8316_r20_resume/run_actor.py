"""在四题已发布consumer上运行原公开actor诊断；不评分或交付私有断言。

由 cpu_slot --mode run 调用。源码、loader、CC启动、资源和清理均沿冻结入口。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time



def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', choices=['8316'], required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--release-dir', type=Path, required=True)
    a = ap.parse_args()
    here = Path(__file__).resolve().parent
    root = Path('/work/rh2-category2-20261003')
    release = a.release_dir.resolve()
    if not release.is_relative_to(root / 'releases'):
        raise ValueError('只消费公共已发布目录')
    repo = release / 'repo'
    code = repo / 'rh2'
    python = root / 'runtime_cpu_v2/rh2/.venv/bin/python'
    iid = 'pydantic__pydantic-' + a.task
    out = Path(a.out).resolve()
    if not out.is_relative_to(root / 'packages/swe_pydantic/formal_8316_r20_resume_v1/actor_outputs'):
        raise ValueError('只能写本包作业输出')
    out.mkdir(parents=True, exist_ok=False)
    config = json.loads((here / 'actor_inputs.json').read_text())
    assert release.name == config['source_release']
    assert sha(release / 'manifest.json') == config['manifest_sha256']
    c = config['tasks'][iid]
    state = dict(task=iid, scope='published_consumer_public_actor_diagnostic',
                 status='running', new_test_material_active=False, formal_grading_verified=False,
                 private_material_registered=True, private_tests_delivered=False,
                 source_release=release.name, manifest_sha256=sha(release / 'manifest.json'),
                 wrapper_sha256=sha(Path(__file__)), input_sha256=sha(here / 'actor_inputs.json'),
                 image=c['derived_id'], port=18195, runtime=sys.executable,
                 runtime_generation='cpu_v2', steps=[], started_at=time.time())

    def save():
        (out / 'diagnostic_result.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def stop(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(code / 'src'),
               RH2_SANDBOX_CPUS='2', RH2_SANDBOX_MEMORY_BYTES=str(4 * 1024**3),
               RH2_GRADER_CPUS='2', RH2_GRADER_MEMORY_BYTES=str(4 * 1024**3),
               SLIME_AGENT_CC_PLATFORM_TARBALL=str(root / 'cc/claude-code-linux-x64-2.1.205.tgz'))

    def run(name, argv, timeout):
        step = dict(name=name, command=[str(x) for x in argv], started_at=time.time())
        # 提示全文另存；状态里不重复展开公开任务。
        if '--prompt' in step['command']:
            step['command'][step['command'].index('--prompt') + 1] = '<public_prompt.txt>'
        state['steps'].append(step)
        save()
        with (out / (name + '.log')).open('wb') as log:
            proc = subprocess.Popen([str(x) for x in argv], env=env, cwd=code, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = proc.wait(timeout=timeout)
            except BaseException:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=180)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=30)
                        state['cleanup_unconfirmed'] = True
                step.update(rc=proc.returncode, finished_at=time.time(), interrupted=True)
                save()
                raise
        step.update(rc=rc, finished_at=time.time())
        save()
        if rc:
            raise RuntimeError(name + ': rc=' + str(rc))

    save()
    try:
        assert state['manifest_sha256'] == config['manifest_sha256'], '发布身份不符'
        manifest_data = json.loads((release / 'manifest.json').read_text())
        assert len(manifest_data['files']) == config['source_release_member_count']
        run('verify_release', [python, '-B', release / 'verify_release.py'], 120)
        # 不让 run 槽隐式拉取镜像，也不接入他人已占用的桩端点。
        for image in (c['derived_id'], 'python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea'):
            run('image_available_' + str(len(state['steps'])), ['docker', 'image', 'inspect', image], 60)
        with socket.socket() as listener:
            listener.bind(('172.17.0.1', 18195))
        run('trusted_prepare', [python, '-B', code / 'scripts/replay_grade.py', 'prepare',
                               '--repo-root', repo, '--out-dir', out / 'prepared', '--private-dir', out / 'private',
                               '--task-ids', 'swe_gym_lite::' + iid, '--sources', 'swe_gym_lite'], 120)
        summary = json.loads((out / 'prepared/replay_summary.json').read_text())
        sys.path.insert(0, str(code / 'src'))
        from repoharness2.envpack.prepared_tasks import load_prepared_manifest, load_prepared_rollout_views
        from repoharness2.envpack.bundles import render_user_prompt
        manifest = load_prepared_manifest(out / 'prepared', expected_sha256=summary['prepared_manifest_sha256'])
        view = load_prepared_rollout_views(out / 'prepared', manifest)['swe_gym_lite::' + iid]
        public = view.public
        assert public.base_commit == c['base_commit']
        assert view.public_bundle_digest == c['public_bundle_digest']
        prompt = render_user_prompt(public) + '\n\n' + public.public_hints
        (out / 'public_prompt.txt').write_text(prompt)
        state['public_prompt_sha256'] = sha(out / 'public_prompt.txt')
        commands = here / 'public_actor_commands' / (iid + '.public_commands.json')
        assert sha(commands) == c['commands_sha256']
        run('actor', [python, '-B', code / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                      '--prepared-summary', out / 'prepared/replay_summary.json', '--task', iid,
                      '--commands', commands, '--image', c['derived_id'], '--out-dir', out / 'actor',
                      '--attempt-id', out.name, '--stub-port', '18195', '--wall-seconds', '1800',
                      '--prompt', prompt], 2400)
        actor = json.loads((out / 'actor/attempt.json').read_text())
        assert actor['harness_exit_code'] == 0 and actor['termination'] == 'returned'
        assert actor['container_inspect'].split() == [c['derived_id'], '2000000000', '4294967296']
        assert actor['checks']['all_match_expect'] is True
        assert actor['launch_facts']['harness_log']['log_complete'] is True
        assert json.loads((out / 'actor/prelaunch.json').read_text())['ok'] is True
        assert json.loads((out / 'actor/activation_check.json').read_text())['ok'] is True
        cleanup = actor['cleanup']
        assert cleanup['residual_after_force'] == [] and cleanup['container_rm'] == 0
        assert not cleanup['network_failures'] and not cleanup['relay_failures'] and cleanup['stub_rc'] == 0
        rows = actor['commands_result']
        requested = json.loads(commands.read_text())
        assert [r['id'] for r in rows] == [x['id'] for x in requested]
        for row in rows:
            text = (out / 'actor/captures' / (row['id'] + '.out')).read_text()
            assert row['output_bytes'] <= 200000
            if row['id'] == 'public_goal':
                assert row['rc'] == 1 and 'TARGET_EQUALS False' in text
                assert 'AssertionError: PUBLIC_ORIGINAL_TARGET_REPRODUCED' in text
            else:
                assert row['rc'] == 0, row['id']
        body_path = out / 'actor/stub/requests/messages_000.json'
        body = json.loads(body_path.read_text())
        user_texts = []
        for msg in body['messages']:
            if msg.get('role') != 'user':
                continue
            content = msg.get('content')
            user_texts.append(content if isinstance(content, str) else '\n'.join(
                x.get('text', '') for x in (content or []) if isinstance(x, dict)))
        delivered = '\n'.join(user_texts)
        assert prompt in delivered and public.problem_statement in delivered and public.public_hints in delivered
        assert not any(x in delivered for x in c['private_only_test_names'])
        state.update(status='published_public_actor_diagnostic_passed', prepared_summary=summary,
                     commands_result=rows, actual_public_delivery=True, actual_request_sha256=sha(body_path),
                     effective_profile=actor['effective_profile'], container_inspect=actor['container_inspect'],
                     cleanup=cleanup, new_test_material_active=False, formal_grading_verified=False)
    except BaseException as exc:
        state.update(status='diagnostic_stopped_needs_analysis', error=repr(exc))
        raise
    finally:
        state['finished_at'] = time.time()
        save()
        print(json.dumps({k: state[k] for k in ('task', 'status')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
