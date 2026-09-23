# CR2' 外层 pytest 完成判据的聚焦复核（2026-09-19）

**结论：原默认格式反例已修复，但 CR2 还不能核销。保留一项同根因 P1：最后一个被匹配的 pytest 摘要，不一定属于外层命令。** 本轮没有新 T0，不重开 CR1、CR3、反作弊、资格记录分期或资源配额决定；不阻止 B 继续环境工作。

## 1. 审查对象与已通过部分

- 相对上轮 78 文件快照，只变更 `rh2/src/repoharness2/grading/manager.py` 与 `rh2/tests/grading/test_w3b_grader_profile_unit.py`。HEAD 为 `bac7659ea70cc07a3a8c872a29e7659a894afc5a`，被审内容仍有工作区改动。78 文件与作者远端独立树 SHA-256 全部相同，审查期间未再变化，见 [快照](source_snapshot.json) 与 [结束核对](review_end_source_check.json)。
- 上轮真实 dvc 镜像 Python 3.9.19 / pytest 6.2.3 的嵌套日志重放后，当前 manager 返回 `tests_failed / 0 / source_rule`；实际 orchestrator → miles buffer → 训练转换得到 `[1, 0]`，组可消费。**这个原反例可以核销。** 本轮只是重放既有原始日志，没有重启云端环境实验。
- 本机 Python 3.12 / pytest 9.1.1 五种输出形态矩阵共 25 场景、30 次 manager 调用：10 个真实语法 collection/conftest 正控保持 `candidate_execution_failed / 0`；10 个无关路径正反控保持 None；5 个普通 Python 捕获输出例保持来源 0；嵌套 pytest 的四个非 quiet 例恢复来源 0，quiet 例仍失败。
- 带边框的收尾格式中，`error/errors`、`warning/warnings`、`rerun`、`deselected`、`xfailed/xpassed`、`no tests ran` 与 `(0:00:01)` 时长后缀均按现有口径解析。裸收尾行未被识别。计数格式对照是构造文本；没有宣称分别运行了 pytest 7、8 或所有插件版本。

## 2. CR2' 余项：P1，子会话摘要被认作外层完成

**位置：** `manager.py:1137` 的 `_PYTEST_FOOTER`、`:1145–1148` 的最后匹配选择、`:1180–1181` 的正常完成短路。后者使 `_decide_execution_failure` 在 `:3145–3150` 直接走 `source_rule`，跳过全局失败的资源、资格与候选归因。

**不变量：** 正常完成的外层测试应保持来源评分；真正的全局启动/收集失败应继续三路判定。子进程的成功或失败摘要都不能代替外层完成事实。以下都是真实 pytest 自然输出，未伪造状态行、未修改评分器或参考测试来制造结果。

| 真实进程对照 | 识别到的摘要 | 现行结果 | 应有结果 |
| --- | --- | --- | --- |
| 父 `-rA` 正常完成，子 pytest collection 失败 | 父 `1 failed, 1 passed` | 来源 0 | 来源 0，通过 |
| 同例仅把父命令改成 `-rA -q` | 子 `1 error`；漏掉父末行 `1 failed, 1 passed in …s` | None；实际组 `[1,None]` 被丢弃 | 来源 0、组可消费 |
| 父 `-rA -q` 收集阶段先运行成功的子 pytest，再因缺依赖中断 | 子 `1 passed`；漏掉父末行 `1 error in …s` | 来源 0；实际组 `[1,0]` 被送入训练 | 无资格且没有语法复证，保持未确定 None |
| 父普通 `-rA`，conftest 先运行成功子 pytest，再因缺依赖启动失败，rc=4 | 只有子 `1 passed`；父没有自己的收尾行 | 来源 0 | 保持未确定 None |

前两类 quiet 日志失败来自强制要求 `===` 边框。最后一类说明**只把边框改成可选还不够**：即使没有 quiet，父启动失败时也可能完全没有收尾行。实际合并输出中，父 conftest 错误还可能先于子进程的捕获输出出现；不能简单假定最靠后的成功摘要属于父进程。

两个方向的影响分别是：丢掉本应训练的失败样本；把未能归因的全局失败当作普通负样本训练。**生产函数及组运输可达已经验证，题库发生频率未知。** 216 条固定命令快照没有显式 `-q`，因此不把 quiet 例写成已在选定题库发生；conftest 例使用的普通 `pytest -rA` 与当前入口一致。这是完成证据不足，不涉及本轮已递延的 stdout 反作弊设计。

