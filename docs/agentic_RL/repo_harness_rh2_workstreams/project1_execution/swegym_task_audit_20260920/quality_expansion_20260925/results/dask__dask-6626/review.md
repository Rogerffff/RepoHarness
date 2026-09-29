# dask__dask-6626 独立交叉复核

结论：支持主审保留为 `development_diagnostic` 静态候选、`needs_review`，不构成 actor 开发资格或训练/正式评测批准。核心修复有依据，用户两条 set_index 路径仍缺直接证据，runner 完整性变化保留未解。与封存独立初判的实质结论一致；下列判断来自本题原件复核，不以人数一致为依据。

## 1. 阅读与暴露边界

三题独立初判先全部完成封存；收到协调者明确 cross_review release 后，才新增读本题 public_read、analysis_before_history、old_findings_delta、card、screening_record 和 history/refs.json 指定的单份 L1_dask 旧记录。旧记录先核 SHA 再读全文，没有扩读其链接、其它题、根汇总或其它包。初判实际读过的文件/源码/逐项日志范围见 reviewer_initial；本次另外完整读本题 gold/noop diagnostics、gold stage/projection，均由 private/run_refs 精确授权。长 JSON 重复运行字段用 stdlib 逐键比对原 ledger/diagnostics；并非把摘要直接当事实。

P 表示本题 RUN/public/dask__dask-6626，V 表示 RUN/private/dask__dask-6626；RUN 与 B 的绝对位置及输入 SHA 见附录。已读 gold/隐藏测试/评分与获释旧质量记录属于 reviewer 授权私有暴露，不能给 solver；actual actor 消息、工具/目录可见性、是否见过答案仍 unknown。共享路径约束不等于 OS 隔离。

## 2. 需求—测试双向复核及源码证据

| 需求/边界 | 公开与源码依据 | 测试及反向规格依据 | 复核 |
|---|---|---|---|
| 已知空 categories 不凭空成为 a/b | 题面；P/base/dask/dataframe/utils.py:543–589；dataframe-design.rst:20–57 的 meta dtype 不变量 | 修改 test_meta_nonempty 的 K；原有两次 dtype equality 因 K 新增而扩展；新增 len(categories)==0 | 直接 helper 目标合理；noop 实际先败于已有 dtype equality，不能称只靠新长度断言 |
| 两条 from_pandas→set_index 路径与 compute 一致 | 题面及 shuffle.set_index、core 的 _meta_nonempty 调用 | 此 F2P 不调用这些用户路径 | 集成缺口成立，但不能据此断言 gold 用户路径失败 |
| 正常/未知类别与元数据属性 | 同文件 _nonempty_index/_nonempty_series；公开已有 tests | A/J 与类别 O/f8/M8[ns]、ordered/name 等现有断言 | 相关 P2P 有保护，非全部合法类别/组合的完备证明 |
| 空 CategoricalIndex | utils.py:445 附近仍有旧分支；test_utils_dataframe.py:172 后相关用例 | 旧空 Index 断言未要求类别长度/内容 | 旧邻接缺陷，非 gold 引入回归，不能把旧26建议用例当已运行证据 |

完整阅读新增 fixture、修改/新增断言及决定性 helper 的初判继续有效。逐 F2P1/P2P14 的身份与两侧状态已在独立初判附表列全。本次对照主审逐项表未发现遗漏预期 node 或把额外 sparse 混入 expected 的问题。

Gold 将空类别从 `None` 改成 `s.cat.categories[:0]`，保留 dtype 的推理成立；`Categorical.from_codes` 等可实现同一不变量，测试未锁补丁文字、分支或物理修改位置。仅在 set_index 调用侧修复而留下 helper 不变量错误的路线未执行，是否属于完整合法解不能只靠“用户示例成功”确定。主审撤回旧“任意等效解都会被误拒”有依据；一般无误拒仍 unknown。

## 3. 八方面与原运行核查

目标/版本：base `56cd4597630feb1b01501c16d52aa862dd257a83`、题面、补丁与 stage 相符。输入/环境：只有静态导出和所引历史 grader；actual actor 的消息、HEAD/status/diff 原始 RC 与采集阶段、初始改动、被忽略资产、UID/HOME/cwd/PATH/权限均未知。功能样例在内存生成，不需求外部数据/GPU，但这不能证明实际环境可开发，也不能以未导出文件断言缺资产。

交付/可信评分：所引 gold candidate.patch 字节 hash 与 V/gold.patch 相符，stage=git_apply；只投影 dask/dataframe/utils.py，ignored/unsupported 为空。原 diff、源码导入 `/testbed/dask/__init__.py` 支持此候选有限生效。两份 diagnostics 的 trusted_setup 显示 apply RC0、restored/expected/present 各1、absent0、protected_files1，支持本题单测试文件恢复；不推广成任意候选或所有 fixture 的完整保护。

实际命令两侧均 `pytest -n0 -rA --color=no dask/dataframe/tests/test_utils_dataframe.py`。compat_v1 使用 Python3.8.19、pytest7.4.4，离线 wheel pin 与 editable no-deps 安装在原脚本/日志中；安装 RC0，noop 测试 RC1、gold RC0。noop log454命令、454后收集16，目标失败454–492/533，最终1 failed/15 passed；gold472命令、508目标通过、522附近16 passed。F2P1、P2P14 均按身份核对；sparse 另在 noop532/gold521 通过。

