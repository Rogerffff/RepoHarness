# coveragepy 5dbb 双模型首轮候选语义非作者窄核

2026-10-03。**两臂最终 `coverage/control.py` 均通过已决定 A 的语义核查；原正式评分各为 1、76／76，与实际源码行为相符。未发现需阻断同版在途普通探针的题面、评分或环境缺陷。Coder 的完整原候选有明确开发测试缺陷，不能作为干净修复示例，也不能称全部新增测试通过。Qwen 修改了公开测试辅助函数，不能据 `test_files_modified=false` 宣称公开测试未改。**

本核查由非作者 Codex 子 agent 执行，只核首轮两份原候选及必要公开 test-like 改动；作者负责完整七维轨迹与效率分析、题卡及总账。已接触私有材料，**不是 fresh 公开读者**。未运行 SSH、Docker、模型、安装或项目测试，未修改共享文件、原件或候选；SQLite 用标准库在内存中解码，并启用 `query_only`。只新增本报告及[机器核对结果](non_author_5dbb_model_semantic_review_20261003.json)。

## 固定范围与证据

题 ID：`coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`。使用材料 038／039／068、R5、76 键；用户已选 A：同 slug 的后续 once 警告不显示，即使消息不同；不同 slug 各显示一次。本轮没有重开这一目标，也没有给 `slug=None`、跨实例或混合 once 调用新增验收条件。

原件目录，下文分别简称 `C/`、`Q/`：

- `C/`：`runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-coveragepy5dbb-coder-a1/`。
- `Q/`：`runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-coveragepy5dbb-qwen36-a1/`。

两份 `attempt/frozen/baseline.tar` 中相关源码均与各自 manifest 摘要相符：原 `coverage/control.py` SHA256 `7d6a28cda461998f6a02a771e243198a5d62251efeafd65081d3c6433dd32cef`；原 `tests/coveragetest.py` SHA256 `7e04a0cb73d00104e41090928dafaf2964d6d41cc002a76fe96f62bdd7e9c83d`。原基线 commit 为 `8240c58c90a0157178e9c5f6fedd9f003aab892d`。逐项解码原 FrozenPatch，Coder 8 项、Qwen 4 项，全部内容 SHA 与声明一致；源码差异及 Git blob SHA 存 JSON，可对照原 `.diff`，没有用整理版补丁替代原身份。

| 模型 | 原 FrozenPatch digest | 源码语义结论 | 完整候选限制 |
| --- | --- | --- | --- |
| Coder a1 | `9b8da278e28bc6c8d6e9845afbfcee078208f34554d5fd35e1555bb12763707b` | 按 slug 的 A 通过 | 保留两个明确失败的新增开发测试、多个打印脚本及生成物 |
| Qwen3.6 a1 | `736f5598979392562bf0524a284a378b6729e7484e088c1b6e8eecc44b587e0d` | 按 slug 的 A 通过 | 多余的公开测试替身扩签名及生成物，需要准确披露 |

题面 SHA256 为 `b2a7f5fb3e3c76a8896ac0f8afb2e9b534bcfbd28baf6ebbe647ddd0857b2415`。已有 [R5 CPU 非作者核查](non_author_5dbb_cpu_review_20261003.md) 与 GPU 有界执行核查按适用身份复用。本轮未重复 98 件原件回收、模型配置、运输、镜像或清理审计；code_v3 元数据关联缺口已有外部补证，不因这一历史缺口抹平原件或要求重跑。

## 两臂源码如何修复根因

以下行号指从原 FrozenPatch 解码的最终源码，不是 `.diff` 文本行号。

**Coder：** 构造函数 `coverage/control.py:209–210` 初始化实例集合 `_once_warnings`；`:338` 增加 `once=False`，消除原 `TypeError`。`:345–347` 先检查 `disable_warnings`，被禁用的 slug 立即返回，不写入一次性集合或 `_warnings`。`:350–355` 只在 `once` 为真且 slug 非空时检查、登记 slug；同 slug 的第二条在追加消息之前返回。`:357–362` 仍按原顺序记录原消息、追加 slug、处理 pid debug 并写 stderr。

**Qwen：** 构造函数 `coverage/control.py:210–211` 初始化 `_warned_slugs`；`:339` 增加默认 `once=False`。`:346–348` 保留禁用警告的优先返回；`:350–352` 对已记录 slug 的 once 调用返回；`:354–358` 对首次有效警告追加消息、格式化 slug 并登记集合，`:359–361` 保留 debug 和 stderr 输出。登记位置与 Coder 有小差异，但在本题正常执行路径上行为相同。

两份修复都满足以下具体行为：

