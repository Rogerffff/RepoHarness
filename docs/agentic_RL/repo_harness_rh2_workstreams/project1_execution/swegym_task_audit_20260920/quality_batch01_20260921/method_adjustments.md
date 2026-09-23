# 首批执行方法与校准记录

2026-09-21，协调者 `/root`。执行范围是冻结 12 题的静态质量审查与后续 CPU 方案；本记录不修改题目、评分或生产准入。

## 开工核对

- 正式授权已取代旧交接卡的“尚未派发/授权后”。权威材料均按项目工作区解析；当前新 worktree 不作源码依据。
- 角色由真实 sub-agent 工具派发，登记工具实际返回的 canonical agent name；工具未返回 UUID，不编造 UUID。每题公开角色为 `fork_turns=none`，只收到公开角色卡、本题公开目录与唯一输出路径。
- 并发上限含协调者为 4；同题按公开落盘 → 私有原件调查 → 保存历史前分析 → 开放历史的顺序。独立 reviewer 先原件初判落盘，再接收其他角色结论。完成角色的上下文不复用于另一题公开阅读。
- 不改共用卡和历史材料。若发现补充事实，写本记录或角色附件，由总协调者决定是否升级材料版本。

## 材料身份复核

只读核验结果：`runs/swegym_quality_batch01_20260921_coordination/material_recheck.json`。

逐一比较 3 个来源文件 SHA-256、36 个来源 JSON 行、12 份 test/gold 补丁、12 个公开 prompt 摘要、9,791 个 base 跟踪文件的 Git blob 字节及可执行位、24 条日志 SHA-256 及对应账本行。没有失配；base 未导出 `.git`。材料快照列出的关键 RH2 源码 SHA-256 也未变化。

这只证明静态材料与所引本地原件一致，不证明运行镜像完整、公开包技术隔离、actor 开发条件或题目质量。没有执行历史项目代码。

## 当前共享环境边界

沿用 `actor_environment_card.md` 与上级 `chain_readiness.md`。定点阅读当前 `rollout_spec_from_view`、`_materialize_rollout_sandbox`、`RolloutSandboxProfile` 和 harness 启动代码，正式 face 仍从 public bundle 取镜像；agent 身份为 54321；`test_globs=()`；激活、修复配方实际消费和工具消息仍待实际 actor 证据。旧评分链已核销缺陷不重新报作当前故障。

本批原始题目、隐藏断言、参考集和二值 reward 保持原样。未知与未检查保持原状态，静态候选保持 `needs_review/static_review`。后续 CPU 或模型执行由总协调者安排，本任务不开 Docker/SSH、不租机、不运行历史项目或付费模型。

## 第一波校准

首波四题公开产物已分别落盘，角色均报告未接触私有材料；Conan15422 的主审历史前稿已保存并登记 SHA-256 后才开放该题 history refs。详细源码/断言映射留前稿；最终 card 和汇总保持短。

**执行过、进入评分参考、实际读过三者分列。** Dask8597 的主审提出相关旧测试未进入 P2P，协调者已只读复核：`test_getitem_avoids_large_chunks` 与 `test_slicing_integer_no_warnings` 均不在 `grading.json.pass_to_pass`，但 gold 原日志第 765/754 行（末尾摘要 908/898 行）明确 PASS；noop 同样 PASS。对应日志由本题 private/run_refs.json 唯一定位。当前 `envpack/scoring.py:250–265` 仅按冻结 F2P/P2P 计算 resolved，不能将其它执行通过项写成对未来候选的 reward 回归保护。

这不是已完成 CPU 的漏测反例，也没有据此改参考集合。后续主审需注明受影响行为由哪份参考真正保护、哪些只是本次日志观测；有具体疑点再排 CPU 对照。独立 reviewer 尚未接收此结论，仍从原件先写初判。

总协调者另核原件并在 `acceptance/dask8597_reference_scope.md` 记录同一事实：此项归类为**来源参考覆盖限制**，不是 RH2 偏离既定语义的接线故障。参考未穷举不自动触发后端修改或淘汰；具体误收后果待 CPU，有证据才提版本化修订，也不阻塞其它成熟单题。此通知不转发尚未封存初判的 reviewer。

**结构化记录保持既有子字段。** 首份主审 JSON 保留了顶层形状，但 `checks` 缺逐项 `evidence_refs/by`，`issues` 与 `usage/costs` 使用了替代字段。已请作者补齐既有定义的子字段，额外解释可保留；未知费用/运行量仍为 null。该校准仅影响可追溯记录，不改变生产 schema 或题目处置。

