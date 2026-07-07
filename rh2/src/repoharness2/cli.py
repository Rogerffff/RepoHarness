"""inspect-rh2-artifact：rh2 契约对象的最小校验命令（S1-1 交付物）。

四步中取三步（完整四步范式的阶段总账本见 inspect-rh2-s1，repoharness2/inspect_s1.py）：

  1. 读 JSON 文件；
  2. 按顶层 `schema_id` 在 FULL_SCHEMA_REGISTRY（S1-9 起为聚合表：contracts
     15 个核心契约 + envpack bundle 三件 + BackpressureEvent + GroupRepairSignal，
     见 repoharness2/registry.py）里判类型；
  3. 用对应 pydantic 模型做严格校验（extra="forbid"，未知字段即失败）；
  4. forbidden marker 扫描（runtime-private 审计资产默认豁免，
     用 --force-marker-scan 强制扫描；--skip-marker-scan 仅供排障）。

退出码约定（脚本/CI 消费）：
  0  全部通过
  2  schema_id 缺失 / 未注册 / 与 --expect-schema 不符
  3  schema 校验失败（含未知字段、非法组合）
  4  forbidden marker 命中
  5  文件读不到或不是合法 JSON

用法示例：
  uv run inspect-rh2-artifact path/to/eligibility_report.json
  uv run inspect-rh2-artifact proj.json --expect-schema rh2.trajectory_projection.v1
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from repoharness2.contracts import scan_for_forbidden_markers
from repoharness2.registry import (
    FULL_MARKER_SCAN_EXEMPT_SCHEMAS as MARKER_SCAN_EXEMPT_SCHEMAS,
)
from repoharness2.registry import (
    FULL_SCHEMA_REGISTRY as SCHEMA_REGISTRY,
)

EXIT_OK = 0
EXIT_UNKNOWN_SCHEMA = 2
EXIT_VALIDATION_FAILED = 3
EXIT_FORBIDDEN_MARKER = 4
EXIT_IO_ERROR = 5


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inspect-rh2-artifact",
        description="校验单个 rh2 契约 JSON 工件：判 schema 类型 -> pydantic 严格校验 -> forbidden marker 扫描。",
    )
    parser.add_argument("path", help="待校验的 JSON 文件路径。")
    parser.add_argument(
        "--expect-schema",
        default=None,
        help="期望的 schema_id（如 rh2.eligibility_report.v1）；实际值不符时以退出码 2 失败。",
    )
    parser.add_argument(
        "--force-marker-scan",
        action="store_true",
        help="对豁免名单内的 runtime-private 资产也执行 marker 扫描。",
    )
    parser.add_argument(
        "--skip-marker-scan",
        action="store_true",
        help="跳过 marker 扫描（仅排障用；正式验收禁止）。",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # 步骤 1：读 JSON
    path = Path(args.path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[inspect-rh2-artifact] 读文件失败: {path}: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"[inspect-rh2-artifact] 不是合法 JSON: {path}: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR

    # 步骤 2：判 schema 类型
    if not isinstance(payload, dict):
        print("[inspect-rh2-artifact] 顶层必须是 JSON object。", file=sys.stderr)
        return EXIT_UNKNOWN_SCHEMA
    schema_id = payload.get("schema_id")
    if not isinstance(schema_id, str):
        print("[inspect-rh2-artifact] 顶层缺少 schema_id 字段，无法判别契约类型。", file=sys.stderr)
        return EXIT_UNKNOWN_SCHEMA
    model_cls = SCHEMA_REGISTRY.get(schema_id)
    if model_cls is None:
        known = ", ".join(sorted(SCHEMA_REGISTRY))
        print(
            f"[inspect-rh2-artifact] 未注册的 schema_id: {schema_id!r}。已注册: {known}",
            file=sys.stderr,
        )
        return EXIT_UNKNOWN_SCHEMA
    if args.expect_schema is not None and schema_id != args.expect_schema:
        print(
            f"[inspect-rh2-artifact] schema_id 不符: 期望 {args.expect_schema!r}，实际 {schema_id!r}。",
            file=sys.stderr,
        )
        return EXIT_UNKNOWN_SCHEMA

    # 步骤 3：pydantic 严格校验（fail-closed：未知字段、非法组合都在这里拦住）
    try:
        model_cls.model_validate(payload)
    except ValidationError as exc:
        print(f"[inspect-rh2-artifact] schema 校验失败（{schema_id}）:\n{exc}", file=sys.stderr)
        return EXIT_VALIDATION_FAILED

    # 步骤 4：forbidden marker 扫描
    scan_skipped_reason: str | None = None
    if args.skip_marker_scan:
        scan_skipped_reason = "--skip-marker-scan（仅排障）"
    elif schema_id in MARKER_SCAN_EXEMPT_SCHEMAS and not args.force_marker_scan:
        scan_skipped_reason = "runtime-private 审计资产豁免（--force-marker-scan 可强制）"

    if scan_skipped_reason is None:
        hits = scan_for_forbidden_markers(payload)
        if hits:
            for hit in hits:
                print(
                    f"[inspect-rh2-artifact] forbidden marker 命中: path={hit.path} "
                    f"marker={hit.marker!r} kind={hit.kind}",
                    file=sys.stderr,
                )
            return EXIT_FORBIDDEN_MARKER
        marker_note = "marker 扫描通过"
    else:
        marker_note = f"marker 扫描跳过：{scan_skipped_reason}"

    print(f"[inspect-rh2-artifact] OK schema={schema_id} 校验通过；{marker_note}。")
    return EXIT_OK


def entry() -> None:
    """console_scripts 入口（inspect-rh2-artifact 命令）。"""

    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
