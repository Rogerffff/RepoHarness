# `repo_harness` Package

This package contains the RepoHarness v1 implementation.

RepoHarness v1 is a lightweight local-process harness for replay-based software engineering agent runs. It implements the first executable loop described in the project design documents:

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

Implemented package areas include:

- `cli`
- `agent_loop`
- `scaffolds`
- `tools`
- `permissions`
- `workspace`
- `tasks`
- `verifier`
- `trajectory`
- `evaluation`
- `export`

The object model and module boundaries are centralized in `docs/11-object-model-config-and-data-flow.md`.

Important v1 boundaries:

- No production-grade secure sandbox.
- No real model provider integration.
- No claim of completed reinforcement learning training.
- No complete SWE-Bench reproduction.

Use `repo-harness --help` for command line entry points.