1. 第一次 `once=True, slug="bot"` 输出并记录消息；同 slug、不同消息的后续 once 调用不输出，也不追加 `_warnings`。
2. 另一个 slug 不命中原集合，可以独立输出一次。去重依赖 slug，不依赖消息内容或单个全局“已警告”布尔值。
3. 普通 `once=False` 调用不检查、不更新一次性集合，仍可以重复输出。同 slug 曾发过 once 警告也不会让后续普通警告被永久禁用；集合没有写入 `config.disable_warnings`。
4. 被禁用的 once 警告不消耗一次性状态；以后解除禁用时首次实际显示仍可发生。该结论来自代码执行顺序，原 GPU 轨迹只覆盖其中的禁用输出观察，不冒称完整组合边界实测。
5. `_warnings` 保持原来的消息记录格式，不被当作包含 slug 的字符串集合使用。两臂均为实例内集合，没有跨实例状态。

正常非 once 回归有源码差异与既有原轨迹双重证据。Coder `attempt/trajectory.jsonl:263/276/289` 分别显示公开 warn6、API74、testing22 通过；Qwen `:241/277/323` 显示相同范围通过，其中后两条命令带 `| head`，应依靠打印出的完整测试小结解释，不能单靠外层返回码。`coverage/report.py:68–86` 的 `ignore_errors` 异常处理、`couldnt-parse` 警告调用均未修改；原警告回调不带 once，因此保留原重复警告、ignore／raise 选择和输出格式。未要求把内部所有警告改成 once。

两份候选对 `slug=None` 或空 slug 都不去重；Qwen 原轨迹 `:255/259` 明确打印无 slug 的两条 once 警告均出现。本版本没有把无 slug 行为定为新的条件，这不构成 R5 的具体误拒或错误通过。一次性集合均在 `stderr.write` 之前登记，若 debug／输出发生异常，重试可能被已记录状态抑制；未见当前运行证据，作为异常边界限制记录，不扩大为当前阻断。

## Coder 的公开开发产物

Coder 首两次 `_warn` 实现尝试有真实缺陷：原轨迹 `:123/:171` 编辑后，`:162/:184` 的工具输出仍同时显示同 slug 的第一、第二条。最终 `:206/:215` 改用独立 slug 集合，`:224/:228` 仅显示第一条 `bot` 与另一条 `bot2`，与最终冻结源码一致。语义通过只针对最终候选，不把中间尝试记成正确。

**C1，P2，test_only：`test_once_functionality.py` 留下两条已知失败测试。** 冻结文件 `:12`、`:33` 调用 `cov.assert_warnings(...)`，但该 helper 是 `CoverageTest` 的方法，不是 `Coverage` 的方法。原轨迹 `:307/:311` 保存运行命令与 `2 failed`、`AttributeError: 'Coverage' object has no attribute 'assert_warnings'`。后续读了公开 helper 并承认测试结构不对（`:351`），只另建 `final_validation.py`（`:355`）；没有修正或删除失败文件，原 FrozenPatch 仍包含它。

影响与建议：完整原候选不适合作为干净修复示例；全树默认 pytest 可能收集这两个新增测试。正式入口只选择 `r2e_tests`，因此这一缺陷没有进入 76 键，也不证明题面／环境／评分有错。若以后整理为可合并修复，应删除探索脚本或用真正的 stderr 捕获断言修复它，派生新的工件身份；原首轮补丁与评分保留，不用整理版覆盖。

`comprehensive_test.py`、`final_validation.py`、`original_issue_test.py`、`test_once_issue.py` 都是公开示例的开发探索或打印展示。它们没有修改既有公开断言、expected、marker 或正式入口。原 `:250/:368` 的输出确实显示同 slug 去重、不同 slug、禁用和普通警告；但 `final_validation.py` 未对输出做断言就返回 True，末尾“all tests completed successfully”不能解释成全面自动验证。`original_issue_test.py` 只支持原例无 TypeError 的观察。

## Qwen 的公开 helper 改动

Qwen 原轨迹 `:201` 修改 `tests/coveragetest.py:267`：

```python
def capture_warning(msg, slug=None, once=False, **kwargs):
```

独立字节比较确认该文件**只有这一处签名变化**；slug 格式化、`saved_warnings.append`、所有正／负断言和 finally 恢复均逐字不变。它仍然记录每次调用，不实现生产 `_warn` 的 once 去重。原 helper 本来就用替身捕获“被调用的警告”，包括禁用的警告；这一边界不能作为真实输出去重的测试 oracle。

用途可以解释为让公开测试替身兼容 `_warn` 的新参数，但当前候选没有新增内部带 once 的调用，已有公开回归不依赖此修改；轨迹也没有先出现 helper TypeError 再修复的过程。因此它是多余的开发辅助修改，不能称为本题修复必需项。`**kwargs` 还会让未知参数在替身里被忽略，限制未来参数误用的检出能力；当前材料没有依赖这一新增行为，不把假想未来测试失败升级成阻断。

