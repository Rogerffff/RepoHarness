"""仅从已冻结的公开数据生成目录、对照表和图；不发网络请求。"""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "snapshots" / "20260917T022438Z"
RUNS = ("pro", "flash")
data = {r: json.loads((SNAP / f"{r}_series_merged.json").read_text()) for r in RUNS}
status = {r: json.loads((SNAP / f"{r}_status_before.json").read_text()) for r in RUNS}
live = {r: json.loads((SNAP / f"{r}_live.json").read_text()) for r in RUNS}
cfg = json.loads((SNAP / "runs.json").read_text())
bench = json.loads((SNAP / "benchmarks.json").read_text())["benchmarks"][0]
tags = sorted(set().union(*(d["series"] for d in data.values())))


def fmt(v):
    if v is None:
        return "—"
    return f"{v:.8g}"


def current(run, tag):
    arr = data[run]["series"].get(tag)
    return arr[-1] if arr else None


def series_stats(run, tag):
    arr = data[run]["series"].get(tag)
    points = [(s, v) for s, v in zip(data[run]["steps"], arr or []) if v is not None]
    if not points:
        return {"present": tag in data[run]["series"], "observations": 0}
    vals = [v for _, v in points]
    return {"present": True, "observations": len(vals), "first_step": points[0][0],
            "first": vals[0], "last_step": points[-1][0], "last": vals[-1],
            "current": current(run, tag), "min": min(vals), "max": max(vals),
            "nonzero_observations": sum(v != 0 for v in vals)}


stats = {t: {r: series_stats(r, t) for r in RUNS} for t in tags}
(ROOT / "metrics_summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n")
counts = Counter(t.split("/")[0] for t in tags)
lines = ["# 全部公开指标目录", "", "冻结快照：2026-09-17 02:24:38 UTC 开始采集。Pro 主曲线 step 1–12，Flash step 1–15。",
         "", "下表显示主曲线末步值；`缺失；最近 sN=…` 表示该末步没有点，严禁当作末步实测值或零。`—` 表示此 run 无公开序列。",
         "完整逐步值见快照中的 `pro_series_merged.json`、`flash_series_merged.json`；精确首末值、范围与非零点数见 [metrics_summary.json](metrics_summary.json)。",
         "", "2,067 个标签是两个 run 的并集：Pro 2,019，Flash 2,050；它们不是 2,067 项独立实验。", ""]


def cell(run, tag):
    st = stats[tag][run]
    if not st["observations"]:
        return "—"
    if st["current"] is not None:
        return fmt(st["current"])
    return f"缺失；最近 s{st['last_step']}={fmt(st['last'])}"


for group, count in sorted(counts.items()):
    lines += [f"## {group} · {count}", "", "| 标签 | Pro s12 | Flash s15 |", "| --- | ---: | ---: |"]
    lines += [f"| `{t}` | {cell('pro', t)} | {cell('flash', t)} |" for t in tags if t.split('/')[0] == group]
    lines.append("")
(ROOT / "metric_catalog.md").write_text("\n".join(lines) + "\n")

# 复现网页 data-source 构成算法；保留估计标识与原始和，不强行归一成 1,568。
datasets = sorted({t.split("/")[1] + "/" + t.split("/")[2]
                   for t in tags if re.match(r"^dynsam/[^/]+/dataset-[^/]+/num_accepted/step$", t)})


def source_composition(run):
    s = data[run]["series"]
    idx = len(data[run]["steps"]) - 1
    def get(ds, kind, i):
        arr = s.get(f"dynsam/{ds}/num_accepted/{kind}") or []
        return (arr[i] or 0) if i >= 0 and i < len(arr) else 0
    raw = {ds: max(0, get(ds, "held", idx-1) + get(ds, "step", idx) - get(ds, "held", idx)) for ds in datasets}
    batch = current(run, "dynsam/num_target")
    sane = idx > 0 and abs(sum(raw.values()) - batch) <= .05 * batch
    if not sane:
        fresh = max(0, batch - sum(get(ds, "carryover", idx) for ds in datasets))
        accepts = sum(get(ds, "step", idx) for ds in datasets) or 1
        raw = {ds: get(ds, "carryover", idx) + get(ds, "step", idx) * fresh / accepts for ds in datasets}
    return {"values": raw, "approximation_fallback": not sane, "sum": sum(raw.values())}


composition = {r: source_composition(r) for r in RUNS}
mix = ["# 数据源、Harness 与统计口径", "", "均为匿名公开名称，不猜测其对应真实数据集或 agent 软件。数据源 prompts 按网页公式推导，不是训练消费者的精确逐来源计数。", "",
       "| 类别 | 数据源数 | Pro 推导 prompts / 占比 | Flash 推导 prompts / 占比 |", "| --- | ---: | ---: | ---: |"]
