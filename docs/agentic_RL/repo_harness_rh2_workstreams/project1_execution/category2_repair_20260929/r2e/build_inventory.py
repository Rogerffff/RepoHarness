"""只读汇总既有 R2E 本地证据；输出本目录，不运行题目。"""
from pathlib import Path
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
EX = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
LC = EX / "r2e_lifecycle_20260929"
RUN = ROOT / "runs/r2e_lifecycle_20260929"


def sha(p):
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p):
    return str(p.relative_to(ROOT))


def ref(p):
    return {"path": rel(p), "sha256": sha(p)}


# 人工结论与可复算事实分开；以下矩阵是尚待验收的目标，不冒充实测。
SPEC = {
"aiohttp__1c1c0ea3": (5, "coverage_repair", "明确：将既有 cleanup 错误后检变为正式行为断言，允许抛出或报告任一合理路线。", ["C3 取消后 gather(return_exceptions=True) 会吞掉 cleanup 错误，v5 仍得 1；旧 S2/后检不能豁免。"], ["题级 R-c 版本落地"], "gold=1、C1=1、C3=0；noop/F1/C5 仍=0。核 cleanup 错误可观察且既有关闭顺序不退化。", "formal_v5", "v5"),
"aiohttp__61833518": (9, "public_and_dev_repair", "明确：中性改正 all(write.mock_calls) 恒真复现，给出已验证的有效断言；恢复目标相关客户端/服务端兼容或交付等效公开路径。", ["旧题面复现断言恒真；真实 client/server 的 asyncio 兼容改写导致 TypeError。", "公开 protocol 层已可验证核心目标，需明确它能覆盖所声明的目标，不以无关 cookie 旧测全过为条件。"], ["R-f 公开材料与 R-d/等效开发路径版本", "相关开发兼容范围核定"], "gold/AP2/A1=1；noop/AP1/AP1m=0。最终公开复现由 agent 执行，压缩与 chunked 分帧、解压载荷及 EOF 均核对。", "formal_v5", "v5"),
"coveragepy__ea6906b0": (6, "coverage_and_acceptance_repair", "明确：补已有 .gitignore 内容保留与实际忽略效果；核 open 替身接受 encoding 的合理写法。", ["gold 无条件覆盖用户已有 .gitignore。", "C-C 添加 encoding 后因公开测试替身签名得 0；不能仅以公开测试同样失败认定无误拒。"], ["题级 R-b/R-c；参考正对照需为安全合并实现"], "安全合并正确解=1、encoding 合理解=1；覆盖已有内容的 gold 类候选=0、空文件 C-B=0、提前写目录 RE=0、noop=0。核已有规则保留与新报告实际被 git 忽略。", "formal_v5", "v5"),
"orange3__22e98f8f": (2, "public_closeout", "明确：采用已通过独立审查的 R-f 草案；公开包已准备。", ["新公开读者未完成；正式 ingest 仍为含答案的旧题面。", "最终实际消息尚未捕获，当前 consumer/准备预算须核对。", "DG 正式评分已完成且为 0，不再是待跑项。"], ["fresh 公开读者", "主线程正式 R-f/pins/ingest 落地与 consumer 核查", "采用已验证 1200 秒准备预算并记录实际生效值"], "复用原材料 noop=0、gold=1、DG=0（DG 20/23，setup 303.30s）。新读者独立读需求；核正式消息 hash 等于修订后 f8701d3a…，不重复不变评分矩阵。", "budget_v5", None),
"orange3__4014f248": (8, "coverage_and_build_repair", "明确：加入已有小量级分割回归，拒绝以 round(p,10) 合并不同值的 C3。", ["C3 v9=1，但 arange(100)*1e-12、n=4 全部落一个区间；属于已知可修行为回归。", "最终入口的 agent 真重编与 pyx_only 配对、准备预算仍需定向验收。"], ["题级 R-c", "最终构建/导出/加载入口", "1200 秒准备预算；源 R2E 机当前不可用"], "gold、C1、pyx_build=1；C3、DG、C4、pyx_only、noop=0。核小量级有有效分割；agent 改 .pyx 后真重编、导出二进制并由新 grader 加载。", "formal_v9", "v9"),
"orange3__9b5494e2": (13, "shared_recipe_dependency", "明确：A+B′ 加 G1 多分类默认模型回归断言，并绑定最终内容的环境配方摘要。", ["旧方案 A/B′ 仍放行 G1（默认 multinomial 改 OvR）。", "当前 environment_overlay.py 批准集合仍仅含旧 512277… 摘要，加入 material 后的配方未获绑定。"], ["主线程/公共实现负责人处理最终配方内容身份", "SciPy 1.5.4 / +env_v2 不可省略"], "gold、V1/V3/V4/V5=1；noop/W1/V7/P1/G1=0；先证 base/gold 的默认与显式 multinomial 行为关系，不能照抄 gold 数值。保留 13 键 expected 精确状态口径。", None, None),
"aiohttp__240da100": (10, "public_and_dead_key_repair", "明确：采用已有 mock 等效公开复现；处置两项兼容死键并验 SC1。", ["题面顶层 ClientRequest 导入无效、真实协程路径 TypeError；部分公开文件不能收集。", "TCP/Unix 两个 expected FAILED 死键需移除或恢复有效的明确方案，不等待候选偶然翻转。"], ["R-f 与 R-a/R-d 版本", "不扩默认端口/Host 等未定范围"], "gold、AL1、SC1=1；noop/DG1/WR1/WR2=0；agent 执行新 mock 复现及相关开发命令，核两死键处置前后精确键集。", "formal_v7", "v7"),
"aiohttp__4075c653": (1, "grading_accepted_public_repair_required", "评分修订独立验收通过；明确仍需改正题面 bytes 插入 f-string 的错误复现。", ["v11 七方、完整日志、136 键映射、替代正对照和 actor 七命令均可收口。", "当前公开题面原例 1 在 base 已抛 InvalidHeader；旧卡所谓可选 R-f 不再适用当前严格口径。", "三个 C 扩展 expected FAILED 键已解释；当前离线纯 Python 路径不会因合理源码修复翻转，不能据其存在要求全 PASS。"], ["窄 R-f、fresh 公开读者和实际题面交付核对", "如以后开放 C 扩展构建路径，先重定 expected/开发范围"], "不重跑 v11 七方。复用 ALT2 主正对照、ALT1 备选；原 gold/noop/DG1=0，ALT1–ALT4=1；新公开复现 base 失败、ALT2 通过并核实际消息。", "codex_status_check_20260929_1020/formal_v11", "codex_status_check_20260929_1020/devcheck_v11"),
"datalad__6b6fa389": (11, "acceptance_repair", "明确：字段直查避开 __eq__、非示例 host:path、合理分类放宽但保留按字段重建原串。", ["C-A 合理解=0，D-eq 绕过解析=1；需独立复核终稿与 R-b/R-c 落地。", "不能以 str(URL(url)) 等于 url 作为重建验收：构造器保存原串会使其恒真。"], ["独立修订审查", "1200 秒准备预算", "新的 material 镜像和 actor 预检"], "gold/C-A=1；noop/C-B/D-eq/D-eq-minus/D-hard=0。gold/noop 各2，其余各1（原计划）；17 键 exact expected，保留已声明 FAILED 键解释。", "budget_v5", "unrev"),
"numpy__d805e9b6": (7, "coverage_and_public_repair", "明确：补 n=3000/threshold=2000 的摘要保值对照；改正 Actual 说明。", ["n>threshold>=1500 的混合截断路线可通过现有断言但静默丢值（目前为静态推导，不冒称已评分）。", "K-A5b 的大 edgeitems>=501 同族丢省略号风险已有具体推导，不能因旧 S2 标签自动豁免；需核影响并用可涵盖声明范围的正对照。", "二维窄轴题外，不并入本题修复。"], ["题级 R-c/R-f", "大 edgeitems 的最小辨别控制与正对照边界"], "至少 K-A5b 在 n=3000,t=2000 应为1，混合截断=0；gold/noop/K-DE/K-DC/K-DF/DG-e/DG-g 保持0。另核 edgeitems 具体反例，必要时窄修正对照，不能先放行再后检。", "formal_v8", "v8"),
"orange3__50f6a758": (12, "acceptance_and_public_repair", "明确：R-b 放宽名单格式、R-c 覆盖加载数据/混合文件/numeric 与已匹配定义仍生效。", ["K1 全列变量名=0，K2/K3/K4 错解=1；独立复核终稿及正式修订矩阵未完成。", "C-deg 补丁存在，本地未找到正式 ledger/私有 probe 结果；不能写已回传。", "TypeError 题面伪影及旧公开不警告断言冲突需要按当前规则处置，不能仅记可选。"], ["独立修订审查", "1200 秒准备预算", "R-f 与公开旧断言冲突的窄处置"], "gold/K1=1；noop/K2/K3/K4/C-deg=0；加不点名 K5=0。核警告实际点名、已匹配定义继续生效、新公开说明与开发路径。", "budget_v5", "unrev"),
"pillow__2d01f7d0": (3, "development_compatibility_closeout", "明确：处置 pytest.warns(None) 开发兼容；复用已完成 v11 九方评分。", ["actor 8命令均执行，但 public_tiff_tests 两个 pytest 8 兼容错误，all_match_expect=false；不能写全过。", "评分修订含 FillOrder 误拒解除已具9方正式证据，尚需完整题级收口审查。"], ["窄 R-d 或公开等效命令", "兼容处理若影响正式 expected，需联动重标版本并定向复验"], "复用 gold/C1/C1FO2=1，noop/D/C3/C2/A/B=0；agent 跑修订后的公开 TIFF 开发路径，base 保持原题失败，正确解修好且相关回归不新增。", "codex_status_check_20260929_1020/formal_v11", "codex_status_check_20260929_1020/devcheck_v11"),
"scrapy__a95a338e": (4, "formal_material_closeout", "明确：采用已完成试跑的第2版，C1 替代 gold，恢复警告两键并覆盖 partial 绑定方法。", ["新版 rev2 9次试跑已齐，重算 observed 与 expected 一致；此前中断摘要已过时。", "最终新版独立复核、正式材料/镜像、正式矩阵仍缺。", "新 setUp 只恢复 UserWarning；其它 warning 类别是否为合理修复相关需按公开要求核，不以改类别属于题外直接豁免。"], ["第2版定向独立审查", "主线程落正式 material/expected 与镜像", "C1 正对照元数据绑定"], "C1×2=1、noop×2=0、gold/D/C2/C2b/C3=0；5键，复活两键 PASSED；完整日志区分 partial 与警告失败原因。试跑不再重复。", None, "unrev"),
}


