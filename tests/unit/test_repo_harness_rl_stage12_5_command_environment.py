from __future__ import annotations

from pathlib import Path
import sys

import pytest

from repo_harness.errors import WorkspaceError
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import LocalWorkspaceAdapter


def test_stage12_5_local_workspace_adapter_injects_runtime_command_env(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-env",
        run_dir=run_dir,
        command_env_provider=lambda path: {
            "PATH": "/usr/bin",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "VIRTUAL_ENV": "/tmp/runtime-env",
            "PYTHONPATH": str(path),
        },
    )
    with RunRecorder("stage12-5-env", run_dir, task_id="task") as recorder:
        result = adapter.run_command(
            workspace,
            [
                sys.executable,
                "-c",
                "import os; print(os.environ['VIRTUAL_ENV']); print(os.environ['PYTHONNOUSERSITE'])",
            ],
            recorder=recorder,
        )

    assert result.exit_code == 0
    assert "/tmp/runtime-env" in result.stdout_preview
    assert "1" in result.stdout_preview


def test_stage12_5_local_workspace_adapter_allows_shared_cache_lease_root(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    shared_workspace = tmp_path / "shared-cache" / "leases" / "snap" / "lease"
    shared_workspace.mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-shared",
        run_dir=run_dir,
        allowed_workspace_roots=[tmp_path / "shared-cache" / "leases"],
    )
    with RunRecorder("stage12-5-shared", run_dir, task_id="task") as recorder:
        result = adapter.run_command(shared_workspace, [sys.executable, "-c", "print('ok')"], recorder=recorder)

    assert result.exit_code == 0
    assert "ok" in result.stdout_preview


def test_stage12_5_local_workspace_adapter_blocks_shared_environment_install_commands(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-block",
        run_dir=run_dir,
        block_shared_environment_writes=True,
    )
    with RunRecorder("stage12-5-block", run_dir, task_id="task") as recorder:
        with pytest.raises(WorkspaceError, match="shared_environment_write_command"):
            adapter.run_command(workspace, "python -m pip install requests", recorder=recorder)


@pytest.mark.parametrize(
    "command",
    [
        "env -S 'bash -lc echo ok'",
        "time bash -lc 'echo ok'",
        "command bash -lc 'echo ok'",
    ],
)
def test_stage12_5_local_workspace_adapter_blocks_shell_wrappers(
    tmp_path: Path,
    command: str,
) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-shell-wrapper",
        run_dir=run_dir,
        block_shared_environment_writes=True,
    )

    with RunRecorder("stage12-5-shell-wrapper", run_dir, task_id="task") as recorder:
        with pytest.raises(WorkspaceError, match="shared_environment_shell_wrapper"):
            adapter.run_command(workspace, command, recorder=recorder)


def test_stage12_5_local_workspace_adapter_blocks_allow_shell_under_shared_environment(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-allow-shell",
        run_dir=run_dir,
        block_shared_environment_writes=True,
    )

    with RunRecorder("stage12-5-allow-shell", run_dir, task_id="task") as recorder:
        with pytest.raises(WorkspaceError, match="shared_environment_shell_wrapper"):
            adapter.run_command(
                workspace,
                "cmd=ya; cmd=${cmd}rn; echo $cmd",
                recorder=recorder,
                allow_shell=True,
            )


def test_stage12_5_local_workspace_adapter_blocks_model_access_to_environment_overlay(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    (workspace / ".repo_harness_env_overlay" / "bin").mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-overlay-block",
        run_dir=run_dir,
        block_shared_environment_writes=True,
    )

    with RunRecorder("stage12-5-overlay-block", run_dir, task_id="task") as recorder:
        with pytest.raises(WorkspaceError, match="model_hidden_runtime_path"):
            adapter.run_command(
                workspace,
                "readlink .repo_harness_env_overlay/bin/python",
                recorder=recorder,
            )