for cat in cfg["categories"]:
    subset = [d for d in datasets if d.startswith(cat + "/")]
    vals = [sum(composition[r]["values"][d] for d in subset) for r in RUNS]
    mix.append(f"| {cat} | {len(subset)} | {vals[0]:.2f} / {vals[0]/composition['pro']['sum']:.2%} | {vals[1]:.2f} / {vals[1]/composition['flash']['sum']:.2%} |")
mix += ["", "## 25 个数据源", "", "target 取同次采集的 live 表；其余取各 run 已完成末步，不能混成同一时刻的队列。",
        "", "| 数据源 | live 目标 Pro/Flash | 推导训练 prompts Pro/Flash | train/passrate Pro/Flash | 平均 response tokens Pro/Flash | 平均 lag Pro/Flash |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
for ds in datasets:
    targets = [live[r]["latest"]["ds"][ds][1] for r in RUNS]
    ps = [composition[r]["values"][ds] for r in RUNS]
    pv = [current(r, f"train/passrate/avg_passrate/{ds}") for r in RUNS]
    lens = [current(r, f"ctx_response_length/{ds}/mean") for r in RUNS]
    lags = [current(r, f"partial/{ds}/avg_staleness") for r in RUNS]
    mix.append(f"| `{ds}` | {targets[0]}/{targets[1]} | {fmt(ps[0])}/{fmt(ps[1])} | {fmt(pv[0])}/{fmt(pv[1])} | {fmt(lens[0])}/{fmt(lens[1])} | {fmt(lags[0])}/{fmt(lags[1])} |")
harnesses = sorted({t.split("/")[2] for t in tags if t.startswith("train/harness/")})
mix += ["", "## 23 个 Harness 标签", "", "网页构成图的 share = 本标签 rollouts / 所有已公开 harness rollouts。它与原始 `trained_rollout_share` 字段不是同一分母。",
        "", "| Harness | Pro rollouts | Flash rollouts | Pro nonzero_adv_rate | Flash nonzero_adv_rate | Pro 原始 share | Flash 原始 share |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
for h in harnesses:
    vals = [current(r, f"train/harness/{h}/training/{k}") for k in ("rollouts", "nonzero_adv_rate", "trained_rollout_share") for r in RUNS]
    mix.append("| `"+h+"` | "+" | ".join(fmt(v) for v in vals)+" |")
mix += ["", "末步公开 harness rollouts 合计 Pro=22,453、Flash=22,410；`train/verdicts/trained` 两者均为 25,088。公开资料没有解释差额。",
        "逐项数值核验发现，原始 share 近似等于该 harness 的非零 advantage 行数 / 所有 harness 非零行数之和；这是算术观察，不是作者公开的字段定义。",
        "不可用这些不同口径强行做跨阶段守恒，也不可据此断言数据丢失。"]
(ROOT / "source_and_harness.md").write_text("\n".join(mix) + "\n")
(ROOT / "composition_derived.json").write_text(json.dumps(composition, ensure_ascii=False, indent=2) + "\n")

history = ["# 逐步训练与事件记录", "", "主曲线和事件流分开；Flash 事件中的旧 step 16/17 不回填进当前主曲线。费用列仅复现固定费率×从 run 起点起的时长。", ""]
for r in RUNS:
    d, st = data[r], status[r]
    history += [f"## {r} 主曲线", "", "| step | 完成时间 UTC | 起跑后 h | 按页面费率估计 USD | sampled avg@n | trained reward | tokens B | step min | lag | DeepSWE |",
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for i, step in enumerate(d["steps"]):
        wall = d["walls"][i]
        stamp = datetime.fromtimestamp(wall, timezone.utc).strftime("%m-%d %H:%M:%S")
        elapsed = wall - st["run"]["start"]
        v = lambda t: d["series"][t][i]
        bv = bench["results"][r].get(str(step))
        history.append(f"| {step} | {stamp} | {elapsed/3600:.3f} | {elapsed*st['cost']['rate_per_s']:.0f} | {fmt(v('dynsam/avg@n'))} | {fmt(v('critic/rewards/mean'))} | {v('perf/total_num_tokens')/1e9:.5f} | {v('timing_s/step')/60:.3f} | {fmt(v('partial/avg_staleness'))} | {fmt(bv)} |")
    history += ["", f"## {r} 事件流", "", "| UTC | 事件 | step | avg@n | redo |", "| --- | --- | ---: | ---: | --- |"]
    for e in st["events"]:
        stamp = datetime.fromtimestamp(e["t"], timezone.utc).isoformat()
        history.append(f"| {stamp} | {e['kind']} | {e.get('step','')} | {fmt(e.get('value'))} | {e.get('redo','')} |")
    history.append("")
(ROOT / "step_history.md").write_text("\n".join(history) + "\n")

# 数据来源和 UI 标签清单的独立核对。
hash_checks = []
for path, base in [(ROOT / "source_manifest.json", ROOT), (SNAP / "manifest.json", SNAP)]:
    for entry in json.loads(path.read_text()):
        f = base / entry.get("file", entry.get("path"))
        assert hashlib.sha256(f.read_bytes()).hexdigest() == entry["sha256"], f
        hash_checks.append(str(f.relative_to(ROOT)))
ui_hash = 2166136261
for ch in "\n".join(tags):
    ui_hash = ((ui_hash ^ ord(ch)) * 16777619) & 0xFFFFFFFF
assert len(tags) == 2067 and f"{ui_hash:08x}" == "67ad9a49"
for r in RUNS:
    tag_data = json.loads((SNAP / f"{r}_tags.json").read_text())
    after = json.loads((SNAP / f"{r}_status_after.json").read_text())
    assert set(data[r]["series"]) == set(tag_data["tags"])
    assert status[r]["version"] == after["version"]
    assert all(len(v) == len(data[r]["steps"]) for v in data[r]["series"].values())
checks = {"snapshot": str(SNAP.relative_to(ROOT)), "tag_union": len(tags), "ui_tag_fnv1a": f"{ui_hash:08x}",
          "group_counts": dict(counts), "raw_files_sha256_checked": len(hash_checks),
          "run_versions_stable_during_capture": True,
          "non_null_points": {r: sum(v is not None for a in data[r]["series"].values() for v in a) for r in RUNS},
          "run_tag_counts": {r: len(data[r]["series"]) for r in RUNS},
          "returns_equal_advantages_all_public_points": {r: all(v == data[r]["series"][k.replace('/returns/', '/advantages/')] for k,v in data[r]['series'].items() if k.startswith('critic/') and '/returns/' in k) for r in RUNS},
          "rewards_equal_scores_all_public_points": {r: all(v == data[r]["series"][k.replace('/rewards/', '/score/')] for k,v in data[r]['series'].items() if k.startswith('critic/') and '/rewards/' in k) for r in RUNS}}
(ROOT / "verification.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")

# 标准绘图库生成静态科研图，不对原始曲线平滑，也不把缺失值补零。
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white", "axes.grid": True,
                     "grid.alpha": .18, "axes.titleweight": "bold"})
colors = {"pro": "#cc6234", "flash": "#2674bf"}
fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), layout="constrained")
specs = [("dynsam/avg@n", "Sampled prompt success (avg@n)", 100, "%"),
         (None, "Offline DeepSWE v1.1 / mini-swe-agent", 1, "avg@3 score"),
         ("ctx_response_length/mean", "Mean trajectory response length", .001, "k tokens"),
         ("partial/avg_staleness", "Mean policy-version lag", 1, "versions"),
         ("timing_s/step", "Reported step duration", 1/60, "minutes"),
         ("penalty/stage_credit_group/time_total_sec_mean", "Group grader: mean elapsed time", 1/60, "minutes")]
