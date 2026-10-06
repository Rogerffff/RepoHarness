"""DVC 自有作业的薄封装：只调用冻结版本的 replay_grade prepare/run。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path('/work/rh2-category2-20261003')
TASKS = {'iterative__dvc-' + str(n) for n in (4166, 5839, 6954, 9395)}
BLOCKED_5839 = {
    'cat2-cpu-r2e088-swe12-git-20261003-v1',
    'cat2-cpu-r2e088-swe13-git-20261003-v1',
    'cat2-cpu-r2e089092-swe13-git-20261003-v1',
}


def sha(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def label(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}', value):
        raise ValueError('invalid output/release label')
    return value


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def prepared_identity(base, task):
    summary_path = base / 'prepared/replay_summary.json'
    summary = json.loads(summary_path.read_text())
    if summary['task_ids'] != ['swe_gym_lite::' + task]:
        raise ValueError('prepared task identity differs')
    if Path(summary['prepared_dir']).resolve() != (base / 'prepared').resolve() or Path(summary['private_dir']).resolve() != (base / 'private').resolve():
        raise ValueError('prepared output directories differ')
    manifest_path = base / 'prepared/prepared_manifest.json'
    if sha(manifest_path).removeprefix('sha256:') != summary['prepared_manifest_sha256']:
        raise ValueError('prepared manifest hash differs')
    prepared = json.loads(manifest_path.read_text())
    if prepared['task_count'] != 1 or len(prepared['tasks']) != 1 or prepared['tasks'][0]['task_id'] != 'swe_gym_lite::' + task or prepared['tasks'][0]['instance_id'] != task:
        raise ValueError('prepared manifest task identity differs')
    for name, item in prepared['files'].items():
        path = base / 'prepared' / name
        if not path.resolve().is_relative_to((base / 'prepared').resolve()) or sha(path).removeprefix('sha256:') != item['sha256']:
            raise ValueError('prepared file hash differs')
    host = base / 'private/host_grading_views.jsonl'
    if sha(host).removeprefix('sha256:') != summary['host_grading_artifact_sha256'] or prepared['host_grading_artifact_sha256'] != summary['host_grading_artifact_sha256']:
        raise ValueError('host grading artifact hash differs')
    return sha(summary_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--mode', choices=['prepare', 'run'], required=True)
    parser.add_argument('--candidate')
    parser.add_argument('--job-id', required=True)
    args = parser.parse_args()
    cfg = json.loads(args.input.read_text())
    task = cfg['instance_id']
    if task not in TASKS or not label(args.job_id).startswith('dvc' + task.rsplit('-', 1)[1] + '-'):
        raise ValueError('wrong task/job ownership')
    release_id = label(cfg['release_id'])
    if task == 'iterative__dvc-5839' and release_id in BLOCKED_5839:
        raise ValueError('known shared UID defect: do not retry this material version')
    release = ROOT / 'releases' / release_id
    repo = release / 'repo'
    manifest = release / 'manifest.json'
    if sha(manifest) != cfg['release_manifest_sha256']:
        raise ValueError('release manifest pin differs')
    declared = json.loads(manifest.read_text())
    if declared['release_id'] != release_id:
        raise ValueError('release ID differs')
    for relative, item in declared['files'].items():
        path = repo / relative
        if not path.resolve().is_relative_to(repo.resolve()):
            raise ValueError('manifest path outside release')
        if path.stat().st_size != item['size'] or sha(path).removeprefix('sha256:') != item['sha256']:
            raise ValueError('frozen release file differs: ' + relative)
    if sha(Path(__file__)) != cfg['runner_sha256']:
        raise ValueError('runner pin differs')
    base = ROOT / 'packages/swe_dvc/formal_jobs' / label(cfg['series'])
    job = base / 'jobs' / args.job_id
    job.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(repo / 'rh2/src'),
               MILES_RH2_RUN_ID=args.job_id, RH2_SANDBOX_CPUS='2',
               RH2_SANDBOX_MEMORY_BYTES=str(4 * 1024**3), RH2_SANDBOX_PIDS_LIMIT='512',
               RH2_GRADER_CPUS='2', RH2_GRADER_MEMORY_BYTES=str(4 * 1024**3),
               RH2_GRADER_PIDS_LIMIT='512', RH2_GRADER_UID='54322', RH2_SANDBOX_RELAY_PORT='18196')
    cmd = [sys.executable, '-B', str(repo / 'rh2/scripts/replay_grade.py'), args.mode]
    if args.mode == 'prepare':
        if (base / 'prepared').exists() or (base / 'private').exists():
            raise ValueError('prepared/private already exists; never overwrite or rebind')
        if args.candidate is not None:
            raise ValueError('prepare has no candidate')
        cmd += ['--repo-root', str(repo), '--out-dir', str(base / 'prepared'),
                '--private-dir', str(base / 'private'), '--task-ids', 'swe_gym_lite::' + task]
    else:
        selected = cfg['candidates'][args.candidate]
        prepare_job = base / 'jobs' / label(cfg['prepare_job_id']) / 'completion.json'
        if sha(prepare_job) != cfg['prepare_completion_sha256']:
            raise ValueError('prepare completion pin differs')
        prior = json.loads(prepare_job.read_text())
        if prior['mode'] != 'prepare' or prior['process_exit_code'] != 0 or prior['instance_id'] != task or prior['release_id'] != release_id or prior['release_manifest_sha256'] != cfg['release_manifest_sha256'] or prior['runner_sha256'] != cfg['runner_sha256'] or prior['runtime_python'] != sys.executable:
            raise ValueError('prepare provenance differs from run task/release/runner')
        prepared_sha = prepared_identity(base, task)
        if prepared_sha != cfg['prepared_summary_sha256'] or prepared_sha != prior['prepared_summary_sha256']:
            raise ValueError('prepared summary differs from successful preparation')
        image = cfg['image_id']
        inspected = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'],
                                   check=True, capture_output=True, text=True)
        if inspected.stdout.strip() != image:
            raise ValueError('actual image ID differs')
        candidate = 'noop'
        if selected['path'] is not None:
            path = base / selected['path']
            if not path.resolve().is_relative_to(base.resolve()) or sha(path) != selected['sha256']:
                raise ValueError('candidate path or bytes differ')
            candidate = 'patch:' + str(path)
        elif args.candidate != 'noop' or selected['sha256'] != 'sha256:' + hashlib.sha256(b'').hexdigest():
            raise ValueError('only explicit empty noop may omit candidate file')
        cmd += ['--prepared-summary', str(base / 'prepared/replay_summary.json'),
                '--task-ids', task, '--candidate', candidate, '--repeat', '1',
                '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                '--cleanup-seconds', '120', '--image-pull-seconds', '1800',
                '--derived-image', image, '--derived-image-recipe', cfg['image_recipe_identity'],
                '--eval-log-dir', str(job / 'eval_logs'), '--artifacts-dir', str(job / 'artifacts'),
                '--ledger', str(job / 'ledger.jsonl')]
    record = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'job_id': args.job_id,
              'mode': args.mode, 'candidate': args.candidate, 'input_sha256': sha(args.input),
              'release_id': release_id, 'release_manifest_sha256': sha(manifest),
              'release_files_checked': len(declared['files']), 'runner_sha256': sha(Path(__file__)),
              'instance_id': task, 'command': cmd, 'runtime_python': sys.executable,
              'environment': {k: v for k, v in env.items() if k.startswith('RH2_') or k in
                              ['PYTHONDONTWRITEBYTECODE', 'PYTHONPATH', 'MILES_RH2_RUN_ID']},
              'formal_entry_unchanged': True, 'qualification_claim': False}
    dump(job / 'invocation.json', record)
    with (job / 'process.log').open('wb') as stream:
        rc = subprocess.run(cmd, cwd=repo / 'rh2', env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
    record.update(completed_at_utc=datetime.now(timezone.utc).isoformat(), process_exit_code=rc,
                  process_log_sha256=sha(job / 'process.log'))
    if args.mode == 'prepare' and rc == 0:
        record['prepared_summary_sha256'] = prepared_identity(base, task)
    if (job / 'ledger.jsonl').exists():
        record['ledger_sha256'] = sha(job / 'ledger.jsonl')
    dump(job / 'completion.json', record)
    print(json.dumps({'job_id': args.job_id, 'driver_exit_code': rc, 'output': str(job)}, ensure_ascii=False), flush=True)
    if (job / 'ledger.jsonl').exists():
        for line in (job / 'ledger.jsonl').read_text().splitlines():
            row = json.loads(line)
            print(json.dumps({k: row.get(k) for k in ['report', 'stage_error', 'reference_missing_count',
                                                   'cleanup', 'grading_revision']}, ensure_ascii=False), flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
