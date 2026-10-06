#!/usr/bin/env python3
"""CPU公开交付窄验：仅追加固定公开brief，求解/导出/清理由冻结入口执行。"""
import dataclasses
import hashlib
import importlib.util
import os
from pathlib import Path
import sys


def digest(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    release = Path(os.environ['COVERAGE_PUBLIC_RELEASE_ROOT']).resolve()
    assert digest(release / 'manifest.json') == os.environ['COVERAGE_PUBLIC_RELEASE_SHA256']
    repo = release / 'repo'
    notes = Path(os.environ['COVERAGE_PUBLIC_NOTES_PATH']).resolve()
    statement = Path(os.environ['COVERAGE_PUBLIC_STATEMENT_PATH']).resolve()
    assert digest(notes) == os.environ['COVERAGE_PUBLIC_NOTES_SHA256']
    assert digest(statement) == os.environ['COVERAGE_PUBLIC_STATEMENT_SHA256']
    sys.path.insert(0, str(repo / 'rh2/src'))
    from repoharness2.contracts import scan_for_forbidden_markers
    notes_text = notes.read_text()
    assert notes_text.strip() and not scan_for_forbidden_markers(notes_text)
    entry = repo / 'rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py'
    spec = importlib.util.spec_from_file_location('coverage_frozen_r2e_solve', entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = module.R2EAttempt

    class PublicNotesAttempt(base):
        async def solve(self, sb, task_spec, agent_env, env_injections):
            assert self.ns.solver == 'stub_script'
            assert task_spec.task_id == 'r2e_gym_subset::coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5'
            assert statement.read_text().strip() in task_spec.prompt
            # 与已验ordinary_gpu入口的公开拼接公式一致；未改材料/环境/评分spec。
            prompt = task_spec.prompt + ('\n\nPublic development instructions (current for this probe; '
                'these supersede older development hints in the public bundle):\n' + notes_text.strip())
            self.rec['public_delivery'] = {
                'mode': 'brief', 'base_prompt_sha256': 'sha256:' + hashlib.sha256(task_spec.prompt.encode()).hexdigest(),
                'delivered_prompt_sha256': 'sha256:' + hashlib.sha256(prompt.encode()).hexdigest(),
                'public_notes_sha256': digest(notes), 'statement_sha256': digest(statement),
            }
            self.rec['prompt_sha256'] = self.rec['public_delivery']['delivered_prompt_sha256']
            self.rec['public_notes_sha256'] = digest(notes)
            self.rec['cpu_public_wrapper'] = {'path': str(Path(__file__).resolve()), 'sha256': digest(Path(__file__)),
                                             'frozen_solve_path': str(entry), 'frozen_solve_sha256': digest(entry)}
            self.write_text('prompt.txt', prompt)
            self.save()
            return await super().solve(sb, dataclasses.replace(task_spec, prompt=prompt), agent_env, env_injections)

    module.R2EAttempt = PublicNotesAttempt
    return module.main(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
