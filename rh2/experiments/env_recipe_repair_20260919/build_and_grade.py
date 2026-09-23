"""本批远端配方构建与真实 replay；不修改生产评分代码。"""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time

ROOT = Path('/work/env_recipe_repair_20260919')
OLD = Path('/work/full216_20260919')
PY = OLD / 'code/rh2/.venv/bin/python'
CASES = [
    ('dask10972', 'dask__dask-10972', 'wheels-v1'),
    ('dvc4778', 'iterative__dvc-4778', 'pathspec-v1'),
    ('monai1121', 'Project-MONAI__MONAI-1121', 'assets-v1'),
]


def save(name, data):
    (ROOT / 'evidence' / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def captured(args, timeout=120):
    return subprocess.check_output(args, text=True, timeout=timeout)


def unchanged_files(image):
    # 已知 metacopy/commit 故障的代表性内容与实际解释器检查；不是全树扫描。
    script = ('sha256sum /opt/miniconda3/envs/testbed/bin/python3 /testbed/setup.py '
              '/testbed/pyproject.toml 2>/dev/null; '
              'cd /testbed && git rev-parse HEAD && git diff; '
              '/opt/miniconda3/envs/testbed/bin/python -c "import json,sys; print(sys.version)"')
    return captured(['docker', 'run', '--rm', '--init', '--network', 'none', image, 'bash', '-c', script])


def run():
    bases = json.loads((ROOT / 'evidence/base_images.json').read_text())
    assert not captured(['docker', 'ps', '-q']).strip(), 'active containers: defer build'
    meta = Path('/sys/module/overlay/parameters/metacopy')
    before = meta.read_text().strip()
    images = {}
    save('build_start.json', {'at': time.time(), 'metacopy_before': before})
    try:
        meta.write_text('N')
        for short, iid, version in CASES:
            recipe = ROOT / 'recipes' / f'Dockerfile.{short}-{version}'
            tag = f'rh2-envrepair/{short}:20260919-{version}'
            with (ROOT / 'logs' / f'build_{short}.log').open('w') as log:
                subprocess.run(['docker', 'build', '--pull=false', '--force-rm',
                                '--build-arg', 'BASE_IMAGE=' + bases[short]['repo_digests'][0],
                                '-f', str(recipe), '-t', tag, str(ROOT / 'recipes')],
                               stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
            image_id = json.loads(captured(['docker', 'image', 'inspect', tag]))[0]['Id']
            original = unchanged_files(bases[short]['image_id'])
            derived = unchanged_files(image_id)
            save(f'content_{short}.json', {'base': original, 'derived': derived, 'same': original == derived})
            assert original == derived, 'base source/interpreter changed: ' + short
            images[short] = {'task': iid, 'tag': tag, 'image_id': image_id, 'base': bases[short],
                             'recipe': recipe.name, 'recipe_sha256': hashlib.sha256(recipe.read_bytes()).hexdigest()}
            save('images.json', images)
            print('BUILT', short, image_id, flush=True)
    finally:
        meta.write_text(before)
        save('metacopy_restored.json', {'at': time.time(), 'value': meta.read_text().strip()})

    dvc = subprocess.run(['docker', 'run', '--rm', '--init', '--network', 'none',
                         '-v', str(ROOT / 'ops/dvc_regex_probe.py') + ':/tmp/probe.py:ro',
                         images['dvc4778']['image_id'], '/opt/miniconda3/envs/testbed/bin/python', '/tmp/probe.py'],
                        text=True, capture_output=True, timeout=60)
    (ROOT / 'evidence/dvc_regex_after.txt').write_text(dvc.stdout + '\n' + dvc.stderr)
    assert dvc.returncode == 0, 'pathspec hypothesis not confirmed'
    for short, iid, version in CASES:
        for kind in ('noop', 'gold'):
            dest = ROOT / 'runs' / f'{short}-{version}-{kind}'
            dest.mkdir(exist_ok=False)
            env = dict(os.environ)
            env['MILES_RH2_RUN_ID'] = f'er19-{short}-{version}-{kind}'
            candidate = 'noop' if kind == 'noop' else 'gold-dir:' + str(OLD / 'replay/gold')
            command = [str(PY), str(OLD / 'code/rh2/scripts/replay_grade.py'), 'run',
                       '--prepared-summary', str(OLD / 'replay/prepared/replay_summary.json'),
                       '--task-ids', iid, '--candidate', candidate, '--repeat', '1',
                       '--derived-image', images[short]['image_id'], '--derived-image-recipe', images[short]['recipe'],
                       '--eval-log-dir', str(dest / 'eval_logs'), '--artifacts-dir', str(dest / 'artifacts'),
                       '--ledger', str(dest / 'ledger.jsonl')]
            save('current.json', {'at': time.time(), 'task': iid, 'kind': kind, 'command': command})
            with (dest / 'driver.log').open('w') as log:
                subprocess.run(command, env=env, cwd=OLD / 'code/rh2', stdout=log,
                               stderr=subprocess.STDOUT, check=True, timeout=4800)
            rows = [json.loads(s) for s in (dest / 'ledger.jsonl').read_text().splitlines()]
            assert len(rows) == 1
            row = rows[0]
            if str(row.get('stage_error') or '').startswith(('grade_exception', 'classify:')):
                raise RuntimeError(row['stage_error'])
            assert row['cleanup']['removed']
            assert not captured(['docker', 'ps', '-q']).strip(), 'container still active after replay'
            print('GRADED', iid, kind, json.dumps(row.get('report')), flush=True)
    save('done.json', {'at': time.time(), 'attempts': 6})


if __name__ == '__main__':
    def terminate(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM, terminate)
    try:
        run()
    except BaseException as exc:
        save('failed.json', {'at': time.time(), 'type': type(exc).__name__, 'detail': str(exc)})
        raise
