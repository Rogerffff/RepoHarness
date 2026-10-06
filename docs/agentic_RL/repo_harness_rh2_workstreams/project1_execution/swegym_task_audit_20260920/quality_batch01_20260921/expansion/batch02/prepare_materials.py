"""首批审查材料导出：只读本地 Git/JSON/日志，不运行任务代码或改生产输入。"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
WORK = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
sys.path.insert(0, str(ROOT / "rh2/src"))
from repoharness2.envpack.bundles import (
    PublicTaskBundle,
    render_user_prompt,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def task_id(row: dict) -> str:
    return row["instance_id"].split("::")[-1]


def git(clone: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(clone), *args])


def export_base(clone: Path, commit: str, destination: Path) -> dict:
    """直接读 blob，避免 archive 属性遗漏测试或替换源文件字节。"""
    tree = git(clone, "rev-parse", commit + "^{tree}").decode().strip()
    entries = git(clone, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    destination.mkdir(parents=True)
    count, total_bytes, links, lfs = 0, 0, [], []
    submodules = []
    proc = subprocess.Popen(
        ["git", "-C", str(clone), "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    )
    try:
        for entry in entries:
            if not entry:
                continue
            metadata, raw_name = entry.split(b"\t", 1)
            mode, kind, oid = metadata.split()
            name = raw_name.decode("utf-8")
            if kind == b"commit" and mode == b"160000":
                submodules.append({"path": name, "commit": oid.decode(),
                                   "status": "contents_not_materialized"})
                continue
            if kind != b"blob":
                raise ValueError(f"材料需要单独补齐的非 blob 对象: {name} {kind!r}")
            target = destination / name
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError(f"base 路径越出导出目录: {name}")
            proc.stdin.write(oid + b"\n")
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError(f"Git 对象读取失败: {name} {header!r}")
            data = proc.stdout.read(int(header[2]))
            if len(data) != int(header[2]) or proc.stdout.read(1) != b"\n":
                raise ValueError(f"Git 对象不完整: {name}")
            if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != oid.decode():
                raise ValueError(f"Git blob 字节不符: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if mode == b"120000":
                link = data.decode("utf-8")
                if not (target.parent / link).resolve().is_relative_to(destination.resolve()):
                    raise ValueError(f"需要人工处理的外部符号链接: {name} -> {link}")
                target.symlink_to(link)
                links.append(name)
            elif mode in (b"100644", b"100755"):
                target.write_bytes(data)
                target.chmod(0o755 if mode == b"100755" else 0o644)
            else:
                raise ValueError(f"未支持的 Git mode: {name} {mode!r}")
            if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                lfs.append(name)
            count += 1
            total_bytes += len(data)
    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError(f"cat-file 退出 {proc.returncode}")
    return {"base_tree": tree, "tracked_entries": count + len(submodules), "materialized_blob_entries": count, "blob_bytes": total_bytes,
            "symlinks": links, "lfs_pointers_not_materialized": lfs, "gitlinks": submodules,
            "git_metadata_exported": False, "blob_bytes_verified": True}


def ledger_refs(ledger: Path, instance: str, role: str | None = None) -> list[dict]:
    result = []
    for number, line in enumerate(ledger.read_text().splitlines(), 1):
        row = json.loads(line)
        if task_id(row) != instance:
            continue
        kind = row.get("candidate", {}).get("kind")
        if role is not None and kind != role:
            continue
        log = row.get("log") or {}
        path = log.get("path")
        if path and path.startswith("/work/full216_20260919/"):
            path = "runs/full216_rh2_diagnostic_20260919/remote/" + path.removeprefix("/work/full216_20260919/")
        elif path and path.startswith("/work/env_recipe_repair_20260919/"):
            path = "runs/env_recipe_repair_20260919/" + path.removeprefix("/work/env_recipe_repair_20260919/")
        result.append({"ledger": str(ledger.relative_to(ROOT)), "line": number,
                       "candidate": kind, "log": path, "log_sha256": log.get("sha256")})
    return result


BRIEF = """# 本题公开审查的环境说明

这是静态材料，不是实际容器或已捕获模型请求。user_prompt.txt 由当前函数渲染；
public_bundle.json 中的 public_hints 是可见字段，尚未核验它是否进入 CLI 的 system message。
base/ 是指定 base_commit 的 Git 跟踪源码、文档和旧测试，没有 .git/未来历史；
真实镜像可能另有环境提交、构建产物、预装包、资产及公开祖先历史，本包未提供这些运行事实。

准备采用真实 Claude Code 工作流，公开工具字段为 bash/edit，工作目录 /testbed。
当前正式 profile 以 agent/54321 执行，可写工作区和 home；解释器/系统包的写权限仍按实际配置核对。
网络仅模型代理与已声明内部服务，不假定可访问公网文档或下载依赖。
代码默认 2 CPU/4 GiB/PID512，tmp1 GiB/home256 MiB；本题实际资源和资产未在此验证。
解释器激活、依赖安装、资产读取和相关公开测试是否可执行，须另做 actor 身份的 CPU 验证。
请根据公开材料列出必要开发条件与最小验证命令；不要把缺证据当题目不可解，也不要填环境已通过。
若 base_identity.json 列有 gitlinks，它只记录子模块路径和固定commit，子模块内容尚未导出；
按公开 .gitmodules 及任务需求判断是否需要补读，不把缺材料当题目不成立。
隐藏验收测试无需提供给解题者；不要求全仓测试均能执行。不要读取其它题或本目录之外的调查材料。

