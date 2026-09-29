"""验证 P-D 将放开的形状在真实投影和应用函数中的组合行为。

当前 artifact 构造仍拒绝父子路径。SimpleNamespace 仅绕过该构造拒绝，
把未来计划允许的条目交给现有函数；命令只在自动清理的临时目录执行。
"""

import asyncio
import base64
import hashlib
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from repoharness2.contracts.frozen_patch import PatchEntry
from repoharness2.grading.manager import FrozenApplyPlan, HygieneRules, SWEGradingManager
from repoharness2.grading.trusted_projection import split_trusted_scoring_projection

def add(path):
    raw=b'answer = 42\n'
    return PatchEntry(path=path, operation='add', object_type='regular', mode='100644', content_b64=base64.b64encode(raw).decode(), content_digest='sha256:'+hashlib.sha256(raw).hexdigest())

class LocalApply:
    async def _exec_bash_checked(self, record, script, *, input_bytes=None, **kwargs):
        p=subprocess.run(['bash','-c',script],input=input_bytes,capture_output=True)
        return SimpleNamespace(exit_code=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())

async def run_apply(root, entries, paths, baseline_entries=()):
    source=SimpleNamespace(frozen_patch=SimpleNamespace(entries=entries),baseline_manifest=SimpleNamespace(entries=baseline_entries))
    plan=FrozenApplyPlan(applied_paths=tuple(paths),stripped_test_paths=(),forbidden_paths=(),applied_entry_set_digest='sha256:'+'0'*64)
    try:
        await SWEGradingManager._apply_frozen_delta(LocalApply(),None,SimpleNamespace(testbed_path=str(root),apply_timeout_seconds=10),source,plan)
        return 'ok'
    except Exception as e:
        return type(e).__name__+':'+str(e).splitlines()[0]

async def main():
    entries=(PatchEntry(path='config',operation='delete',object_type='regular'),add('config/default.json'))
    rules=HygieneRules(test_files=('config',),test_globs=(),forbidden_globs=())
    split=split_trusted_scoring_projection(entries,rules)
    print('projected_paths',split.candidate_paths,'ignored_paths',split.ignored_paths)
    assert split.candidate_paths == ('config/default.json',)
    assert split.ignored_paths == ('config',)
    with tempfile.TemporaryDirectory(prefix='rh2_pd_review_') as tmp:
        root=Path(tmp)
        (root/'config').write_text('base config')
        projected_result=await run_apply(root,entries,split.candidate_paths)
        print('projected_apply',projected_result)
        assert projected_result.startswith('GradingInfraError:delta_write_failed:')
        assert (root/'config').is_file()
        full_result=await run_apply(root,entries,[e.path for e in entries])
        print('full_delta_apply',full_result)
        assert full_result == 'ok'
        print('full_delta_written',(root/'config/default.json').read_text().strip())
        assert (root/'config/default.json').read_text() == 'answer = 42\n'
asyncio.run(main())
