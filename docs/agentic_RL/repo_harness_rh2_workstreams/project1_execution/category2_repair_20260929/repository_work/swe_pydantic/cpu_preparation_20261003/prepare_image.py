"""只恢复固定来源镜像和离线 wheel；由 cpu_slot --mode prepare 调用。

结果仅为镜像准备，不表示材料登记、候选安装、评分或 actor 验收通过。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    plans = json.loads((here / 'image_plans.json').read_text())
    plan = plans['tasks'][args.task]
    out = Path(args.out).resolve()
    package = here.parent.resolve()
    if not out.is_relative_to(package / 'outputs'):
        raise ValueError('输出必须位于本包 outputs 内')
    out.mkdir(parents=True, exist_ok=False)
    state = dict(task=args.task, status='preparing', scope='image_preparation_only',
                 started_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 inputs_sha256={p.name: sha(p) for p in (
                     here / 'image_plans.json', here / 'wheelhouse_manifest.json',
                     here / 'Dockerfile.wheelhouse', Path(__file__))}, steps=[])

    def save():
        (out / 'preparation_result.json').write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def command(name, argv, timeout):
        step = dict(name=name, command=[str(x) for x in argv], started_at=time.time())
        state['steps'].append(step)
        save()
        with (out / (name + '.log')).open('wb') as log:
            proc = subprocess.Popen(step['command'], stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            try:
                rc = proc.wait(timeout=timeout)
            except BaseException:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=30)
                step.update(rc=proc.returncode, finished_at=time.time(), interrupted=True)
                save()
                raise
        step.update(rc=rc, finished_at=time.time())
        save()
        if rc != 0:
            raise RuntimeError(name + ': rc=' + str(rc))
        return (out / (name + '.log')).read_text()

    save()
    try:
        ctx = out / 'build_context'
        wheels = ctx / 'wheels'
        wheels.mkdir(parents=True)
        manifest = json.loads((here / 'wheelhouse_manifest.json').read_text())
        observed = []
        for item in manifest['public_wheels']:
            with urllib.request.urlopen(item['url'], timeout=90) as response:
                data = response.read()
            if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise RuntimeError('wheel内容不符: ' + item['filename'])
            (wheels / item['filename']).write_bytes(data)
            observed.append({k: item[k] for k in ('filename', 'bytes', 'sha256', 'url')})
        state['wheels'] = observed
        save()
        base = plan['base_image']
        if '@sha256:' not in base:
            raise ValueError('base必须固定registry摘要')
        command('pull_base', ['docker', 'pull', base], 2400)
        before = json.loads(command('base_inspect', ['docker', 'image', 'inspect', base], 60))
        if len(before) != 1 or before[0]['Id'] != plan['expected_base_id']:
            raise RuntimeError('base配置ID不符')
        before = before[0]
        dockerfile = here / 'Dockerfile.wheelhouse'
        if sha(dockerfile) != plans['dockerfile_sha256']:
            raise RuntimeError('Dockerfile内容不符')
        (ctx / 'Dockerfile').write_bytes(dockerfile.read_bytes())
        tag = 'rh2-cpu-category2/swe_pydantic-' + args.task.rsplit('-', 1)[1] + ':' + out.name.lower()
        command('build_derived', ['docker', 'build', '--pull=false', '--network=none',
                                 '--build-arg', 'BASE_IMAGE=' + base, '-t', tag, ctx], 1200)
        after = json.loads(command('derived_inspect', ['docker', 'image', 'inspect', tag], 60))
        if len(after) != 1:
            raise RuntimeError('派生镜像身份不唯一')
        after = after[0]
        layers = before['RootFS']['Layers']
        if after['RootFS']['Layers'][:len(layers)] != layers:
            raise RuntimeError('base层未保留')
        state.update(status='image_prepared_pending_task_acceptance', image=dict(
            base_image=base, base_id=before['Id'], base_repo_digests=before['RepoDigests'],
            derived_tag=tag, derived_id=after['Id'], base_layers_preserved=True,
            expected_python=plan['python'], expected_core=plan['expected_core'],
            dockerfile_sha256=sha(dockerfile)), runtime_identity_verified=False,
            candidate_install_verified=False, formal_grading_verified=False,
            independent_review='pending', actor_acceptance='pending')
    except BaseException as exc:
        state.update(status='preparation_failed', error=repr(exc))
        raise
    finally:
        state['finished_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        save()
        print(json.dumps({k: state[k] for k in ('task', 'status')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
