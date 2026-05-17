from __future__ import annotations

import subprocess
import os
import sys
from pathlib import Path

import pytest

from repo_harness.errors import WorkspaceError
from repo_harness.workspace import (
    DependencyEnvironmentLockfile,
    DependencyEnvironmentManager,
    DependencyEnvironmentSpec,
    DependencySetupCommandGroups,
    build_command_environment,
    build_dependency_environment_key,
    classify_shared_environment_write_command,
    dependency_environment_resource_fields,
)


def _spec(**updates):
    payload = {
        "python_version": "3.11",
        "platform": "linux",
        "cpu_arch": "x86_64",
        "os_release": "ubuntu-22.04",
        "libc": "glibc-2.35",
        "execution_mode": "local_process",
        "package_manager_versions": {"pip": "24.0", "uv": "0.5.0"},
        "dependency_lockfiles": [
            {
                "relative_path": "requirements.txt",
                "sha256": "a" * 64,
                "required": True,
            }
        ],
        "setup_commands": {
            "third_party_install": ["python -m pip install -r requirements.txt"],
            "source_bound": [],
            "workspace_write": [],
            "unsupported": [],
        },
        "pythonpath_entries": [".", "src"],
        "environment_allowlist_digest": "env-allowlist-hash",
        "package_index_digest": "public-index-hash",
        "source_tree_hash": "b" * 64,
        "base_commit": "abc123",
    }
    payload.update(updates)
    return DependencyEnvironmentSpec.model_validate(payload)


def test_stage12_5_dependency_environment_key_is_layered_and_stable() -> None:
    first = build_dependency_environment_key(_spec())
    second = build_dependency_environment_key(_spec())
    changed_source = build_dependency_environment_key(_spec(source_tree_hash="c" * 64))
    changed_lock = build_dependency_environment_key(
        _spec(dependency_lockfiles=[DependencyEnvironmentLockfile(relative_path="requirements.txt", sha256="d" * 64)])
    )

    assert first == second
    assert first.base_environment_key == changed_source.base_environment_key
    assert first.source_snapshot_key != changed_source.source_snapshot_key
    assert first.base_environment_key != changed_lock.base_environment_key
    assert first.environment_key.startswith("rhenv-")


def test_stage12_5_dependency_environment_manager_publishes_once_and_reports_hit(tmp_path: Path) -> None:
    manager = DependencyEnvironmentManager(tmp_path / "dep-cache", creator_id="stage12-5-test")
    spec = _spec()

    first = manager.prepare_environment(spec)
    second = manager.prepare_environment(spec)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert first.dependency_cache_key == second.dependency_cache_key
    assert second.facts.environment_ref == f"rh://environment/{second.dependency_cache_key}"
    assert (second.environment_path / "environment_facts.json").exists()
    assert second.environment_path.stat().st_mode & 0o222 == 0
    assert (second.environment_path / "environment_facts.json").stat().st_mode & 0o222 == 0
    report = second.report()
    assert report.dependency_cache_hit is True
    assert report.dependency_cache_key == second.dependency_cache_key
    fields = dependency_environment_resource_fields(second)
    assert fields["repo_harness_environment_ref"] == second.environment_ref
    assert "/Users/" not in str(fields)


def test_stage12_5_read_only_hit_policy_fails_on_cache_miss(tmp_path: Path) -> None:
    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")

    with pytest.raises(WorkspaceError, match="read_only_hit cache miss"):
        manager.prepare_environment(_spec(cache_policy="read_only_hit"))


def test_stage12_5_command_environment_uses_spec_pythonpath_entries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("REPO_HARNESS_REVIEW_SECRET_TOKEN", "shhh")
    monkeypatch.setenv("HOME", "/Users/roger")
    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")
    handle = manager.prepare_environment(_spec())
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)

    env = build_command_environment(handle, workspace_path=workspace, base_env={"PATH": "/usr/bin"})

    assert env["VIRTUAL_ENV"] == handle.environment_ref
    assert str(handle.environment_path) not in env["VIRTUAL_ENV"]
    assert str(handle.environment_path) not in env["PATH"]
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["REPO_HARNESS_ENVIRONMENT_REF"] == handle.environment_ref
    assert env["REPO_HARNESS_ENVIRONMENT_MODE"] == "workspace_overlay"
    assert "REPO_HARNESS_REVIEW_SECRET_TOKEN" not in env
    assert env["HOME"] != "/Users/roger"
    assert ".repo_harness_runtime" in env["HOME"]
    assert ".repo_harness_runtime" in env["XDG_CACHE_HOME"]
    assert ".repo_harness_runtime" in env["PIP_CACHE_DIR"]
    assert ".repo_harness_runtime" in env["UV_CACHE_DIR"]
    assert ".repo_harness_runtime" in env["TMPDIR"]
    assert env["TEMP"] == env["TMPDIR"]
    assert env["TMP"] == env["TMPDIR"]
    assert ".repo_harness_runtime" in env["PYTHONPYCACHEPREFIX"]
    assert str(handle.environment_path) not in env["HOME"]
    assert str(handle.environment_path) not in env["XDG_CACHE_HOME"]
    assert str(workspace.resolve()) in env["PYTHONPATH"]
    assert str((workspace / "src").resolve()) in env["PYTHONPATH"]


