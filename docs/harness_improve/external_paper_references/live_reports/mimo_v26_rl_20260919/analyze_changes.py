"""仅分析已冻结公开快照；保留缺失，不把相关性写成因果关系。"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / "mimo_v26_rl_20260917" / "snapshots" / "20260917T022438Z"
NEW = ROOT / "snapshots" / "20260919T051100Z"
RUNS = ("pro", "flash")
load = lambda p: json.loads(p.read_text())
data = {r: load(NEW / f"{r}_series_merged.json") for r in RUNS}
old = {r: load(OLD / f"{r}_series_merged.json") for r in RUNS}
status = {r: load(NEW / f"{r}_status_before.json") for r in RUNS}
old_status = {r: load(OLD / f"{r}_status_before.json") for r in RUNS}
bench = load(NEW / "benchmarks.json")["benchmarks"]
old_bench = load(OLD / "benchmarks.json")["benchmarks"]
tags = sorted(set().union(*(d["series"] for d in data.values())))
tick = chr(96)

def fmt(x):
    return "—" if x is None else f"{x:.8g}"

def at(r, tag, step=None, dataset=None):
    d = (dataset or data)[r]
    arr = d["series"].get(tag)
    if arr is None:
        return None
    i = -1 if step is None else d["steps"].index(step)
    return arr[i]

def stats(d, t):
    vals = [(s, v) for s, v in zip(d["steps"], d["series"].get(t, [])) if v is not None]
    if not vals:
        return {"current": None, "observations": 0}
    return {
        "current": d["series"][t][-1], "observations": len(vals),
        "first_step": vals[0][0], "first": vals[0][1],
        "last_step": vals[-1][0], "last": vals[-1][1],
        "min": min(v for _, v in vals), "max": max(v for _, v in vals),
    }

all_stats = {t: {r: {"old": stats(old[r], t), "new": stats(data[r], t)} for r in RUNS} for t in tags}
(ROOT / "metrics_comparison.json").write_text(json.dumps(all_stats, ensure_ascii=False, indent=2) + "\n")
lines = [
    "# 全部公开指标：09-17 与 09-19 对照", "",
    "旧快照 09-17 02:24 UTC：Pro s12 / Flash s15；新快照 09-19 05:11 UTC：Pro s23 / Flash s30。",
    "每列取对应已完成末步；缺失不填零、不拿历史最后值冒充末步。不是同预算或同分布消融。", "",
]
for prefix, count in sorted(Counter(t.split("/")[0] for t in tags).items()):
    lines += [f"## {prefix} · {count}", "", "| 指标 | Pro s12 | Pro s23 | Flash s15 | Flash s30 |", "| --- | ---: | ---: | ---: | ---: |"]
    for t in tags:
        if t.split("/")[0] != prefix:
            continue
        vals = [at("pro", t, dataset=old), at("pro", t), at("flash", t, dataset=old), at("flash", t)]
        lines.append(f"| {tick}{t}{tick} | " + " | ".join(fmt(v) for v in vals) + " |")
    lines.append("")
(ROOT / "metric_changes.md").write_text("\n".join(lines) + "\n")

revisions = {}
new_tags = {}
events = {}
for r in RUNS:
    differences = []
    for t in set(old[r]["series"]) & set(data[r]["series"]):
        for i, step in enumerate(old[r]["steps"]):
            new_i = data[r]["steps"].index(step)
            if old[r]["series"][t][i] != data[r]["series"][t][new_i]:
                differences.append({"tag": t, "step": step})
    revisions[r] = differences
    new_tags[r] = sorted(set(data[r]["series"]) - set(old[r]["series"]))
    dedup = {}
    for st in (old_status[r], status[r]):
        for e in st["events"]:
            dedup[(e["t"], e["kind"], e.get("step"))] = e
    events[r] = sorted(dedup.values(), key=lambda e: e["t"])
(ROOT / "events_merged.json").write_text(json.dumps(events, indent=2) + "\n")

# 按前端算法估计来源构成；重启后的比例分摊必须保留标签。
sources = sorted({"/".join(t.split("/")[1:3]) for t in tags if re.match(r"^dynsam/[^/]+/dataset-[^/]+/num_accepted/step$", t)})
def composition(r, idx):
    d = data[r]
    def get(ds, k, i):
        arr = d["series"].get(f"dynsam/{ds}/num_accepted/{k}", [])
        return (arr[i] or 0) if 0 <= i < len(arr) else 0
    batch = d["series"]["dynsam/num_target"][idx]
    values = {ds: max(0, get(ds, "held", idx-1)+get(ds, "step", idx)-get(ds, "held", idx)) for ds in sources}
    fallback = not (idx > 0 and abs(sum(values.values()) - batch) <= .05*batch)
    if fallback:
        fresh = max(0, batch-sum(get(ds, "carryover", idx) for ds in sources))
        accepts = sum(get(ds, "step", idx) for ds in sources) or 1
        values = {ds: get(ds, "carryover", idx)+get(ds, "step", idx)*fresh/accepts for ds in sources}
    return {"step": d["steps"][idx], "fallback": fallback, "sum": sum(values.values()), "sources": values,
            "categories": {c: sum(v for k, v in values.items() if k.startswith(c+"/")) for c in ("code","general","cyber","visual","chat")}}
mix = {r: [composition(r, i) for i in range(len(data[r]["steps"]))] for r in RUNS}
(ROOT / "composition_derived.json").write_text(json.dumps(mix, indent=2) + "\n")

rows = ["# 逐步训练、离线评测与事件", "",
        "cost 是公开固定费率乘运行起点以来时长，不是审计账单。空评测点保留为空，绝不前值填充。", ""]
summary = {"historical_metric_revisions": revisions, "new_tags": new_tags, "run_summary": {}, "benchmark_summary": []}
for r in RUNS:
    d, st = data[r], status[r]
    latest_old = old[r]["steps"][-1]
    rs = {
        "old_last_step": latest_old, "new_last_step": d["steps"][-1],
        "old_cost": old_status[r]["cost"]["so_far"], "new_cost": st["cost"]["so_far"],
        "old_tokens": old_status[r]["totals"]["tokens_cum"], "new_tokens": st["totals"]["tokens_cum"],
        "old_restarts": old_status[r]["totals"]["restarts"], "new_restarts": st["totals"]["restarts"],
        "latest_mix": mix[r][-1],
        "response_growth_sources": sum(at(r,f"ctx_response_length/{ds}/mean") is not None and at(r,f"ctx_response_length/{ds}/mean",dataset=old) is not None and at(r,f"ctx_response_length/{ds}/mean") > at(r,f"ctx_response_length/{ds}/mean",dataset=old) for ds in sources),
        "comparable_response_sources": sum(at(r,f"ctx_response_length/{ds}/mean") is not None and at(r,f"ctx_response_length/{ds}/mean",dataset=old) is not None for ds in sources),
        "last_step_mixed_groups_share": 1-at(r,"dynsam/passrate/zero")-at(r,"dynsam/passrate/one"),
    }
    # 相邻已完成步 wall 间隔和报告 step duration 的差额；不命名为纯宕机时间。
    gaps = []
    for i in range(1, len(d["steps"])):
        gap = d["walls"][i]-d["walls"][i-1]-d["series"]["timing_s/step"][i]
        if gap > 60:
            gaps.append({"step":d["steps"][i],"gap_hours":gap/3600,
                         "restarts_between":sum(d["walls"][i-1] < e["t"] <= d["walls"][i] and e["kind"]=="restart" for e in events[r])})
    rs["wall_gaps_beyond_reported_step"] = gaps
    summary["run_summary"][r] = rs
    rows += [f"## {r}", "", "| step | 完成 UTC | 起跑后 h | 费用口径 USD | tokens B | step min | trainer min | rollout min | avg@n | trained reward | lag | DeepSWE | In-house | Automation |",
             "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for i, step in enumerate(d["steps"]):
        wall = d["walls"][i]; elapsed=wall-st["run"]["start"]
        vals = [step,datetime.fromtimestamp(wall,timezone.utc).strftime("%m-%d %H:%M:%S"),
                round(elapsed/3600,3),round(elapsed*st["cost"]["rate_per_s"]),
                at(r,"perf/total_num_tokens",step)/1e9,at(r,"timing_s/step",step)/60,
                at(r,"timing_s/trainer_ops",step)/60,at(r,"timing_s/outer_gen",step)/60,
                at(r,"dynsam/avg@n",step),at(r,"critic/rewards/mean",step),at(r,"partial/avg_staleness",step)]
        vals += [b["results"].get(r,{}).get(str(step)) for b in bench]
        rows.append("| " + " | ".join(v if isinstance(v,str) else fmt(v) for v in vals) + " |")
    rows += ["", "重启/终止事件（合并两次快照的事件窗口）：", ""]
    for e in events[r]:
        if e["kind"] != "step":
            rows.append(f"- {datetime.fromtimestamp(e['t'],timezone.utc).isoformat()} · {e['kind']}")
    rows += [""]
(ROOT / "step_history.md").write_text("\n".join(rows)+"\n")

for b in bench:
    for r in RUNS:
        items = sorted((int(k), v) for k,v in b["results"].get(r,{}).items())
        ob = next((bb for bb in old_bench if bb["key"]==b["key"]), None)
        oitems = sorted((int(k), v) for k,v in ob["results"].get(r,{}).items()) if ob else []
        common_old = b["results"].get(r,{}).get(str(old[r]["steps"][-1]))
        summary["benchmark_summary"].append({"benchmark":b["key"],"run":r,"first":items[0],"latest":items[-1],
            "previously_published_latest":oitems[-1] if oitems else None,"old_training_endpoint_now_evaluated":common_old,
            "best":max(items,key=lambda x:x[1]),"point_count":len(items)})
(ROOT / "comparison_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n")

# 保留匿名来源的同口径对照；harness 的缺失不能像网页表格那样用历史末值补齐。
rows = ["# 来源、harness 与观测口径", "",
        "旧：Pro s12 / Flash s15；新：Pro s23 / Flash s30。缺失不前值填充；匿名 ID 不推定实际数据集或产品。", "",
        "## 各来源平均 response 长度", "",
        "| 来源 | Pro 旧 | Pro 新 | Flash 旧 | Flash 新 |", "| --- | ---: | ---: | ---: | ---: |"]
for ds in sources:
    t = f"ctx_response_length/{ds}/mean"
    rows.append(f"| {ds} | " + " | ".join(fmt(v) for v in [at("pro",t,dataset=old),at("pro",t),at("flash",t,dataset=old),at("flash",t)]) + " |")
rows += ["", "## 当前 step 的 harness rollouts 与非零 advantage 比率", "",
         "rollouts 的求和不是 25,088；公开资料未解释两个统计分母的差异，不擅自认定是过滤率。",
         "网页 Pro s23 表格中的 harness-R=1,022 是 s14 的最后一次记录；s15–23 缺失。表格由 lastOf 聚合，柱图则把空值视为 0，二者不能混读。", "",
         "| harness | Pro rollouts | Pro 非零 ADV | Flash rollouts | Flash 非零 ADV |", "| --- | ---: | ---: | ---: | ---: |"]
harnesses = sorted({t.split('/')[2] for t in tags if t.startswith('train/harness/')})
for h in harnesses:
    base = f"train/harness/{h}/training/"
    vals=[at(r,base+k) for r in RUNS for k in ['rollouts','nonzero_adv_rate']]
    rows.append(f"| {h} | " + " | ".join(fmt(v) for v in vals) + " |")
rows += ["", "## 最新数据源构成（复算网页近似算法）", "",
         "| 类别 | Pro s23（重启后按比例近似） | Flash s30（池计数推导） |", "| --- | ---: | ---: |"]
for c in ['code','general','cyber','visual','chat']:
    rows.append(f"| {c} | " + " | ".join(f"{100*mix[r][-1]['categories'][c]/mix[r][-1]['sum']:.3f}%" for r in RUNS) + " |")
(ROOT / "source_and_harness_changes.md").write_text("\n".join(rows)+"\n")

# 静态科研图；图中缺失值为 NaN，不平滑、不插值，不把旧 checkpoint 值当成当前评测。
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.alpha":.18})
colors={"pro":"#cc6234","flash":"#2674bf"}
(ROOT/"figures").mkdir(exist_ok=True)
def draw(ax, r, tag, scale=1, label=None):
    y=[np.nan if v is None else v*scale for v in data[r]["series"].get(tag,[])]
    ax.plot(data[r]["steps"],y,".-",color=colors[r],label=label or r.title(),linewidth=1.5,markersize=5)
def save(fig,name):
    fig.savefig(ROOT/"figures"/name,dpi=170,bbox_inches="tight")
    plt.close(fig)

fig,axs=plt.subplots(1,3,figsize=(15,4.4),layout="constrained")
for ax,b in zip(axs,bench):
    for r in RUNS:
        items=sorted((int(k),v) for k,v in b["results"][r].items())
        ax.plot([x for x,y in items],[y for x,y in items],".-",color=colors[r],label=r.title())
        x,y=items[-1];ax.annotate(f"{y:.2f} (s{x})",(x,y),xytext=(4,4),textcoords="offset points",fontsize=8)
    ax.set(title=b["title"],xlabel="Evaluated checkpoint step",ylabel="avg@3 score")
    ax.legend(frameon=False)
fig.suptitle("MiMo-V2.6 | published evaluation coverage, 19 Sep 2026 05:11 UTC",fontsize=14)
fig.supxlabel("Training reached Pro s23 / Flash s30. Evaluation lags; the curves are not matched-budget comparisons.",fontsize=9)
save(fig,"benchmarks.png")

fig,axs=plt.subplots(2,3,figsize=(15,8),layout="constrained")
specs=[("ctx_response_length/mean",.001,"Response length","k tokens / trajectory"),
       ("timing_s/trainer_ops",1/60,"Trainer wall time","minutes / step"),
       ("timing_s/step",1/60,"Whole reported step","minutes / step"),
       ("actor/entropy_loss",1,"Policy entropy","reported mean per-token entropy"),
       ("dynsam/passrate/one",100,"All-success prompt groups","% of measured prompts"),
       ("penalty/stage_credit_group/time_total_sec_max",1/60,"Grader longest group","minutes")]
for ax,(tag,scale,title,ylabel) in zip(axs.flat,specs):
    for r in RUNS:draw(ax,r,tag,scale)
    ax.set(title=title,xlabel="Published step",ylabel=ylabel);ax.legend(frameon=False)
fig.suptitle("Workload grows during the RL run | no smoothing",fontsize=14)
save(fig,"workload_and_system.png")

fig,axs=plt.subplots(2,3,figsize=(15,8),layout="constrained")
for r in RUNS:draw(axs[0,0],r,"partial/avg_staleness")
axs[0,0].set(title="Average policy lag",ylabel="versions",xlabel="Published step")
for r in RUNS:draw(axs[0,1],r,"train_infer_diff/new_infer/kl")
axs[0,1].set(title="Aggregate inference / trainer KL",xlabel="Published step")
for r in RUNS:draw(axs[0,2],r,"partial/0/train_infer_diff/new_infer/kl")
axs[0,2].set(title="Same-version (lag 0) KL",xlabel="Published step")
x=np.arange(3)
for step,off,c in [(22,-.18,"#dca68e"),(23,.18,colors["pro"])]:
    axs[1,0].bar(x+off,[100*at("pro",f"partial/{i}/frac",step) for i in x],.34,label=f"Pro s{step}",color=c)
    axs[1,1].plot(x,[at("pro",f"partial/{i}/train_infer_diff/new_infer/kl",step) for i in x],".-",label=f"Pro s{step}",color=c)
axs[1,0].set(title="Pro: composition changed after restarts",ylabel="logged frac (%)",xlabel="Lag bucket",xticks=x)
axs[1,1].set(title="Pro: each shown bucket KL increased",xlabel="Lag bucket",xticks=x)
for r in RUNS:draw(axs[1,2],r,"penalty/signed/neg_hit_tokens",1e-6)
axs[1,2].set(title="Signed penalty: negative hit tokens",ylabel="million tokens",xlabel="Published step")
for ax in axs.flat:ax.legend(frameon=False)
fig.suptitle("Aggregate metrics can hide a different conditional trend",fontsize=14)
fig.supxlabel("Pro s22 -> s23 is separated by restarts. Signed penalty fields do not establish a cause or stop reason.",fontsize=9)
save(fig,"lag_and_penalty.png")

checks={}
for mf,base in [(NEW/"manifest.json",NEW),(ROOT/"source_manifest.json",ROOT)]:
    for entry in load(mf):
        p=base/entry["file"]
        assert hashlib.sha256(p.read_bytes()).hexdigest()==entry["sha256"],p
checks["hashes_verified"]=sum(len(load(p)) for p in (NEW/"manifest.json",ROOT/"source_manifest.json"))
checks["tag_union"]=len(tags)
checks["tag_counts"]={r:len(data[r]["series"]) for r in RUNS}
checks["non_null_points"]={r:sum(v is not None for arr in data[r]["series"].values() for v in arr) for r in RUNS}
checks["historical_common_metric_revisions"]={r:len(revisions[r]) for r in RUNS}
checks["stable_capture"]={}
checks["shape_and_tag_checks"]={}
for r in RUNS:
    checks["stable_capture"][r]=status[r]["version"]==load(NEW/f"{r}_status_after.json")["version"]
    checks["shape_and_tag_checks"][r]=(set(data[r]["series"])==set(load(NEW/f"{r}_tags.json")["tags"]) and all(len(a)==len(data[r]["steps"]) for a in data[r]["series"].values()))
    assert checks["stable_capture"][r] and checks["shape_and_tag_checks"][r]
checks["critic_returns_equal_advantages"]={r:all(v==data[r]["series"][k.replace("/returns/","/advantages/")] for k,v in data[r]["series"].items() if k.startswith("critic/") and "/returns/" in k) for r in RUNS}
checks["critic_rewards_equal_scores"]={r:all(v==data[r]["series"][k.replace("/rewards/","/score/")] for k,v in data[r]["series"].items() if k.startswith("critic/") and "/rewards/" in k) for r in RUNS}
checks["verified_utc"]=datetime.now(timezone.utc).isoformat()
(ROOT/"verification.json").write_text(json.dumps(checks,indent=2)+"\n")
print(json.dumps({"checks":checks,"run_summary":summary["run_summary"],"benchmarks":summary["benchmark_summary"]},ensure_ascii=False,indent=2))