本次未发现删断言、改 expected、skip 或伪造评分。正式 once 两键直接调用真实 `_warn` 并检查 stderr，没有使用 `assert_warnings` 替身；现有用该 helper 的正式回归仍使用原参数调用，断言行为未变。公开 helper 没有替代源代码去重缺陷让 once 键变绿。Qwen `:219/:223` 的公开直调也只输出首次 `bot` 与首次 `other`；`:255/:259` 同时展示普通警告可以重复、不同 slug 各一次。

## 二进制生成物与正式评分边界

两臂原 FrozenPatch 均包含 `.coverage` 和 `tests/modules/.coverage`，各 53248 字节。SQLite 解码得到 coverage schema 7，无自定义 view／trigger，也没有评分逻辑、测试断言或可执行代码。

| 工件 | Coder 原内容 | Qwen 原内容 | 解释 |
| --- | --- | --- | --- |
| `.coverage` | `sys_argv=['test_once_issue.py']`，测量表全空 | `sys_argv=['-c']`，测量表全空 | 公开 MCVE 的 `cov.load()` 初始化空数据文件，与 `coverage/sqldata.py:239–257` 创建 schema／元数据的行为一致 |
| `tests/modules/.coverage` | `sys_argv` 指向公开 API74 测试命令 | `sys_argv` 指向公开 API74 测试命令 | 9 个公开 pkg1 模块路径、1 个空 context、3 条 line_bits，arc／tracer 为零；与公开 API 模块测试产生的数据相符 |

完整元数据、摘要和表计数存 JSON。两个 `tests/modules/.coverage` 的内容不同在命令参数／时间等正常生成元数据；不是测试源码或 expected 修改。这些文件不是功能修复必需项，且实际被原投射运输，不能说评分前都被清理掉。本题正式 once 测试在 `CoverageTest` 的临时目录中创建实例并读 stderr；源码修复也不读取 DB 决定去重。现有模块测量路径从新 `Coverage` 的 start／get_data 收集数据，没有从这些 DB 恢复去重状态。未发现本次正式验收由生成物注入答案的具体路径；这不等于任意数据文件修改都可安全接纳。

两个 report 的 `patch_hygiene.test_files_modified=false` 指正式受保护测试路径，不是公开测试文件全集。Qwen diagnostics 已列 `tests/coveragetest.py`、`tests/modules/.coverage`；Coder diagnostics 也列新增测试脚本与模块 DB。正式 setup 恢复的是 3 个 `r2e_tests` 文件并重写 `run_tests.sh`，没有把 Qwen 的公开 helper 恢复成原版。该 helper 确实随原工件进入 grader 并被导入，上述审计正是据其实际内容作出结论。

本轮重新读取两份原 eval.log 的最终 pytest 状态行：各恰为 76 个唯一 expected 键、76 PASSED，无缺失、额外或错配。Coder once 两键在 log `:7825/:7827`，Qwen在 `:7818/:7820`；真实测试退出码分别见 `:7880`、`:7876`，均为 0。评分正确性还依据正式 once 测试直接走真实 `_warn` 的调用链及公开 A 一致性，并非从 reward 1 推定源码正确。

## 用途与停止条件

- **题级结论：** 公开 A、材料 038／039／068、76 键与两臂最终源码行为一致，没有发现须修订材料或补跑同版 CPU 的新阻断。已有 CPU 与执行证据可以按适用版本复用；候选开发垃圾文件不构成首轮普通探针重跑理由。
- **模型结论：** 两份源码修复在本题首轮表现正确。Coder 的开发测试错误和打印式“成功”须作为候选质量限制保留；Qwen 的公开测试辅助修改及生成物须披露，不能报“完全未改测试”。
- **当前允许用途：** 标明 R5 自建修订版本的普通探针结果、源码语义及候选质量分析；后续 GPU 第二阶段按原批次另安排。单次首轮不能推出稳定能力，不能报原 benchmark 成绩或授予训练资格。
- **后续修复范围：** 如需干净可合并示例，再整理候选开发文件，并保存新派生身份、按修改影响验证；本报告不修改原候选，不把整理工作变成新材料发布或全套 CPU 审批。通用测试控制保护的完整安全验收继续保留既有边界。

停止条件已满足：原源码、最终冻结内容、真实公开观察、正式评分调用链及全部 test-like 内容已完成有界核查；不存在需立即通知 GPU／发布停发同版作业的具体缺陷。作者可据此落首轮题级结论，同时保留候选质量、单次样本与用途限制。