for ax, (tag, title, scale, ylabel) in zip(axes.flat, specs):
    for r in RUNS:
        if tag:
            xs = data[r]["steps"]
            ys = [np.nan if v is None else v*scale for v in data[r]["series"][tag]]
        else:
            xs = sorted(map(int, bench["results"][r]))
            ys = [bench["results"][r][str(s)] for s in xs]
        ax.plot(xs, ys, marker="o", markersize=3.5, linewidth=1.7, color=colors[r], label=r.title())
    ax.set(title=title, xlabel="Published step", ylabel=ylabel)
    ax.legend(frameon=False)
fig.suptitle("MiMo-V2.6 live RL | frozen public snapshot: 17 Sep 2026, 02:24 UTC", fontsize=16)
fig.supxlabel("No smoothing. Different run/checkpoint coverage; these are not controlled ablations.", fontsize=10)
(ROOT / "figures").mkdir(exist_ok=True)
fig.savefig(ROOT / "figures" / "learning_and_system.png", dpi=180)
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
xs = np.arange(10)
for r, offset in [("pro", -.18), ("flash", .18)]:
    # 无观测的 bucket 用 NaN，不把跨 step 的最近旧值放进当前分布。
    ys = [current(r, f"partial/{i}/frac") for i in xs]
    yv = [np.nan if v is None else 100*v for v in ys]
    axes[0].bar(xs+offset, yv, width=.34, color=colors[r], label=f"{r.title()} s{data[r]['steps'][-1]}")
    kl = [current(r, f"partial/{i}/train_infer_diff/new_infer/kl") for i in xs]
    axes[1].plot(xs, [np.nan if v is None else v for v in kl], marker="o", color=colors[r], label=r.title())
axes[0].set(title="Current lag buckets", xlabel="Policy versions behind", ylabel="Logged frac (%)", xticks=xs)
axes[1].set(title="Inference / trainer KL by lag", xlabel="Policy versions behind", ylabel="Logged KL", xticks=xs)
for ax in axes: ax.legend(frameon=False)
fig.suptitle("Averages hide the asynchronous tail", fontsize=16)
fig.supxlabel("Pro s12 has no public points for buckets 2-9. Omitted values are not filled with earlier observations.", fontsize=9)
fig.savefig(ROOT / "figures" / "lag_and_kl.png", dpi=180)
plt.close(fig)
print(json.dumps(checks, ensure_ascii=False, indent=2))
