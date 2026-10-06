"""以冻结R6 devcheck装配和CC桩执行公开输入；宿主逐内容应用完整原Frozen。

只扩展本包solve前的基线/候选检查，不创建新solver或评分器；公开函数
本身由原库调用。候选全部条目原样应用，原reward从不读写成新成绩。
"""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()

ap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
ap.add_argument('--fixed-repo', required=True, type=Path)
ap.add_argument('--input-manifest', required=True, type=Path)
ap.add_argument('--case', required=True, choices=['baseline','coder_full_frozen','qwen_full_frozen'])
ap.add_argument('--expected-prepared-summary-sha256', required=True)
owner, forwarded = ap.parse_known_args()
inputs = json.loads(owner.input_manifest.read_text())
inputs_dir = owner.input_manifest.parent
for item in inputs['files']:
    path = inputs_dir/item['name']
    assert path.is_file() and digest(path.read_bytes()) == item['sha256'], item['name']
bound=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
bound.add_argument('--commands',required=True,type=Path)
bound.add_argument('--overlays',required=True,type=Path)
bound.add_argument('--prepared-summary',required=True,type=Path)
paths,_=bound.parse_known_args(forwarded)
assert paths.commands.resolve()==(inputs_dir/(owner.case+'_commands.json')).resolve()
assert paths.overlays.resolve()==(inputs_dir/'original_overlays.jsonl').resolve()
assert digest(paths.prepared_summary.read_bytes())==owner.expected_prepared_summary_sha256
commands=json.loads(paths.commands.read_text())
probe_commands=[c for c in commands if c['id']=='cancelled_main']
expected_prefix='cd /testbed && python -B - --label '+owner.case+' --expected-web-sha256 '+inputs['cases'][owner.case]['web_sha256']
assert len(probe_commands)==1 and probe_commands[0]['cmd'].startswith(expected_prefix+' ')
release = owner.fixed_repo.resolve().parent
assert digest((release/'manifest.json').read_bytes()) == inputs['release_manifest_sha256']
verify = subprocess.run([sys.executable,'-B',str(release/'verify_release.py')], cwd=release, capture_output=True, text=True)
assert verify.returncode == 0, verify.stdout[-1200:] + verify.stderr[-1200:]
baseline_json = json.loads((inputs_dir/'baseline_manifest.json').read_text())
entry = owner.fixed_repo/'rh2/experiments/r2e_actor_20260925/r2e_devcheck.py'
spec = importlib.util.spec_from_file_location('aiohttp_fixed_cancelled_main_devcheck',entry)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from repoharness2.adapters.slime.baseline_census import build_census_script, parse_census_output
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest
from repoharness2.grading.manager import build_delta_write_command

baseline = BaselineWorkspaceManifestV1.model_validate(baseline_json)
assert compute_baseline_manifest_digest(baseline) == inputs['canonical_baseline_digest']
frozen = None
if owner.case != 'baseline':
    model = owner.case.split('_')[0]
    frozen = FrozenPatchArtifactV1.model_validate_json((inputs_dir/(model+'_frozen_patch.json')).read_text())
    assert frozen.baseline_manifest_digest == inputs['canonical_baseline_digest']
    assert compute_frozen_patch_digest(frozen) == inputs['cases'][owner.case]['canonical_frozen_digest']

