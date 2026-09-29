# 独立核对：材料、reward 与原始证据

2026-09-24，角色：Falsifier / Training Semantics Reviewer。只读核对本地材料和历史日志；没有运行 Docker、远端作业、48 题重评，也没有修改生产代码、测试、数据或历史 evidence。对账工具、测试顺序问题与静态筛查 export 由主审覆盖。

**结论：在本次证据范围内，接受 pandas `4ec87eb9` 与 scrapy `cfed9b66` 的修订及所报 noop/gold 结果；未发现需要阻断这两题修订的新问题。** orange3 仍是有限诊断，不能据此关闭残余风险或宣布资格通过。

## 核对产物

- [只读探针](reward_evidence_probe.py) 与 [结构化结果](reward_evidence_probe.json)。运行：`python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_batch2_review_20260924/evidence/reward_evidence_probe.py`。
- 探针独立提取 pytest 摘要 nodeid，不调用生产 parser 或 reconcile；验证 8 条正式行、16 份 dryrun、7 份 orange3 诊断日志及 48 份逐题状态。全部断言通过。

## 两题材料与评分语义

**pandas**：私有 conftest 中两个 fixture 的 decorator 和函数体与捕获的 base `pandas/conftest.py` 逐字相同。来源文件重新计算的 git blob 为 `46975aa039b18fbb29f9edffb339d0ad96066ddb`，与来源记录一致。没有新增 hook、autouse、skip 或删改测试断言。隐藏 `test_1.py` 与原修复提交的 `pandas/tests/groupby/test_quantile.py` 完整新文件相同。

原断言要求组内 `[0.2, NaN]` 的 quantile 正确忽略缺失值，覆盖 scalar 和多 quantile；Float32/Float64 扩展 dtype 对应题面所述部分 NA 场景。新增 fixture 展开 5 个浮点参数和 8 个整数扩展参数，因此 expected 仅删 2 个未展开 ERROR 键、加 13 个 PASSED 键，其余 224 键状态不变。noop 原有 allNA 两键加新恢复的 NA_float 两键失败，gold 全部通过；不是通过放宽断言让 gold 满分。

“第一次”只能限定为恢复了题面 `[2.5, pd.NA] → 2.5` 的**部分 NA 场景**。原材料的 allNA 两条 F2P 已验证 `[pd.NA, pd.NA] → NaN`，仍是与题面相关的信号，不能说原来完全没有题面信号。`NA_int` 用例实际输入是 `[2, 5]`，没有缺失值；展开的 8 个整数键在修订后 noop/gold 都通过，本次恢复的是回归覆盖。

**scrapy**：恢复的 egg 为 2231 字节，修订文件与捕获的 base 文件逐字节相同；重新计算 git blob 为 `238517694b306bb2daa59a6734d26f14f0a55c98`。两份来源隐藏测试分别与原修复提交 `tests/test_utils_misc/__init__.py`、`tests/test_middleware.py` 的完整新文件相同。`test_2.py` 修订只改变两处模块自引用字符串，断言保持不变。

`test_instances_from_settings` 同时要求字符串引用解析为 M1、类 M2 被实例化、已有 M3 实例保持身份（`assertIs`）。新支撑让该键成为真实目标信号：noop 在对 M2 调 `.rindex` 时失败，gold 能走完三条断言。源码还能说明仅修 load_object 仍不足：base middleware 对 M3 实例执行 `mwcls()`；这是源码推断，本次未运行这种部分候选。只加 egg / 只改路径的分离 dryrun 与各自修复目标一致。

| 题 | 正式 noop（各两次） | 正式 gold（各两次） | dryrun 对照 |
| --- | --- | --- | --- |
| pandas `4ec87eb9` | reward 0，233/237 | reward 1，237/237 | 每次逐键相同 |
| scrapy `cfed9b66` | reward 0，7/9 | reward 1，9/9 | 每次逐键相同 |

两题原材料 gold dryrun 的摘要重新生成 JSON 后，与原始行 `expected_output_json` **逐字相同**。修订后两次 gold dryrun 与最小修订 expected 逐键相同；正式八行的日志 SHA256、解析键集、差异集、reward、recipe、镜像身份、源码投影、`/testbed` 导入路径、完整日志和清理结果均核对通过。gold 投影仅含生产源码，未包含隐藏测试或新增支撑。expected 的变化有原断言、缺失支撑和独立试跑支持，没有发现任意按 gold 输出重定义正确性的证据。

边界：本次核对的是已捕获来源快照及其声明的 git blob，没有重新向上游拉取对象。修订后无同材料版本的外部独立 runner，dryrun 是不同执行入口的对照，并不消除两者共用测试断言的限制。

## orange3 诊断支持与不支持的结论

日志确认 SciPy 1.4.1、1.5.4 变体保留 scikit-learn 0.22.2.post1、numpy 1.17.5，setup 全部成功。两版本的 noop/gold 都使 `test_LogisticRegression`、`test_coefficients` 从 FAILED 变 PASSED；两个 scorer 键仍因特征排序断言失败。1.4.1 的 gold 两次、1.5.4 的 gold 一次；各有 noop 一次。原版本 gold 日志直接保留了 `test_coefficients` 的 `.decode` AttributeError 路径。

三个换版 gold 的**另一次开启警告的运行**均出现 `ConvergenceWarning status=1`。这支持“这些实测变体在发生未收敛时能够给出警告而不被 message 类型错误打断”，不证明任意正确候选、任意来源版本运行或每一个 fit 都必然进入出错分支；过滤后的 warn 日志也没有逐个 fit 的归属与次数。1.6.x 未测，1.5.4 只是本次试过的较高版本；两个 scorer 的根因仍未定位。

非阻断措辞建议：`acceptance_20260924.md:129`、`decisions.md:21` 和 orange3 `screening_record.json:260` 的“说明来源环境里出错分支每次都会走到”应限定为上述已观测范围。可改为：“三个换版 gold 的警告复跑均观测到未收敛；来源版本的已采样日志已观测到对应解码错误，但尚不能推广到所有正确候选。” 当前仍将 orange3 保留为 `grading_ok_open_items` 是恰当的。

## 状态统计

直接遍历 48 份 `screening_record.json` 得到：`environment_qualified=32`、`qualified_with_recipe=2`、`qualified_with_revision=4`、`grading_ok_open_items=10`，`needs_decision=0`。结果表 48 行的状态逐一与记录相同；只有这 10 份存在 disposition.open_items。

10 个未完成题为其余 pandas 6 题、orange3 `9b5494e2`、pillow `2b061b68`、scrapy `9a15fcf8`、coveragepy `5dbbe143`。四个修订资格题是 coveragepy `016af5f6`、datalad `58ba5165` 和本批两题。统计成立，不能据此把 48 题解释为已选定的训练池。
