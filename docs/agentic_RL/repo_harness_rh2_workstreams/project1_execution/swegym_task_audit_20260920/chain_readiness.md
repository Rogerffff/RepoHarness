# SWE 评分链已登记问题：当前状态核对

2026-09-20 / Codex。范围为现有问题的状态与分期，不是新一轮评分安全总审计。基线为 `e3d120b5` 加当前工作区；只新增本文件，未修改生产代码、维护测试或历史证据，未运行 Docker、远端、模型或全题库。

**结论：可以继续 216 题的静态逐题复核，不需要先把正在做 R2E 的 Claude 拉回重修整个 SWE 评分链。** 原 CR1–CR3、跨 manager 误清理、中断事实主路径与 R-0 收口退出码主路径均已独立核销；本次当前代码窄测试也通过。仍欠的工作应按下面的具体入口安排，不能沿用 09-19 19:00 的“生产未修”快照。

3–5 题真实基座探针的关键前置是**选中题的修复环境确实被 agent 与 grader 消费，候选代码确实生效，资格/参考与该环境身份一致**。现有 replay driver 可以引用诊断派生镜像和资格账本；这不等于正式 actor 已能消费本地派生环境。若探针指定正式 actor 入口，须先补/核验这个入口接缝；若是独立 harness 解题后经真实 RH2 grader 重放的小批诊断，可沿现有诊断路径设计，但结果不能称为正式 actor 全链验收。

## 已核销

下列“核销”只指各原问题及登记的验证范围，不等于全部题目合格或整个训练系统完成。

| 已登记项 | 当前证据 | 静态复核 / 3–5 题探针 / 正式训练的额外阻塞 |
| --- | --- | --- |
| P-A CR1：普通路径提及误作候选语法因果；原 R2 复证导入候选模块、R3 终止事实未知仍给 0 | manager 只关联语法异常实际位置与编译复证；`python -I -S` 隔离；未知必要终止事实不作候选归因。原独立复核及当前对应单测保留 | 均无；无需重修 |
| P-A CR2：捕获的 traceback / 子 pytest 收尾污染外层判定 | 以外层 `test_rc` 0/1 与最后摘要共同判断正常完成；bare footer、pytest-pretty、error 计数有维护测试。[最终收口](../batch4_scoring_20260910/chainfix_footer_followup_20260919/README.md)明确核销 | 均无；不重开任意嵌套运行器扩审 |
| CR3 排除区缓存误删、formal 缓存计数未持久化 | `build_cache_normalization_command` 先剪 manifest 排除区；`bringup.py:757` 序列化 `omitted_cache_counts`。[后续复核](../batch4_scoring_20260910/chainfix_followup_20260919/README.md)有真实 Git/manifest 与 fsync 后重读证据 | 均无 |
| 原 R6 缓存反向类型、R7 冲突诊断、日志全文释放、派生 inspect/后观测取消账本、派生资格按实际 ID、grader `--init` | [09-19 原复核 §4](../batch4_scoring_20260910/chainfix_review_20260919/README.md)已分别核销；当前窄测试覆盖相关 replay/profile 路径。完整冲突详情在 execution audit；tag inspect 后重指仍是已接受的条件性残余 | 均无新增阻塞；不以 `--init` 宣称 Modin 配方已解决 |
| 19:00 跨 manager 删除活跃长任务容器 | `manager.py:1552` 的 `startup()` 恒返回 `[]`；实例清理只沿自己的 records。当前 manager 摘要与[独立清扫复核快照](../manager_cleanup_review_20260920/snapshot_after.json)相同 | 均无；崩溃残留仍需确认所属 run 结束后精确清理 |
| exec=137 且 inspect 尚 running / 已 stopped 时丢中断事实、误写完整日志 | `manager.py:2398, 2974–3014` 保留已交付输出和退出码，未收尾被信号终止记 partial、infra / None；[独立清扫复核](../manager_cleanup_review_20260920/README.md)有两支及正常正负分对照 | 均无；不涵盖下表的取消窗口残余 |
| R-0：grader 未收口而 CLI 返回 0；年龄字段删除造成实验脚本不兼容 | `final_exit_status` 区分正常/晚清成功 0、停批 2、最终未清容器 3；CLI 捕获 typed 停批；两份实验脚本已适配或标注历史用途。[R-0 独立复核](../r2e_grading_wiring_review_20260920/followup_20260920.md)已验证真实控制流主路径 | 均无；reward 0、逐题 stage_error、整批运行失败仍须分别对账 |

## 已实现待独立验证

**上述清单中没有核心修复仍只停留在“作者称已实现、等待独立验证”。** manager 清扫修复和 R-0 主功能都已有 09-20 的独立复核；本次也重新执行了相关维护测试。不得把 R-0 的诊断残余写成其退出码主功能尚未验。未实施的正式资格来源、派生环境正式入口和 F4 构建归因应列在“仍欠”，不能写成等待验收。

## 仍欠：最小动作与 owner