**CPU 草案按现成 CLI 源码核参数。** 安装 recipe wrapper 的 `--code-root` 是必填；本批 `cpu_queue.json` 中完整重放草案已注明。actor 薄入口仍未实现；容器内部的公开验证命令不冒充宿主即可运行的完整入口。

**记录私有环境元数据暴露。** Dask reviewer 主动报告读取允许的 `private/dask__dask-8597/environment_record.json`，其中有环境配对的 status/checks 和名为 history 的 compat_v1 来源引用。协调者核得该字段不含旧质量结论，属于已授权私有环境元数据；无须重启角色，但初判须明确见过环境汇总并用原始日志独立核实。未授权提前打开旧分析总结或质量 `history/<id>/refs.json`。

**同仓 reviewer 先封存包内全部初判。** 总协调者指出：主审可能在第一题短卡/JSON追加第二题跨题发现，因此仅要求“第二题不读其主审”仍不够。已立即改进：Dask8597 初判封存后不开放主审结论，待8801也初判后一次开放两题；下一包同样先完成包内各题初判，再开结论（也可逐题独立 reviewer）。Conan14177初判当时已完成；此前派发消息已禁止重读15422更新卡，现要求 reviewer 依据实际读取记录说明是否见过跨题补充，不能将已暴露关系称独立发现，不机械重跑全部调查。

Conan14177 reviewer 按实际读取记录确认：其初判前未重读 15422 后补卡/JSON；15422 base 已含 14177 gold 行为的跨题关系只在第二阶段核实，不计作独立再发现。公开读者将 Applying 示例读成固定措辞，主审/复核收口已校正：后续公开行为 oracle 允许等义清晰日志。初判与公开读稿保持原样。

**首波收口。** 四题7份产物齐全；Dask两个初判均先封存后开放结论，哈希未变。8597保留受限静态候选但先等指定CPU，8801首个同义候选保留path!r，路径引号另作独立变量；文件/目录权限分支分记。结构核验另补8597遗漏的 applied_version=upstream_unchanged。全部修改只在协调者获授权结果文件，未回写封存前稿、题目或参考。现在进入固定余八题，同仓 reviewer 延续包内全初判先行规则。

**第二波阶段校准。** mypy install_wave1的逐题image.json保存COPY离线wheel及PIP环境配方，使用原安装流程，不套用其它波的revised_install wrapper。10424配方消息在主稿封存后读取，另存并封存recipe_before_history.md再开放历史；原稿不变。Pydantic两初判先封存后交叉：8511 G1是reviewer初判遗漏，第二阶段核实，归属明确；5706初判后段读取8511较新base同函数的原件暴露已披露。收口脚本尊重exposure_notes原有文本或列表形状。Mypy最终复核分为单题10424与两题16963/12417两个新上下文包，各包全初判后才开放结论。


## 全批收口补记

**保留实质分歧并缩小实验。** mypy10424主审与reviewer分别提出相同收窄错误控制，首验只需两个已有Any/Union case。16963先核完整公开原例，不因零P2P判坏。12417 reviewer补入保留current_type的较窄替代，四实现分别区分subject类型与body可达性；不把静态预计失配登记成误拒。DVC3620 reviewer更倾向hardlink合理推广，主审更重旧契约冲突；协调者保留两种依据，优先能检验评分后果的数据丢失负对照，symlink-only列可选，不增两个硬门。

**引用与环境条件更正可追溯。** 9395主稿部分GL/NL行号混用了不同旧日志，review给出同SHA原件的正确定位；最终card/record引用该更正，封存主稿不回写。3620 local.py:532–538正确对应is_protected的缺失文件False行为，不能机械改成unprotect入口；review另补初判漏记的moto环境预改。公开旧测试可能含本题要改变的行为或内部次数断言，不能要求solver所有旧断言原样全绿，也不能泄露私有替换值。

**新历史原件只做有界增量。** 按总协调者明确派发，5706原reviewer回读12份矩阵日志、脚本/单行生产补丁及两条旧计分原件，仅追加review。原正文13597字节和初判哈希保留。report-only结论随原件升级，不倒写为当时已核；09-16矩阵的行为计数与启动身份条件分层，当前CPU目标只验证现配方/真实RH2适用性。

**末次元数据核验。** 84份必需文件和1份配方附录齐全，37份封存内容未变。校验器原先假定task_id等于instance_id，误报Dask8597；当前源码bundles_v2定义source::instance_id，核其配套instance_id后接受合法带来源主键，原记录未改。最终输入身份与记录审计均无错误，路径见batch_report。验证只执行元数据/哈希/只读Git操作，不执行历史项目或测试。
