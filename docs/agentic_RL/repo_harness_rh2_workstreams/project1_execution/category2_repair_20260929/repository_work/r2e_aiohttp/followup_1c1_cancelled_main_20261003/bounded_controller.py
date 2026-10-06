"""在cpu_slot内为既定三侧作业设置1800秒及120秒清理边界。"""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ap=argparse.ArgumentParser()
ap.add_argument('--inputs',required=True,type=Path)
ap.add_argument('--out',required=True,type=Path)
ap.add_argument('--run-id',required=True)
ns=ap.parse_args()
argv=['/work/rh2-category2-20261003/runtime_cpu_v2/rh2/.venv/bin/python','-B',str(ns.inputs/'run_cpu_job.py'),'--inputs',str(ns.inputs),'--out',str(ns.out),'--run-id',ns.run_id]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
child=subprocess.Popen(argv,start_new_session=True)
timed_out=False
try:
    rc=child.wait(timeout=1800)
except subprocess.TimeoutExpired:
    timed_out=True
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    deadline=time.monotonic()+120
    # 即使controller先退出，也继续等待同进程组的devcheck完成finally。
    while time.monotonic()<deadline:
        child.poll()
        try:os.killpg(child.pid,0)
        except ProcessLookupError:break
        time.sleep(1)
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    child.wait()
    rc=124
record={'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'returncode':rc,'whole_run_seconds':1800,'cleanup_grace_seconds':120,'timeout_occurred':timed_out,'raw_grades_changed':False}
with ns.out.with_name(ns.out.name+'_bounded_controller_receipt.json').open('x') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(record),flush=True)
raise SystemExit(rc)