输入身份/政策/预算、安装 timing、report、projection、candidate、observations、cleanup、parser 逐键与原 ledger/diagnostics 比较无差异。实际派生 image ID `sha256:9776743c862cf253a473d545325b5975b3cab8f098028b4dfbe5bc0622e0b8d0` 与 expected source digest 分开；UID54322/rh2grader、deny_all、cpus2、memory_bytes4294967296、pids512、grading deadline3600 均仅历史条件。raw mem_peak_mb noop468.746/gold286.508 原值保留，不推导 actor 用量。两侧 runner_integrity_changed=true，pre/post digest 改变；已见 pytest pin 不能证明全部字节变化均由它解释。无重复运行，未核 parser 一般算法。

测试有效性/范围与回归见表；gold 默认目标受支持但完整性未证。答案暴露/用途保持 check29 unknown、授权 review 暴露在 usage；check40 unknown，封存合规不证明无误拒、漏检或抽样偏差。

## 4. 主审与历史 delta 的决定性复核

L1 旧记录先核 SHA 后阅读。确认：空类别 helper 根因、公开 set_index 目标、元数据长度新增、端到端覆盖不足。修正：已有 dtype 断言的有效覆盖被旧记录低估；物理修复位置并未被测试强制。过时：旧 pytest8 sparse 失败不能套在所引 pytest7.4.4 两侧均通过的条件，旧“需pytest<7”也不是当前所引配方。未核：旧 raw hints/候选/建议回归的实际执行；其链接不在本次授权范围。旧26的 proposed_regression 和“补一条即可准入”、29因题面无gold而pass，均不保留为运行或资格结论。主审 delta 的这些收窄有原件依据。

结构化记录保留规定13个顶层键；checks 为原编号稀疏字典、状态合法、每项有 status/evidence_refs/by；issues 有规定五字段。6/9/23/24/27 比我的初判更保守：初判有限静态/历史 pass 与一般 actor/全部合法解 unknown 不冲突，以后者加范围说明收口更准确。17 的有限 pass 有本次新读 diagnostics 支持；29与usage分开，40未滥用pass。card/record 的 reviewer 未收口标记反映其冻结时点，应由协调者在本 review 后收口，reviewer 不改主审文件。

保留一个非决定性编写问题：本题 record 的2/27/40及部分 scope 带9378特定说明，属于跨题模板残留；本题应使用自己的证据说明，不将其作为6626的正面证据。没有因此翻转核心结论。

## 5. 唯一优先下一步

所需事实交任务二（Claude B）：在真实 actor 入口执行公开两条 from_pandas/set_index 流程，记录真实消息/初态/用户、解释器及 import 位置、原命令/RC，并比较 col1 的类别元数据及 compute 结果与 col2。此项能区分“helper评分成功”与“用户功能且实际开发环境可用”。本 review 没有执行或派发，不能把未来私有 gold 对照诊断当 actor 资格。runner digest 等独立未解边界仍保留，不为唯一优先项删去。

## 封存与引用附录

本次仅新增此review.md；reviewer_initial保持原SHA。路径：

- B：`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925`
- RUN：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925`

| 本题输入 | SHA256 |
|---|---|
| reviewer_initial.md | `36f79fbc1b03c2893756e54ad5f4399d4439de334e3fe993688fc826bf125e61` |
| public_read.md | `514289b22d344ced640f6dc70db2e887584466d2e65e2c18110546dfd96407d5` |
| analysis_before_history.md | `521b13b61b153d74919eb17113f90bab473398d10fbfc782f9c0413ad338ca99` |
| old_findings_delta.md | `bb1f3ede4ea8da26a20b2f2f1ab073a838e7555997e0dc67c34e119e3bdfc323` |
| card.md | `7848f20ba8736f31e92d84f8eed70806ba17d83193cd6b3a0f98727f5f2bf23f` |
| screening_record.json | `f3e6ca80ee48aa81a2e1a1e6f5ade83acebd5ace380d45e7ee2690b3678808db` |

历史只读refs.json中的sources；已先校验下列SHA后阅读：

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-6626.json`，SHA256 `469df00e11632d09f6d7adec272283a80cbf99eecc64b86901936f11f21687b0`。

本题原运行精确引用（未读共享账本其它行）：

- gold：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/gold/ledger.jsonl` 第1行；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/gold/eval_logs/evallog_replay-er19-cv1-dask__da_1ff4e1b3.eval.log`。
- noop：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/noop/ledger.jsonl` 第1行；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/noop/eval_logs/evallog_replay-er19-cv1-dask__da_0b698030.eval.log`。

未进行项目执行/导入/测试、安装下载联网、容器SSH/GPU/模型实验；未改原题/测试/gold/评分/生产文件，未commit/push或派生子agent。未读原评分器实现、实际actor轨迹、完整仓库所有测试；细化实际已读范围以初判和本文列项为准。成本未获工具观测，不造token/金额/CPU耗时。