def main():
    start = EX / "category2_repair_20260929/starting_inventory.json"
    tasks = [t for t in json.loads(start.read_text())["tasks"] if t["source"] == "R2E"]
    grading_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl"
    public_path = grading_path.with_name("public_bundles_v0.jsonl")
    grading = {x["instance_id"]: x for x in map(json.loads, grading_path.read_text().splitlines())}
    public = {x["instance_id"]: x for x in map(json.loads, public_path.read_text().splitlines())}
    doc_refs = {}
    def add(p):
        if p.is_file():
            doc_refs[rel(p)] = sha(p)
    ledger_paths = list(RUN.rglob("ledger_*.jsonl"))
    # 只扫描明确的账本，不读取私有模型会话或其它工作树。
    formal = []
    for p in ledger_paths:
        for lineno, line in enumerate(p.read_text().splitlines(), 1):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("instance_id") not in {x["instance_id"] for x in tasks}:
                continue
            formal.append((p, lineno, d))
    records = []
    for t in tasks:
        iid, key = t["instance_id"], t["short_name"]
        priority, status, repair, remains, deps, matrix, run_sub, dev_sub = SPEC[key]
        result = LC / "results" / iid
        sources = []
        for p in result.glob("*.md"):
            if p.name in {"card.md", "probe_card.md", "revision_plan.md", "review.md", "reviewer_initial.md", "public_read.md"}:
                add(p); sources.append(rel(p))
        for n in ["revision_draft.json", "screening_record.json"]:
            p = result / n
            if p.exists(): add(p); sources.append(rel(p))
        rows = []
        seen_log = set()
        if run_sub:
            for p, lineno, d in formal:
                if d["instance_id"] != iid or run_sub not in str(p): continue
                log_id = d.get("log", {}).get("sha256")
                if log_id in seen_log:
                    continue
                seen_log.add(log_id)
                report, vd = d.get("report", {}), d.get("verdict_diagnostics", {}).get("expected_match", {})
                rows.append({"ledger":rel(p), "line":lineno, "candidate_patch_sha256": d.get("candidate", {}).get("patch_sha256"), "origin":Path(d.get("candidate", {}).get("origin", "")).name, "reward":report.get("reward"), "expected_match":report.get("expected_match"), "expected_total":report.get("expected_total"), "keys_equal":vd.get("keys_equal"), "mismatched":vd.get("mismatched"), "image_id":d.get("image_id_actual"), "recipe":d.get("overlay"), "log_sha256":d.get("log", {}).get("sha256"), "test_complete":d.get("test", {}).get("segment_completed"), "cleanup_removed":d.get("cleanup", {}).get("removed"), "started_at_utc":d.get("started_at_utc")})
                add(p)
        dev = []
        if dev_sub:
            db = RUN/dev_sub if "/" in dev_sub else RUN/"devcheck_rev"/dev_sub
            for p in db.glob(iid+"/orig/attempt.json"):
                d=json.loads(p.read_text()); add(p)
                dev.append({"source":rel(p),"image":d.get("image"),"checks":d.get("checks"),"commands":[{k:x.get(k) for k in ["id","rc","expect","matches_expect"]} for x in d.get("commands_result",[])],"cleanup":d.get("cleanup")})
        g=grading[iid]
        records.append({"instance_id":iid,"short_name":key,"source":"R2E","starting_category":2,"proposed_category":2,"priority":priority,"status":status,"repair_direction":repair,"remaining":remains,"dependencies":deps,"minimum_acceptance_matrix_expected_not_run":matrix,"material_current":{"material_revisions":g.get("material_revisions"),"hidden_tests_tree_sha256":g.get("hidden_tests_tree_sha256"),"expected_output_sha256":g.get("expected_output_json_sha256"),"expected_count":len(json.loads(g["expected_output_json"])),"expected_nonpass":{k:v for k,v in json.loads(g["expected_output_json"]).items() if v!="PASSED"},"statement_sha256":public[iid].get("problem_statement_sha256")},"sources":sources,"existing_formal_rows":rows,"existing_devcheck":dev,"verification_scope":"本轮读取当前卡/修订/独立意见并结构化核对既有账本和开发记录；除4075专项与scrapy rev2外，不声称完整独立重验所有原件。"})
    # aiohttp4075：直接从完整 eval log 的逐测试输出重算，而不是采用卡片结论。
    iid=next(x["instance_id"] for x in tasks if x["short_name"]=="aiohttp__4075c653")
    expected=json.loads(grading[iid]["expected_output_json"])
    base=RUN/"codex_status_check_20260929_1020/formal_v11"
    recomputed=[]
    for p,lineno,d in formal:
        if p.parent!=base or d["instance_id"]!=iid: continue
        log=base/Path(d["log"]["path"]).parent.name/Path(d["log"]["path"]).name
        text=log.read_text(); observed={}
        for line in text.splitlines():
            m=re.match(r"r2e_tests/[^:]+::(.+?)\s+(PASSED|FAILED|ERROR)\s+(?:\[|$)",line)
            if m: observed[m.group(1).replace("::", ".")]=m.group(2)
        mismatch=[k for k in expected if observed.get(k)!=expected[k]]
        assert set(observed)==set(expected), (p,len(observed),len(expected))
        assert len(expected)-len(mismatch)==d["report"]["expected_match"]
        assert sha(log)==d["log"]["sha256"]
        assert "RH2_TS_TEST_END=" in text and "RH2_TEST_RC=1" in text
        assert f"RH2_SETUP_HIDDEN_TESTS_TREE={grading[iid]['hidden_tests_tree_sha256'].split(':')[-1]}" in text
        add(log)
        recomputed.append({"ledger":rel(p),"log":rel(log),"log_sha256":sha(log),"observed_count":len(observed),"match_count":len(expected)-len(mismatch),"mismatched":mismatch,"reward":d["report"]["reward"],"test_rc":1,"test_complete":True,"cleanup_removed":d["cleanup"]["removed"]})
    assert len(recomputed)==7
    # scrapy 最新草案与输入、observed 逐键核对。
    sid=next(x["instance_id"] for x in tasks if x["short_name"]=="scrapy__a95a338e")
    rd=LC/"results"/sid; draft=json.loads((rd/"revision_draft.json").read_text())
    old=(ROOT/"runs/r2e_static_prep_20260924/v3/private"/sid/"hidden_tests/test_1.py").read_text()
    for edit in draft["revisions"][0]["edits"]:
        assert old.count(edit["old"])==1
        old=old.replace(edit["old"],edit["new"])
    reconstructed="sha256:"+hashlib.sha256(old.encode()).hexdigest()
    assert reconstructed==draft["revised_hidden_test_sha256"]
    trials=[]
    for p in sorted((rd/"trials").glob("rev2_*.json")):
        d=json.loads(p.read_text()); obs=d["observed"]; exp=draft["expected_after"]
        assert set(obs)==set(exp)
        mismatched=[k for k,v in exp.items() if obs[k]!=v]
        assert (not mismatched)==d["match"]
        add(p); trials.append({"path":rel(p),"sha256":sha(p),"mismatched":mismatched,"match":not mismatched})
    assert len(trials)==9
    add(start);add(grading_path);add(public_path)
    aio=LC/"results"/iid
    for p in (aio/"cands").glob("*.patch"):add(p)
    for name in ["pcheck_public_ALT1.json", "pcheck_public_ALT2.json", "pcheck_cext_agent.json"]:
        add(RUN/"inv/aiohttp_4075"/name)
    for p in (RUN/"codex_status_check_20260929_1020/devcheck_v11"/iid/"orig/captures").glob("*.out"):add(p)
    add(RUN/"codex_status_check_20260929_1020/devcheck_v11"/iid/"private_control.json")
    add(ROOT/"runs/r2e_static_prep_20260924/v3/public"/iid/"user_prompt.txt")
    for sub in ["orange3_22e9", "datalad_6b6f", "orange3_50f6"]:
        for p in (RUN/"inv"/sub).glob("ledger*.jsonl"):add(p)
    for p in (RUN/"inv/orange3_22e9/logs_DG").glob("*.eval.log"):add(p)
    for name in ["manifest.json", "environment_brief.md", "user_prompt.txt"]:
        add(ROOT/"runs/category2_repair_20260929/r2e/orange3_22e98_public_v1"/name)
    add(ROOT/"rh2/src/repoharness2/envpack/environment_overlay.py")
    for p in (LC/"codex_reviews").glob("review_revision*.md"):add(p)
    data={"schema":"category2.r2e.local_inventory.v1","as_of":"2026-09-29","scope":"starting_inventory source=R2E 的13题；不领取第1/3类。无新SSH、容器、模型或题目运行。","source_inventory":ref(start),"all_remain_category2":True,"tasks":sorted(records,key=lambda x:x["priority"]),"aiohttp4075_log_recomputation":recomputed,"scrapy_rev2_reconstructed_test_sha256":reconstructed,"scrapy_rev2_observed_checks":trials,"source_hashes":doc_refs}
    (OUT/"r2e_inventory.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    md=["# R2E 13题：本地证据续接清单", "", "整理：2026-09-29。**本轮不直接转类**：4075 评分修订可验收，但公开复现仍需窄修；22e98 待 fresh 公开阅读与正式交付；其余按已知缺口继续。旧 probe_ready、S2 标签和后检许可均不作为豁免。", "", "本轮未 SSH、未启动容器、未运行模型；现有 R2E 机器连接已由主线程确认不可用。下列矩阵是待验收目标，已有运行事实另列。全部来源 SHA256、当前材料身份、选定正式账本与 actor 开发结果见 [JSON](r2e_inventory.json)。常规题基于既有独立意见和当前作者卡续接，不冒称 fresh 初审；4075 的完整日志专项重算与 scrapy rev2 的 observed 重算已单列。", "", "| 次序 | 题目 | 当前需完成 |", "|---|---|---|"]
    for r in sorted(records,key=lambda x:x["priority"]):md.append(f"| {r['priority']} | {r['short_name']} | {r['repair_direction']} |")
    for r in sorted(records,key=lambda x:x["priority"]):
        md.extend(["",f"## {r['priority']}. {r['short_name']}","",r["repair_direction"],"",*["- "+x for x in r["remaining"]],"", "**依赖：**"+"；".join(r["dependencies"])+"。","", "**最小验收矩阵（预期）：**"+r["minimum_acceptance_matrix_expected_not_run"],"", "**当前材料：**修订 "+str(r["material_current"]["material_revisions"])+"；expected "+str(r["material_current"]["expected_count"])+" 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。", "", "**原件：**"+"；".join(f"[{Path(x).name}]({os.path.relpath(ROOT/x,OUT)})" for x in r["sources"] if Path(x).name in {"probe_card.md","card.md","revision_plan.md","review.md"})])
    md.extend(["", "## 首批执行建议", "", "1. 先派 22e98 fresh 公开读者；包与提示已就绪，主线程接管正式 R-f 落地和实际消息核对。DG 已正式为0，不重复评分。", "2. 4075 采用 [专项结论](aiohttp4075_acceptance.md) 收掉 v11 评分验收；只对错误公开复现做 R-f 与交付验证。C 扩展死键不得等同为必须全 PASS。", "3. Pillow 2d01 只补公开开发兼容的窄验证，复用 v11 九方；Scrapy a95a 先定向复核第2版后跑正式矩阵，复用9次试跑。", "4. 第一批需新 CPU 运行的题优先 1c1 cleanup、coverage 已有 .gitignore、numpy 自定义阈值。所有远端运行由主线程唯一调度，先核可迁移镜像与 consumer，再启动容器。", "5. orange3 9b54 等待共用配方身份支持；不得绕过摘要检查。公共控制面、网络/捕获/停止与清理、代码版本、模型与预算是共用前提，不在这13份题卡中重复授予。", "", "这里只给普通探针前的题级续接建议；不授予训练/留出资格，跨题答案关联与仓库划分沿用已有登记。历史评分与题卡未覆盖，未改生产源码或共享看板。", ""])
    (OUT/"r2e_inventory.md").write_text("\n".join(md))
    print(json.dumps({"tasks":len(records),"aiohttp_logs_recomputed":len(recomputed),"scrapy_rev2":len(trials),"source_files_hashed":len(doc_refs)},ensure_ascii=False))


if __name__ == "__main__":
    main()
