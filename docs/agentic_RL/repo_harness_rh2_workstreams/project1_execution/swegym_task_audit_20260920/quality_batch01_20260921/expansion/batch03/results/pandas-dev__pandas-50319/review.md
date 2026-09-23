# pandas-dev__pandas-50319 — B3 对照复审

**结论：同意保留 needs_review / static_review，用途 development_diagnostic；修改检查项范围，不撤回独立初判。** 公开允许原例返回 `None`，新增断言只接受指定格式串，二者接受范围不一致。历史 gold/noop 和 reference_v1 修复成立，但不能抵消这项语义问题。没有新的 CPU 候选运行，也不据此宣布已证实实际 reward 误拒或正式 actor 可用。

## 封存、放行与本轮范围

本包两份 reviewer_initial.md 由 root 在 `2026-09-20T22:05:49.422998+00:00` 重算匹配后封存，随后明确放行比较。本题 initial SHA256 为 `848e760cd05d0ecc1f3a18441bb41b36b364c6d565473e20ac89874007c664c1`，另一题为 `ce75440a9c77b4d8f9554f4ad94772c80292094aa1a27727115ab1fe22850de6`；两份封存字节均未改写。

放行后只读本题及同包 51605 的 public_read、analysis_before_history、old_findings_delta、card、screening_record，以及各自 history/refs.json 精确指向的唯一旧单题 JSON。没有追读旧记录中的其它报告、其它任务、聚合或 analysis_reference。另读共用原 40 项检查表，并针对自己的公开源码补核调用者与 helper；未执行项目。独立阶段已见 environment_record 内 gold/noop 摘要与本题全部私有测试/gold 的暴露，仍按 initial 披露；本次又见主审和旧结论，不能作为公开盲读或 solver。

路径：`ROOT=${REPO_ROOT}`；`I3=ROOT/runs/swegym_quality_batch03_20260921_v1`；`P=I3/public/pandas-dev__pandas-50319/base`；`Q=I3/private/pandas-dev__pandas-50319`；`R=ROOT/runs/env_recipe_repair_20260919/reference_v1`。本题结果目录为 `ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/pandas-dev__pandas-50319`。

对照主审封存稿 SHA256=`2148d157f3ab1b723305abbc7d61998cc7403afc0b651643c6ce0938a0c88d44`。读取时 screening_record SHA256=`ddb3dd292063bf116713ca23441a9a7d5342c47387f1e5dcf8b6f611ed19ba5d`；以下涉及其状态的意见针对该版本，最终结构补齐由 root 负责。

## 同意、修改和保留边界

| 对照点 | 复审意见与决定性依据 |
| --- | --- |
| 公开目标与原错误 | 同意。原例 `guess_datetime_format('27.03.2003 14:55:00.000')` 明确接受 None 或格式，P/parsing.pyx:875–879 写 str 或 None；core/tools/datetimes.py:129–146、435–461 实际处理 None fallback。原 noop 的 ValueError 栈位于 _fill_token/int("")，与公开 base 对应。 |
| 唯一新增断言、全部相关旧行为 | 同意。test.patch 只有一个参数元组，进入 test_parsing.py:184–186 的 result == fmt。独立阶段全读 327 行、1 F2P 与 109 P2P 键及关键 helper。主审的 62 个相关旧实际节点/58 个参考键，加 51 个旁路旧节点，解释了 113 个旧实际节点；不可把键数当实际执行数。主审封存稿“14 个 None 分支”已由 delta 更正为 12；接受该更正，原稿不回写。 |
| 合法非 gold 路线与 #24 | **修改所读 record 的 #24=pass。** 原检查表 #24 明确要求检查满足公开要求、不同于 gold 的合法替代路线。成功猜格式的子分支不强制 regex，不能支持整个问题通过；题面允许的 None 路线已被断言排除。应 #24=issue，并保留 #23=issue。这是静态接受范围差异；局部 ValueError→None 候选是否保住全部旧行为及实际 reward，仍待 CPU。root 已明确接受这项修正，现无该项未解决分歧。 |
| gold 本身 | 同意其修复原例且没有新增包依赖：gold 只改 token 的数字小数识别，已有 re 导入；历史 114 节点通过。#27 的支持范围只能是已查目标及旧文件，不能外推完整日期语法、性能或全仓回归。 |
| 调用者与额外公开测试 | 独立初稿已追直接业务调用者 to_datetime；放行后补读 P/pandas/tests/tools/test_to_datetime.py:2294–2321，确有猜格式数组及全 NaN→None 的公开测试。它们提供 None 的接口背景，未被本题历史评分命令执行，也不能替代新候选端到端验证。 |
| #3 实际输入、#29 暴露 | 同意 root 的范围修正：#3 问“求解者实际收到的输入”，没有真实消息捕获应 unknown；公开语义证据归 #23。当前 public_hints 非空与旧上游 hints_text 为空是不同字段/版本，不能单凭前者推翻后者当年的字段事实。可以撤回旧“无隐藏信息/泄漏 pass”对当前 actor 的外推：实际消息、镜像内答案资产均未核。 |
| 单样例与错误补丁 | 同意 delta 的限缩。单一字符串新增覆盖不能自动推出已发生错误通过；本题公开明确原例，无经验证的其它违约行为时，不把未运行的单例特判包装成已证实 reward 漏洞。当前优先问题是明确允许 None 却被拒。 |
| 解析绑定 | 同意当前 reference_v1 已修复反斜杠旧键缺席；不继承旧“gold 恒失败”。两组空白截断碰撞仍存在，但当前六个成员都通过，不能宣称此次错分或任意早期 FAILED 必被后续 PASSED 覆盖。 |
| 开发与成本 | 同意 actor 条件未知、.pyx 需要重编译、历史安装成功不等于正式 actor 成功。旧“pip 必联网”被当前已满足依赖及 deny_all 成功记录否定；旧 26 分钟不成为本轮耗时。保留原字段 mem_peak_mb，不擅自换单位。 |

