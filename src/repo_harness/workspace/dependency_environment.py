"""Runtime-only dependency environment cache helpers."""

from __future__ import annotations

import ast
import os
import platform as platform_module
import re
import shlex
import shutil
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.errors import WorkspaceError
from repo_harness.schema_base import StrictBaseModel, stable_hash

DEPENDENCY_ENVIRONMENT_POLICY_VERSION = "repo_harness_dependency_environment_stage12_5_v0"
DEPENDENCY_ENVIRONMENT_FACTS_FILENAME = "environment_facts.json"

ExecutionMode = Literal["local_process", "docker", "remote_worker"]
CachePolicy = Literal["read_only_hit", "create_if_missing", "disable_cache"]
NodeDependencyPolicy = Literal["unsupported_diagnostics", "pnpm_store_overlay", "node_modules_overlay"]

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ABSOLUTE_PATH_MARKERS = (
    "/Users/",
    "/home/",
    "/private/",
    "/var/folders/",
    "/tmp/",
    "C:\\",
    "D:\\",
)
_EMBEDDED_POSIX_ABSOLUTE_PATH_RE = re.compile(r"(^|[\s=:,'\"])/(?!/)[^\s'\"]*")
_SECRET_KEY_MARKERS = ("token", "secret", "password", "credential", "private_key")
_INSTALL_COMMANDS = {
    ("pip", "install"),
    ("pip", "uninstall"),
    ("uv", "add"),
    ("uv", "sync"),
    ("uv", "pip", "install"),
    ("uv", "pip", "uninstall"),
    ("npm", "install"),
    ("npm", "add"),
    ("npm", "ci"),
    ("npm", "i"),
    ("pnpm", "install"),
    ("pnpm", "add"),
    ("pnpm", "i"),
    ("yarn", "install"),
    ("yarn", "add"),
    ("yarn",),
}
_SHELL_EXECUTABLES = {"bash", "dash", "sh", "zsh"}
_COMMAND_FORWARDERS = {"command", "time"}
_RUNTIME_ENVIRONMENT_PROBE_COMMANDS = {"env", "printenv", "which", "whereis"}
_IMPORTLIB_IMPORT_MODULE_ALIAS = "importlib.import_module"
_PYTHON_RUNTIME_PROBE_MODULES = {
    "builtins",
    "importlib",
    "os",
    "runpy",
    "shutil",
    "site",
    "subprocess",
    "sys",
    "sysconfig",
}
_PYTHON_RUNTIME_PROBE_MODULE_EXECUTIONS = {
    "ensurepip",
    "pip",
    "pydoc",
    "site",
    "sysconfig",
    "venv",
    "virtualenv",
}
_PYTHON_RUNTIME_PROBE_BUILTIN_CALLS = {
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
_PYTHON_RUNTIME_PROBE_ATTRS = {
    "builtins": {"__import__"},
    "importlib": {"import_module"},
    "os": {
        "environ",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "getenv",
        "get_exec_path",
        "popen",
        "posix_spawn",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "system",
    },
    "runpy": {"run_module", "run_path"},
    "sys": {
        "_base_executable",
        "base_exec_prefix",
        "base_prefix",
        "exec_prefix",
        "executable",
        "path",
        "prefix",
    },
    "sysconfig": {"get_config_var", "get_config_vars", "get_path", "get_paths", "get_platform"},
    "site": {"getsitepackages", "getusersitepackages"},
    "shutil": {"which"},
    "subprocess": {
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
        "run",
    },
}
_PYTHON_RUNTIME_PROBE_FALLBACK_MARKERS = (
    "os.environ",
    "os.getenv",
    "os.get_exec_path",
    "sys.executable",
    "sys.prefix",
    "sys.base_prefix",
    "sys.path",
    "site.getsitepackages",
    "site.getusersitepackages",
    "shutil.which",
    "from sys import executable",
    "__import__",
    "__import__('sys')",
    '__import__("sys")',
)


class DependencyEnvironmentLockfile(StrictBaseModel):
    schema_version: str = "repo_harness_dependency_lockfile_stage12_5_v0"
    relative_path: str
    sha256: str
    required: bool = True

    @model_validator(mode="after")
    def validate_lockfile(self) -> "DependencyEnvironmentLockfile":
        _validate_safe_relative_path(self.relative_path, field_name="relative_path")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", self.sha256):
            raise ValueError("lockfile sha256 must be a 64 character hex digest")
        return self


class DependencySetupCommandGroups(StrictBaseModel):
    schema_version: str = "repo_harness_dependency_setup_commands_stage12_5_v0"
    third_party_install: list[str] = Field(default_factory=list)
    source_bound: list[str] = Field(default_factory=list)
    workspace_write: list[str] = Field(default_factory=list)
    unsupported: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_commands(self) -> "DependencySetupCommandGroups":
        for group_name in ["third_party_install", "source_bound", "workspace_write", "unsupported"]:
            for index, command in enumerate(getattr(self, group_name)):
                _validate_no_absolute_local_path(command, field_name=f"{group_name}[{index}]")
                _validate_no_secret_text(command, field_name=f"{group_name}[{index}]")
        return self


class DependencyEnvironmentSpec(StrictBaseModel):
    """Runtime-only source of dependency environment facts.

    The spec is intentionally separate from episode request schema. It may
    contain local runtime decisions, but its persisted facts must stay free of
    absolute paths and secrets.
    """

    schema_version: str = "repo_harness_dependency_environment_spec_stage12_5_v0"
    python_version: str = Field(default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}")
    platform: str = Field(default_factory=lambda: sys.platform)
    cpu_arch: str = Field(default_factory=platform_module.machine)
    os_release: str = Field(default_factory=platform_module.platform)
    libc: str | None = Field(default_factory=lambda: _libc_identifier())
    cuda_abi: str | None = None
    torch_abi: str | None = None
    compiler_abi: str | None = None
    execution_mode: ExecutionMode = "local_process"
    docker_image_digest: str | None = None
    package_manager_versions: dict[str, str] = Field(default_factory=dict)
    dependency_lockfiles: list[DependencyEnvironmentLockfile] = Field(default_factory=list)
    setup_commands: DependencySetupCommandGroups = Field(default_factory=DependencySetupCommandGroups)
    pythonpath_entries: list[str] = Field(default_factory=lambda: ["."])
    environment_allowlist_digest: str = "none"
    package_index_digest: str = "none"
    cache_policy: CachePolicy = "create_if_missing"
    node_dependency_policy: NodeDependencyPolicy = "unsupported_diagnostics"
    source_tree_hash: str | None = None
    source_archive_sha256: str | None = None
    base_commit: str | None = None
    schema_policy_version: str = DEPENDENCY_ENVIRONMENT_POLICY_VERSION
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_spec(self) -> "DependencyEnvironmentSpec":
        if self.execution_mode == "docker" and not self.docker_image_digest:
            raise ValueError("docker execution mode requires docker_image_digest")
        for field_name in [
            "python_version",
            "platform",
            "cpu_arch",
            "os_release",
            "libc",
            "cuda_abi",
            "torch_abi",
            "compiler_abi",
            "docker_image_digest",
            "environment_allowlist_digest",
            "package_index_digest",
            "source_tree_hash",
            "source_archive_sha256",
            "base_commit",
            "schema_policy_version",
        ]:
            value = getattr(self, field_name)
            if value is not None:
                _validate_no_absolute_local_path(str(value), field_name=field_name)
                _validate_no_secret_text(str(value), field_name=field_name)
        for name, version in self.package_manager_versions.items():
            _validate_safe_name(name, field_name="package_manager_versions")
            _validate_no_absolute_local_path(version, field_name=f"package_manager_versions.{name}")
            _validate_no_secret_text(version, field_name=f"package_manager_versions.{name}")
        for entry in self.pythonpath_entries:
            _validate_safe_relative_path(entry, field_name="pythonpath_entries")
        for diagnostic in self.diagnostics:
            _validate_no_absolute_local_path(diagnostic, field_name="diagnostics")
            _validate_no_secret_text(diagnostic, field_name="diagnostics")
        if self.node_dependency_policy == "unsupported_diagnostics":
            lock_names = {PurePosixPath(lock.relative_path).name for lock in self.dependency_lockfiles}
            node_locks = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
            if lock_names & node_locks and not any("node_dependency_unsupported" in item for item in self.diagnostics):
                object.__setattr__(
                    self,
                    "diagnostics",
                    [*self.diagnostics, "node_dependency_unsupported_diagnostics_only"],
                )
        return self


class DependencyEnvironmentKey(StrictBaseModel):
    schema_version: str = "repo_harness_dependency_environment_key_stage12_5_v0"
    base_environment_key: str
    overlay_environment_key: str
    source_snapshot_key: str
    environment_key: str | None = None

    @model_validator(mode="after")
    def fill_environment_key(self) -> "DependencyEnvironmentKey":
        for field_name in ["base_environment_key", "overlay_environment_key", "source_snapshot_key"]:
            _validate_safe_identifier(getattr(self, field_name), field_name=field_name)
        payload = {
            "base_environment_key": self.base_environment_key,
            "overlay_environment_key": self.overlay_environment_key,
            "source_snapshot_key": self.source_snapshot_key,
            "policy_version": DEPENDENCY_ENVIRONMENT_POLICY_VERSION,
        }
        object.__setattr__(
            self,
            "environment_key",
            self.environment_key or f"rhenv-{stable_hash(payload)[:24]}",
        )
        _validate_safe_identifier(str(self.environment_key), field_name="environment_key")
        return self


class DependencyEnvironmentFacts(StrictBaseModel):
    schema_version: str = "repo_harness_dependency_environment_facts_stage12_5_v0"
    policy_version: str = DEPENDENCY_ENVIRONMENT_POLICY_VERSION
    environment_key: str
    environment_ref: str
    base_environment_key: str
    overlay_environment_key: str
    source_snapshot_key: str
    python_version: str
    execution_mode: ExecutionMode
    cache_policy: CachePolicy
    node_dependency_policy: NodeDependencyPolicy
    pythonpath_entries: list[str] = Field(default_factory=list)
    created_by: str
    created_at_unix: float = Field(ge=0.0)
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_facts(self) -> "DependencyEnvironmentFacts":
        if not self.environment_ref.startswith("rh://environment/"):
            raise ValueError("environment_ref must be an opaque environment ref")
        for field_name in [
            "environment_key",
            "environment_ref",
            "base_environment_key",
            "overlay_environment_key",
            "source_snapshot_key",
            "python_version",
            "created_by",
        ]:
            value = getattr(self, field_name)
            _validate_no_absolute_local_path(str(value), field_name=field_name)
            _validate_no_secret_text(str(value), field_name=field_name)
        for entry in self.pythonpath_entries:
            _validate_safe_relative_path(entry, field_name="pythonpath_entries")
        for diagnostic in self.diagnostics:
            _validate_no_absolute_local_path(diagnostic, field_name="diagnostics")
            _validate_no_secret_text(diagnostic, field_name="diagnostics")
        return self


class DependencyEnvironmentReport(StrictBaseModel):
    schema_version: str = "repo_harness_dependency_environment_report_stage12_5_v0"
    environment_ref: str
    dependency_cache_key: str
    dependency_cache_hit: bool
    dependency_restore_seconds: float = Field(ge=0.0)
    cache_policy: CachePolicy
    diagnostics: list[str] = Field(default_factory=list)


class CommandEnvironmentDecision(StrictBaseModel):
    schema_version: str = "repo_harness_command_environment_decision_stage12_5_v0"
    allowed: bool
    reason: str | None = None
    normalized_command: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class DependencyEnvironmentHandle:
    facts: DependencyEnvironmentFacts
    environment_path: Path
    cache_hit: bool
    dependency_restore_seconds: float
    diagnostics: tuple[str, ...] = ()

    @property
    def environment_ref(self) -> str:
        return self.facts.environment_ref

    @property
    def dependency_cache_key(self) -> str:
        return self.facts.environment_key

    def report(self) -> DependencyEnvironmentReport:
        return DependencyEnvironmentReport(
            environment_ref=self.facts.environment_ref,
            dependency_cache_key=self.facts.environment_key,
            dependency_cache_hit=self.cache_hit,
            dependency_restore_seconds=self.dependency_restore_seconds,
            cache_policy=self.facts.cache_policy,
            diagnostics=[*self.facts.diagnostics, *self.diagnostics],
        )


class DependencyEnvironmentManager:
    """Create and reuse runtime-only dependency environments."""

    def __init__(
        self,
        cache_root: str | Path,
        *,
        creator_id: str | None = None,
        lock_timeout_seconds: float = 10.0,
    ) -> None:
        if lock_timeout_seconds <= 0:
            raise ValueError("lock_timeout_seconds must be > 0")
        self.cache_root = Path(cache_root)
        self.creator_id = creator_id or f"pid-{os.getpid()}"
        self.lock_timeout_seconds = lock_timeout_seconds
        self.environments_dir = self.cache_root / "environments"
        self.tmp_dir = self.cache_root / ".tmp"
        self.locks_dir = self.cache_root / ".locks"
        for directory in [self.environments_dir, self.tmp_dir, self.locks_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def prepare_environment(
        self,
        spec: DependencyEnvironmentSpec,
        *,
        initializer: Callable[[Path, DependencyEnvironmentSpec], None] | None = None,
    ) -> DependencyEnvironmentHandle:
        start = time.perf_counter()
        key = build_dependency_environment_key(spec)
        environment_key = _require_environment_key(key)
        if spec.cache_policy == "disable_cache":
            env_path = self.tmp_dir / f"{environment_key}.{uuid.uuid4().hex}.disabled"
            env_path.mkdir(parents=True)
            _initialize_environment_dir(env_path, spec, initializer)
            facts = _facts_from_spec(spec, key, created_by=self.creator_id)
            return DependencyEnvironmentHandle(
                facts=facts,
                environment_path=env_path,
                cache_hit=False,
                dependency_restore_seconds=time.perf_counter() - start,
                diagnostics=("dependency_cache_disabled",),
            )

        lock_path = self.locks_dir / f"{environment_key}.lock"
        with _DependencyEnvironmentLocalLock(lock_path, timeout_seconds=self.lock_timeout_seconds):
            env_path = self.environments_dir / environment_key
            facts_path = env_path / DEPENDENCY_ENVIRONMENT_FACTS_FILENAME
            if facts_path.exists():
                facts = DependencyEnvironmentFacts.model_validate_json(facts_path.read_text(encoding="utf-8"))
                _assert_facts_match_key(facts, key)
                read_only_diagnostics = _ensure_environment_tree_read_only(env_path)
                return DependencyEnvironmentHandle(
                    facts=facts,
                    environment_path=env_path,
                    cache_hit=True,
                    dependency_restore_seconds=time.perf_counter() - start,
                    diagnostics=tuple(read_only_diagnostics),
                )
            if spec.cache_policy == "read_only_hit":
                raise WorkspaceError("dependency environment read_only_hit cache miss")
            if env_path.exists():
                raise WorkspaceError("dependency environment exists without facts")
            tmp_path = self.tmp_dir / f"{environment_key}.{uuid.uuid4().hex}"
            try:
                tmp_path.mkdir(parents=True)
                _initialize_environment_dir(tmp_path, spec, initializer)
                facts = _facts_from_spec(spec, key, created_by=self.creator_id)
                _write_json(tmp_path / DEPENDENCY_ENVIRONMENT_FACTS_FILENAME, facts.model_dump(mode="json"))
                if env_path.exists():
                    shutil.rmtree(tmp_path, ignore_errors=True)
                    facts = DependencyEnvironmentFacts.model_validate_json(facts_path.read_text(encoding="utf-8"))
                    _assert_facts_match_key(facts, key)
                    read_only_diagnostics = _ensure_environment_tree_read_only(env_path)
                    return DependencyEnvironmentHandle(
                        facts=facts,
                        environment_path=env_path,
                        cache_hit=True,
                        dependency_restore_seconds=time.perf_counter() - start,
                        diagnostics=tuple(read_only_diagnostics),
                    )
                tmp_path.rename(env_path)
                _make_environment_tree_read_only(env_path)
                return DependencyEnvironmentHandle(
                    facts=facts,
                    environment_path=env_path,
                    cache_hit=False,
                    dependency_restore_seconds=time.perf_counter() - start,
                )
            except Exception:
                shutil.rmtree(tmp_path, ignore_errors=True)
                raise


def build_dependency_environment_key(spec: DependencyEnvironmentSpec) -> DependencyEnvironmentKey:
    base_payload = {
        "python_version": spec.python_version,
        "platform": spec.platform,
        "cpu_arch": spec.cpu_arch,
        "os_release": spec.os_release,
        "libc": spec.libc,
        "cuda_abi": spec.cuda_abi,
        "torch_abi": spec.torch_abi,
        "compiler_abi": spec.compiler_abi,
        "execution_mode": spec.execution_mode,
        "docker_image_digest": spec.docker_image_digest,
        "package_manager_versions": spec.package_manager_versions,
        "dependency_lockfiles": [lock.model_dump(mode="json") for lock in spec.dependency_lockfiles],
        "package_index_digest": spec.package_index_digest,
        "environment_allowlist_digest": spec.environment_allowlist_digest,
        "policy_version": spec.schema_policy_version,
    }
    overlay_payload = {
        "setup_commands": spec.setup_commands.model_dump(mode="json"),
        "pythonpath_entries": spec.pythonpath_entries,
        "node_dependency_policy": spec.node_dependency_policy,
        "policy_version": spec.schema_policy_version,
    }
    source_payload = {
        "source_tree_hash": spec.source_tree_hash,
        "source_archive_sha256": spec.source_archive_sha256,
        "base_commit": spec.base_commit,
        "policy_version": spec.schema_policy_version,
    }
    return DependencyEnvironmentKey(
        base_environment_key=f"base-{stable_hash(base_payload)[:24]}",
        overlay_environment_key=f"overlay-{stable_hash(overlay_payload)[:24]}",
        source_snapshot_key=f"source-{stable_hash(source_payload)[:24]}",
    )


def build_command_environment(
    handle: DependencyEnvironmentHandle,
    *,
    workspace_path: str | Path,
    base_env: Mapping[str, str] | None = None,
    expose_shared_environment_path: bool = False,
    overlay_directory_name: str = ".repo_harness_env_overlay",
    runtime_directory_name: str = ".repo_harness_runtime",
) -> dict[str, str]:
    workspace_root = Path(workspace_path).resolve()
    _validate_safe_relative_path(overlay_directory_name, field_name="overlay_directory_name")
    _validate_safe_relative_path(runtime_directory_name, field_name="runtime_directory_name")
    env = dict(_minimal_command_environment() if base_env is None else base_env)
    runtime_root = workspace_root.parent / runtime_directory_name / workspace_root.name
    home_dir = runtime_root / "home"
    cache_dir = runtime_root / "cache"
    tmp_dir = runtime_root / "tmp"
    pycache_dir = runtime_root / "pycache"
    pip_cache_dir = cache_dir / "pip"
    uv_cache_dir = cache_dir / "uv"
    for path in (home_dir, cache_dir, tmp_dir, pycache_dir, pip_cache_dir, uv_cache_dir):
        path.mkdir(parents=True, exist_ok=True)
    if expose_shared_environment_path:
        virtual_env = handle.environment_path
        bin_dir = handle.environment_path / "bin"
    else:
        virtual_env = workspace_root.parent / overlay_directory_name / workspace_root.name
        bin_dir = virtual_env / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        _populate_overlay_bin(bin_dir, handle.environment_path / "bin")
    env["VIRTUAL_ENV"] = str(virtual_env if expose_shared_environment_path else handle.environment_ref)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HOME"] = str(home_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    env["PIP_CACHE_DIR"] = str(pip_cache_dir)
    env["UV_CACHE_DIR"] = str(uv_cache_dir)
    env["TMPDIR"] = str(tmp_dir)
    env["TEMP"] = str(tmp_dir)
    env["TMP"] = str(tmp_dir)
    env["PYTHONPYCACHEPREFIX"] = str(pycache_dir)
    env["PYTHONPATH"] = os.pathsep.join(
        str(_resolve_pythonpath_entry(workspace_root, entry)) for entry in handle.facts.pythonpath_entries
    )
    env["REPO_HARNESS_ENVIRONMENT_REF"] = handle.environment_ref
    env["REPO_HARNESS_ENVIRONMENT_MODE"] = (
        "shared_environment_path" if expose_shared_environment_path else "workspace_overlay"
    )
    return env


def classify_shared_environment_write_command(command: str | Sequence[str]) -> CommandEnvironmentDecision:
    shell_wrapper_pattern = _raw_shell_wrapper_pattern(command)
    if shell_wrapper_pattern is not None:
        return CommandEnvironmentDecision(
            allowed=False,
            reason=f"shared_environment_write_command:{' '.join(shell_wrapper_pattern)}",
            normalized_command=_normalize_command(command),
        )
    shell_dynamic_pattern = _raw_shell_dynamic_expansion_pattern(command)
    if shell_dynamic_pattern is not None:
        return CommandEnvironmentDecision(
            allowed=False,
            reason=f"shared_environment_write_command:{' '.join(shell_dynamic_pattern)}",
            normalized_command=_normalize_command(command),
        )
    argv = _normalize_command(command)
    argv = _effective_command_argv(argv)
    if not argv:
        return CommandEnvironmentDecision(allowed=True, normalized_command=[])

    command_tuple = tuple(_strip_executable_suffix(part) for part in argv)
    normalized = list(command_tuple)
    embedded_pattern = _raw_embedded_shared_environment_write_pattern(command)
    if embedded_pattern is not None:
        return CommandEnvironmentDecision(
            allowed=False,
            reason=f"shared_environment_write_command:{' '.join(embedded_pattern)}",
            normalized_command=normalized,
        )
    forbidden_pattern = _first_shared_environment_write_pattern(command_tuple)
    if forbidden_pattern is not None:
        return CommandEnvironmentDecision(
            allowed=False,
            reason=f"shared_environment_write_command:{' '.join(forbidden_pattern)}",
            normalized_command=normalized,
        )
    return CommandEnvironmentDecision(allowed=True, normalized_command=normalized)


def assert_command_allowed_for_shared_environment(command: str | Sequence[str]) -> None:
    decision = classify_shared_environment_write_command(command)
    if not decision.allowed:
        raise WorkspaceError(decision.reason or "shared_environment_write_command")


def assert_command_avoids_runtime_overlay_path(command: str | Sequence[str]) -> None:
    raw = _raw_command_string(command).replace("\\", "/")
    if ".repo_harness_env_overlay" in raw:
        raise WorkspaceError("model_hidden_runtime_path:.repo_harness_env_overlay")
    if ".repo_harness_runtime" in raw:
        raise WorkspaceError("model_hidden_runtime_path:.repo_harness_runtime")


def classify_runtime_environment_probe_command(command: str | Sequence[str]) -> CommandEnvironmentDecision:
    argv = _normalize_command(command)
    effective_argv = _effective_command_argv(argv)
    normalized = [_strip_executable_suffix(part) for part in effective_argv]
    if not argv:
        return CommandEnvironmentDecision(allowed=True, normalized_command=[])

    raw_executable = _strip_executable_suffix(argv[0])
    if raw_executable in {"env", "printenv"} and not effective_argv:
        return CommandEnvironmentDecision(
            allowed=False,
            reason=f"runtime_environment_probe_command:{raw_executable}",
            normalized_command=[raw_executable],
        )
    if normalized and normalized[0] in _RUNTIME_ENVIRONMENT_PROBE_COMMANDS:
        return CommandEnvironmentDecision(
            allowed=False,
            reason=f"runtime_environment_probe_command:{normalized[0]}",
            normalized_command=normalized,
        )

    if normalized and normalized[0] == "python":
        module_reason = _python_module_execution_probe_reason(effective_argv)
        if module_reason is not None:
            return CommandEnvironmentDecision(
                allowed=False,
                reason=f"runtime_environment_probe_command:python:{module_reason}",
                normalized_command=normalized,
            )
        inline_code = _python_inline_code(effective_argv)
        if inline_code is not None:
            probe_reason = _python_inline_runtime_probe_reason(inline_code)
            if probe_reason is not None:
                return CommandEnvironmentDecision(
                    allowed=False,
                    reason=f"runtime_environment_probe_command:python:{probe_reason}",
                    normalized_command=normalized,
                )
        script_reason = _python_script_execution_probe_reason(effective_argv)
        if script_reason is not None:
            return CommandEnvironmentDecision(
                allowed=False,
                reason=f"runtime_environment_probe_command:python:{script_reason}",
                normalized_command=normalized,
            )
    return CommandEnvironmentDecision(allowed=True, normalized_command=normalized)


def _python_module_execution_probe_reason(argv: Sequence[str]) -> str | None:
    for index, part in enumerate(argv):
        if part == "-m" and index + 1 < len(argv):
            module = str(argv[index + 1]).split(".", 1)[0]
            if module in _PYTHON_RUNTIME_PROBE_MODULE_EXECUTIONS:
                return f"module:{module}"
        if part.startswith("-m") and len(part) > 2:
            module = part[2:].split(".", 1)[0]
            if module in _PYTHON_RUNTIME_PROBE_MODULE_EXECUTIONS:
                return f"module:{module}"
    return None


def _python_script_execution_probe_reason(argv: Sequence[str]) -> str | None:
    if any(part == "-c" for part in argv[1:]):
        return None
    if any(part == "-m" or part.startswith("-m") for part in argv[1:]):
        return None
    skip_next = False
    for part in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if part in {"-W", "-X"}:
            skip_next = True
            continue
        if part == "-":
            return "stdin_execution"
        if part.startswith("-"):
            continue
        return "script_execution"
    return None


def assert_command_does_not_probe_runtime_environment(command: str | Sequence[str]) -> None:
    decision = classify_runtime_environment_probe_command(command)
    if not decision.allowed:
        raise WorkspaceError(decision.reason or "runtime_environment_probe_command")


def assert_no_shell_wrapper_for_shared_environment(command: str | Sequence[str]) -> None:
    pattern = _raw_shell_wrapper_pattern(command)
    if pattern is not None:
        raise WorkspaceError(f"shared_environment_shell_wrapper:{' '.join(pattern)}")


def dependency_environment_resource_fields(
    handle: DependencyEnvironmentHandle,
) -> dict[str, str | bool | float]:
    return {
        "dependency_state_key": handle.dependency_cache_key,
        "dependency_cache_key": handle.dependency_cache_key,
        "dependency_cache_hit": handle.cache_hit,
        "repo_harness_environment_ref": handle.environment_ref,
        "dependency_restore_seconds": handle.dependency_restore_seconds,
    }


def _initialize_environment_dir(
    path: Path,
    spec: DependencyEnvironmentSpec,
    initializer: Callable[[Path, DependencyEnvironmentSpec], None] | None,
) -> None:
    (path / "bin").mkdir(parents=True, exist_ok=True)
    if initializer is not None:
        initializer(path, spec)
    else:
        _write_python_launcher(path / "bin" / "python", Path(sys.executable))
        _write_python_launcher(path / "bin" / "python3", Path(sys.executable))
        (path / "pyvenv.cfg").write_text(
            f"home = {Path(sys.executable).parent}\nversion = {spec.python_version}\n",
            encoding="utf-8",
        )


def _facts_from_spec(
    spec: DependencyEnvironmentSpec,
    key: DependencyEnvironmentKey,
    *,
    created_by: str,
) -> DependencyEnvironmentFacts:
    environment_key = _require_environment_key(key)
    return DependencyEnvironmentFacts(
        environment_key=environment_key,
        environment_ref=f"rh://environment/{environment_key}",
        base_environment_key=key.base_environment_key,
        overlay_environment_key=key.overlay_environment_key,
        source_snapshot_key=key.source_snapshot_key,
        python_version=spec.python_version,
        execution_mode=spec.execution_mode,
        cache_policy=spec.cache_policy,
        node_dependency_policy=spec.node_dependency_policy,
        pythonpath_entries=list(spec.pythonpath_entries),
        created_by=created_by,
        created_at_unix=time.time(),
        diagnostics=[*spec.diagnostics, "shared_environment_read_only_mode_bits_applied"],
    )


def _assert_facts_match_key(facts: DependencyEnvironmentFacts, key: DependencyEnvironmentKey) -> None:
    if facts.environment_key != _require_environment_key(key):
        raise WorkspaceError("dependency environment facts do not match requested key")
    if facts.base_environment_key != key.base_environment_key:
        raise WorkspaceError("dependency environment base key mismatch")
    if facts.overlay_environment_key != key.overlay_environment_key:
        raise WorkspaceError("dependency environment overlay key mismatch")
    if facts.source_snapshot_key != key.source_snapshot_key:
        raise WorkspaceError("dependency environment source key mismatch")


def _resolve_pythonpath_entry(workspace_root: Path, entry: str) -> Path:
    _validate_safe_relative_path(entry, field_name="pythonpath_entries")
    resolved = (workspace_root / entry).resolve(strict=False)
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise WorkspaceError("pythonpath entry escapes workspace root") from exc
    return resolved


def _normalize_command(command: str | Sequence[str]) -> list[str]:
    if isinstance(command, str):
        try:
            return shlex.split(command)
        except ValueError:
            return [command]
    return [str(part) for part in command]


def _python_inline_code(argv: Sequence[str]) -> str | None:
    for index, part in enumerate(argv[:-1]):
        if part == "-c":
            return str(argv[index + 1])
    return None


def _python_inline_runtime_probe_reason(code: str) -> str | None:
    for marker in _PYTHON_RUNTIME_PROBE_FALLBACK_MARKERS:
        if marker in code:
            return marker.replace(" ", "_")
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    module_aliases: dict[str, str] = {"__builtins__": "builtins"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".", 1)[0]
                # In shared dependency environment mode, inline imports can
                # leak concrete site-packages or interpreter paths through
                # module reprs even when the imported module itself looks
                # harmless. Keep `python -c "print('ok')"` available, but
                # require real import diagnostics to go through files/tests
                # whose output can be audited by the normal tool pipeline.
                return f"import:{module}"
                module_aliases[alias.asname or module] = module
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".", 1)[0]
            return f"from_import:{module}"
        elif isinstance(node, ast.Assign):
            alias_target = _runtime_probe_assignment_alias(node.value, module_aliases)
            if alias_target is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_aliases[target.id] = alias_target
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            alias_target = _runtime_probe_assignment_alias(node.value, module_aliases)
            if alias_target is not None:
                module_aliases[node.target.id] = alias_target

    for node in ast.walk(tree):
        name_reason = _runtime_probe_name_reason(node, module_aliases)
        if name_reason is not None:
            return name_reason
        attr_reason = _runtime_probe_attribute_reason(node, module_aliases)
        if attr_reason is not None:
            return attr_reason
        if isinstance(node, ast.Call):
            direct_call_reason = _runtime_probe_direct_call_reason(node, module_aliases)
            if direct_call_reason is not None:
                return direct_call_reason
            magic_getattribute_reason = _runtime_probe_magic_getattribute_reason(node, module_aliases)
            if magic_getattribute_reason is not None:
                return magic_getattribute_reason
            dict_get_reason = _runtime_probe_dict_get_reason(node, module_aliases)
            if dict_get_reason is not None:
                return dict_get_reason
            import_reason = _runtime_probe_import_call_reason(node)
            if import_reason is not None:
                return import_reason
            getattr_reason = _runtime_probe_getattr_reason(node, module_aliases)
            if getattr_reason is not None:
                return getattr_reason
        subscript_reason = _runtime_probe_subscript_reason(node, module_aliases)
        if subscript_reason is not None:
            return subscript_reason
    return None


def _runtime_probe_name_reason(node: ast.AST, module_aliases: Mapping[str, str]) -> str | None:
    if not isinstance(node, ast.Name):
        return None
    if node.id.startswith("__") and node.id.endswith("__"):
        return f"dunder_name:{node.id}"
    alias_target = module_aliases.get(node.id)
    if alias_target is not None and "." in alias_target:
        return alias_target
    return None


def _runtime_probe_assignment_alias(node: ast.AST, module_aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        if node.id in _PYTHON_RUNTIME_PROBE_BUILTIN_CALLS:
            return f"builtins.{node.id}"
        return module_aliases.get(node.id)
    if isinstance(node, ast.Call):
        return _dynamic_import_call_module(node, module_aliases)
    return None


def _runtime_probe_attribute_reason(node: ast.AST, module_aliases: Mapping[str, str]) -> str | None:
    if not isinstance(node, ast.Attribute):
        return None
    if node.attr.startswith("__") and node.attr.endswith("__"):
        return f"dunder_attribute:{node.attr}"
    root = node.value
    if isinstance(root, ast.Name):
        module = module_aliases.get(root.id, root.id)
        if "." in module:
            return module
        if node.attr in _PYTHON_RUNTIME_PROBE_ATTRS.get(module, set()):
            return f"{module}.{node.attr}"
    if isinstance(root, ast.Call):
        module = _dynamic_import_call_module(root, module_aliases)
        if module is not None and node.attr in _PYTHON_RUNTIME_PROBE_ATTRS.get(module, set()):
            return f"{module}.{node.attr}"
    return None


def _runtime_probe_direct_call_reason(node: ast.Call, module_aliases: Mapping[str, str]) -> str | None:
    if not isinstance(node.func, ast.Name):
        return None
    if node.func.id in _PYTHON_RUNTIME_PROBE_BUILTIN_CALLS:
        return f"builtins.{node.func.id}"
    alias_target = module_aliases.get(node.func.id)
    if alias_target is not None and "." in alias_target:
        return alias_target
    return None


def _runtime_probe_getattr_reason(node: ast.Call, module_aliases: Mapping[str, str]) -> str | None:
    if not isinstance(node.func, ast.Name) or node.func.id != "getattr" or len(node.args) < 2:
        return None
    attr = _constant_string(node.args[1])
    if attr is None:
        return None
    target = node.args[0]
    module: str | None = None
    if isinstance(target, ast.Name):
        module = module_aliases.get(target.id, target.id)
    elif isinstance(target, ast.Call):
        module = _dynamic_import_call_module(target, module_aliases)
    if module is not None and "." in module:
        return module
    if module is not None and attr in _PYTHON_RUNTIME_PROBE_ATTRS.get(module, set()):
        return f"{module}.{attr}"
    return None


def _runtime_probe_magic_getattribute_reason(
    node: ast.Call,
    module_aliases: Mapping[str, str],
) -> str | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "__getattribute__" or not node.args:
        return None
    attr = _constant_string(node.args[0])
    if attr is None:
        return None
    module = _module_name_from_ast(node.func.value, module_aliases)
    if module is not None and attr in _PYTHON_RUNTIME_PROBE_ATTRS.get(module, set()):
        return f"{module}.{attr}"
    return None


def _runtime_probe_dict_get_reason(node: ast.Call, module_aliases: Mapping[str, str]) -> str | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "get" or not node.args:
        return None
    attr = _constant_string(node.args[0])
    if attr is None:
        return None
    module = _runtime_probe_dict_module(node.func.value, module_aliases)
    if module is not None and attr in _PYTHON_RUNTIME_PROBE_ATTRS.get(module, set()):
        return f"{module}.{attr}"
    return None


def _runtime_probe_subscript_reason(node: ast.AST, module_aliases: Mapping[str, str]) -> str | None:
    if not isinstance(node, ast.Subscript):
        return None
    attr = _constant_string(node.slice)
    if attr is None:
        return None
    module = _runtime_probe_dict_module(node.value, module_aliases)
    if module is not None and attr in _PYTHON_RUNTIME_PROBE_ATTRS.get(module, set()):
        return f"{module}.{attr}"
    return None


def _runtime_probe_dict_module(node: ast.AST, module_aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Attribute) and node.attr == "__dict__":
        value = node.value
        if isinstance(value, ast.Name):
            module = module_aliases.get(value.id, value.id)
            return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
        if isinstance(value, ast.Call):
            module = _dynamic_import_call_module(value, module_aliases)
            return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "vars" and node.args:
            target = node.args[0]
            if isinstance(target, ast.Name):
                module = module_aliases.get(target.id, target.id)
                return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
            if isinstance(target, ast.Call):
                module = _dynamic_import_call_module(target, module_aliases)
                return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
        if isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2:
            attr = _constant_string(node.args[1])
            if attr != "__dict__":
                return None
            target = node.args[0]
            if isinstance(target, ast.Name):
                module = module_aliases.get(target.id, target.id)
                return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
            if isinstance(target, ast.Call):
                module = _dynamic_import_call_module(target, module_aliases)
                return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
    return None


def _module_name_from_ast(node: ast.AST, module_aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        module = module_aliases.get(node.id, node.id)
        return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
    if isinstance(node, ast.Call):
        module = _dynamic_import_call_module(node, module_aliases)
        return module if module in _PYTHON_RUNTIME_PROBE_ATTRS else None
    return None


def _runtime_probe_import_call_reason(node: ast.Call) -> str | None:
    module = _dynamic_import_call_module(node, {})
    if module in _PYTHON_RUNTIME_PROBE_MODULES:
        return f"dynamic_import:{module}"
    return None


def _dynamic_import_call_module(node: ast.Call, module_aliases: Mapping[str, str]) -> str | None:
    if not node.args:
        return None
    if isinstance(node.func, ast.Name):
        func_name = module_aliases.get(node.func.id, node.func.id)
        if func_name not in {"__import__", _IMPORTLIB_IMPORT_MODULE_ALIAS}:
            return None
        module = _constant_string(node.args[0])
        return None if module is None else module.split(".", 1)[0]
    if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
        value = node.func.value
        if isinstance(value, ast.Name) and module_aliases.get(value.id, value.id) == "importlib":
            module = _constant_string(node.args[0])
            return None if module is None else module.split(".", 1)[0]
    if isinstance(node.func, ast.Attribute) and node.func.attr == "__import__":
        value = node.func.value
        if isinstance(value, ast.Name) and module_aliases.get(value.id, value.id) == "builtins":
            module = _constant_string(node.args[0])
            return None if module is None else module.split(".", 1)[0]
    return None


def _import_call_module(node: ast.Call) -> str | None:
    if not isinstance(node.func, ast.Name) or node.func.id != "__import__" or not node.args:
        return None
    module = _constant_string(node.args[0])
    if module is None:
        return None
    return module.split(".", 1)[0]


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _constant_string(node.left)
        right = _constant_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            parts.append(value.value)
        return "".join(parts)
    return None


def _effective_command_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    executable = _strip_executable_suffix(argv[0])
    if executable in _COMMAND_FORWARDERS and len(argv) > 1:
        return _effective_command_argv(argv[1:])
    if executable == "env":
        index = 1
        while index < len(argv):
            part = argv[index]
            if part == "--":
                index += 1
                break
            if part == "-S" and index + 1 < len(argv):
                split_args = _normalize_command(argv[index + 1])
                return _effective_command_argv([*split_args, *argv[index + 2 :]])
            if part in {"-i", "-0"}:
                index += 1
                continue
            if part in {"-u", "--unset"} and index + 1 < len(argv):
                index += 2
                continue
            if part.startswith("-"):
                index += 1
                continue
            if "=" in part and not part.startswith("="):
                index += 1
                continue
            break
        return _effective_command_argv(argv[index:])
    if executable == "time":
        index = 1
        while index < len(argv) and argv[index].startswith("-"):
            index += 1
        return _effective_command_argv(argv[index:])
    if executable in _SHELL_EXECUTABLES:
        for index, part in enumerate(argv[1:], start=1):
            if part in {"-c", "-lc", "-ec", "-euc"} and index + 1 < len(argv):
                return _effective_command_argv(_normalize_command(argv[index + 1]))
        for index, part in enumerate(argv[1:], start=1):
            if "c" in part and part.startswith("-") and index + 1 < len(argv):
                return _effective_command_argv(_normalize_command(argv[index + 1]))
    if executable == "eval" and len(argv) > 1:
        return _effective_command_argv(_normalize_command(" ".join(argv[1:])))
    return argv


def _first_shared_environment_write_pattern(command_tuple: tuple[str, ...]) -> tuple[str, ...] | None:
    separators = {"&&", "||", ";", "|", "(", ")"}
    tokens = tuple(part for part in command_tuple if part not in separators)
    for index in range(len(tokens)):
        executable = tokens[index]
        following = tokens[index + 1 :]
        if executable == "pip" and _contains_any(following, {"install", "uninstall"}):
            command = "install" if "install" in following else "uninstall"
            return ("pip", command)
        if executable == "python":
            pip_index = _python_module_pip_index(following)
            if pip_index is not None:
                pip_args = following[pip_index + 1 :]
                if _contains_any(pip_args, {"install", "uninstall"}):
                    command = "install" if "install" in pip_args else "uninstall"
                    return ("python", "-m", "pip", command)
        if executable == "uv":
            if _contains_any(following, {"sync", "add"}):
                command = "sync" if "sync" in following else "add"
                return ("uv", command)
            pip_positions = [offset for offset, token in enumerate(following) if token == "pip"]
            for offset in pip_positions:
                pip_args = following[offset + 1 :]
                if _contains_any(pip_args, {"install", "uninstall"}):
                    command = "install" if "install" in pip_args else "uninstall"
                    return ("uv", "pip", command)
        if executable in {"npm", "pnpm", "yarn"} and _contains_any(following, {"install", "add", "ci"}):
            for command in ("install", "add", "ci"):
                if command in following:
                    return (executable, command)
        if executable in {"npm", "pnpm"} and "i" in following:
            return (executable, "i")
        if executable == "yarn" and not following:
            return ("yarn",)
        for pattern in sorted(_INSTALL_COMMANDS, key=len, reverse=True):
            if tokens[index : index + len(pattern)] == pattern:
                return pattern
        if tokens[index] == "python" and tokens[index + 1 : index + 4] == ("-m", "pip", "install"):
            return ("python", "-m", "pip", "install")
        if tokens[index] == "python" and tokens[index + 1 : index + 4] == ("-m", "pip", "uninstall"):
            return ("python", "-m", "pip", "uninstall")
    return None


def _contains_any(tokens: tuple[str, ...], candidates: set[str]) -> bool:
    return any(token in candidates for token in tokens)


def _python_module_pip_index(tokens: tuple[str, ...]) -> int | None:
    for index, token in enumerate(tokens[:-1]):
        if token == "-m" and tokens[index + 1] == "pip":
            return index + 1
        if token == "-mpip":
            return index
    return None


def _strip_executable_suffix(value: str) -> str:
    name = Path(value).name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    if name.startswith("python"):
        return "python"
    if name == "pip" or re.fullmatch(r"pip[0-9.]*", name):
        return "pip"
    return name


def _populate_overlay_bin(overlay_bin: Path, shared_bin: Path) -> None:
    if not shared_bin.exists():
        return
    for name in ["python", "python3", "pip", "pip3", "pytest"]:
        target = shared_bin / name
        if target.exists():
            _publish_overlay_launcher(overlay_bin / name, target)


def _make_environment_tree_read_only(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o555)
        elif path.is_file():
            executable = bool(path.stat().st_mode & 0o111)
            path.chmod(0o555 if executable else 0o444)
    root.chmod(0o555)


def _ensure_environment_tree_read_only(root: Path) -> list[str]:
    writable: list[Path] = []
    for path in [root, *root.rglob("*")]:
        if path.is_symlink():
            continue
        if path.stat().st_mode & 0o222:
            writable.append(path)
    if not writable:
        return []
    _make_environment_tree_read_only(root)
    return ["shared_environment_read_only_mode_bits_repaired"]


def _harden_workspace_overlay_directory(overlay_root: Path) -> None:
    for path in sorted(overlay_root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o111)
    overlay_root.chmod(0o111)


def _publish_overlay_launcher(link_path: Path, target: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        return
    link_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, link_path, follow_symlinks=True)
    if link_path.name in {"python", "python3"}:
        _copy_python_runtime_libraries(link_path.parent.parent, source_executable=target)


def _write_python_launcher(path: Path, python_executable: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\nexec {shlex.quote(str(python_executable))} \"$@\"\n", encoding="utf-8")
    path.chmod(0o755)


def _copy_python_runtime_libraries(destination_root: Path, *, source_executable: Path) -> None:
    candidates: list[Path] = []
    for root in {Path(sys.base_prefix), source_executable.parent.parent}:
        lib_dir = root / "lib"
        if lib_dir.exists():
            candidates.extend(sorted(lib_dir.glob("libpython*")))
    if not candidates:
        return
    target_lib_dir = destination_root / "lib"
    target_lib_dir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        if candidate.is_file():
            destination = target_lib_dir / candidate.name
            if destination.exists():
                continue
            shutil.copy2(candidate, destination, follow_symlinks=True)


def _minimal_command_environment() -> dict[str, str]:
    source_env = os.environ
    env = {
        key: source_env[key]
        for key in ("TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE")
        if key in source_env
    }
    python_bin_dir = str(Path(sys.executable).parent)
    default_path = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    env["PATH"] = f"{python_bin_dir}{os.pathsep}{default_path}"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _raw_embedded_shared_environment_write_pattern(command: str | Sequence[str]) -> tuple[str, ...] | None:
    raw = _raw_command_string(command)
    lowered = raw.lower()
    shell_expanded_for_policy = lowered.replace("${ifs}", " ").replace("$ifs", " ")
    shell_variable_pattern = _raw_shell_variable_package_manager_write_pattern(lowered)
    if shell_variable_pattern is not None:
        return shell_variable_pattern
    python_node_pattern = _looks_like_python_c_node_write(lowered)
    if python_node_pattern is not None:
        return python_node_pattern
    for command_name in ("install", "uninstall"):
        if re.search(rf"\bpip(?:[0-9.]*)?\s+{command_name}\b", shell_expanded_for_policy):
            return ("pip", command_name)
        if _looks_like_python_c_pip_write(lowered, command_name):
            return ("python", "-c", "pip", command_name)
        if "pip._internal" in lowered and re.search(rf"['\"]{command_name}['\"]", lowered):
            return ("python", "pip._internal", command_name)
        if "subprocess" in lowered and "pip" in lowered and re.search(rf"['\"]{command_name}['\"]", lowered):
            return ("python", "subprocess", "pip", command_name)
        if "$(" in lowered and "pip" in lowered and re.search(rf"\b{command_name}\b", lowered):
            return ("shell-substitution", command_name)
        if "|" in lowered and re.search(rf"\bpip(?:[0-9.]*)?\s+{command_name}\b", shell_expanded_for_policy):
            return ("shell-pipe", command_name)
    return None


def _raw_shell_wrapper_pattern(command: str | Sequence[str]) -> tuple[str, ...] | None:
    try:
        argv = shlex.split(command) if isinstance(command, str) else [str(part) for part in command]
    except ValueError:
        argv = [_raw_command_string(command)]
    if not argv:
        return None
    for part in argv:
        part_executable = _strip_executable_suffix(part)
        if part_executable in _SHELL_EXECUTABLES:
            return ("shell-wrapper", part_executable)
        try:
            nested_parts = shlex.split(part)
        except ValueError:
            nested_parts = []
        if nested_parts and _strip_executable_suffix(nested_parts[0]) in _SHELL_EXECUTABLES:
            return ("shell-wrapper", _strip_executable_suffix(nested_parts[0]))
    effective = _effective_command_argv(argv)
    if not effective:
        return None
    executable = _strip_executable_suffix(effective[0])
    if executable in _SHELL_EXECUTABLES:
        return ("shell-wrapper", executable)
    return None


def _raw_shell_dynamic_expansion_pattern(command: str | Sequence[str]) -> tuple[str, ...] | None:
    raw = _raw_command_string(command)
    lowered = raw.lower()
    if "$" not in lowered and "`" not in lowered:
        return None
    try:
        argv = shlex.split(raw) if isinstance(command, str) else [str(part) for part in command]
    except ValueError:
        argv = [raw]
    if not argv:
        return None
    executable = _strip_executable_suffix(argv[0])
    if executable in _SHELL_EXECUTABLES:
        return ("shell-dynamic-expansion",)
    if executable == "env" and any(_strip_executable_suffix(part) in _SHELL_EXECUTABLES for part in argv[1:]):
        return ("shell-dynamic-expansion",)
    return None


def _raw_shell_variable_package_manager_write_pattern(command: str) -> tuple[str, ...] | None:
    if "$" not in command:
        return None
    package_manager_present = any(
        re.search(rf"\b{name}\b", command)
        for name in ("pip", "npm", "pnpm", "yarn")
    )
    python_pip_present = re.search(r"\bpython(?:[0-9.]*)?\b", command) and "-m" in command and "pip" in command
    if not package_manager_present and not python_pip_present:
        return None
    if re.search(r"\$\(?|\$\{?[a-zA-Z_][A-Za-z0-9_]*\}?", command):
        return ("shell-variable", "package-manager-write")
    if (
        re.search(r"\b(install|uninstall|add|ci)\b", command)
        or re.search(r"(^|[\s;])i($|[\s;])", command)
        or re.search(r"(^|[\s;])[^;\s=]+=['\"]?i['\"]?($|[\s;])", command)
    ):
        return ("shell-variable", "package-manager-write")
    return None


def _looks_like_python_c_pip_write(command: str, command_name: str) -> bool:
    if "-c" not in command or "pip" not in command:
        return False
    if not re.search(r"\bpython(?:[0-9.]*)?\b", command):
        return False
    if re.search(rf"\b{command_name}\b", command):
        return True
    return re.search(rf"['\"]{command_name}['\"]", command) is not None


def _looks_like_python_c_node_write(command: str) -> tuple[str, ...] | None:
    if "-c" not in command:
        return None
    if not re.search(r"\bpython(?:[0-9.]*)?\b", command):
        return None
    for manager in ("npm", "pnpm"):
        if manager in command and re.search(r"\b(?:i|install|add|ci)\b", command):
            return ("python", "subprocess", manager, "install")
    if "yarn" in command:
        return ("python", "subprocess", "yarn")
    return None


def _raw_command_string(command: str | Sequence[str]) -> str:
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def _libc_identifier() -> str | None:
    try:
        libc_name, libc_version = platform_module.libc_ver()
    except Exception:
        return None
    if not libc_name and not libc_version:
        return None
    return f"{libc_name or 'unknown'}-{libc_version or 'unknown'}"


def _require_environment_key(key: DependencyEnvironmentKey) -> str:
    if key.environment_key is None:
        raise WorkspaceError("dependency environment key was not populated")
    return key.environment_key


def _validate_safe_identifier(value: str, *, field_name: str) -> None:
    if not value or not _SAFE_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a safe identifier")


def _validate_safe_name(value: str, *, field_name: str) -> None:
    if not value or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        raise ValueError(f"{field_name} contains unsafe name")


def _validate_safe_relative_path(value: str, *, field_name: str) -> None:
    _validate_no_absolute_local_path(value, field_name=field_name)
    path = PurePosixPath(value)
    if value in {"", "/"} or path.is_absolute() or any(part in {"..", ""} for part in path.parts):
        raise ValueError(f"{field_name} must be a safe relative path")


def _validate_no_absolute_local_path(value: str, *, field_name: str) -> None:
    if (
        Path(value).is_absolute()
        or any(marker in value for marker in _ABSOLUTE_PATH_MARKERS)
        or _EMBEDDED_POSIX_ABSOLUTE_PATH_RE.search(value)
    ):
        raise ValueError(f"{field_name} must not contain an absolute local path")


def _validate_no_secret_text(value: str, *, field_name: str) -> None:
    normalized = value.lower()
    if "://" in value and "@" in value:
        raise ValueError(f"{field_name} must not contain credentials")
    compact = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    sensitive_names = {
        "api_key",
        "access_token",
        "auth_token",
        "bearer_token",
        "secret_access_key",
        "aws_secret_access_key",
        "private_key",
        "client_secret",
    }
    for name in sensitive_names:
        if re.search(rf"(^|_){re.escape(name)}($|_)", compact):
            raise ValueError(f"{field_name} must not contain secret material")
    for marker in _SECRET_KEY_MARKERS:
        if re.search(rf"(^|[^a-z0-9]){re.escape(marker)}([^a-z0-9]|$)", normalized) and "=" in normalized:
            raise ValueError(f"{field_name} must not contain secret material")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    import json

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


class _DependencyEnvironmentLocalLock:
    def __init__(self, path: Path, *, timeout_seconds: float) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self._fd: int | None = None

    def __enter__(self) -> "_DependencyEnvironmentLocalLock":
        start = time.perf_counter()
        while True:
            try:
                self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("utf-8"))
                return self
            except FileExistsError:
                if time.perf_counter() - start >= self.timeout_seconds:
                    raise WorkspaceError("dependency environment lock timeout")
                time.sleep(0.01)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
