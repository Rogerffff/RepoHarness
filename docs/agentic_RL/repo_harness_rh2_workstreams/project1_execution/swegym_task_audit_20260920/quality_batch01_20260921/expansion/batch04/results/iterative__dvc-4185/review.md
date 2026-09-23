# iterative__dvc-4185 — B4 独立交叉复核

2026-09-21。**支持主审 `needs_review / static_review`、仅 `development_diagnostic` 的处置；选择先做公开双症状的 base/gold CPU 诊断，再决定是否排入普通能力 probe。** 本题可保留在诊断队列，但目前不建议作为仅待 actor 验收的普通静态候选。原因是 score=1 与“完成公开全部目标”之间已有具体、强静态反证链；这影响能力结果解释，不只是覆盖数量不足。也不据此永久拒题或静默删掉 commit 要求。

## 独立性与交叉范围

先封存 `reviewer_initial.md`，SHA256=`9f20590371883eafc67f1dd5368edd0bf87e206e8e57d2e1473c8b94d1746561`；协调者核验并显式解封后，才读本题 `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`，以及 `history/iterative__dvc-4185/refs.json` 指定的唯一旧记录：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-4185.json`。未沿旧记录读取 raw hints、旧日志、聚合或其他题。

交叉时确认初稿散列不变；主审封存稿 SHA256=`46933a127ba240a729f8fbcd230c21fb3e37f012e17c58795eba6e30b44d88cf`，公开读稿 SHA256=`12ba0ac7e72c588d84a7e3297aa51128d2fca65434da7df8d755173bd9eebc80`。主审与 reviewer 的 commit 路径判断均在本次交叉前形成；公开读稿也独立识别同一双目标。这不是多数票证明，决定性依据仍是以下源码与断言。

继承初稿的原件范围，并补读公开 `tests/unit/stage/test_loader_pipeline_file.py:41–86,138–145` 与 `dvc/output/base.py:90–117,168–218`。没有新项目 import、测试、安装、容器、下载、网络或模型执行；只新写本 review，所有封存稿及其他角色稿不改。已见 gold、隐藏测试、历史结果和旧质量判断，故不是 result blind，亦不适合作为 solver 上下文。

路径约定：ROOT=`${REPO_ROOT}`；P=`runs/swegym_quality_batch04_20260921_v1/public/iterative__dvc-4185/base/`；E=`runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-4185/`。以下源码位置相对 P。

## 对主审决定性主张的判定

| 主张 | 复核结果与证据 |
| --- | --- |
| 公开目标包含 status 与 commit 两个症状 | **支持。** 题面末尾明确编号；get_base_dv 只跟踪 start/end/universe/benchmark 等真值，不能把它的 commit 误报并入 false 的同一输入。公开读稿 R1/R2/R3 的区分有依据。题意可理解与真实消息已渲染是不同事实，record 检查 23 限定 pass、3 unknown 合理。 |
| gold 修复假值加载，但很可能仍未修 commit | **支持 I1，证据仍为强静态推断。** `repo/commit.py:42–45` → `stage/__init__.py:397–410` → `output/base.py:172–195`；参数 info 保存选定参数值、无 md5，而现存参数文件有文件哈希。继承的 changed_checksum 仍会判变；gold 只改 `param.py:43–50`，未动此链。普通 status 又在 `param.py:62–77` 独立按参数值比较，恰能产生“status 干净、commit 仍提示”的组合。本轮未执行该组合，不能写已复现。 |
| 七 F2P 与 22 P2P 不足以保障双目标和真变化检测 | **支持 I2/检查 25、26。** 七 F2P 全是写本地 YAML→fill_values→status=={}；其七种文本只有 False、None、空 list、空 dict 四类语义。空文本不是引号空字符串；0/0.0 未测。22 P2P 无参数 commit 或 status 变值/删键断言。`test_run_params_default` 虽被 test.patch 补类型断言且实际运行，但不在参考集合；公开 repro/loader/commit 回归不能算本次已执行评分保护。status 恒空是具体漏测候选，尚未证明真实 RH2 满分。 |
| 没有已证实的合法解误拒 | **支持降为 unknown，不支持旧记录的广泛 pass。** 哨兵或选键映射加载假值有公开依据；完整替代路线还需处理参数 commit，例如仅让 Stage 对 ParamsDependency 使用参数状态判断，普通文件继续用 checksum。测试未锁 gold 表达式，但未实跑任何完整替代解，不能保证所有重构均通过。 |
| 旧安装和 ID 阻塞在指定历史条件下已覆盖 | **支持限定结论。** 初稿已核 E 下原日志与两 ledger 第 1 行：noop=0/7 F2P、22/22 P2P；gold=7/7、22/22，实际两文件 49 passed/2 skipped、rc=0。条件是 dvc_install_v1c、离线 networkx=2.3+rh2.1、shared moto 预改、reference-bindings-v1。单反斜杠 P2P 的显式 node 绑定没有补测 commit，也不表示通用 parser 已完整审计。 |
| grader≠actor，交付和泄漏检查须保留边界 | **支持 I3 及检查 6/7/11/29 的 unknown。** 参数源码位于已投影路径，官方只恢复两个具体测试文件，正常修复未见交付阻挡。真实 actor 是否拿到兼容依赖、离线资产、激活脚本、完整消息及安全的可见历史仍未验；冻结 face 取 public.image，grader wrapper 的 recipe 改动不证明 actor 消费。无 .git 的静态导出不构成真实资产无泄漏证明。 |

上述结论覆盖八方面；跨题关系、完整原业务/WSL 重放、所有回归、真实模型表现仍未检查，不能补为 pass。主审 record 对成本填 null、additional_exclusions 保持空、revision_refs 为空均与本轮范围相符。card/record 的“尚未纳入 reviewer”是本稿生成前状态，由协调者后续收口，本 reviewer 不回写。

## 对旧记录及主审补充的复核

支持主审纠正旧记录的“params.yaml 缺键应 new”：`param.py:65–68` 明确先看当前键是否存在，缺当前键为 deleted；当前有键但记录没有才是 new。旧建议不能直接成为新回归断言。主审给出的有效反例是非空 lock 映射只含别的键、当前有 `p: null`；无条件 `values.get(p)` 会伪造已记录 None，使本应 new 的参数被视为干净。保留 `if not values:return` 时也不能称“永久压掉 new”。补读的公开 `test_fill_from_lock_params:54–72` 明确要求缺失 foobar 不出现在 info 中，说明此语义可从公开资料推导；但它不在本次执行命令，`test_save_info_missing_param` 又未调用 fill_values，均不能冒作现有评分保护。

反对旧记录从“parser 误判”推到“题目和 gold 都没问题”，也反对先裁掉第一症状以迎合 gold。新主审没有沿用这两项推论，处置正确。旧 raw hints 的代码/链接说法未查原件，不能确认当前 actor 泄漏，也不能据当前 bundle 没有该内容证明无泄漏。旧 20 条双侧环境失败的精确计数未重审；最新两文件运行证据足以使它不再代表 09-19 配方状态。

有两项需要明确限定或更正：

1. **本 reviewer 初稿资源单位更正。** 初稿把约 387/482 的峰值称为 MiB，没有核单位实现。现仅引用原 ledger 字段：gold `mem_peak_mb=386.82`，noop `mem_peak_mb=482.152`；不换成二进制单位，不用它验收 actor 预算。主审已在 delta/card/record 对同类表述更正。两份初稿均不回写。
2. **主审替代解中的 KeyError 提醒应是条件性风险。** 单独覆盖 changed_checksum，不会对普通无 md5 参数必然导致 `super().status()=={}`：`output/base.py:213–214` 仍会返回 new，因而存在 `[str(self)]`。当 checksum 为真且比较判未变等条件使基类返回 `{}` 时，`param.py:59` 才有索引风险。该提醒有代码依据，但不应扩大成任何参数专用比较方案都不合法、或已证实误拒。本题推荐下一实验无需加入这个边界矩阵。

共享 moto 预改已经由两侧日志确认，未来的 base/gold 必须保持同一 `setup.py` 差异，不能称 pristine base；它是环境条件，不应算入 solver 的业务修复。本项与上述资源单位更正均不改变 I1 主结论。

## 唯一优先未来 CPU 实验

**一组固定环境的 base/gold 双症状对照；先不跑错误候选或全仓回归。** 准备本题已经记录的镜像/recipe/networkx 与共同 moto 预改，记录实际源码来源和身份；两侧唯一业务代码差异是官方 gold。每侧建立同一临时 no-scm 仓库，params.yaml 仅需 `start: 20200101` 和嵌套 `eval.filter_limitup: false`，分别建 get_base_dv、eval 两个只输出小文件的阶段。保存后重新打开 Repo，强制经过 lock 加载。

记录两个结果：A，重新加载后的 JSON status 是否只在 base 把 false 报 new；B，未改文件时 get_base_dv 的不带 force commit 是否仍进入确认路径。用可记录且拒绝确认的本地 hook 避免交互挂起，记录调用次数/提示或 StageCommitError，而不是要求用户批准。并保存参数 info 和当前文件哈希。作为同一小样例的一个正向控制，把 start 改成 20200102，确认 status 报 modified，防止把全空状态当作正确完成。

静态预测：base 的 A 失败、gold 的 A 恢复；两侧 B 都误报，且正向控制仍能报 modified。若出现这个组合，即确认 gold 的既有满分与完整题意脱节，应先明确诊断范围或设计独立的规格一致验收版本，再考虑普通能力 probe。若 gold 的 B 意外正确，先据实际调用链/初态差异纠正静态判断，不坚持已有结论。无需在第一轮扩大到全部假值、删键、未跟踪字段、错误候选或全仓测试；那些属于后续修订校准。

该实验尚未执行，也不能替代正式 actor 消费链和真实消息验收。当前最终建议保持 `needs_review / static_review / development_diagnostic`。