## 原运行结论保持的精确范围

原入口是 R/run_reference_cases.py → replay_with_install_recipe.py → 冻结 replay CLI。输入为 R/reference_bindings_v1.json 顶层 tasks 中本题项；运行目录 bindings/reference_bindings.json 与 .reference.json 是审计输出，不作为原输入。wrapper 没有 install/materials/derived image 覆写。内部 harness 以 `ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz` 的历史字节为准，仅 extractfile 读取相关成员及调用链。

| 层次 | 已有原始观测；不是本轮重跑 |
| --- | --- |
| 实际测试 | 两次 `pytest -rA --tb=long pandas/tests/tslibs/test_parsing.py`；gold 114 passed/RC0，noop 1 failed+113 passed/RC1。gold 日志 c332d5e5:5007/5057/5065；noop 55456694:4954–4960/5089–5098，完整路径见 initial 的 R/runs 两角色目录。 |
| 节点、解析、参考 | 114 个实际节点→原 parser 110 键→单一反斜杠 binding 后 111 键；冻结参考 1 F2P+109 P2P。两组碰撞分别含 2/4 个完整成员。gold 1/1+109/109/reward1，noop 0/1+109/109/reward0；普通 RC 只作诊断，不直接定义 reward。 |
| 安装 | gold 明确重新 Cythonize parsing.pyx、复制 .so、built/installed；noop 也有 built/installed。末命令是 uninstall pytest-qt，install_rc_last_command=0 单独不足以证明前面的安装成功，本题由实际成功行补证。 |
| 原资源字段 | gold install_seconds=731.263、test_seconds=5.252、mem_peak_mb=902.945；noop 701.046、5.424、838.82；resource_facts=null。此处不把 mem_peak_mb 数值重命名为另一单位或当成本轮测量。 |
| 身份与镜像 | 评分 rh2grader/54322；机械 apply agent/54321 不是正式 actor。image_id_actual=null、env_qualification 缺失；expected identity 不是实测 image ID。当前镜像/依赖/路径可用性与实际 actor 工具消息未知。 |
| 交付与环境 | official test_parsing.py 精确恢复/保护，业务 parsing.pyx 投影 included、ignored=[]；没有额外排除依据。原 /work prepared 路径以后必须新建重定位副本，本轮未动。 |

原日志 SHA256：gold `48bba71fe66e379c3e42c8086860852460054196ca2c3b082df641e74ce4b89f`，noop `83ac6be555387a8d9c650c70a3f4274648e54629d379b9a12098d96c7a038390`。这些原件及所选账本行已在独立阶段核验。旧 record 仅来自 `ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-50319.json`；其 stage1、碰撞附件等未跟读，故不对旧运行当时是否正确作超出本题新证据的判定。

## 同包关系与新增披露

独立阶段已读并发现：`I3/public/pandas-dev__pandas-51605/base/pandas/_libs/tslibs/parsing.pyx:1009–1023` 含 50319 gold 的完整 _fill_token 核心条件与注释，包括 `re.search(r"\d+\.\d+", token) is None`。这是“同包晚题公开源码包含早题修复”的具体线索，应在跨任务上下文隔离与答案暴露检查中记录；**不证明 Git 祖先关系、重复任务，也不证明真实 solver 已经看到或使用答案**。本包的两个业务目标不同；不能据同仓或此源码重合推导模型学习价值。

本轮与初稿相比无实质撤回；增加 #24 整体状态修正、#3 输入交付范围修正及 hints 字段区分。已知两份 record 共 7 个 issue 的结构字段不全由 root 补齐，reviewer 不代改 record。各检查必须保留证据来源和静态/历史/未来边界，不能把补齐结构本身当新增运行验证。

## 唯一优先 CPU 实验（未来，未执行）

仅做一次固定 grader 的 **None 路线误拒诊断**：在新重定位副本中构造一份通用、局部的 _fill_token ValueError→None fallback 非 gold 候选，保持已有成功路径与官方测试/reference。沿原 reference_v1 wrapper、原顶层 bindings 输入和原 profile，先核题面样例返回 None、不抛错，再核现有 P2P（特别是小数秒、dayfirst、无填充）、公开 to_datetime fallback；记录完整节点、locale/skip、解析键、测试 RC 与 reward。若公开行为成立且旧行为保持，新 F2P 仅因 None 拒绝，才补上实际误拒证据。

实验不强制第二候选，不要求先跑模型。固定 grader 的导入、构建和源码生效是实验有效性条件；正式 actor 身份/工具/开发环境的资格验证是以后模型开发门槛。若未来修订，接受 None 或经语义验证的有效格式，保留旧成功格式保护；不能改题面排除 None，也不能只验“没异常”而接受错误值。解析成员缺席/skip 是次级诊断，不与主实验并列优先。

本轮仅静态读文件与 stdlib JSON/hash，未运行测试、项目 import、安装、网络、Docker、SSH、模型或 quota/reset；未改任何源、tests、gold、reference、reward、expected 或 prepared。费用/token 无观测为 null。最终保留 needs_review / static_review / development_diagnostic。