def test_stage12_5_local_workspace_adapter_blocks_model_access_to_runtime_directory(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    (workspace / ".repo_harness_runtime" / "home").mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-runtime-block",
        run_dir=run_dir,
        block_shared_environment_writes=True,
    )

    with RunRecorder("stage12-5-runtime-block", run_dir, task_id="task") as recorder:
        with pytest.raises(WorkspaceError, match="model_hidden_runtime_path"):
            adapter.run_command(
                workspace,
                "ls .repo_harness_runtime/home",
                recorder=recorder,
            )


def test_stage12_5_shared_environment_output_redacts_parent_overlay_listing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    overlay_bin = run_dir / "workspaces" / ".repo_harness_env_overlay" / "workspace" / "bin"
    overlay_bin.mkdir(parents=True)
    (overlay_bin / "python").write_text(
        f"#!/bin/sh\nexec {sys.executable} \"$@\"\n",
        encoding="utf-8",
    )
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-overlay-output-redact",
        run_dir=run_dir,
        block_shared_environment_writes=True,
        command_env_provider=lambda path: {
            "PATH": f"{overlay_bin}:/usr/bin:/bin",
            "VIRTUAL_ENV": "rh://environment/rhenv-test",
            "PYTHONPATH": str(path),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )

    with RunRecorder("stage12-5-overlay-output-redact", run_dir, task_id="task") as recorder:
        result = adapter.run_command(workspace, ["ls", "-la", ".."], recorder=recorder)

    assert result.exit_code == 0
    assert ".repo_harness_env_overlay" not in result.stdout_preview
    assert ".repo_harness_runtime" not in result.stdout_preview
    assert str(run_dir) not in result.stdout_preview
    assert "[repo_harness_hidden_runtime_path]" in result.stdout_preview
    assert result.stdout_ref is not None
    stdout_payload = (run_dir / result.stdout_ref.relative_path).read_text(encoding="utf-8")
    assert ".repo_harness_env_overlay" not in stdout_payload
    assert ".repo_harness_runtime" not in stdout_payload


