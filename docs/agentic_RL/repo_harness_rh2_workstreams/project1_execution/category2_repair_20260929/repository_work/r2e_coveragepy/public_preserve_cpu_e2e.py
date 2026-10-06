#!/usr/bin/env python3
"""仅本题已分配18210/18211端口的窄验包装；正式E2E评分/往返/清理不改。"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path


def digest(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('release-root', 'release-sha256', 'scenario', 'out-root', 'prepared-summary', 'overlays',
                'cc-tarball', 'attempt-id', 'notes', 'notes-sha256', 'statement', 'statement-sha256'):
        ap.add_argument('--' + key, required=True)
    args = ap.parse_args()
    release = Path(args.release_root).resolve()
    assert digest(release / 'manifest.json') == args.release_sha256
    assert not Path(args.out_root).exists(), '必须使用新输出目录'
    entry = release / 'repo/rh2/experiments/r2e_lifecycle_20260929/r2e_probe_e2e.py'
    spec = importlib.util.spec_from_file_location('coverage_frozen_e2e', entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOLVE = Path(__file__).resolve().with_name('public_notes_cpu_solve.py')
    os.environ.update(COVERAGE_PUBLIC_RELEASE_ROOT=str(release), COVERAGE_PUBLIC_RELEASE_SHA256=args.release_sha256,
        COVERAGE_PUBLIC_NOTES_PATH=str(Path(args.notes).resolve()), COVERAGE_PUBLIC_NOTES_SHA256=args.notes_sha256,
        COVERAGE_PUBLIC_STATEMENT_PATH=str(Path(args.statement).resolve()),
        COVERAGE_PUBLIC_STATEMENT_SHA256=args.statement_sha256)
    # 旧E2E命令行只接18190–18199；这里仅使用资源分配者已核准的本题固定两端口。
    ns = argparse.Namespace(scenario=args.scenario, out_root=args.out_root, prepared_summary=args.prepared_summary,
        overlays=args.overlays, cc_tarball=args.cc_tarball, gw_host='172.17.0.1', gw_port=18210, stub_port=18211,
        gateway_request_cap=12, subnet_skip=0, attempt_id=args.attempt_id, label='rh2.coveragepy=ea69-public-preserve-v3',
        no_grade=False, controls='', gold_dir='/unused', grade_seconds=5400, env_reset_timeout=0.0,
        candidate_stage_seconds=0.0, regrade='', regrade_note='', controls_only=False)
    class EmptyPublicDelivery(module.E2E):
        def solve(self):
            record = super().solve()
            candidate = record.get('candidate') or {}
            frozen = json.loads((self.out / 'attempt/frozen/frozen_patch.json').read_text())
            empty_ok = (candidate.get('export_ok') is True and candidate.get('empty') is True
                        and candidate.get('entry_count') == 0 and candidate.get('entries') == []
                        and frozen.get('entries') == [])
            self.summary['public_delivery_empty_scope'] = {
                'required_empty': True, 'verified': empty_ok, 'wrapper_sha256': digest(Path(__file__)),
                'frozen_patch_file_sha256': digest(self.out / 'attempt/frozen/frozen_patch.json'),
            }
            if not empty_ok:
                self.summary['stop_reason'] = 'public_delivery_candidate_not_empty_or_export_failed'
                self.save()
                raise RuntimeError(self.summary['stop_reason'])
            self.save()
            return record

    return EmptyPublicDelivery(ns).main()


if __name__ == '__main__':
    raise SystemExit(main())