证据：

- [真实 pytest 矩阵](matrix/probe_pytest_shapes.json)、[简表](matrix/summary.json)。每个反例保留真实 stdout、退出码、来源 verdict、manager decision 与 compile 次数。
- [原真机日志重放、quiet 双向反例与实际组运输](footer_review_result.json)，脚本 [probe_footer_review.py](probe_footer_review.py)。
- [普通模式 conftest 对照](startup_control/result.json)，脚本 [probe_startup_control.py](probe_startup_control.py)。测试文件保持固定，仅改候选源码；该例无环境资格，不应绕过 P-A。

**修复建议与分期：** 在核销本次 P-A/CR2 修复前补齐这个局部判据。支持 bordered/bare footer；正常完成的正向证据还须与已有外层命令结束事实相容。明确的启动/collection 异常退出不能被一个子 pytest 的成功摘要覆盖。不要把非零退出码直接改判候选 0 分，也无需修改 binary reward、来源参考键或引入新安全策略。

为检验改动是否仍可局部收敛，另做了**未实施的设计对照**：仅在探针进程内兼容裸 footer，并在已知 `test_rc` 不属于 pytest 正常完成的 0/1 时禁用正常完成短路，让现有三路判定继续运行。28 个既有/新增对照均符合预期，见 [结果](hypothesis_result.json) 与 [脚本](probe_narrow_hypothesis.py)。这证明一个窄修方向可行，不等于该实现已获交付或对任意复合命令的段末 rc 均充分；具体落地要说明所用退出事实来自哪个命令。

**验收与停止条件：**

1. 默认与 quiet 的“父正常完成、子 collection 失败”都回来源 0，实际组含 `[1,0]`。
2. quiet 的真实外层 collection 中断，以及普通模式的“子成功、父 conftest 启动失败”，均不借子摘要走来源 0；无资格的这些对照保持 None。
3. 保持已通过的 10 个语法正例、原无关路径例、普通捕获例和原 pytest 6.2.3 日志。满足即结束这一边界的扩审；不重跑全题库/GPU，不重开已核销项。

## 3. 本轮验证与限制

| 验证 | 本轮主审结果 |
| --- | --- |
| `uv run pytest tests/grading/test_w3b_grader_profile_unit.py tests/adapters/test_batch4_pa_transport.py -q -rs`（rh2 目录） | **58 passed**，见 [输出](pytest_targeted.txt) |
| `uv run ruff check src tests scripts` | 通过，见 [输出](ruff.txt) |
| 原真实 pytest 6.2.3 日志 → 当前 manager → 实际 miles buffer/转换 | `[1,0]`，组可消费 |
| 当前真实 pytest 9.1.1 多形态/启动对照 | 已复现上表剩余边界；不是仅对手写文本运行正则 |
| 59 条既有真机日志离线对照 | 53 条 e2 A/B + 4 条 dvc-2141 + 2 条新 PA 坏补丁；日志 hash 全匹配，本次完成短路没有改变其形状判定。见 [结果](saved_corpus_result.json) |
| 远端核对 | 只读 SHA-256，78 文件一致；没有启动远端容器或干扰 B 作业 |

59 条离线对照是 `reference_all_missing` 分支形状的比较，不等于重新评分、重新鉴定环境或证明全题库没有嵌套调用。未复跑作者报告中的全量 1408 非 Docker / 34 Docker，也不将作者数字当作本轮主审验证。

复现可直接从上述 JSON 的真实日志调用当前 `classify_execution_failure_shape(log, rc, zero_parsed=False)`，完整运输脚本则应复制代码到新的同层证据目录再运行，避免覆盖写一次的 fixture 工件。生产逻辑、维护测试、旧 evidence 均未修改；本轮只新增本目录和 A 线/原计划登记，没有提交。

范围：A/B/E/F/G/N 重点验证完成事实、评分语义、真实入口与外部格式；J 检查“外层”命名及注释是否有证据支持，M 保留 sidecar/组运输证据，I 以上述停止条件控制范围。C/D/H/L 的配置、状态 owner、资源清理与性能实现没有新增改动，沿用此前核销结果，不展开重复审计。