| 项目与当前事实 | 阻塞静态逐题复核？ | 阻塞 3–5 题模型探针？ | 是否仅正式训练前置？最小动作 / owner |
| --- | --- | --- | --- |
| **R-0 CR1 / P2**：未捕获异常或取消继续传播，但 CLI `finally` 仍可能打印 `final_status=0/ok`（`scripts/replay_grade.py:99–104`） | 否 | 不阻塞现有诊断路径；派发方须以真实进程退出和逐题账本判定，不能把摘要 0 当成功 | **不是训练硬闸门**。按既有分期，在 R-f 或摘要消费者启用前补异常/取消状态；保留异常传播与 0/2/3 正控。owner：B driver 实现者（R2E Claude） |
| **R-0 CR2 / P2**：scope 异常覆盖报告返回后，已落盘日志/sidecar 未挂入停批账本；取消行新 `test` 块仍空（adapter `replay_grade.py:588–630`） | 否 | 不阻塞正常主路径；异常案暂按原始日志/sidecar核对，不能把空字段解释为无异常 | **不是训练硬闸门**。在 R-f 异常对账前统一正常/取消/typed 停批的事实填充，未知仍为 None。owner：B driver；如需 manager 引用字段，与 A 串行 |
| **manager 清扫复核 CR1 / P2**：exec 已返回后在 inspect/读 tee 的 await 被取消可丢已交付输出；短 tee 可覆盖较长 stdout（`manager.py:2394, 2980`） | 否 | 否；原反例保持 infra / None、取消传播及清理，没有新增错误 reward | **不是训练硬闸门**。后续维护先保存已交付结果，再用 tee 补充；复验两个取消窗口与短 tee。owner 建议 A manager 实现者，作者处置仍待回填 |
| **R5 正式资格来源**：构造器→spec→manager 已通；`PreparedTaskFace.load()` 无资格输入，bringup 两个 loader 均不提供资格（`prepared_task_face.py:387–420`、`bringup.py:1188–1208`） | 否 | replay 可用现有 `--qualification-ledger`；正式 actor 缺资格时保守 None，仍可做有限诊断，但不能声称已验证完整候选失败归因 | **正式采用已定资格机制前须接齐**，无需重问是否使用资格。B 流水线产出选中环境的真实资格，正式 loader 的单一 owner 接入并验身份/脚本失配。不是现在给 216 题全部补跑 |
| **修复环境的正式 actor 消费入口（已披露范围边界）**：诊断 driver 支持 `--derived-image`，正式 face 仍取 public bundle 的 image/digest；R2E 计划 §3.5 明确不在本片接 SWE overlay | 否 | **若探针要求正式 actor 在本地派生 SWE 镜像运行，须先补/核验；独立诊断入口需证明实际消费修复环境** | **不只是训练前置**，也影响声称“真实基座在已修环境”的有效性。先固定 3–5 题的实际启动入口、镜像身份和 recipe；复用已支持表示或按 D4=B 分工接入口。owner：B 环境流水线 + actor 入口单一写入者；不把基础镜像 digest冒作派生身份 |
| **F4 构建切片**：ERR trap 仅记录部分命令失败；关键构建结果、产物生效、候选归因仍未完成。当前 P-A 只比较安装段末码与资格基线，不是构建生效证明 | 否，正可静态定位相关题 | **选中题若依赖未确认生效的构建，先处理该题**；纯 Python / 已有候选生效证据的题不必等全套构建归因 | **按题与构建切片安排，非整个池的新硬闸门**。B 逐题确认候选实际被测试；需要编译失败负信号时由评分实现者补已批 producer。详见 [实施计划 F4](../batch4_scoring_20260910/impl_plan_20260915.md) |
| **已知 stdout/hook 信任边界** | 否 | 否；正是按用户既定流水线/真实模型探针取证的对象 | **不能自动升级成全部正式训练前置**。保留已登记风险，按真实证据处置；不借本轮新增防作弊平台。owner：B 筛题/基座诊断 |

最小安排：静态逐题复核继续；R2E Claude 在下一次 driver 窄改顺带收 R-0 两个诊断 P2，无需停下 R2E 重做 CR1–CR3。3–5 题探针先确定环境入口与候选生效证据。A 的诊断残余留原 owner，正式资格与派生环境加载由流水线接入，不混成新的评分安全总审计。

## 本次验证与限制

从 `rh2/` 执行：

```sh
.venv/bin/pytest -p no:cacheprovider -q tests/grading/test_manager_unit.py tests/grading/test_w3b_grader_profile_unit.py tests/adapters/test_replay_grade.py tests/adapters/test_batch4_pa_transport.py
```

结果：**156 passed in 18.13s，退出码 0**。没有重跑全套、Docker、既有真机评分或合成攻击矩阵。历史独立复核数字只作既有证据，不冒充本次执行。当前代码直接确认 R-0 两个残余、manager 取消窗口残余与正式 loader 缺口；未扩大搜索新问题。

本次核对核心源文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `rh2/src/repoharness2/grading/manager.py` | `eadaa64acc2e9dc358ad4c7c4f9ad3bb60d81a1c72298a41dabbdf6397ad6342` |
| `rh2/scripts/replay_grade.py` | `935d569fcb68af9341be824c1bb0aba7ff402ee50176d9637b403ed0077803e5` |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py` | `3afe4a6ff5d8764c8fe942bd06729e7838073df0ac8c7030239a3e23ec5979a4` |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` | `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3` |

本轮没有改变 reward、资格、安全边界、资源配方、题目准入或既定分工。
