"""Reserve6 MONAI CPU实验；只由root远端派发，不改正式题面/测试/评分。"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import re
import signal
import shlex
import time
from pathlib import Path
from mixed_followups import Campaign, ROOT, CODE, PY, FROZEN, digest, load, write, require, hash_check

TASKS = {'Project-MONAI__MONAI-4583': (18109, 'degenerate_2d_only.patch'),
         'Project-MONAI__MONAI-6975': (18110, 'degenerate_discard_dict_output.patch')}
PARENT_SHA = '605f4326beb120c00cbbb6a6bbc36f04a03ce6a64f834cd557edc9fba4d799c6'
HELPER_SHA = '379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc'
BUDGET_SHA = 'd8a6c0244b00d206762b20a0684179b218fb9002fe0204af1784139395d1c1ca'

class ReserveCampaign(Campaign):
    def __init__(self, iid, attempt):
        self.iid, self.attempt = iid, attempt
        self.port, self.mutant = TASKS[iid]
        self.inp = ROOT / 'inputs_reserve6_v1' / iid
        self.out = ROOT / 'results' / iid / attempt
        self.out.mkdir(parents=True, exist_ok=False)
        self.state = {'task': iid, 'attempt': attempt, 'started_at': time.time(), 'steps': [],
                      'status': 'running', 'scope': 'CPU deterministic; no solver, no qualification',
                      'remaining': ['全部新失败与skip的人工归因', '独立复核', '公共GPU入口与预算'],
                      'private_scope': 'root behavior only; not actor permissions'}
        self.env = dict(os.environ, SLIME_AGENT_CC_PLATFORM_TARBALL=str(ROOT / 'cc/claude-code-linux-x64-2.1.205.tgz'),
                        RH2_SANDBOX_CPUS='2', RH2_SANDBOX_MEMORY_BYTES=str(4 * 1024**3),
                        RH2_GRADER_CPUS='2', RH2_GRADER_MEMORY_BYTES=str(4 * 1024**3))
        self.save()

    def verify_inputs(self):
        require(digest(Path(__file__).with_name('mixed_followups.py')) == PARENT_SHA, 'reviewed helper changed')
        require(digest(ROOT / 'tools_v1/private_behavior.py') == HELPER_SHA, 'private helper changed')
        require(digest(ROOT / 'tools_v1/replay_with_cpu_budget_v2.py') == BUDGET_SHA, 'budget wrapper changed')
        for rel, expected in FROZEN.items():
            require(digest(CODE / rel) == expected, 'frozen source changed: ' + rel)
        manifests = load(self.inp / 'input_manifest.json')
        for item in manifests:
            require(digest(self.inp / item['path']) == item['sha256'], 'input mismatch: ' + item['path'])
        required = {'public_commands.json','recovery.json','buildplan.json','private/gold.patch',
                    'private/'+self.mutant,'private/behavior_commands.json','private/patch_validation.json',
                    'private/expected_behavior.json','private/reference_expectations.json'}
        require(required.issubset({x['path'] for x in manifests}), 'missing required manifest entries')
        self.commands = load(self.inp / 'public_commands.json')
        self.recovery = load(self.inp / 'recovery.json')
        self.plan = load(self.inp / 'buildplan.json')
        require(self.plan['mode'] == 'use_original_no_repair', 'unreviewed recovery mode')
        self.validations = {x['patch']:x for x in load(self.inp / 'private/patch_validation.json')}
        views = [json.loads(x) for x in (ROOT/'prepared/reserve6_v1/rollout_task_views.jsonl').read_text().splitlines() if x.strip()]
        matches = [x['public'] for x in views if x['instance_id'] == self.iid]
        require(len(matches)==1, 'prepared view missing/ambiguous')
        self.public=matches[0]
        require(self.public['base_commit']==self.recovery['base_commit'], 'base mismatch')
        require(self.recovery['source_image'].split('@')[-1]==self.public['image_manifest_digest'], 'image manifest mismatch')
        hosts=[json.loads(x) for x in (ROOT/'private/reserve6_v1/host_grading_views.jsonl').read_text().splitlines() if x.strip()]
        grading=[x['grading'] for x in hosts if x['instance_id']==self.iid]
        require(len(grading)==1, 'private grading missing/ambiguous')
        expected=load(self.inp/'private/reference_expectations.json')
        for field in ['base_commit','fail_to_pass','pass_to_pass','test_patch']:
            require(grading[0][field]==expected[field], 'frozen private reference mismatch: '+field)
        self.gold=ROOT/'gold/reserve6_v1'/(self.iid+'.gold.patch')
        require(self.gold.read_bytes()==(self.inp/'private/gold.patch').read_bytes(), 'prepared gold mismatch')
        self.state.update(inputs={x['path']:x['sha256'] for x in manifests}, code_sha256=FROZEN,
                          helper_sha256={'mixed':PARENT_SHA,'private':HELPER_SHA,'budget':BUDGET_SHA})
        self.save()

    def actor(self, name, image, *, require_expected):
        dest = self.out / name
        self.run(name, [PY, CODE / 'experiments/task2_swegym_dev_20260925/devcheck.py',
                       '--prepared-summary', ROOT / 'prepared/reserve6_v1/replay_summary.json', '--task', self.iid,
                       '--commands', self.inp / 'public_commands.json', '--image', image, '--out-dir', dest,
                       '--attempt-id', 'cpu29-' + self.iid.lower().replace('__', '-') + '-' + self.attempt + '-' + name,
                       '--stub-port', self.port, '--wall-seconds', '1800'], timeout=2160)
        rec = load(dest / 'attempt.json')
        cleanup = rec.get('cleanup') or {}
        require(rec.get('harness_exit_code') == 0 and rec.get('result') == 'ran', 'actor harness incomplete')
        require(cleanup.get('container_rm') == 0 and cleanup.get('stub_rc') == 0 and cleanup.get('labeled_containers_left') == [] and cleanup.get('labeled_networks_left') == [] and cleanup.get('residual_after_force') == [] and not cleanup.get('network_failures')
                and not cleanup.get('relay_failures'), 'actor cleanup unconfirmed')
        checks = rec.get('checks') or {}
        for field in ['host_log_present', 'message_start_matches_stub_requests', 'result_event_present',
                      'log_complete', 'all_commands_ran']:
            require(checks.get(field) is True, 'actor evidence incomplete: ' + field)
        rows = rec.get('commands_result') or []
        require(len(rows) == len(self.commands), 'actor command count mismatch')
        require(all(x.get('rc') is not None and x['rc'] not in (124, 137) for x in rows), 'actor command timeout/not run')
        self.state.setdefault('actor_results', {})[name] = {'attempt': str(dest / 'attempt.json'),
                                                         'all_match_expect': checks.get('all_match_expect'),
                                                         'commands': rows}
        self.save()
        if require_expected:
            require(all(x.get('matches_expect') is True for x in rows), 'actor public behavior/dependency mismatch; manual diagnosis required')
            self.verify_target_evidence(dest)

    def verify_target_evidence(self, dest):
        expectations = load(self.inp/'private/expected_behavior.json')
        for cid, rc in expectations['base'].items():
            rec = next(x for x in self.state['actor_results'][dest.name]['commands'] if x['id']==cid)
            require(rec['rc']==rc, 'unexpected base command RC: '+cid)
            text=(dest/'captures'/(cid+'.out')).read_text()
            self.check_behavior_output(cid,text,'base')
            for token in expectations.get('nonzero_requirements',{}).get(cid,[]):
                if rc:
                    require(token in text, 'base nonzero lacks exact target evidence: '+cid)
            if cid=='public_regression':
                require('passed' in text and 'collected' in text and not re.search(r'\b(?:ERROR|FAILED)\b',text), 'public old tests incomplete')

    def check_behavior_output(self,cid,text,variant):
        if self.iid.endswith('4583') and cid.startswith('mask_'):
            lines=[x for x in text.splitlines() if x.startswith('MASK_OBSERVATIONS ')]
            require(len(lines)==1, 'missing/ambiguous mask observation')
            observed=json.loads(lines[0].split(' ',1)[1])
            dims=int(cid[5]); rows=observed['rows']
            require(observed['dims']==dims and len(rows)==4,'mask matrix incomplete')
            require({(x['backend'],x['custom']) for x in rows}=={(a,b) for a in ('numpy','torch') for b in (False,True)},'mask backend matrix mismatch')
            labels=[-1,-1] if variant=='base' or (variant=='degenerate' and dims==3) else [0,7]
            for row in rows:
                require(all(row[k] for k in ['ok_box','ok_type','ok_dtype','ok_device']), 'non-label mask regression')
                require(row['labels']==labels,'unexpected mask labels')
        elif self.iid.endswith('6975') and cid=='lazy_value_matrix':
            lines=[x for x in text.splitlines() if x.startswith('LAZY_VALUE_MATRIX ')]
            require(len(lines)==1,'missing/ambiguous lazy image observation')
            rows=json.loads(lines[0].split(' ',1)[1])
            require(len(rows)==6 and {(x['entry'],x['mode']) for x in rows}=={(a,b) for a in ('direct','dataset') for b in (True,False,None)},'lazy matrix incomplete')
            for row in rows:
                actual_policy=False if variant=='base' and row['entry']=='dataset' else row['mode'] is not False
                require(len(row['trace'])==2 and all(len(t)==1 and t[0]['effective']==actual_policy for t in row['trace']),'unexpected effective lazy dispatch')
                good_value=not (variant=='degenerate' and row['entry']=='dataset' and row['mode'] is True)
                require(row['value_ok'] is good_value,'unexpected returned image values')
                require(row['policy_ok'] is (actual_policy==(row['mode'] is not False)),'inconsistent lazy policy evidence')
                require(row['device']=='cpu' and isinstance(row['resample_function_calls'],int),'invalid CPU/resample observation')
                # real resample function is wrapped, not replaced; call counts are evidence, not a unique implementation oracle.
                require(row['resample_function_calls']>=0,'invalid resample count')
        elif cid=='public_regression':
            require('passed' in text and 'collected' in text and not re.search(r'\b(?:ERROR|FAILED)\b',text),'public regression unexpected failure')

    def private_behavior(self, image):
        # 每个变体独立调用已冻结helper，先解释结果/清理再启动下一变体。
        out=self.out/'private_behavior'
        out.mkdir()
        aggregate={'scope':'private root only; not actor','image':image,'variants':{}}
        identity=next(x['cmd'] for x in self.commands if x['id']=='identity')
        expected=load(self.inp/'private/expected_behavior.json')
        commands=load(self.inp/'private/behavior_commands.json')
        for variant,patch in [('base',None),('gold','gold.patch'),('degenerate',self.mutant)]:
            validation=self.validations[patch or 'gold.patch']
            steps=['git config --global --add safe.directory /testbed',identity,
                   hash_check([(validation['path'],validation['source_sha256'])])]
            files={}
            if patch:
                files[patch]=str(self.inp/'private'/patch)
                steps += ['git apply --check '+shlex.quote('/in/'+patch),
                          'git apply '+shlex.quote('/in/'+patch),
                          hash_check([(validation['path'],validation['applied_sha256'])])]
            spec={'image':image,'cpus':2,'memory':'4g','variants':{variant:steps},'files':files,'commands':commands}
            specpath=out/(variant+'_spec.json')
            write(specpath,spec)
            dest=out/(variant+'_run')
            self.run('private_'+variant,[PY,ROOT/'tools_v1/private_behavior.py',specpath,'--out',dest],timeout=1200)
            summary=load(dest/'summary.json')
            require(summary.get('image_id_actual')==image,'private image identity mismatch')
            require(set(summary['variants'])=={variant},'private variant missing/ambiguous')
            row=summary['variants'][variant]
            aggregate['variants'][variant]={'summary':str(dest/'summary.json'),**row}
            write(out/'summary.json',aggregate)
            require(row.get('status')=='executed_interpret_separately' and all(x['rc']==0 for x in row['preparation']),'private preparation incomplete')
            clean=row.get('cleanup') or {}
            require(clean.get('rm_rc')==0 and clean.get('query_rc')==0 and clean.get('remaining')==[],'private cleanup unconfirmed')
            require(len(row['commands'])==len(commands),'private commands incomplete')
            for command in row['commands']:
                cid=command['id']; rc=expected[variant][cid]
                text=(dest/variant/(cid+'.out')).read_text()
                self.check_behavior_output(cid,text,variant)
                require(command['rc']==rc,'private unexpected RC: '+variant+'/'+cid)
                require(len(text.encode())==command['stdout_bytes']+command['stderr_bytes'],'private output incomplete')
                if rc:
                    require(all(t in text for t in expected['nonzero_requirements'][cid]),'private failure not exact target')
            aggregate['variants'][variant]['expected_behavior_checked']=True
            write(out/'summary.json',aggregate)
        self.state['private_behavior']=str(out/'summary.json')
        self.state['private_expected_rc_matrix_confirmed']=True
        self.save()

    def grade(self, kind, image):
        dest = self.out / ('grade_' + kind)
        dest.mkdir()
        run_id = 'cpu29-' + self.iid.lower().replace('__', '-') + '-' + self.attempt + '-' + kind
        patchname = {'gold': 'gold.patch', 'degenerate': self.mutant}.get(kind)
        candidate = 'noop' if kind == 'noop' else ('gold-dir:' + str(ROOT / 'gold/reserve6_v1') if kind == 'gold'
                                                  else 'patch:' + str(self.inp / 'private' / self.mutant))
        wrapper = ROOT / 'tools_v1/replay_with_cpu_budget_v2.py'
        common = [PY, wrapper, '--setup-seconds', '900', '--budget-audit-dir', dest / 'budget', '--code-root', CODE]
        cmd = common + ['--mode', 'direct']
        if self.plan['mode'] == 'use_original_no_repair':
            require(self.inspect(self.public['image'])['Id'] == image, 'original image tag changed before grade')
        cmd += ['run', '--prepared-summary', ROOT / 'prepared/reserve6_v1/replay_summary.json', '--task-ids', self.iid,
                '--candidate', candidate, '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                '--cleanup-seconds', '120', '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts',
                '--ledger', dest / 'ledger.jsonl']
        name = 'grade_' + kind
        self.run(name, cmd, timeout=4380, more_env={'MILES_RH2_RUN_ID': run_id})
        lines = [json.loads(x) for x in (dest / 'ledger.jsonl').read_text().splitlines() if x.strip()]
        require(len(lines) == 1, 'expected exactly one grading record')
        row = lines[0]
        require(row.get('stage_error') is None and row.get('cleanup', {}).get('removed') is True, 'grade stage/cleanup incomplete')
        report = row.get('report') or {}
        expected_refs=load(self.inp/'private/reference_expectations.json')
        require(report.get('f2p_total')==len(expected_refs['fail_to_pass']) and report.get('p2p_total')==len(expected_refs['pass_to_pass']), 'formal reference counts differ')
        require(report.get('reward') in (0, 1) and not report.get('execution_failure_stage')
                and not report.get('infra_failure_detail'), 'formal grading did not complete valid target execution')
        require(row.get('reference_missing_count') == 0 and not (row.get('verdict_diagnostics') or {}).get('reference_skipped'),
                'reference missing/skipped; cannot interpret reward')
        install = row.get('install') or {}
        require(not install.get('install_failed_commands') and install.get('install_rc_last_command') == 0 and install.get('log_partial') is False, 'install/log incomplete')
        test = row.get('test') or {}
        require(test.get('segment_completed') is True and test.get('rc') is not None, 'test segment incomplete')
        require(not row.get('runner_integrity_changed'), 'runner integrity changed')
        require((row.get('observations') or {}).get('RH2_OBS_IMPORT_PATH', '').startswith('/testbed/'),
                'grader actual package import is not recorded from candidate workspace')
        projection = row.get('projection') or {}
        if patchname:
            validation = self.validations[patchname]
            require(projection.get('included_paths') == [validation['path']], 'unexpected projected source paths')
            patches = list((dest / 'artifacts').rglob('frozen_patch.json'))
            require(len(patches) == 1, 'missing/ambiguous frozen artifact')
            require(load(patches[0]).get('excluded_pathset_changed') is False, 'excluded source changed')
            require(len(load(patches[0])['entries'])==1, 'unexpected extra frozen entries')
            entries = [x for x in load(patches[0])['entries'] if x['path'] == validation['path']]
            require(len(entries) == 1, 'expected source bytes absent from frozen patch')
            require(entries[0]['mode']=='100644' and entries[0]['object_type']=='regular', 'unexpected source type/mode')
            actual = hashlib.sha256(base64.b64decode(entries[0]['content_b64'], validate=True)).hexdigest()
            require(actual == validation['applied_sha256'], 'frozen source differs from actually validated candidate')
            write(dest / 'frozen_source_checked.json', {'path': validation['path'], 'sha256': actual, 'patch': patchname})
        else:
            require(projection.get('included_paths') == [], 'noop unexpectedly changed projected files')
        footers = []
        for line in (self.out / (name + '.log')).read_text().splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and 'manager_close' in obj:
                footers.append(obj)
        require(len(footers) == 1, 'driver cleanup footer missing/ambiguous')
        footer = footers[0]
        require(not footer.get('halted') and not footer.get('aborted') and not footer.get('cleanup_failures')
                and not footer.get('manager_close', {}).get('containers_open')
                and footer.get('final_status', {}).get('exit_code') == 0, 'driver cleanup/status unconfirmed')
        require(footer['manager_close'].get('containers_created_total')==footer['manager_close'].get('containers_removed_total')==1, 'manager container accounting mismatch')
        require(not footer['manager_close'].get('supply_open') and not footer['manager_close'].get('cleanup_failures'), 'manager resource cleanup incomplete')
        logfile = dest/'eval_logs'/Path(row['log']['path']).name
        require('sha256:'+digest(logfile)==row['log']['sha256'], 'formal log hash mismatch')
        write(dest / 'driver_close_checked.json', footer)
        self.state.setdefault('formal_results', {})[kind] = {'reward': report['reward'], 'test_rc': test['rc'], 'ledger': str(dest / 'ledger.jsonl')}
        self.save()
        # 正负控制异常先停；退化得1是待审查的误收证据，不阻止该题完成取证。
        if kind in ('noop', 'gold'):
            require(report['reward'] == (1 if kind == 'gold' else 0), kind + ' control changed; diagnose')
        if report['reward'] == 1:
            require(test['rc'] == 0, 'reward=1 but complete test command failed; diagnose before next candidate')

    def execute(self):
        self.verify_inputs()
        source=self.recovery['source_image']
        self.run('pull_original',['docker','pull',source],timeout=3600)
        base=self.inspect(source)
        # 冻结grader仍引用公开tag；仅把已拉取且验明digest的同一image设为本地别名，不再请求可变latest。
        self.run('alias_original_for_frozen_grader',['docker','tag',base['Id'],self.public['image']],timeout=60)
        require(self.inspect(self.public['image'])['Id']==base['Id'], 'public local alias differs from pinned source')
        write(self.out/'original_alias.json',{'source':source,'image_id':base['Id'],'local_alias':self.public['image'],
              'scope':'local alias only; no new layer or dependency change, frozen formal CLI preserved'})
        write(self.out/'original_image.json',base)
        self.actor('actor_original',base['Id'],require_expected=True)
        self.private_behavior(base['Id'])
        for kind in ['noop','gold','degenerate']:
            self.grade(kind,base['Id'])
        self.state['status']='executed_pending_review'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task',choices=TASKS,required=True)
    ap.add_argument('--attempt',default='reserve6-v1')
    args=ap.parse_args()
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,24}',args.attempt) is not None,'invalid attempt')
    campaign=ReserveCampaign(args.task,args.attempt)
    def interrupted(signum,_frame):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        campaign.execute()
    except BaseException as exc:
        campaign.state.update(status='stopped_needs_diagnosis',error=repr(exc))
        raise
    finally:
        campaign.state['finished_at']=time.time()
        campaign.save()

if __name__=='__main__':
    main()