@pytest.mark.parametrize(
    "command",
    [
        "pip install requests",
        "pip3 install requests",
        "pip3.11 uninstall requests",
        "python -m pip install -r requirements.txt",
        "python -mpip install requests",
        "bash -lc 'pip install requests'",
        "bash -lc 'echo ok && pip install requests'",
        'bash -lc "$(which pip) install requests"',
        "bash -lc 'eval \"pip install requests\"'",
        "bash -lc 'pip --no-input install requests'",
        "sh -c 'python -m pip install requests'",
        "sh -c 'true; python -m pip install requests'",
        "bash -lc 'python -m pip --disable-pip-version-check install requests'",
        "env PIP_DISABLE_PIP_VERSION_CHECK=1 pip install requests",
        "env -S 'pip install requests'",
        "env FOO=1 bash -lc 'echo ok && pip install requests'",
        ["/usr/bin/env", "pip", "install", "requests"],
        "time -p pip install requests",
        "uv --directory . sync",
        ["uv", "pip", "install", "-r", "requirements.txt"],
        "uv sync",
        "npm ci",
        "npm i lodash",
        "bash -lc 'npm i lodash'",
        "pnpm add lodash",
        "pnpm i",
        "yarn",
        "yarn install",
        "python -c \"__import__('subprocess').check_call(['python','-m','pip','install','requests'])\"",
        "python -c \"__import__('pip._internal')._internal.main(['install','requests'])\"",
        "bash -lc 'printf \"pip install requests\\n\" | sh'",
        "bash -lc '$(echo pip) install requests'",
        "bash -lc 'python -m pip${IFS}install requests'",
        "python -c \"import sys,runpy; sys.argv=['pip','install','requests']; runpy.run_module('pip', run_name='__main__')\"",
        "bash -lc 'cmd=pip; $cmd install requests'",
        "bash -lc 'sub=install; pip $sub requests'",
        "bash -lc 'mod=pip; python -m $mod install requests'",
        "bash -lc 'sub=install; python -m pip $sub requests'",
        "bash -lc 'cmd=npm; $cmd i lodash'",
        "bash -lc 'sub=i; npm $sub lodash'",
        "bash -lc 'cmd=yarn; $cmd'",
        "bash -lc 'cmd=yarn; ${cmd}'",
        "bash -lc 'cmd=ya; cmd=${cmd}rn; $cmd'",
        "bash -lc '$(echo yarn)'",
        "bash -lc '$(printf yarn)'",
        "bash -lc 'yarn${IFS}'",
        "bash -lc 'npm $(echo i) lodash'",
        "bash -lc 'pnpm $(echo i) lodash'",
        "bash -lc 'cmd=npm; $cmd $(echo i) lodash'",
        "bash -lc 'cmd=pnpm; $cmd $(echo i) lodash'",
        "python -c \"import subprocess; subprocess.check_call(['npm','i','lodash'])\"",
        "python -c \"import subprocess; subprocess.check_call(['pnpm','i'])\"",
        "python -c \"import subprocess; subprocess.check_call(['yarn'])\"",
        "python -c \"import os; os.system('npm i lodash')\"",
        "python -c \"import os; os.system('pnpm i')\"",
        "python -c \"import os; os.system('yarn')\"",
    ],
)
def test_stage12_5_shared_environment_write_commands_are_rejected(command: str | list[str]) -> None:
    decision = classify_shared_environment_write_command(command)

    assert decision.allowed is False
    assert decision.reason and decision.reason.startswith("shared_environment_write_command")


def test_stage12_5_dependency_environment_rejects_absolute_paths_and_docker_without_digest() -> None:
    with pytest.raises(ValueError, match="pythonpath_entries"):
        _spec(pythonpath_entries=["/Users/roger/private"])

    with pytest.raises(ValueError, match="docker_image_digest"):
        _spec(execution_mode="docker", docker_image_digest=None)

    with pytest.raises(ValueError, match="relative_path"):
        DependencyEnvironmentLockfile(relative_path="../requirements.txt", sha256="a" * 64)

    with pytest.raises(ValueError, match="third_party_install"):
        _spec(
            setup_commands=DependencySetupCommandGroups(
                third_party_install=["python -m pip install /tmp/local-wheel.whl"],
            )
        )


