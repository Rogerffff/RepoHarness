from pathlib import Path

import pytest

from repo_harness.errors import WorkspaceError
from repo_harness.workspace import LocalWorkspaceAdapter


def test_workspace_path_resolution_rejects_outside_and_sensitive_paths(tmp_path: Path):
    adapter = LocalWorkspaceAdapter(run_id="run_paths", run_dir=tmp_path / "run")
    workspace = adapter.workspaces_dir / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "safe.py").write_text("print('safe')\n", encoding="utf-8")

    assert adapter.resolve_workspace_path(workspace, "safe.py", must_exist=True) == workspace / "safe.py"

    with pytest.raises(WorkspaceError, match="workspace 边界"):
        adapter.resolve_workspace_path(workspace, "../outside.txt")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, ".env")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, ".git/config")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, "secrets/id_rsa")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, "certs/prod.pem")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, ".netrc")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, ".aws/credentials")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, ".config/gh/hosts.yml")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, "pip.conf")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, "credentials.json")
    with pytest.raises(WorkspaceError, match="敏感路径"):
        adapter.resolve_workspace_path(workspace, "token")


def test_workspace_path_resolution_rejects_symlink_to_outside(tmp_path: Path):
    adapter = LocalWorkspaceAdapter(run_id="run_paths", run_dir=tmp_path / "run")
    workspace = adapter.workspaces_dir / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir(parents=True)
    outside.write_text("outside", encoding="utf-8")
    (workspace / "link.txt").symlink_to(outside)

    with pytest.raises(WorkspaceError, match="workspace 边界|符号链接"):
        adapter.resolve_workspace_path(workspace, "link.txt", must_exist=True)


def test_write_text_creates_only_inside_workspace(tmp_path: Path):
    adapter = LocalWorkspaceAdapter(run_id="run_paths", run_dir=tmp_path / "run")
    workspace = adapter.workspaces_dir / "workspace"
    workspace.mkdir(parents=True)

    adapter.write_text(workspace, "pkg/module.py", "VALUE = 1\n")

    assert (workspace / "pkg" / "module.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_workspace_operations_reject_workspace_outside_run_dir(tmp_path: Path):
    adapter = LocalWorkspaceAdapter(run_id="run_paths", run_dir=tmp_path / "run")
    outside = tmp_path / "outside_workspace"
    outside.mkdir()

    with pytest.raises(WorkspaceError, match="workspaces"):
        adapter.resolve_workspace_path(outside, "file.txt")
