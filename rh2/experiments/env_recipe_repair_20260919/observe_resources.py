"""无候选代码执行的宿主采样；记录长测试资源和同期负载，不作评分判据。"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import time


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--root', required=True)
    args.add_argument('--output', required=True)
    args.add_argument('--batches', nargs='+', required=True)
    cfg = args.parse_args()
    root = Path(cfg.root)
    deadline = time.monotonic() + 12 * 3600
    with Path(cfg.output).open('x') as out:
        while time.monotonic() < deadline:
            row = {'at': time.time(), 'loadavg': os.getloadavg(), 'containers': []}
            try:
                row['host_memory'] = {line.split(':')[0]: line.split(':', 1)[1].strip()
                                      for line in Path('/proc/meminfo').read_text().splitlines()
                                      if line.split(':')[0] in {'MemTotal','MemAvailable','SwapFree'}}
                ids = subprocess.check_output(['docker','ps','-q'],text=True,timeout=10).split()
                infos = json.loads(subprocess.check_output(['docker','inspect',*ids],text=True,timeout=15)) if ids else []
                for info in infos:
                    run_id = (info['Config'].get('Labels') or {}).get('rh2.run_id','')
                    if not run_id.startswith('er19-'):
                        continue
                    r = {'container':info['Name'],'run_id':run_id,
                         'policy':{k:info['HostConfig'][k] for k in ['Memory','NanoCpus','ShmSize','PidsLimit','Tmpfs']}}
                    try:
                        proc = Path('/proc',str(info['State']['Pid']))
                        rel = next(line.split('::',1)[1] for line in (proc/'cgroup').read_text().splitlines() if '::' in line)
                        cg = Path('/sys/fs/cgroup')/rel.lstrip('/')
                        r['cgroup'] = {name:(cg/name).read_text().strip() if (cg/name).exists() else None
                                       for name in ['memory.current','memory.peak','memory.events','pids.current','pids.peak','pids.events','cpu.stat']}
                        r['filesystems'] = {}
                        for path in ['tmp','dev/shm']:
                            v = os.statvfs(proc/'root'/path)
                            r['filesystems'][path] = {'capacity_bytes':v.f_frsize*v.f_blocks,
                                                      'available_bytes':v.f_frsize*v.f_bavail}
                    except (OSError, StopIteration) as exc:
                        r['missing_reason'] = repr(exc)
                    row['containers'].append(r)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                row['sampling_error'] = repr(exc)
            batch_file = root/'resource_observer_batches.json'
            batches = json.loads(batch_file.read_text()) if batch_file.exists() else cfg.batches
            row['batches'] = {b:('done' if (root/b/'done.json').exists() else 'failed' if (root/b/'failed.json').exists() else 'open')
                              for b in batches}
            out.write(json.dumps(row)+'\n')
            out.flush()
            if all(s != 'open' for s in row['batches'].values()):
                break
            time.sleep(15)


if __name__ == '__main__':
    main()