def test_stage12_5_command_environment_rejects_pythonpath_escape(tmp_path: Path) -> None:
    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")
    handle = manager.prepare_environment(_spec(pythonpath_entries=["."]))
    escaped = handle.facts.model_copy(update={"pythonpath_entries": ["../escape"]})
    bad_handle = type(handle)(
        facts=escaped,
        environment_path=handle.environment_path,
        cache_hit=handle.cache_hit,
        dependency_restore_seconds=handle.dependency_restore_seconds,
    )

    with pytest.raises((WorkspaceError, ValueError)):
        build_command_environment(bad_handle, workspace_path=tmp_path / "workspace")


def test_stage12_5_command_environment_workspace_overlay_is_not_model_enumerable(
    tmp_path: Path,
) -> None:
    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")
    handle = manager.prepare_environment(_spec())
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    env = build_command_environment(handle, workspace_path=workspace, base_env={"PATH": "/usr/bin"})
    output = subprocess.check_output(
        [
            "python",
            "-c",
            "from pathlib import Path; print([str(p) for p in Path('.').rglob('*')])",
        ],
        cwd=workspace,
        env=env,
        text=True,
        stderr=subprocess.STDOUT,
    )

    assert ".repo_harness_env_overlay" not in output
    assert not (handle.environment_path / "probe.txt").exists()


def test_stage12_5_command_environment_connects_overlay_to_shared_environment_bin(tmp_path: Path) -> None:
    def initializer(path: Path, _spec: DependencyEnvironmentSpec) -> None:
        bin_dir = path / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        python = bin_dir / "python"
        python.write_text("#!/bin/sh\nprintf shared-python\n", encoding="utf-8")
        python.chmod(0o755)

    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")
    handle = manager.prepare_environment(_spec(), initializer=initializer)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    env = build_command_environment(handle, workspace_path=workspace, base_env={"PATH": "/usr/bin:/bin"})
    output = subprocess.check_output(["python"], env=env, text=True)

    assert output == "shared-python"
    overlay_python = Path(env["PATH"].split(os.pathsep)[0]) / "python"
    assert overlay_python.exists()
    assert not overlay_python.is_symlink()
    assert overlay_python.stat().st_ino != (handle.environment_path / "bin" / "python").stat().st_ino
    assert str(handle.environment_path) not in env["PATH"]
    assert "_REPO_HARNESS_SHARED_ENV_BIN" not in env


def test_stage12_5_default_overlay_python_entry_is_executable_without_shared_path_in_path(
    tmp_path: Path,
) -> None:
    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")
    handle = manager.prepare_environment(_spec(python_version=f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    env = build_command_environment(handle, workspace_path=workspace, base_env={"PATH": "/usr/bin:/bin"})
    output = subprocess.check_output(["python", "-c", "import sys; print(sys.version_info[0])"], env=env, text=True)
    overlay_python = Path(env["PATH"].split(os.pathsep)[0]) / "python"

    assert output.strip() == str(__import__("sys").version_info.major)
    assert overlay_python.exists()
    assert not overlay_python.is_symlink()
    assert overlay_python.stat().st_ino != (handle.environment_path / "bin" / "python").stat().st_ino
    assert str(handle.environment_path) not in env["PATH"]
    assert str(handle.environment_path) not in env["VIRTUAL_ENV"]
    assert env["VIRTUAL_ENV"].startswith("rh://environment/")
    assert "_REPO_HARNESS_SHARED_ENV_BIN" not in env


def test_stage12_5_overlay_python_preserves_shared_venv_site_packages(tmp_path: Path) -> None:
    def initializer(path: Path, _spec: DependencyEnvironmentSpec) -> None:
        subprocess.run([sys.executable, "-m", "venv", str(path)], check=True)
        site_packages = subprocess.check_output(
            [
                str(path / "bin" / "python"),
                "-c",
                "import site; print(site.getsitepackages()[0])",
            ],
            text=True,
        ).strip()
        Path(site_packages, "shared_dep_marker.py").write_text(
            'VALUE = "shared-venv-site-packages-ok"\n',
            encoding="utf-8",
        )

    manager = DependencyEnvironmentManager(tmp_path / "dep-cache")
    handle = manager.prepare_environment(_spec(), initializer=initializer)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    env = build_command_environment(handle, workspace_path=workspace, base_env={"PATH": "/usr/bin:/bin"})
    output = subprocess.check_output(
        ["python", "-c", "import shared_dep_marker; print(shared_dep_marker.VALUE)"],
        env=env,
        text=True,
    )
    overlay_python = Path(env["PATH"].split(os.pathsep)[0]) / "python"

    assert output.strip() == "shared-venv-site-packages-ok"
    assert overlay_python.exists()
    assert not overlay_python.is_symlink()
    assert overlay_python.stat().st_ino != (handle.environment_path / "bin" / "python").stat().st_ino
    assert str(handle.environment_path) not in env["PATH"]
