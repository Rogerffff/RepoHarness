#!/usr/bin/env python3
"""扩题实验的旁路观测；评分、gold 重建、测试命令和原 runner 的结果原样保留。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import r2e_probe as probe
from swegym_probe import Container as SWEContainer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--out', required=True)
    args, _ = parser.parse_known_args()
    root = Path(args.out) / 'observations'
    original_start, original_exec, original_rm = probe.Container.start, probe.Container.exec, probe.Container.rm

    def directory(container):
        p = root / container.name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def save(container, name, value):
        (directory(container) / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def start(container):
        original_start(container)
        result = probe.sh(['docker', 'inspect', container.name], timeout=30)
        facts = json.loads(result.stdout)[0]
        container.container_id = facts['Id']
        save(container, 'initial.json', {
            'container_id': facts['Id'], 'image_id': facts['Image'], 'created': facts['Created'],
            'user': facts['Config']['User'],
            'host_config': {k: facts['HostConfig'][k] for k in ('Memory', 'MemorySwap', 'NanoCpus', 'ShmSize', 'NetworkMode')},
        })
        script = original_exec(container, 'cat /testbed/run_tests.sh', timeout=30)
        (directory(container) / 'run_tests.sh').write_bytes(script.stdout)
        save(container, 'script_identity.json', {'read_rc': script.returncode, 'sha256': hashlib.sha256(script.stdout).hexdigest()})

    def execute(container, script, *args, **kwargs):
        result = original_exec(container, script, *args, **kwargs)
        if 'echo RH2_SETUP_OK' in script:
            # 原 echo 会掩盖前面命令失败，故另读目录差异；不改 setup 或结果码。
            check = original_exec(container, 'diff -qr /r2e_tests /testbed/r2e_tests', timeout=120)
            save(container, 'setup_observation.json', {
                'runner_rc': result.returncode, 'stdout': result.stdout.decode(errors='replace'),
                'stderr': result.stderr.decode(errors='replace'),
                'test_tree_diff_rc': check.returncode,
                'test_tree_diff': (check.stdout + check.stderr).decode(errors='replace'),
            })
            patch = original_exec(container, 'cd /testbed && git diff --no-ext-diff --no-color HEAD', timeout=60)
            (directory(container) / 'pre_test.diff').write_bytes(patch.stdout)
            save(container, 'pre_test_diff.json', {'returncode': patch.returncode, 'stderr': patch.stderr.decode(errors='replace')})
        return result

    def remove(container):
        try:
            try:
                facts = SWEContainer.resource_facts(container)
                save(container, 'resources.json', facts)
            except Exception as exc:
                save(container, 'resources.json', {'observation_error': str(exc)})
        finally:
            try:
                original_rm(container)
            finally:
                # inspect 非零还可能是 daemon 错误，保留原始错误，不自行写 cleanup=true。
                result = probe.sh(['docker', 'inspect', container.name], timeout=30)
                save(container, 'cleanup_observation.json', {
                    'inspect_rc': result.returncode, 'stdout': result.stdout.decode(errors='replace'),
                    'stderr': result.stderr.decode(errors='replace'),
                })

    probe.Container.start, probe.Container.exec, probe.Container.rm = start, execute, remove
    return probe.main()


if __name__ == '__main__':
    sys.exit(main())
