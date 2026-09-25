#!/usr/bin/env python3
"""R2E 真机对账（R-f）：RH2 账本 vs 独立 runner（M3 / 09-09）的**逐键**比较。

两侧都用固定的同一套规则（`envpack.r2e_parsers` + `scoring.expected_map_matches`）重新解析原始日志，再比较：
  - 观测状态映射（键 → 状态）是否逐键相同；
  - 相对期望映射的 missing / unexpected / mismatched 三个集合是否相同；
  - RH2 报告的 reward 与"对参考日志套上游 calculate_reward"的 reward 是否相同；参考账本（M3）自报的 reward 在场时
    另与日志重算值互核，矛盾单列（`reference_ledger_consistent=False`），缺失记 None（不可互核）。
`agree` 要求三件事**同时**成立：reward 相同、三个差异集合逐条相同、观测状态映射逐键相同——前两项不能代替第三项
（Codex closeout F1 的反例：期望 PASSED、RH2 得 FAILED、参考得 ERROR，两侧 reward 都 0、mismatched 集合都是这一个键，
但执行行为不同）。不看 46/48 总数，逐题逐键给差异；分歧只登记，不改题、不改 expected。

**材料版本（2026-09-24 夜，Codex 复核 F1）**：输入账本可能是来源版评分（R-f、中央复跑），也可能是修订版评分；不能拿当前受信池的
修订去解释历史账本。每行按账本自带证据判定版本（`decide_material_version`）：有期望修订的题，看来源版 / 修订版期望哪一版能
重现 grader 记下的判定明细；有隐藏测试修订的题，看评分所用派生镜像的配方是否带 `+material_`。判不出、混版或与 `--material`
显式指定不符的行标"版本未匹配"，不计入一致总数。修订版且改过隐藏测试的行照旧单列（参考 runner 跑的是修订前的测试）。

用法（从 rh2/）：
  .venv/bin/python scripts/reconcile_r2e.py --repo-root .. --ledger <noop账本> --ledger <gold账本> \\
      --m3-root runs/env_overnight_20260916/M3 [--old-root runs/env_probe_20260909_codex_backup/ledger] --out <目录>
输出：<out>/reconcile.json（逐行）与 <out>/reconcile.md（汇总表）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repoharness2.envpack import scoring  # noqa: E402
from repoharness2.envpack.ingest_r2e_subset import (  # noqa: E402
    EXPECTED_REVISION_KINDS,
    HIDDEN_REVISION_KINDS,
    load_r2e_rows,
    load_trusted_r2e_ingest_outputs,
)
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest, prime_calculate_reward  # noqa: E402


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", "replace")


def reference_logs(kind: str, repo: str, commit12: str, *, m3: Path, old: Path | None) -> list[tuple[str, Path]]:
    """独立 runner 的原始日志（同题、同 gate）及其来源：M3 的 noop_x2 / gold a1,a2；09-09 旧 24 题的 noop/gold a1–a3。
    来源标签用于账本互核：M3 账本只能与 M3 自己的日志互核，不同来源之间的分歧沿 comparisons 展示。"""

    out: list[tuple[str, Path]] = []
    if kind == "noop":
        out += [("m3", p) for p in sorted((m3 / "facts" / commit12 / "noop_x2").glob("out*.txt"))]
    else:
        out += [("m3", p) for p in sorted((m3 / "gold_ledger" / "logs_r2e" / repo / commit12 / "gold").glob("a*/test_output.txt"))]
    if old is not None:
        out += [("old", p) for p in sorted((old / "logs_r2e" / repo / commit12 / kind).glob("a*/test_output.txt"))]
    return [(src, p) for src, p in out if p.is_file()]


def observed_from_rh2_log(text: str) -> dict[str, str]:
    """RH2 评分日志只取 Start/End 标记段（与生产 parser 同纪律）。"""

    start, end = scoring.R2E_EVAL_START_MARKER, scoring.R2E_EVAL_END_MARKER
    if start not in text:
        return {}
    segment = text.split(start, 1)[1]
    segment = segment.split(end, 1)[0] if end in segment else ""
    return normalize_status_map(parse_log_pytest(segment))


def compare(expected: dict[str, str], rh2_obs: dict[str, str], ref_obs: dict[str, str]) -> dict:
    a, b = scoring.expected_map_matches(expected, rh2_obs), scoring.expected_map_matches(expected, ref_obs)
    keys = sorted(set(rh2_obs) | set(ref_obs))
    diff = {k: (rh2_obs.get(k), ref_obs.get(k)) for k in keys if rh2_obs.get(k) != ref_obs.get(k)}
    return {
        "rh2": {"resolved": a.resolved, "match": a.match_count, "total": a.total_count, "missing": a.missing, "unexpected": a.unexpected, "mismatched": a.mismatched},
        "reference": {"resolved": b.resolved, "match": b.match_count, "total": b.total_count, "missing": b.missing, "unexpected": b.unexpected, "mismatched": b.mismatched},
        "sets_equal": (a.missing, a.unexpected, a.mismatched) == (b.missing, b.unexpected, b.mismatched),
        "observed_maps_equal": not diff,
        "observed_diff": diff,
    }


def source_expected_json(iid: str, row_expected_text: str, revisions) -> str:
    """修订前的来源期望原文（M3 / 09-09 的账本是按它算分的，互核这些账本必须用同一份期望）。

    直接取来源原始行的 `expected_output_json`；有期望修订时核对它的摘要等于修订单的 `sha256_before`
    （修订单与来源不一致时不猜，抛错）。整份期望替换无法从修订后文本倒推，所以不做倒放。"""

    for rev in revisions:
        if rev.kind in EXPECTED_REVISION_KINDS and _sha256_text(row_expected_text) != rev.sha256_before:
            raise ValueError(f"{iid}/{rev.revision_id}: 来源行的期望原文摘要与修订单 sha256_before 不符")
    return row_expected_text


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


MATERIAL_SOURCE, MATERIAL_CURRENT, MATERIAL_UNMATCHED = "source", "current", "unmatched"


def verdict_tuple(expected: dict[str, str], observed: dict[str, str]) -> tuple:
    m = scoring.expected_map_matches(expected, observed)
    return (m.total_count, m.match_count, sorted(m.missing), sorted(m.unexpected), sorted(m.mismatched))


def recorded_verdict(ledger_row: dict) -> tuple | None:
    """账本行里 grader 自己记下的判定明细（verdict_diagnostics.expected_match）；缺字段 → None。"""

    d = (ledger_row.get("verdict_diagnostics") or {}).get("expected_match") or {}
    if "match_count" not in d or "total_count" not in d:
        return None
    return (d["total_count"], d["match_count"], sorted(d.get("missing") or []), sorted(d.get("unexpected") or []),
            sorted(d.get("mismatched") or []))


def decide_material_version(*, recorded: tuple | None, observed: dict[str, str] | None, source_expected: dict[str, str],
                            current_expected: dict[str, str], has_expected_rev: bool, has_hidden_rev: bool,
                            recipe_id: str | None, forced: str | None = None) -> dict:
    """账本行评分时实际用的是哪一版材料（纯函数，可测；Codex 09-24 复核 F1）。

    不能拿当前受信池的修订去解释历史账本：R-f 的行是按来源版评分的。判定只看账本自带的证据——
    ① 有期望修订：分别用来源版、当前版期望，从同一份 RH2 日志重算判定，**恰好一版**能逐项重现账本记下的
       (总键数, 符合数, missing, unexpected, mismatched)，就是那一版；
    ② 有隐藏测试修订：看这次评分所用派生镜像的配方身份，带 `+material_` 的是修订版隐藏测试，否则是来源版；
    两类证据都在时必须指向同一版。判不出、互相矛盾，或与 `forced`（用户显式指定）不符 → `unmatched`：
    这行不计入一致总数、不写分歧，只标"版本未匹配"。没有修订的题两版相同，记 current。"""

    if not (has_expected_rev or has_hidden_rev):
        return {"version": MATERIAL_CURRENT, "why": "该题没有材料修订，两版相同"}
    votes, why = set(), []
    if has_hidden_rev:
        if not recipe_id:
            return {"version": MATERIAL_UNMATCHED, "why": "账本没有记录派生镜像配方，无法判断隐藏测试版本"}
        hv = MATERIAL_CURRENT if "+material_" in recipe_id else MATERIAL_SOURCE
        votes.add(hv)
        why.append(f"镜像配方 {recipe_id} → 隐藏测试为{'修订版' if hv == MATERIAL_CURRENT else '来源版'}")
    if has_expected_rev:
        if recorded is None or observed is None:
            return {"version": MATERIAL_UNMATCHED, "why": "账本缺判定明细或日志缺失，无法核对期望版本"}
        fits = [v for v, exp in ((MATERIAL_SOURCE, source_expected), (MATERIAL_CURRENT, current_expected))
                if verdict_tuple(exp, observed) == recorded]
        if len(fits) != 1:
            return {"version": MATERIAL_UNMATCHED, "why": f"账本判定能被 {fits or '两版都不能'} 重现"}
        votes.add(fits[0])
        why.append(f"账本判定只能由{'来源版' if fits[0] == MATERIAL_SOURCE else '修订版'}期望重现")
    if len(votes) != 1:
        return {"version": MATERIAL_UNMATCHED, "why": "隐藏测试版本与期望版本不一致（混版）；" + "；".join(why)}
    version = votes.pop()
    if forced and forced != version:
        return {"version": MATERIAL_UNMATCHED, "why": f"指定 {forced}，但账本证据指向 {version}；" + "；".join(why)}
    return {"version": version, "why": "；".join(why)}


def row_class(*, version: str, hidden_tests_revised: bool, recipe_id: str | None) -> str:
    """一行怎样计入一致性统计（纯函数，可测）。参考 runner（M3 / 09-09）跑的是来源材料与来源环境：
    版本未匹配 → `unmatched`；隐藏测试已修订 → `hidden_revised`；评分镜像带环境配方（`+env_`，依赖版本被改过）→
    `env_recipe`。后两类单列、不计入"与来源一致"的总数，但照样报告其中有几行仍与参考一致。其余 → `counted`。"""

    if version == MATERIAL_UNMATCHED:
        return "unmatched"
    if hidden_tests_revised:
        return "hidden_revised"
    if "+env_" in (recipe_id or ""):
        return "env_recipe"
    return "counted"


def decide_agreement(rh2_reward, comparisons: list[dict], ledger_rewards: list) -> dict:
    """一致性判定（纯函数，可测）。返回各事实分列 + 总体 `agree`。

    `reference_ledger_consistent`（Codex 09-24 P2）：M3 账本自报的 reward **只与 M3 自己的日志**重算值互核
    （`source == "m3"` 的 comparisons）；旧来源（09-09）的日志不参与——不同参考来源之间的分歧由 `agree=False`
    与逐份 comparisons 表达，不冒充"账本自相矛盾"。没有可互核的 reward（账本缺席、全为 None、或没有 M3 日志）→ None。
    期望被修订过的题：M3 账本是按**来源期望**算的，互核用 comparisons 里的 `reference_prime_reward_source_expected`
    （缺省时退回 `reference_prime_reward`）；`reward_equal` 仍用修订后期望的重算值（RH2 按修订后期望评分）。"""

    ref_rewards = {c["reference_prime_reward"] for c in comparisons}
    comps = [c["comparison"] for c in comparisons if c.get("comparison")]
    m3_rewards = {c.get("reference_prime_reward_source_expected", c["reference_prime_reward"])
                  for c in comparisons if c.get("source", "m3") == "m3"}
    ledger_valid = [float(x) for x in ledger_rewards if x is not None]
    if not ledger_valid or not m3_rewards:
        ledger_consistent = None
    else:
        ledger_consistent = len(m3_rewards) == 1 and all(x == next(iter(m3_rewards)) for x in ledger_valid)
    facts = {
        "reward_equal": rh2_reward is not None and len(ref_rewards) == 1 and float(rh2_reward) == next(iter(ref_rewards)),
        "diff_sets_equal": bool(comps) and all(c["sets_equal"] for c in comps),
        "observed_maps_equal": bool(comps) and all(c["observed_maps_equal"] for c in comps),
        "reference_ledger_consistent": ledger_consistent,
    }
    facts["agree"] = bool(comparisons) and facts["reward_equal"] and facts["diff_sets_equal"] and facts["observed_maps_equal"]
    return facts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--ledger", action="append", required=True)
    ap.add_argument("--m3-root", required=True)
    ap.add_argument("--old-root", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--material", choices=["auto", MATERIAL_SOURCE, MATERIAL_CURRENT], default="auto",
                    help="账本评分时的材料版本：auto 按账本自带证据逐行判定；source / current 为显式指定（仍逐行核对，不符标 unmatched）")
    ns = ap.parse_args(argv)
    forced = None if ns.material == "auto" else ns.material
    repo_root, m3 = Path(ns.repo_root).resolve(), Path(ns.m3_root).resolve()
    old = Path(ns.old_root).resolve() if ns.old_root else None
    out = Path(ns.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    trusted = load_trusted_r2e_ingest_outputs(repo_root)
    gradings = {g.instance_id: g for g in trusted.result.grading_bundles}
    source_rows = {row["commit_hash"]: row for row in load_r2e_rows(repo_root, trusted.pins)[0]}
    m3_ledger: dict[tuple[str, str], list[dict]] = {}
    ledger_path = m3 / "gold_ledger" / "r2e_gold_m3.jsonl"
    if ledger_path.is_file():
        for line in _read(ledger_path).splitlines():
            if line.strip():
                row = json.loads(line)
                m3_ledger.setdefault((row.get("commit_hash", "")[:12], row.get("gate", "")), []).append(row)

    rows: list[dict] = []
    for ledger in ns.ledger:
        for line in _read(Path(ledger)).splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            iid, kind = r["instance_id"], r["candidate"]["kind"]
            g = gradings.get(iid)
            entry: dict = {"ledger": ledger, "instance_id": iid, "kind": kind, "attempt": r.get("attempt"),
                           "stage_error": r.get("stage_error"), "rh2_report": r.get("report")}
            if g is None:
                entry["note"] = "not_an_r2e_task"
                rows.append(entry)
                continue
            commit12 = g.source_commit_hash[:12]
            revs = trusted.revisions.get(iid, ())
            row_expected_text = source_expected_json(iid, source_rows[g.source_commit_hash]["expected_output_json"], revs)
            log_path = (r.get("log") or {}).get("path")
            rh2_obs = observed_from_rh2_log(_read(Path(log_path))) if log_path and Path(log_path).is_file() else None
            mv = decide_material_version(
                recorded=recorded_verdict(r), observed=rh2_obs,
                source_expected=normalize_status_map(json.loads(row_expected_text)),
                current_expected=normalize_status_map(g.expected_map()),
                has_expected_rev=any(rev.kind in EXPECTED_REVISION_KINDS for rev in revs),
                has_hidden_rev=any(rev.kind in HIDDEN_REVISION_KINDS for rev in revs),
                recipe_id=(r.get("overlay") or {}).get("recipe_id"), forced=forced)
            entry["material_version"] = mv
            entry["rh2_log"] = log_path
            if mv["version"] == MATERIAL_UNMATCHED:
                entry.update({"note": "material_version_unmatched", "comparisons": [], "agree": None, "reward_equal": None,
                              "diff_sets_equal": None, "observed_maps_equal": None, "reference_ledger_consistent": None})
                rows.append(entry)
                continue
            # 按判定出的版本取期望与修订标记：来源版行不贴当前修订（Codex F1），修订版行按修订后的期望比较；
            # 隐藏测试修订版的行，参考 runner 跑的是修订前的测试，单列、不计入"与来源一致"的总数。
            use_source = mv["version"] == MATERIAL_SOURCE
            expected_json = row_expected_text if use_source else g.expected_output_json
            expected = normalize_status_map(json.loads(expected_json))
            src_expected_json = row_expected_text
            entry["material_revisions"] = [] if use_source else list(g.material_revisions)
            entry["hidden_tests_revised"] = (not use_source) and any(rev.kind in HIDDEN_REVISION_KINDS for rev in revs)
            entry["recipe_id"] = (r.get("overlay") or {}).get("recipe_id")
            entry["row_class"] = row_class(version=mv["version"], hidden_tests_revised=entry["hidden_tests_revised"],
                                           recipe_id=entry["recipe_id"])
            entry["rh2_observed_count"] = None if rh2_obs is None else len(rh2_obs)
            refs = reference_logs(kind, g.repo, commit12, m3=m3, old=old)
            entry["reference_logs"] = [str(p) for _, p in refs]
            entry["comparisons"] = []
            for source, ref in refs:
                text = _read(ref)
                ref_obs = normalize_status_map(parse_log_pytest(text))
                comp = compare(expected, rh2_obs or {}, ref_obs) if rh2_obs is not None else None
                item = {"source": source, "reference_log": str(ref),
                        "reference_prime_reward": prime_calculate_reward(text, expected_json), "comparison": comp}
                if src_expected_json != expected_json:
                    item["reference_prime_reward_source_expected"] = prime_calculate_reward(text, src_expected_json)
                entry["comparisons"].append(item)
            rh2_reward = (r.get("report") or {}).get("reward")
            entry["m3_ledger_rewards"] = [x.get("reward") for x in m3_ledger.get((commit12, kind), [])]
            entry.update(decide_agreement(rh2_reward, entry["comparisons"], entry["m3_ledger_rewards"]) if entry["comparisons"]
                         else {"agree": None, "reward_equal": None, "diff_sets_equal": None, "observed_maps_equal": None,
                               "reference_ledger_consistent": None})
            rows.append(entry)

    (out / "reconcile.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["| 题 | gate | RH2 结论 | RH2 reward | 参考 reward（上游规则） | M3 账本自报 | 账本互核 | 差异集合相同 | 状态映射逐键相同 | 说明 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for e in rows:
        rep = e.get("rh2_report") or {}
        refs = sorted({c["reference_prime_reward"] for c in e.get("comparisons", [])})
        notes = []
        if e.get("stage_error"):
            notes.append(e["stage_error"])
        if e.get("comparisons") and not e.get("agree"):
            notes.append("分歧：见 reconcile.json")
        if e.get("reference_ledger_consistent") is False:
            notes.append("M3 账本自报 reward 与 M3 自己的日志重算不符")
        if e.get("note") == "material_version_unmatched":
            notes.append("版本未匹配：" + e["material_version"]["why"])
        if e.get("row_class") == "env_recipe":
            notes.append(f"环境配方 {e.get('recipe_id')}：参考 runner 跑的是来源环境，单列不计")
        if e.get("material_revisions"):
            notes.append(f"材料修订 {','.join(e['material_revisions'])}"
                         + ("（隐藏测试已修订：参考 runner 跑的是修订前的测试，不计入一致总数）" if e.get("hidden_tests_revised") else "（期望已修订：两侧都按修订后的期望计算）"))
        lines.append(f"| {e['instance_id'][:28]} | {e['kind']} | {rep.get('outcome')}/{rep.get('failure_category')} {rep.get('expected_match')}/{rep.get('expected_total')} "
                     f"| {rep.get('reward')} | {refs} | {e.get('m3_ledger_rewards')} | {e.get('reference_ledger_consistent')} "
                     f"| {e.get('diff_sets_equal')} | {e.get('observed_maps_equal')} | {'；'.join(notes)} |")
    counted = [e for e in rows if e.get("comparisons") and e.get("row_class") == "counted"]
    agree = sum(1 for e in counted if e.get("agree"))
    lines.append(f"\n一致（reward 相同 ∧ 差异集合逐条相同 ∧ 观测状态映射逐键相同）：{agree} / {len(counted)}（有参考日志、材料与环境都可与来源参考相比的行）")
    revised_rows = [e for e in rows if e.get("comparisons") and e.get("row_class") == "hidden_revised"]
    if revised_rows:
        lines.append(f"隐藏测试已修订、单列不计的行：{len(revised_rows)}（其中与修订前参考一致 {sum(1 for e in revised_rows if e.get('agree'))}）")
    env_rows = [e for e in rows if e.get("comparisons") and e.get("row_class") == "env_recipe"]
    if env_rows:
        lines.append(f"评分镜像带环境配方（依赖版本改过）、单列不计的行：{len(env_rows)}（其中仍与来源环境的参考一致 {sum(1 for e in env_rows if e.get('agree'))}）")
    unmatched = [e for e in rows if e.get("note") == "material_version_unmatched"]
    versions: dict[str, int] = {}
    for e in rows:
        v = (e.get("material_version") or {}).get("version")
        if v:
            versions[v] = versions.get(v, 0) + 1
    lines.append(f"材料版本（按账本自带证据逐行判定{'' if forced is None else '，指定 ' + forced}）：{versions}；版本未匹配、不计入的行：{len(unmatched)}")
    contradictions = sum(1 for e in rows if e.get("reference_ledger_consistent") is False)
    lines.append(f"M3 账本自报值与其自身日志重算矛盾的行：{contradictions}（None = 无可互核的账本 reward）")
    (out / "reconcile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