class OriginalFrozenPublicProbeRunner(module.R2EDevRunner):
    async def image_facts(self):
        # 不调用旧DevRunner的额外root探查容器；原像事实由inspect、正式actor核。
        self.docker = module.devcheck.acc_docker()
        image = inputs['actor_image_id']
        facts = await self.dk('image','inspect',image,'--format','{{.Id}} {{.Architecture}} {{.Os}}',timeout=60)
        assert facts.exit_code == 0 and facts.stdout.strip() == image+' amd64 linux', facts.stdout+facts.stderr
        self.rec['image_facts'] = {'image':image,'inspect':facts.stdout.strip(),'inspect_rc':facts.exit_code,'extra_root_probe_container_created':False}
        self.save()

    async def census(self, label):
        result = await self.sh(build_census_script('/testbed',baseline.policy),timeout=120)
        (self.out/(label+'_census.txt')).write_text(result.stdout)
        (self.out/(label+'_census.stderr')).write_text(result.stderr)
        assert result.exit_code == 0, result.stderr[-1000:]
        head = await self.sh('git -C /testbed rev-parse HEAD',user=self.profile.agent_user,timeout=30)
        assert head.exit_code == 0 and head.stdout.strip() == baseline.materialized_head
        return parse_census_output(result.stdout,task_id=baseline.task_id,workdir='/testbed',public_bundle_digest=baseline.public_bundle_digest,runtime_image_digest=inputs['actor_image_id'],materialized_head=head.stdout.strip(),task_base_commit=baseline.task_base_commit,policy=baseline.policy)

    async def solve(self, task_spec, env_inj):
        assert task_spec.image == inputs['actor_image_id'] and task_spec.expected_interpreter_prefix == '/testbed/.venv'
        actual = await self.census('initial')
        (self.out/'actual_initial_manifest.json').write_text(actual.model_dump_json(indent=2)+'\n')
        # 真实初态全scoreable树/模式及excluded路径集一致，不用HEAD代替内容。
        assert compute_baseline_manifest_digest(actual) == inputs['canonical_baseline_digest'], (compute_baseline_manifest_digest(actual),inputs['canonical_baseline_digest'])
        expected = {e.path:e.model_dump() for e in baseline.entries}
        applied = []
        if frozen is not None:
            for item in frozen.entries:
                assert item.object_type == 'regular' and item.operation in ('add','modify')
                raw = base64.b64decode(item.content_b64,validate=True)
                assert digest(raw) == item.content_digest
                run = await self.sh(build_delta_write_command('/testbed',item.path,mode=item.mode,operation=item.operation),user=self.profile.agent_user,input_bytes=raw,timeout=120)
                assert run.exit_code == 0, (item.path,run.stderr[-1000:])
                expected[item.path]={'path':item.path,'object_type':'regular','mode':item.mode,'content_digest':item.content_digest,'symlink_target_digest':None}
                applied.append({'path':item.path,'content_digest':item.content_digest,'operation':item.operation})
        after = await self.census('after_full_original_frozen')
        (self.out/'actual_candidate_manifest.json').write_text(after.model_dump_json(indent=2)+'\n')
        assert {e.path:e.model_dump() for e in after.entries} == expected
        self.rec['cancelled_main_followup']={'case':owner.case,'input_manifest_sha256':digest(owner.input_manifest.read_bytes()),'baseline_digest':compute_baseline_manifest_digest(actual),'original_frozen_digest':None if frozen is None else compute_frozen_patch_digest(frozen),'complete_original_entries_applied':applied,'candidate_full_tree_verified':True,'excluded_runtime_files_not_replayed':True,'model_generation':False,'new_formal_grade':False,'library_functions_not_replaced':True}
        self.save()
        return await super().solve(task_spec,env_inj)

    def evaluate(self):
        super().evaluate()
        capture=self.out/'captures/cancelled_main.out'
        rows=[]
        if capture.is_file():
            for line in capture.read_text().splitlines():
                try:
                    row=json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row,dict) and row.get('schema_id') == 'rh2.category2.aiohttp.public_cancelled_main_observation.v1':
                    rows.append(row)
        commands={row['id']:row for row in self.rec.get('commands_result') or []}
        command=commands.get('cancelled_main') or {}
        self.rec['cancelled_main_public_observation']={'valid_json_count':len(rows),'observation':rows[0] if len(rows)==1 else None,'command_rc':command.get('rc')}
        self.rec['checks']['cancelled_main_input_executed_and_observed']=len(rows)==1 and rows[0]['label']==owner.case and command.get('rc')==0 and rows[0]['identity']['python'].startswith('3.9.21 ') and rows[0]['identity']['web_sha256']==inputs['cases'][owner.case]['web_sha256'].removeprefix('sha256:')
        # 只检查观察确实发生，不按资源状态判通过；归因由题主与非作者核。
        self.save()

module.R2EDevRunner = OriginalFrozenPublicProbeRunner
raise SystemExit(module.main(forwarded))
