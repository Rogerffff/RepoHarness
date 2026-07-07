# data_freeze 工作流 implementation-notes

维护者：实验设计/检查线程。三节制。

## 设计决策

1. **D1（数字勘误）SWE-Gym Lite 官方行数是 230，不是 234**。HF size 端点实测（num_rows=230）。实验设计文档 E4/附录 B 与 final_review 中所有 "Lite 234" 表述需勘误（影响 bring-up 候选数的表述，不影响任何决策结论）。
2. **D2（取数方式）R2E 元数据改用 parquet 列裁剪**（HfFileSystem + pyarrow，`uv run --no-project` 临时环境不动项目 venv）。原因：datasets-server /rows 整行返回，R2E 巨型字段（parsed_commit_content 等）使单页 >100MB 反复超时。四个数据集元数据全部落地 `meta/*.jsonl`（Verified 500 / Lite 230 / Full 2438 / R2E 4578，R2E repo 分布与前期网络核实逐仓库一致）。
3. **D3（新增处置类别 validation_only）**：strip_spec.yaml 在 E4 原有类别外增加 `validation_only`——金标解字段（swe 系 `patch`、R2E `parsed_commit_content`）既不能进 rollout/grading（模型补丁评分）侧，又必须供离线环境验证门（golden_patch_must_pass）使用，原有类别表达不了这个双重约束。ingestion 遇 spec 未列字段 fail-closed。
4. **D4（断言口径）repo 互斥断言用短名（`repo.split('/')[-1]` 小写）**，因 R2E 只有短名。三方互斥（train/heldout/verified）全 PASS；跨源重复 repo 仅 pandas，去重规则（(repo, base_commit) 级）留给 S2 ingestion，已写入报告。

5. **D5（训练数据不变量）一切训练 run（含 bring-up）排除 held-out repos**。发现 Lite 230 含 hydra 11 题 + bokeh 1 题（E5 划给主判据 held-out 的仓库）；虽然 bring-up checkpoint 本就即弃，但排除这 12 题（剩 ~218）零成本且让不变量无例外。写入 DF-7 提案与 freeze manifest 规则。
6. **D6（DF-2 结论，线程 6 待核项关闭）**：codex 抽样 orange3/coveragepy/numpy 三镜像实测——**全部处于修复前状态**；`commit_hash` 语义 = 金标修复 commit 本身，容器 HEAD = 其 parent；关键修复行均不存在于容器内文件。无 ALERT，R2E 可用性确认。已把"HEAD 必须是 commit_hash 的 parent"写成 ingestion 物化断言（strip_spec 注释）。另记录数据分布事实：R2E 行序按 repo 聚集（前 5 行全 orange3），任何"取前 N 行"式抽样都会偏斜，抽样必须跨 offset。

7. **D7（泄漏门口径）泄漏判定只对模型可见面生效**：正则分字段实测——problem_statement 命中仅 2/230（0.9%），36/230 的命中全部只在 hints_text（已被 strip_spec 剥离，不进上下文）。规则定为：ps 来源泄漏 → 影响准入（fail 剔除 / warn 观察）；仅 hints 来源 → 只记录不剔题。LLM 标签（合并判定）收尾时用 leakage_evidence 片段做字段归因后处理。副产品：**"剥离 hints 消掉 95% 正则可测泄漏面"是可量化治理证据，进 E8 数据证据**。
8. **D8（校准结果）**：试点 20 题零解析错误，与人工校准集一致率 100%（口径：**5 题 × 3 标签 = 15 个标签级判定**，非 15 题），打标 prompt v1 放行批量。泄漏分布（合并判）fail 3/warn 11/pass 6，与 SWE-Bench+ 基线同量级。

9. **D9（DF-6 结论，含一个高危勘误）**：SWE-Gym 镜像命名实测为 `__` → **`_s_`**（非 SWE-bench 官方的 `_1776_`）——此前实验文档附录 B 的"按 instance_id 拼镜像名"若按官方惯例实现会全量失败，勘误进 P5 清单，S2 ingestion 必须用 `_s_` 规则（已有实测清单 `meta/image_refs_swegym.txt` 可直接消费，无需再拼）。磁盘外推：Lite ~0.5 TiB / Full ~5.3 TiB / R2E ~2.3 TiB（朴素压缩和），显著高于早前"2000 题 0.5~2TB"粗估——success run 扩容前的磁盘规划以 DF-6 报告为准。

10. **D10（P1 收口）**：Lite 230 批量打标零错误；字段归因后静态门存活 216/230（剔 held-out 12 / adequacy fail 1 / ps 泄漏 fail 1）；hints 剥离中和 47.4% 的泄漏面。冻结包 v0（manifest 12 项 digest + 报告）已落盘，DF-1~8 全部完成。

11. **D11（评审修复轮，2026-07-08，回应 codex + claude 检查线程）**：
    - **P0 pin 修复**：`.revision` 原抓到的是配置键 "default"（fetch_meta.sh jq 表达式 bug，已修脚本）——四个数据源的真实 HF revision 已取回写入 manifest v0.1 与 .revision 文件；artifact_digests 从 12 项扩到 **24 项**（补四个原始 meta jsonl、试点/原始标签文件、全部脚本与 prompt）。
    - **抽检补做（门控全查代替随机 10%）**：2 个 fail 题人工读题复核——dvc-2017（打包/文档整理，无可断言行为差异）与 MONAI-3326（题面直接含修复代码）剔除均正确；13 个 ps-warn 的 evidence 归因 13/13 程序复核在题面中。随机 10% 未执行的理由与口径已写入 manifest scope_caveats。
    - **warn 下游义务补全**：ps-warn 存活题带 leakage_watch 标记进池 + evidence 随行，写入 manifest invariants。
    - 其余：DF-5 标题格式损坏修复；Lite 234→230 勘误（计划文档 + fetch 脚本）；R2E 抽样警示（禁取前 N 行）升入 invariants；"S2 重抓数据必须重跑 strip_spec fail-closed 检查"升入 invariants。

## 偏离说明

- 无（计划内执行；fetch_meta.sh 的 rows-API 方案对 R2E 失败后按 D2 更换实现，属方法调整非目标偏离）。

## 执行坑记录

1. **后台驱动 `codex exec` 必须显式关闭 stdin（`< /dev/null`）**：否则它把打开的管道 stdin 当作额外输入源无限阻塞（日志停在 "Reading additional input from stdin..."），且不报错——DF-2 首次启动因此空转约 2 小时才被进度检查发现。已修复重启并验证推进正常。后续所有 codex 后台任务沿用此模式，并配"日志增长探针"确认开工。

## 开放问题

1. **DF-2（已完成，见 D6）**：修复前状态确认、commit_hash 语义已定。注意范围限定：这是 3 仓库抽样的 git 语义核验，**不等于环境质量验证**——golden/empty/determinism 门仍需 S2 rh2 库执行（已列 manifest pending_gpu_steps）。
2. Lite 230 勘误的文档回写（实验设计文档/final_review）待与其他勘误（P5 文档一致性扫描）合并处理，避免碎片化改动。
3. R2E 的 `problem_statement` 截断存储（20k 字符）：打标够用；若 S2 ingestion 需全文，从 parquet 重取。
