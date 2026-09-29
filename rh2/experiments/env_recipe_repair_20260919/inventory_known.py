"""只读盘点已知问题题目的实际镜像声明/依赖，供配方分组，不运行安装或测试。"""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path("/work/env_recipe_repair_20260919/inventory")
PROBE = r'''
import json, pathlib, sys, subprocess
from importlib import metadata
files = ['pyproject.toml','setup.py','setup.cfg','Makefile','requirements.txt','requirements-dev.txt',
         'test-requirements.txt','tests/requirements.txt','test-requirements.in','tox.ini',
         'tests/utils.py','tests/conftest.py','conftest.py','test-data/unit/fixtures/object.pyi',
         'test-data/unit/fixtures/object_hashable.pyi','test-data/unit/check-protocols.test']
out = {'python':sys.version, 'files':{}, 'packages':{}}
for name in files:
 p=pathlib.Path('/testbed')/name
 out['files'][name]=p.read_text(errors='replace') if p.is_file() and p.stat().st_size < 300000 else None
for dist in metadata.distributions():
 name=dist.metadata.get('Name')
 if name: out['packages'][name.lower()]=dist.version
out['git_head']=subprocess.check_output(['git','-C','/testbed','rev-parse','HEAD'],text=True).strip()
print(json.dumps(out))
'''


def main():
    tasks = json.loads((ROOT / "plan.json").read_text())
    (ROOT / "records").mkdir(exist_ok=True)
    for index, task in enumerate(tasks, 1):
        dest = ROOT / "records" / (task["instance_id"] + ".json")
        assert not dest.exists()
        name = "er19-inventory-" + str(index)
        record = {**task, "at": time.time()}
        try:
            info = json.loads(subprocess.check_output(["docker", "image", "inspect", task["image"]], text=True))[0]
            record['image_id'] = info['Id']
            record['repo_digests'] = info['RepoDigests']
            assert any(d.endswith('@' + task['expected_digest']) for d in info['RepoDigests'])
            out = subprocess.run(['docker','run','--name',name,'--rm','--init','--read-only','--network','none',
                                  '--cpus','1','--memory','1g','--pids-limit','128',info['Id'],
                                  '/opt/miniconda3/envs/testbed/bin/python','-I','-B','-c',PROBE],
                                 text=True,capture_output=True,timeout=60)
            record['rc'] = out.returncode
            record['stderr'] = out.stderr
            record['facts'] = json.loads(out.stdout) if out.returncode == 0 else {'raw':out.stdout}
        except Exception as exc:
            record['probe_error'] = repr(exc)
        finally:
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)
        dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        (ROOT / 'progress.json').write_text(json.dumps({'completed':index,'total':len(tasks),'last':task['instance_id'],'at':time.time()}))
        print(index,task['instance_id'],record.get('rc'),record.get('probe_error',''),flush=True)
    (ROOT / 'done.json').write_text(json.dumps({'at':time.time(),'records':len(tasks)}))


if __name__ == '__main__':
    main()
