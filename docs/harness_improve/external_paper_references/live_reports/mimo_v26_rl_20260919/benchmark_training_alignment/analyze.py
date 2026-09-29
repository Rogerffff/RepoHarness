"""对齐已有冻结快照，不刷新 live 数据，不把同 step 当作同一行为策略。"""
from pathlib import Path
import hashlib
import json
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SNAP = ROOT.parent / "snapshots" / "20260919T051100Z"
load = lambda p: json.loads(p.read_text())
data = {r: load(SNAP / f"{r}_series_merged.json") for r in ("pro", "flash")}
benchmarks = load(SNAP / "benchmarks.json")["benchmarks"]
steps = list(range(16, 26))

def value(run, tag, step):
    d = data[run]
    return d["series"][tag][d["steps"].index(step)]

def scores(key, run="flash"):
    return next(b for b in benchmarks if b["key"] == key)["results"][run]

metrics = ["dynsam/avg@n", "critic/rewards/mean", "train/passrate/avg_passrate",
           "ctx_response_length/mean", "dynsam/agg_turn/mean", "partial/avg_staleness",
           "train_infer_diff/new_infer/kl", "actor/entropy_loss", "actor/pg_loss",
           "actor/grad_norm", "actor/pg_tis_clipfrac", "penalty/signed/neg_hit_tokens",
           "penalty/signed/neg_mass_added", "penalty/signed/neg_scale",
           "penalty/stage_credit_group/select_hack_attempt_rate",
           "penalty/stage_credit_group/end2end_success_rate", "dynsam/infra_error/seq_rate",
           "ctx_total_length/clip_ratio", "dynsam/passrate/one", "dynsam/passrate/zero"]
rows = [{"step": step,
         **{b["key"]: b["results"]["flash"][str(step)] for b in benchmarks},
         **{tag: value("flash", tag, step) for tag in metrics}} for step in steps]
drops = []
for prev, current in zip(rows, rows[1:]):
    if current["deepswe"] < prev["deepswe"]:
        code = [t for t in data["flash"]["series"] if t.startswith("critic/code/") and t.endswith("/rewards/mean")]
        drops.append({"from": prev["step"], "to": current["step"],
                      "delta": {k: current[k]-prev[k] for k in current if k != "step"},
                      "code_source_reward_up": sum(value("flash",t,current["step"]) > value("flash",t,prev["step"]) for t in code),
                      "code_source_count": len(code)})
summary = {}
for key in [b["key"] for b in benchmarks]+metrics[:3]:
    deltas = [b[key]-a[key] for a,b in zip(rows,rows[1:])]
    summary[key] = {"first": rows[0][key], "last": rows[-1][key],
                    "net_change": rows[-1][key]-rows[0][key],
                    "decreases": sum(v < 0 for v in deltas),
                    "mean_absolute_adjacent_change": statistics.mean(abs(v) for v in deltas),
                    "adjacent_pairs": len(deltas)}
assert [x["to"] for x in drops] == [17,19,21,23,25]
assert all(x["delta"]["dynsam/avg@n"] > 0 for x in drops)
assert sum(x["delta"]["critic/rewards/mean"] > 0 for x in drops) == 2
assert drops[0]["code_source_reward_up"] == 9
assert summary["critic/rewards/mean"]["decreases"] == 6
result = {"snapshot": SNAP.name, "window": steps, "summary": summary, "deepswe_declines": drops, "all_aligned_rows": rows,
          "input_sha256": {name: hashlib.sha256((SNAP/name).read_bytes()).hexdigest() for name in ["benchmarks.json","flash_series_merged.json","pro_series_merged.json"]},
          "limits": ["Descriptive adjacent changes, not an estimate of evaluation noise.",
                     "Same logged step does not imply the same behavior policy or task distribution.",
                     "No lagged-correlation search or statistical significance claim."]}
(ROOT / "aligned_metrics.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")

lines = ["# Flash s16–25 完整对齐数值", "", "冻结快照：09-19 05:11 UTC。每表均按日志 step，非因果对齐。", ""]
for keys in [[b["key"] for b in benchmarks]+metrics[:3], metrics[3:10],metrics[10:]]:
    lines += ["| step | "+" | ".join(keys)+" |", "| ---: | "+" | ".join("---:" for _ in keys)+" |"]
    for row in rows:
        lines.append("| "+str(row["step"])+" | "+" | ".join(f"{row[k]:.8g}" for k in keys)+" |")
    lines.append("")
(ROOT / "all_aligned_values.md").write_text("\n".join(lines)+"\n")

plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":9,"axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.alpha":.2})
fig,axs=plt.subplots(3,2,figsize=(13.5,10.5),layout="constrained")
colors=["#2674bf","#cc6234","#409177"]
for b,c in zip(benchmarks,colors):
    vals=[row[b["key"]] for row in rows]
    axs[0,0].plot(steps,[v-vals[0] for v in vals],".-",color=c,label=b["title"])
axs[0,0].set(title="Evaluation change from s16",ylabel="score points relative to s16")
for t,label,c in zip(metrics[:3],["Sampler avg@n","Trained reward","Train/passrate field"],colors):
    axs[0,1].plot(steps,[row[t] for row in rows],".-",label=label,color=c)
axs[0,1].set(title="Training-side means also fluctuate",ylabel="raw values; different populations / definitions")
specs=[(axs[1,0],"train_infer_diff/new_infer/kl",1,"Inference / trainer KL","reported KL"),
       (axs[1,1],"partial/avg_staleness",1,"Average policy lag","versions"),
       (axs[2,0],"ctx_response_length/mean",.001,"Response length","k tokens / trajectory"),
       (axs[2,1],"penalty/signed/neg_hit_tokens",1e-6,"Negative penalty hit tokens","million tokens")]
for ax,key,scale,title,ylabel in specs:
    ax.plot(steps,[row[key]*scale for row in rows],".-",color=colors[0])
    ax.set(title=title,ylabel=ylabel)
for ax in axs.flat:
    for d in drops: ax.axvspan(d["to"]-.17,d["to"]+.17,color="#ba4550",alpha=.10,lw=0)
    ax.axvline(24.5,color="#555555",linestyle="--",linewidth=1)
    ax.set(xlabel="Logged / evaluated step",xticks=steps)
axs[0,0].legend(frameon=False,fontsize=8,loc="lower right")
axs[0,1].legend(frameon=False,fontsize=8,loc="upper left")
fig.suptitle("Flash s16–25 | benchmark swings and training-side signals",fontsize=15)
fig.supxlabel("Red bands: DeepSWE fell vs the previous step. Dashed line: restart interval. No smoothing; co-movement is not causation.",fontsize=9)
fig.savefig(ROOT/"aligned_flash_s16_s25.png",dpi=170,bbox_inches="tight")
plt.close(fig)
print(json.dumps({"summary":summary,"decline_steps":[d['to'] for d in drops],"checks":"passed"},ensure_ascii=False,indent=2))
