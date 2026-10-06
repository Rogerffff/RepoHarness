"""只为冻结 devcheck 的 root 镜像初态探针补 CPU/内存/PID 限额；其余正式路径保持。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code-root', required=True, type=Path)
    args, remaining = p.parse_known_args()
    entry = args.code_root / 'experiments/task2_swegym_dev_20260925/devcheck.py'
    spec = importlib.util.spec_from_file_location('monai_frozen_devcheck', entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.acc_docker
    requests = []

    def factory():
        runner = original()

        async def bounded(*argv, **kwargs):
            if argv and argv[0] == 'run' and '--cpus' not in argv:
                # image_facts 的 --rm 探针没有 profile；正式 actor 的 run 由原 Runner 自己装配。
                assert '--memory' not in argv and '--pids-limit' not in argv
                argv = (argv[0], '--cpus', '2', '--memory', '4g', '--pids-limit', '512',
                        '--label', 'rh2.package=swe_monai', *argv[1:])
                requests.append(list(argv))
            return await runner(*argv, **kwargs)

        return bounded

    module.acc_docker = factory
    try:
        return module.main(remaining)
    finally:
        if '--out-dir' in remaining:
            out = Path(remaining[remaining.index('--out-dir') + 1])
            if out.is_dir():
                (out / 'bounded_image_probe.json').write_text(json.dumps({
                    'scope': 'resource flags only for original root image_facts probe',
                    'frozen_entry_sha256': hashlib.sha256(entry.read_bytes()).hexdigest(),
                    'shim_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'docker_run_requests': requests,
                }, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
