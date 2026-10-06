"""8801原FP有界CPU补评；复用已验CPU执行收口，仅新构造原输入的setup900。"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)
        f.write('\n')


def load_module(name, path):
    loader = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def construct(ns, base):
    root = base.verify_snapshot(ns)
    inputs = json.loads((root / 'inputs_8801.json').read_text())
    closed = root / 'closed'
    source_manifest = json.loads((closed / 'sync_receipt_v3.json').read_text())
    for row in source_manifest['file_mapping']:
        p = closed / row['source_relative']
        need(p.is_file() and not p.is_symlink() and digest(p) == row['expected_sha256']
             and p.stat().st_size == row['expected_bytes'], 'original closed source changed')
    job = closed / inputs['original_job_directory']
    result = json.loads((job / 'result.json').read_text())
    attempt = json.loads((job / 'attempt/attempt.json').read_text())
    old_diag_paths = list((job / 'grading/eval_logs').glob('*.diagnostics.json'))
    need(len(old_diag_paths) == 1, 'original unique diagnostics absent')
    old_diag = json.loads(old_diag_paths[0].read_text())
    report = result['report']
    need(report['reward'] is None and report['failure_category'] == 'infra_failure'
         and report['infra_failure_detail'] == 'grading_control_surface_protect_timeout_after_300s'
         and old_diag['candidate'] is None and old_diag['supply'] is None, 'original timeout/mode differs')
    need(result['baseline_rebuild_passed'] and result['cleanup_ok'] and attempt['cleanup']['cleanup_ok']
         and attempt['termination'] == 'completed', 'original baseline/solve/cleanup incomplete')
    close = result['manager_close']
    need(close['containers_open'] == close['supply_open'] == close['cleanup_failures'] == []
         and close['containers_created_total'] == close['containers_removed_total'] == 1, 'original grader not closed')
    cleanup = attempt['cleanup']
    need(cleanup['container_rm'] == 0 and not cleanup['container_left']
         and not any(cleanup[k] for k in ['network_failures', 'relay_failures', 'labeled_containers_left', 'labeled_networks_left']), 'original actor not closed')
    drain = attempt['gateway_drain']
    need(drain['drained'] and drain['revoked'] and drain['active_requests'] == 0, 'original gateway not drained')
    frozen = json.loads((job / 'attempt/frozen/frozen_patch.json').read_text())
    need(frozen['baseline_manifest_digest'] == result['baseline_manifest_digest'] == inputs['old_baseline_digest']
         and result['frozen_patch_digest'] == inputs['old_FP_digest'], 'original FP/baseline provenance drift')
    old_record = json.loads((job / 'input_check.json').read_text())
    for field, name in [('tasks_config', 'source_config'), ('prepared_summary', 'source_summary'),
                        ('gateway_config', 'gateway_config'), ('adapter_config', 'adapter_config')]:
        need('sha256:' + digest(closed / inputs[name]) == old_record['input_sha256'][field],
             'actual original config SHA differs: ' + field)
    original = json.loads((closed / inputs['source_config']).read_text())
    changed = copy.deepcopy(original)
    cfg = changed[inputs['task_id']]
    need(cfg['grader']['setup_seconds'] == 300, 'original preparation budget differs')
    cfg['grader']['setup_seconds'] = 900
    revert = copy.deepcopy(changed)
    revert[inputs['task_id']]['grader']['setup_seconds'] = 300
    need(revert == original, 'more than sole setup budget changed')
    # Transport-only path projection follows the fixed input files, before load_inputs.
    summary = json.loads((closed / inputs['source_summary']).read_text())
    summary['prepared_dir'] = str((closed / inputs['source_summary']).parent / 'prepared')
    summary['private_dir'] = str((closed / inputs['source_summary']).parent / 'private')
    save(ns.out / 'summary.json', summary)
    cfg['prepared_summary'] = str(ns.out / 'summary.json')
    save(ns.out / 'tasks.json', changed)
    fixed_code = root / 'frozen_code_v8'
    sys.path.insert(0, str(fixed_code / 'rh2/src'))
    entry_path = fixed_code / 'rh2/experiments/ordinary_gpu_probe_20261002/entry.py'
    entry = load_module('dask8801_CPU_fixed_entry', entry_path)
    params = SimpleNamespace(tasks_config=ns.out / 'tasks.json', task=inputs['task_id'],
        prepared_summary=None, gateway_config=closed / inputs['gateway_config'],
        adapter_config=closed / inputs['adapter_config'], adapter_idle_drop_seconds=14400,
        gateway_host='172.17.0.1', gateway_port=18081, attempt_id=inputs['original_attempt_id'],
        solver='coder', out_dir=ns.out)
    _, _, rollout, spec, profile, prompt, record = entry.load_inputs(params)
    for key in inputs['fixed_input_record_fields']:
        need(record[key] == old_record[key], 'original input identity drift: ' + key)
    need(record['grading_budgets'] == inputs['grading_budgets'], 'bounded grading budgets differ')
    need(spec.image == inputs['expected_source_image'] and not spec.image_local_build
         and spec.image_manifest_digest == inputs['expected_source_manifest_digest'], 'exact original source grader drift')
    need(profile.cpus == 2 and profile.memory_bytes == 4294967296 and profile.pids_limit == 512
         and profile.candidate_exec_uid == 54322, 'fixed CPU grader profile differs')
    # GraderSandboxProfile固定断网，无network_mode属性；实际NetworkMode由已验base独立inspect核。
    source = entry.source_from_original(job / 'attempt', spec, inputs['public_bundle_digest'],
        expected_attempt_id=inputs['original_attempt_id'])
    need(source.frozen_patch_digest == inputs['old_FP_digest'], 'original FP digest drift')
    from repoharness2.grading.manager import SWEGradingManager, grading_scripts_digest
    SWEGradingManager._verify_frozen_delta_binding(None, spec, source)
    single = grading_scripts_digest(spec, two_stage=False)
    need(single == inputs['scripts_digest'], 'original complete single-shell scripts changed')
    scripts = {key: getattr(spec, key) for key in ['trusted_setup_script', 'candidate_test_script',
        'candidate_install_script', 'candidate_test_after_install_script', 'eval_script']}
    loaded = []
    for name, module in tuple(sys.modules.items()):
        if name.split('.', 1)[0] in {'repoharness2', 'slime'} and getattr(module, '__file__', None):
            p = Path(module.__file__).resolve()
            need(p.is_relative_to(fixed_code / 'rh2/src'), 'runtime module outside fixed code8: ' + name)
            loaded.append({'module': name, 'path': str(p), 'sha256': digest(p)})
    save(ns.out / 'runtime_code_binding.json', {'python': sys.executable, 'prefix': sys.prefix,
        'actual_modules': loaded, 'worker_path': str(Path(__file__).resolve()),
        'worker_sha256': digest(Path(__file__)), 'validated_execution_base_sha256': inputs['execution_base_sha256'],
        'actual_entry_path': str(entry_path)})
    save(ns.out / 'complete_scripts.json', scripts)
    save(ns.out / 'input_check.json', record)
    save(ns.out / 'projection.json', source.projection.model_dump(mode='json'))
    binding = {'job_id': ns.job_id, 'original_attempt_id': inputs['original_attempt_id'],
        'original_FP_digest': inputs['old_FP_digest'], 'original_baseline_digest': inputs['old_baseline_digest'],
        'original_materials_identity': spec.grading_materials_identity,
        'resource_profile': {'cpus': 2, 'memory_bytes': 4294967296, 'pids_limit': 512, 'candidate_uid': 54322},
        'budgets': inputs['grading_budgets'], 'reference_total': 45,
        'script_sha256': {k: hashlib.sha256(v.encode()).hexdigest() if v is not None else None for k, v in scripts.items()},
        'single_shell_scripts_digest': single, 'two_stage_scripts_digest': grading_scripts_digest(spec, two_stage=True),
        'expected_actual_mode': 'single_shell_deny_all_no_supply', 'expected_actual_scripts_digest': single,
        'recipe_id': inputs['recipe_id'], 'new_model_calls': 0,
        'snapshot_manifest_sha256': ns.snapshot_manifest_sha256,
        'baseline_binding_verified_without_rewriting_original': True,
        'actual_mode_not_inferred_from_script_presence': True,
        'source_closed_manifest_sha256': inputs['source_closed_manifest_sha256'],
        'image_binding_scope': inputs['image_binding_scope'], 'only_change': 'setup300to900',
        'execution_base_sha256': inputs['execution_base_sha256']}
    save(ns.out / 'binding.json', binding)
    return inputs, spec, profile, source, binding


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--snapshot-root', type=Path, required=True)
    p.add_argument('--snapshot-manifest-sha256', required=True)
    p.add_argument('--instance', choices=['8801'], required=True)
    p.add_argument('--job-id', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    ns = p.parse_args()
    need(ns.job_id == 'dask8801-original-fp-cpu-recovery-20261003-v1', 'unexpected job; no automatic retry')
    need(not ns.out.exists(), 'output exists; never overwrite or auto-retry')
    base_path = ns.snapshot_root.parent / 'validated_execution_base.py'
    need(digest(base_path) == '3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312', 'validated execution base changed')
    base = load_module('dask8801_validated_CPU_execution_base', base_path)
    ns.out.mkdir(parents=True, mode=0o700)
    inputs, spec, profile, source, binding = construct(ns, base)
    if ns.execute:
        need(os.geteuid() == 0 and str(ns.out).startswith('/work/rh2-category2-20261003/packages/swe_dask/'), 'CPU package execution boundary differs')
        asyncio.run(base.execute_with_signals(ns, inputs, spec, profile, source, binding))
    else:
        save(ns.out / 'pure_check_done.json', {'identity_constructed_only': True, 'candidate_executed': False})
    print(json.dumps({'output': str(ns.out), 'job_id': ns.job_id, 'executed': ns.execute}))


if __name__ == '__main__':
    main()
