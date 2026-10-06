"""验证 P-C 计划的名字过滤，不代表当前 census 已采用该规则。

SimpleNamespace 将模拟过滤后的事实交给当前应用函数，不运行完整 formal
入口。所有对象和“树外”写入都限制在同一个自动清理的临时目录内。
"""

import asyncio
import base64
import hashlib
import importlib.util
import os
import py_compile
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from repoharness2.contracts.frozen_patch import PatchEntry
from repoharness2.grading.manager import FrozenApplyPlan, SWEGradingManager

def planned_paths(root):
    args=['find','.', '-name','__pycache__','-prune','-o','-name','.pytest_cache','-prune','-o','(', '-type','f','-o','-type','l','-o','(', '!', '-type','d','!', '-type','f','!', '-type','l',')',')','!', '-name','*.pyc','-print']
    p=subprocess.run(args,cwd=root,capture_output=True,text=True,check=True)
    return sorted(p.stdout.splitlines())
class LocalApply:
    async def _exec_bash_checked(self, record, script, *, input_bytes=None, **kwargs):
        p=subprocess.run(['bash','-c',script],input=input_bytes,capture_output=True)
        return SimpleNamespace(exit_code=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
async def apply_one(root, baseline_entries):
    raw=b'answer = 42\n'
    entry=PatchEntry(path='alias.pyc/payload.py',operation='add',object_type='regular',mode='100644',content_b64=base64.b64encode(raw).decode(),content_digest='sha256:'+hashlib.sha256(raw).hexdigest())
    source=SimpleNamespace(frozen_patch=SimpleNamespace(entries=(entry,)),baseline_manifest=SimpleNamespace(entries=baseline_entries))
    plan=FrozenApplyPlan(applied_paths=(entry.path,),stripped_test_paths=(),forbidden_paths=(),applied_entry_set_digest='sha256:'+'0'*64)
    try:
        await SWEGradingManager._apply_frozen_delta(LocalApply(),None,SimpleNamespace(testbed_path=str(root),apply_timeout_seconds=10),source,plan)
        return 'ok'
    except Exception as e:
        return type(e).__name__+':'+str(e).splitlines()[0]
async def main():
    with tempfile.TemporaryDirectory(prefix='rh2_pc_review_') as tmp:
        allroot=Path(tmp)
        names=allroot/'names'; names.mkdir()
        (names/'__pycache__').write_text('ordinary answer file')
        (names/'.pytest_cache').symlink_to('code.py')
        (names/'alias.pyc').symlink_to('code.py')
        os.mkfifo(names/'pipe.pyc')
        (names/'code.py').write_text('ANSWER=42\n')
        print('plan_name_filter_kept',planned_paths(names))
        print('plan_name_filter_omitted_regular_symlink_fifo',all('./'+p not in planned_paths(names) for p in ['__pycache__','.pytest_cache','alias.pyc','pipe.pyc']))
        assert planned_paths(names) == ['./code.py']
        fresh=allroot/'fresh'; fresh.mkdir()
        outside=allroot/'outside_testbed'; outside.mkdir()
        (fresh/'alias.pyc').symlink_to(outside,target_is_directory=True)
        post=allroot/'post'; (post/'alias.pyc').mkdir(parents=True)
        (post/'alias.pyc/payload.py').write_text('answer = 42\n')
        print('plan_filtered_baseline',planned_paths(fresh),'plan_filtered_post',planned_paths(post))
        assert planned_paths(fresh) == []
        assert planned_paths(post) == ['./alias.pyc/payload.py']
        with_fact=await apply_one(fresh,(SimpleNamespace(path='alias.pyc',object_type='symlink'),))
        print('apply_with_symlink_baseline_fact',with_fact)
        assert with_fact.startswith('GradingInfraError:apply_path_ancestor_is_symlink:')
        assert not (outside/'payload.py').exists()
        without_fact=await apply_one(fresh,())
        print('apply_after_name_filter_omits_fact',without_fact)
        assert without_fact == 'ok'
        print('write_outside_testbed_within_temporary_directory',(outside/'payload.py').exists())
        assert (outside/'payload.py').read_text() == 'answer = 42\n'
        src=allroot/'standalone.py'; src.write_text('ANSWER=42\n')
        bytecode=allroot/'standalone.pyc'; py_compile.compile(str(src),cfile=str(bytecode),doraise=True)
        src.unlink()
        spec=importlib.util.spec_from_file_location('standalone',bytecode)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        print('sourceless_pyc_is_executable_delivery',module.ANSWER)
        assert module.ANSWER == 42
        assert not src.exists()
asyncio.run(main())
