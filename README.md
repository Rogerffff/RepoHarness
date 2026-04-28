# RepoHarness

RepoHarness is a design-stage Python project for a lightweight software engineering agent harness aimed at agentic training, post-training, and verifier-aligned trajectory collection.

The project goal is not to reimplement Claude Code, Cursor, OpenHands, or any production coding assistant. The first phase is a documented architecture and Python package skeleton for a future implementation.

## Project Definition

RepoHarness is intended to support this closed loop:

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

The eventual implementation will let a model work on real or semi-real repository tasks through tools such as file reading, search, patch editing, shell commands, and tests. It will record action-observation trajectories and use the same verifier surface for evaluation, reward metadata, and training-data export.

## Current Phase

This repository currently contains:

- A Python package skeleton under `src/repo_harness/`.
- Design documents under `docs/`.
- Review records under `docs/review/`.
- Local Claude Code reference material under `reference/`.

It does not yet contain a working agent loop, tool runtime, sandbox executor, verifier, or reinforcement learning integration.

## Reading Path

Start with:

1. `docs/00-reading-guide.md`
2. `docs/01-project-positioning-and-requirements.md`
3. `docs/02-system-architecture.md`

Then read the module documents in order from `03` to `10`.

For implementation handoff and resume packaging, also read:

1. `docs/11-object-model-config-and-data-flow.md`
2. `docs/12-resume-narrative-and-demo-artifacts.md`

## Project Lineage

RepoHarness is designed to complement two existing reinforcement learning oriented projects:

- CaRR DeepSearch contributes experience with long-horizon search agents, asynchronous rollout infrastructure, reward history, and trajectory diagnostics.
- Coding GRPO contributes experience with verifier-based coding post-training, executable feedback, shared verifier design, and checkpoint evaluation.
- RepoHarness transfers those ideas to repository-level software engineering tasks, where the important artifacts are workspace state, tool calls, tests, patches, trajectories, verifier results, and training export records.

This repository is still a design-stage repository. The lineage above describes the intended technical continuity, not a claim that RepoHarness already trains or evaluates a model end to end.

## Explicit Boundaries

RepoHarness is:

- A lightweight, training-aware software engineering agent harness design.
- A future framework for executable repository tasks, trajectory logging, verifier-aligned evaluation, and training export.
- A project inspired by product-grade agent architecture patterns, especially the separation of agent loop, tool contract, permission checks, and transcript storage.

RepoHarness is not:

- A production-grade secure sandbox.
- A complete Claude Code, Cursor, OpenHands, or SWE-agent clone.
- A new reinforcement learning algorithm.
- A complete SWE-Bench reproduction.
- A claim that a frontier coding agent has already been trained.

## Local Reference Material

`reference/claude-code-docs/` contains local analysis documents for Claude Code architecture. `reference/claude-code-typescript-src/` contains local TypeScript reference source and is ignored by Git by default.