def test_stage12_5_shared_environment_output_redacts_overlay_launcher_contents(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    overlay_bin = run_dir / "workspaces" / ".repo_harness_env_overlay" / "workspace" / "bin"
    overlay_bin.mkdir(parents=True)
    (overlay_bin / "python").write_text(
        f"#!/bin/sh\nexec {sys.executable} \"$@\"\n",
        encoding="utf-8",
    )
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-overlay-launcher-redact",
        run_dir=run_dir,
        block_shared_environment_writes=True,
        command_env_provider=lambda path: {
            "PATH": f"{overlay_bin}:/usr/bin:/bin",
            "VIRTUAL_ENV": "rh://environment/rhenv-test",
            "PYTHONPATH": str(path),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )

    with RunRecorder("stage12-5-overlay-launcher-redact", run_dir, task_id="task") as recorder:
        result = adapter.run_command(
            workspace,
            ["find", "..", "-name", "python", "-type", "f", "-exec", "cat", "{}", ";"],
            recorder=recorder,
        )

    assert result.exit_code == 0
    assert ".repo_harness_env_overlay" not in result.stdout_preview
    assert str(sys.executable) not in result.stdout_preview
    assert str(run_dir) not in result.stdout_preview
    assert "[repo_harness_hidden_python_executable]" in result.stdout_preview
    assert result.output_artifact_ref is not None
    output_payload = (run_dir / result.output_artifact_ref.relative_path).read_text(encoding="utf-8")
    assert ".repo_harness_env_overlay" not in output_payload
    assert str(sys.executable) not in output_payload


@pytest.mark.parametrize(
    "command",
    [
        "env",
        "printenv PATH",
        "which python",
        "python -m site",
        "python -m sysconfig",
        "python -m pip --version",
        "python -msite",
        [
            sys.executable,
            "-c",
            "import os, sys; print(os.environ.get('PATH')); print(sys.executable)",
        ],
        [
            sys.executable,
            "-c",
            "from sys import executable as exe; print(exe)",
        ],
        [
            sys.executable,
            "-c",
            "import sys; print(getattr(sys, 'executable'))",
        ],
        [
            sys.executable,
            "-c",
            "print(__import__('sys').executable)",
        ],
        [
            sys.executable,
            "-c",
            "import importlib; print(importlib.import_module('sys').executable)",
        ],
        [
            sys.executable,
            "-c",
            "from importlib import import_module; print(import_module('sys').executable)",
        ],
        [
            sys.executable,
            "-c",
            "import subprocess; print(subprocess.check_output(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import subprocess as sp; sp.run(['which', 'python'])",
        ],
        [
            sys.executable,
            "-c",
            "from subprocess import check_output; print(check_output(['which', 'python'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import os; os.system('env')",
        ],
        [
            sys.executable,
            "-c",
            "from os import popen; print(popen('which python').read())",
        ],
        [
            sys.executable,
            "-c",
            "import runpy; runpy.run_module('os')",
        ],
        [
            sys.executable,
            "-c",
            "import subprocess; sp = subprocess; print(sp.check_output(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import os; o = os; o.system('env')",
        ],
        [
            sys.executable,
            "-c",
            "import importlib; sp = importlib.import_module('subprocess'); print(sp.check_output(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "sp = __import__('subprocess'); print(sp.check_output(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import os; print(os.__dict__['environ'])",
        ],
        [
            sys.executable,
            "-c",
            "import os; print(vars(os)['environ'])",
        ],
        [
            sys.executable,
            "-c",
            "import os; print(getattr(os, '__dict__')['environ'])",
        ],
        [
            sys.executable,
            "-c",
            "import sys; print(getattr(sys, 'exec' + 'utable'))",
        ],
        [
            sys.executable,
            "-c",
            "import subprocess; f = getattr(subprocess, 'check_' + 'output'); print(f(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import subprocess; f = subprocess.__dict__['check_' + 'output']; print(f(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import os; print(vars(os).get('environ'))",
        ],
        [
            sys.executable,
            "-c",
            "import os; print(os.__dict__.get('environ'))",
        ],
        [
            sys.executable,
            "-c",
            "import os; print(os.__getattribute__('environ'))",
        ],
        [
            sys.executable,
            "-c",
            "import sys; print(sys.__getattribute__('exec' + 'utable'))",
        ],
        [
            sys.executable,
            "-c",
            "import subprocess; f = subprocess.__getattribute__('check_' + 'output'); print(f(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "import builtins; sp = builtins.__import__('subprocess'); print(sp.check_output(['env'], text=True))",
        ],
        [
            sys.executable,
            "-c",
            "print(__import__('sysconfig').get_paths())",
        ],
        [
            sys.executable,
            "-c",
            "import sysconfig; print(sysconfig.get_paths())",
        ],
        [
            sys.executable,
            "-c",
            "import os; print('ok')",
        ],
        [
            sys.executable,
            "-c",
            "import sys; print(sys.version)",
        ],
        [
            sys.executable,
            "-c",
            "import pip; print(pip)",
        ],
        [
            sys.executable,
            "-c",
            "from pathlib import Path; print(Path.home())",
        ],
        [
            sys.executable,
            "-c",
            "import posix; print(posix.environ)",
        ],
        [
            sys.executable,
            "probe_env.py",
        ],
        [
            sys.executable,
            "-u",
            "probe_env.py",
        ],
        [
            sys.executable,
            "-",
        ],
        [
            sys.executable,
            "-c",
            "m='sys'; print(__import__(m).executable)",
        ],
        [
            sys.executable,
            "-c",
            "m='sysconfig'; print(__import__(m).get_paths())",
        ],
        [
            sys.executable,
            "-c",
            "m='os'; print(__import__(m).environ.get('PATH'))",
        ],
        [
            sys.executable,
            "-c",
            "m='os'; p=__import__(m).environ['PATH'].split(':')[0]+'/python'; print(open(p).read())",
        ],
        [
            sys.executable,
            "-c",
            "f=getattr(__builtins__,'__im'+'port__'); print(f('sys').executable)",
        ],
        [
            sys.executable,
            "-c",
            "f=getattr(__builtins__,'__im'+'port__'); print(f('sysconfig').get_paths())",
        ],
        [
            sys.executable,
            "-c",
            "f=getattr(__builtins__,'__im'+'port__'); print(f('os').environ.get('PATH'))",
        ],
        [
            sys.executable,
            "-c",
            "f=getattr(__builtins__,'__im'+'port__'); p=f('os').environ['PATH'].split(':')[0]+'/python'; print(open(p).read())",
        ],
        [
            sys.executable,
            "-c",
            "b=globals()['__builtins__']; f=getattr(b,'__im'+'port__'); print(f('sys').executable)",
        ],
        [
            sys.executable,
            "-c",
            "b=locals()['__builtins__']; f=getattr(b,'__im'+'port__'); print(f('os').environ.get('PATH'))",
        ],
        [
            sys.executable,
            "-c",
            "print(eval('__im'+'port__(\"sys\").executable'))",
        ],
        [
            sys.executable,
            "-c",
            "exec('m=__im'+'port__(\"sysconfig\"); print(m.get_paths())')",
        ],
        [
            sys.executable,
            "-c",
            "c=compile('print(__im'+'port__(\"sys\").executable)','<x>','exec'); exec(c)",
        ],
        [
            sys.executable,
            "-c",
            "b=globals()['__builtins__']; f=getattr(b,'__im'+'port__'); p=f('os').environ['PATH'].split(':')[0]+'/python'; print(open(p).read())",
        ],
    ],
)
def test_stage12_5_local_workspace_adapter_blocks_runtime_environment_probe_commands(
    tmp_path: Path,
    command: str | list[str],
) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    overlay_bin = run_dir / "workspaces" / ".repo_harness_env_overlay" / "workspace" / "bin"
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-env-probe-block",
        run_dir=run_dir,
        block_shared_environment_writes=True,
        command_env_provider=lambda path: {
            "PATH": f"{overlay_bin}:/usr/bin",
            "VIRTUAL_ENV": "rh://environment/rhenv-test",
            "PYTHONPATH": str(path),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )

    with RunRecorder("stage12-5-env-probe-block", run_dir, task_id="task") as recorder:
        with pytest.raises(WorkspaceError, match="runtime_environment_probe_command"):
            adapter.run_command(workspace, command, recorder=recorder)


def test_stage12_5_local_workspace_adapter_allows_non_probe_python_command(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    adapter = LocalWorkspaceAdapter(
        run_id="stage12-5-env-probe-allow",
        run_dir=run_dir,
        block_shared_environment_writes=True,
    )

    with RunRecorder("stage12-5-env-probe-allow", run_dir, task_id="task") as recorder:
        result = adapter.run_command(workspace, [sys.executable, "-c", "print('ok')"], recorder=recorder)

    assert result.exit_code == 0
    assert "ok" in result.stdout_preview
    assert result.output_artifact_ref is not None
    output_payload = (run_dir / result.output_artifact_ref.relative_path).read_text(encoding="utf-8")
    assert str(sys.executable) not in output_payload
    assert "[repo_harness_hidden_python_executable]" in output_payload


def test_stage12_5_workspace_overlay_is_excluded_from_final_patch(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    adapter = LocalWorkspaceAdapter(run_id="stage12-5-overlay", run_dir=run_dir)

    with RunRecorder("stage12-5-overlay", run_dir, task_id="task") as recorder:
        snapshot = adapter.create_agent_start_snapshot(workspace, None, recorder)
        overlay = workspace / ".repo_harness_env_overlay"
        (overlay / "bin").mkdir(parents=True)
        (overlay / "bin" / "python").symlink_to(sys.executable)
        (overlay / "pyvenv.cfg").write_text(f"home = {sys.executable}\n", encoding="utf-8")
        (workspace / "tracked.py").write_text("VALUE = 2\n", encoding="utf-8")
        from repo_harness.workspace import DependencyState, RunWorkspace

        run_workspace = RunWorkspace(
            run_id="stage12-5-overlay",
            workspace_path=str(workspace),
            artifact_dir=str(run_dir / "artifacts"),
            dependency_state=DependencyState(),
            agent_start_snapshot=snapshot,
            agent_diff_base=snapshot,
        )
        patch = adapter.capture_final_patch(run_workspace, recorder=recorder)

    assert ".repo_harness_env_overlay" not in patch.patch_text
    assert "tracked.py" in patch.patch_text