## 旧提示字段的适用范围（v2 补充；原 bundle 不改）

分别记录 issue 的目标需求、harness 操作指令、待验环境声明。public_hints 中“conda 已激活”
不是运行证明；原“禁止改测试”指令是否应用于本次实际求解仍须核对，审查不授权自行忽略。
其“所有测试修改都会恢复、永不计分”的解释已经不能代表当前机制：目前没有按测试文件名
统一排除，仍有官方文件恢复等具体限制。逐题哪些文件受影响由私有调查核实。
若原指令会限制合理修复，分别说明该指令适用与不适用时的影响，记为共享输入/运行条件问题，
不要直接判原题无效或把受限条件静默取消。public bundle 会写入真实解题容器的公开路径；
字段没有出现在 user_prompt.txt，不等于解题者不可读。实际消息、工具及 shell 环境仍待验证。
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/swegym_quality_batch01_20260921")
    args = parser.parse_args()
    output = ROOT / args.output
    if output.exists():
        raise SystemExit("输出目录已存在；不覆盖，请为新材料指定另一个 --output")
    manifest = json.loads((HERE / "batch_manifest.json").read_text())
    source_lines = {}
    for key, ref in manifest["source_files"].items():
        data = (ROOT / ref["path"]).read_bytes()
        if sha(data) != ref["sha256"]:
            raise ValueError(f"来源已变化，先另存材料版本: {key}")
        source_lines[key] = data.splitlines()
    catalog_path = WORK / "env_recipe_repair_20260919/repair_catalog.json"
    catalog = {task_id(r): r for r in json.loads(catalog_path.read_text())["tasks"]}
    baseline_ledgers = list((ROOT / "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers").glob("*/ledger.jsonl"))
    check = {"scope": "materials_only_no_task_review_or_runtime", "output": args.output,
             "tasks": [], "source_files": manifest["source_files"], "code_sha256": {}}
    for name in ("envpack/bundles.py", "envpack/materialize.py", "adapters/slime/prepared_task_face.py",
                 "adapters/slime/sandbox_profile.py", "adapters/slime/generate.py", "adapters/slime/bringup.py"):
        path = ROOT / "rh2/src/repoharness2" / name
        check["code_sha256"][str(path.relative_to(ROOT))] = sha(path.read_bytes())
    output.mkdir(parents=True)
    for task in manifest["tasks"]:
        instance = task["instance_id"]
        pub, priv = output / "public" / instance, output / "private" / instance
        pub.mkdir(parents=True)
        priv.mkdir(parents=True)
        rows = {}
        for key, ref in task["source_refs"].items():
            raw = source_lines[key][ref["line"] - 1]
            rows[key] = json.loads(raw)
            if task_id(rows[key]) != instance:
                raise ValueError(f"来源行不匹配: {instance}/{key}")
            (pub / "public_bundle.json" if key == "public" else priv / f"{key}.json").write_bytes(raw + b"\n")
        public = PublicTaskBundle.model_validate(rows["public"])
        if public.base_commit != task["base_commit"] or rows["grading"]["base_commit"] != public.base_commit:
            raise ValueError(f"base 不匹配: {instance}")
        prompt = render_user_prompt(public)
        (pub / "user_prompt.txt").write_text(prompt)
        (pub / "environment_brief.md").write_text(BRIEF)
        base = export_base(ROOT / task["repo_mirror"], task["base_commit"], pub / "base")
        write_json(pub / "base_identity.json", {"instance_id": instance, "base_commit": task["base_commit"], **base})
        (priv / "test.patch").write_text(rows["grading"]["test_patch"])
        (priv / "gold.patch").write_text(rows["validation"]["golden_patch"])
        refs = []
        if instance in catalog:
            env = catalog[instance]
            write_json(priv / "environment_record.json", env)
            for role, obs in env["observations"].items():
                log = ROOT / obs["log"]
                refs.extend(ledger_refs(log.parent.parent / "ledger.jsonl", instance, role))
        else:
            env = task["environment"]
            write_json(priv / "environment_record.json", env)
            for ledger in baseline_ledgers:
                refs.extend(ledger_refs(ledger, instance))
        if len(refs) != 2 or {r["candidate"] for r in refs} != {"noop", "gold"}:
            raise ValueError(f"最终环境对照定位不唯一: {instance} {refs}")
        for ref in refs:
            if not ref["log"] or not (ROOT / ref["log"]).is_file():
                raise ValueError(f"日志未在本地找到: {instance} {ref}")
            if sha((ROOT / ref["log"]).read_bytes()) != ref["log_sha256"].removeprefix("sha256:"):
                raise ValueError(f"日志内容与所引账本不一致: {instance} {ref['log']}")
        write_json(priv / "run_refs.json", refs)
        history = task["history_sources"]
        for path in history:
            if not (ROOT / path).is_file():
                raise ValueError(f"历史引用缺失: {path}")
        write_json(output / "history" / instance / "refs.json", {"read_after_independent_analysis": history})
        write_json(priv / "source_refs.json", task["source_refs"])
        check["tasks"].append({"instance_id": instance, "base_commit": task["base_commit"], **base,
                               "public_prompt_sha256": sha(prompt.encode()), "run_refs": refs,
                               "source_identity_checked": True})
        print(f"prepared {instance}: {base['tracked_entries']} base entries, {len(refs)} run refs", flush=True)
    check["task_count"] = len(check["tasks"])
    check["code_sha256"][str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).read_bytes())
    write_json(output / "material_check.json", check)


if __name__ == "__main__":
    main()
