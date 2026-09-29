"""仅补 MONAI6975 三方正式评分；复用原 actor/private，不改生产代码。"""
from __future__ import annotations

import argparse
import json
import signal
import subprocess
import time
from pathlib import Path

from monai_reserve_followups_v1 import ReserveCampaign, ROOT, load, require, write, digest

IID = 'Project-MONAI__MONAI-6975'
PARENT_SHA = '32fb723f773569858cdf97d148616a67c43c55bd55aabb2e07649df55e735145'
OLD = ROOT / 'results' / IID / 'reserve6-v1'


def driver_footer(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and 'manager_close' in obj:
            rows.append(obj)
    require(len(rows) == 1, 'missing/ambiguous manager footer')
    footer = rows[0]
    close = footer.get('manager_close') or {}
    final = footer.get('final_status') or {}
    require(not footer.get('halted') and not footer.get('aborted')
            and not footer.get('cleanup_failures'), 'driver halted or cleanup failed')
    require(close.get('containers_created_total') == close.get('containers_removed_total') == 1,
            'manager created/removed accounting differs')
    for key in ['containers_open', 'supply_open', 'cleanup_failures']:
        require(close.get(key) == [], 'manager cleanup unknown: ' + key)
    require(final.get('exit_code') == 0 and final.get('grader_containers_open') == []
            and final.get('cleanup_failures_total') == 0, 'final cleanup/status incomplete')
    return footer


def runtime_empty():
    containers = subprocess.check_output(['docker', 'ps', '-aq'], text=True, timeout=60).strip()
    networks = subprocess.check_output(['docker', 'network', 'ls', '--format', '{{.Name}}'],
                                       text=True, timeout=60).splitlines()
    require(not containers and not [n for n in networks if n not in ('bridge', 'host', 'none')],
            'runtime not empty before/after bounded recovery')


class Recovery(ReserveCampaign):
    def __init__(self, approval):
        super().__init__(IID, 'grading-setup1800-v1')
        self.approval = load(approval)
        self.state['recovery_approval'] = {'path': str(approval), 'sha256': digest(approval)}
        self.state['scope'] = 'grade only; preparation1800, test1800/whole3600 unchanged; actor/private reused'
        self.save()

    def run(self, name, args, *, timeout=3600, more_env=None):
        args = list(map(str, args))
        if name.startswith('grade_'):
            pos = args.index('--setup-seconds') + 1
            require(args[pos] == '900', 'unexpected inherited preparation budget')
            args[pos] = '1800'
            require(args[args.index('--grading-deadline-seconds') + 1] == '3600', 'whole deadline changed')
            require(args[args.index('--candidate-stage-seconds') + 1] == '900', 'candidate deadline changed')
        super().run(name, args, timeout=timeout, more_env=more_env)
        if not name.startswith('grade_'):
            return
        dest = self.out / name
        rows = [json.loads(line) for line in (dest / 'ledger.jsonl').read_text().splitlines() if line.strip()]
        require(len(rows) == 1, 'expected one grading record')
        row = rows[0]
        footer = driver_footer(self.out / (name + '.log'))
        write(dest / 'driver_close_checked.json', footer)
        require((row.get('cleanup') or {}).get('removed') is True, 'candidate cleanup incomplete')
        report = row.get('report') or {}
        write(dest / 'execution_classification.json', {
            'stage_error': row.get('stage_error'), 'report': report,
            'install': row.get('install'), 'test': row.get('test'),
            'resource_facts': row.get('resource_facts'),
            'scope': 'classify actual infra before comparing nullable reference counts',
        })
        require(row.get('stage_error') is None, 'candidate/export stage failed')
        require(report.get('reward') in (0, 1) and not report.get('infra_failure_detail')
                and not report.get('execution_failure_stage'),
                'formal execution unavailable: ' + str(report.get('infra_failure_detail') or report))
        budget = load(dest / 'budget' / (IID + '.json'))
        require(budget.get('after') == 1800 and budget.get('test_seconds_unchanged') == 1800,
                'unexpected actual preparation/test budget')
        # inherited grade() now verifies original references, full logs, frozen source and both cleanup layers.

    def execute(self):
        require(digest(Path(__file__).with_name('monai_reserve_followups_v1.py')) == PARENT_SHA,
                'frozen parent changed')
        self.verify_inputs()
        require(self.approval['task'] == IID and self.approval['setup_seconds'] == 1800,
                'wrong recovery approval')
        require(self.approval['old_attempt'] == str(OLD), 'wrong prior attempt')
        for rel, info in self.approval['old_run_evidence'].items():
            path = (OLD / rel).resolve()
            require(path.is_relative_to(OLD.resolve()) and path.is_file(), 'invalid reuse path')
            require(path.stat().st_size == info['bytes'] and digest(path) == info['sha256'],
                    'reuse evidence changed: ' + rel)
        old_status = load(OLD / 'status.json')
        require(old_status.get('status') == 'stopped_needs_diagnosis'
                and old_status.get('private_expected_rc_matrix_confirmed') is True,
                'prior actor/private not closed as reviewed')
        rows = [json.loads(x) for x in (OLD / 'grade_noop/ledger.jsonl').read_text().splitlines() if x.strip()]
        require(len(rows) == 1, 'prior ledger ambiguous')
        old = rows[0]
        require(old['report'].get('infra_failure_detail') == 'grading_control_surface_protect_timeout_after_900s'
                and old['report'].get('reward') is None and old.get('install') is None
                and old.get('test') is None and old['cleanup'].get('removed') is True,
                'prior failure not the reviewed preparation timeout')
        driver_footer(OLD / 'grade_noop.log')
        sibling = load(ROOT / 'results/Project-MONAI__MONAI-4583/reserve6-v1/status.json')
        require(sibling.get('status') == 'executed_pending_review', 'sibling task has not closed normally')
        runtime_empty()
        source = self.recovery['source_image']
        before = load(OLD / 'original_image.json')
        actual = self.inspect(source)
        require(actual['Id'] == before['Id'] == self.approval['image_id'], 'pinned image changed')
        require(self.inspect(self.public['image'])['Id'] == actual['Id'], 'local alias changed')
        write(self.out / 'original_image.json', actual)
        write(self.out / 'reused_evidence.json', self.approval)
        for kind in ['noop', 'gold', 'degenerate']:
            self.grade(kind, actual['Id'])
        runtime_empty()
        self.state['status'] = 'executed_pending_review'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--approval', required=True, type=Path)
    args = ap.parse_args()
    campaign = Recovery(args.approval)
    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        campaign.execute()
    except BaseException as exc:
        campaign.state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        campaign.state['finished_at'] = time.time()
        campaign.save()


if __name__ == '__main__':
    main()
