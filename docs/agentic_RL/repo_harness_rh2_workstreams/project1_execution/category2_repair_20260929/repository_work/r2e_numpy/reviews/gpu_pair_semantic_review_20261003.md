# NumPy 两模型首轮候选的独立语义核查

日期：2026-10-03。范围仅限 `numpy__d805e9b66228e68a0eb14d901cd350159c49af18` 的 Coder／Qwen3.6 首轮原候选；不扩大到二维、性能或通用打印平台。

## 结论

两份原始 `reward=0` 均有真实、公开可见的失败依据。Coder 没有修复公开问题，并把显示的整数变成带引号的字符串；Qwen 已修复公开默认实例的值选择和省略提示，但缺少省略号后的逗号，未保持公开示例及该版本 NumPy 的摘要格式。Qwen 应记录为**内容摘要接近正确、公开格式兼容失败**，不应描述为“完全没有修复省略问题”。本次没有发现要求修改题面、隐藏测试或 CPU 配方的新题级阻断；两份样本可保留为完整的能力分析案例。

这里的“完整”指执行和证据已完整回传，不表示候选满足全部要求，也不表示本题已有训练资格或确定的 RL 信号。不存在必须通过新增运行才能裁定这两次原始零分的决定性缺口。

## 核查身份与方法

核查者沿用 GPT-6.1 Sol／high 的非作者 reviewer 身份；未创作两份候选，也不是执行者。已知此前私有修订、父版、预发布及登记后 CPU 核查上下文，**不是 fresh solver／干净上下文公开读者**。已接续 `remaining_workflow_20261002.md` 的独立核查约定。

本轮仅读取本地已下载材料：两份完整 FrozenPatch（解码全部 `core.py`）、完整候选 diff、原 `baseline.tar` 中的 `core.py`／`arrayprint.py`／公开 `test_str_repr`、实际 solver prompt、完整评分失败段及原始状态行。对完整源码做 AST 文本核对：除 `MaskedArray.__str__` 及 Qwen 新增 sentinel 外，两份 `core.py` 的 AST 均与原 baseline 一致。没有导入或运行 NumPy，没有 SSH、容器操作、CPU／GPU 重跑或补造候选。

执行完整性复用两份独立执行核查：`runs/ordinary_gpu_probe_20261002/reviews/numpyd805_coder_a1_execution_review.md/json` 与 `numpyd805_qwen36_a1_execution_review.md/json`。本报告不重做它们的镜像、请求交付、退出和清理验收，也不以作者汇总标签代替语义判断。两份原日志的末段均直接列出 228 个 `PASSED` 和一个 `FAILED`；唯一失败为 `TestMaskedArray.test_str_repr`，位置均为隐藏测试第 458 行。

## Coder：失败包含内容和格式错误

候选继续使用固定 `_print_width=100`，先取前后各 50 项。改动是将字符串 `'...'` 拼入数值 `data`，同时在对应 `mask` 拼入 `True`。之后 `data.astype("O")` 与 `res.view(ndarray)[mask] = f` 仍按原顺序执行。

这个顺序有两个直接问题：拼入字符串使整数打印成字符串，而新加的 `True` 又把省略号所在槽位覆盖成遮罩标记 `--`。原始失败输出实际包含 `'0'`、`'1950'` 到 `'1999'`，并且数据部分没有省略号，仍保留约 100 个数据槽位。它与公开要求的 `[0 -- -- ..., 1997 1998 1999]` 存在实质差异，不能归为仅标点不一致。

固定裁剪条件也未遵循公开要求的 printing options：在本题已有的 500 项全量实例以及 `threshold=2000` 的 2000 项实例中，代码仍会裁到前后各 50 项。此结论是源码推导，**不是这些后续隐藏断言已实际执行的结果**。新增 `fix_description.md` 宣称“确保显示省略号并匹配 NumPy”与原始输出矛盾，不能作为成功证据。

可以确认的局部正确性是首个失败之前的小数组 `str`／`repr` 断言已经通过，另外 228 个评分键通过。它们不支持大数组修复成功，也不能证明后续 printing-options 断言通过。

## Qwen：不是无依据误拒，但失败应准确归因

候选从公开源码读取 `_summaryThreshold` 和 `_summaryEdgeItems`，先取指定首尾，再转换为 object 并替换遮罩，最后插入自定义 `_SummaryEllipsis`。该对象的 `__repr__` 返回 `"..."`，避免了 Coder 的字符串引号问题，也避免省略槽位被遮罩覆盖。

原日志的两个完整字符串已用标准库字面量读取核对：实际为 142 字符、预期为 143 字符；将预期的 `..., 1997` 改成 `... 1997` 后，两者完全相同。默认公开实例的首项、两个前端遮罩、末端三项、mask、fill value 和其它排版都一致。不能把这次失败说成首尾数据错误或未显示省略号。

缺逗号仍是有公开依据的格式失败：

- 实际交付给两个 solver 的公开 Expected Behavior 示例明确写了 `[0 -- -- ..., 1997 1998 1999]`，并且任务本身要求修复字符串表示。
- 原 baseline 的 `numpy/core/arrayprint.py:252–254` 在摘要分支使用 `summary_insert = "..., "`；第 489–490 行将这个标记交给统一排版器。这是当时 NumPy 的公开源码行为，不是隐藏测试临时创造的标点规则。
- Qwen 的压缩结果只有 7 个 object 元素，未超过默认阈值 1000；因此普通 formatter 将 sentinel 当成一个元素，只输出其 `repr()` 的 `...` 及普通空格，而没有经过原生摘要标记路径。原输出与这个源码原因一致。

据此，当前严格字符串断言没有因私有、未披露的算法要求误拒 Qwen。公开文字里的 “For example” 不应被扩张成所有情形下任意空格／换行都必须逐字相同；本次差异则恰好落在明确交付的同一个实例和公开原生摘要标记上。若将任务重新定义为“只要求省略语义、不要求 NumPy 摘要格式”，Qwen 默认实例可接受，但这是改变现有验收契约，现有样本没有要求作此更改。

## 后续断言及边界：只作静态判断

第 458 行失败后，`test_str_repr` 中第 468 行及以后均未执行；两臂的 228／229 是**评分键**的结果，不能拆成其内部断言的通过数。

| 已有本题条件 | Coder 的静态结果 | Qwen 的静态结果 |
| --- | --- | --- |
| 默认阈值，100000 项且尾部遮罩（468） | 仍硬裁、字符化且遮掉省略号 | 首尾／遮罩选择符合要求，但 sentinel 仍少逗号；预期会在精确字符串比较失败 |
| 默认阈值以下的 500 项（476–478） | 静默丢值，不符合全量要求 | 不触发裁剪；源码支持全量值与遮罩保留 |
| `n=2000, threshold=2000`（489–492） | 仍硬裁，不符合全量要求 | 严格 `>` 条件不触发裁剪；源码支持全量保留 |
| `n=3000, threshold=2000`（499） | 硬裁、不符合选项要求 | 首尾选择符合要求，仍少逗号；预期精确字符串比较失败 |
| `n=3000, threshold=1000, edgeitems=501`（511） | 不能保留指定首尾 | 第一阶段保留 1002 项、加 sentinel 后为 1003；原生 formatter 再摘要，取首尾各 501 项并用原生省略标记替掉中间 sentinel，静态支持当前 token 判据 |

表中的“支持”不是正式通过声明，也不是将候选改一个逗号后即可全过的保证。Qwen 没有沿用公开 `_leading_trailing` 的 `len(a) > 2*edgeitems` 保留完整数组条件，因而不能据此宣称它覆盖全部一维参数边界。本轮不为这一范围外的完整性声明追加测试或启动 CPU。若未来要把它升级成“修改后完整通过”的正对照，具体缺口是修改后的原补丁在现有完整测试函数中的实际结果；当前无需获得该证据来保留原零分能力案例。

## 证据身份与处置

原件根目录：

- Coder：`runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-numpyd805-coder-a1/`。
- Qwen：`runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-numpyd805-qwen36-a1/`。

本轮直接核对的 SHA-256：

- 两臂实际 `solver_prompt.txt`：`fe7277aaeff919ddbfa883ae9a5e7876f1f3b41db52bbdf2bbaf3b4fc90d0e41`。
- 两臂 baseline `numpy/ma/core.py`：`808ccf063667b293159708066bdde01a18690251c8ce7452144d015c3aed6303`。
- 当前隐藏测试：`09d0aa6d80f85d394fc0a7971e23de8dd43a79d817749f0246693f62898bf67a`。
- Coder FrozenPatch 原 JSON 文件：`7fdab266c5a05ab42201430342838ff96d2f2a7ad48c938db5ac2d36620eb489`；其契约规范化 digest 为 `1b60acc9099e6c2599d9c2698976ab00e524489ac4c23b3a56554fd716fdb815`。解码 `core.py`：`2efb31bcdfe89ff05441343c19b31de48b16bb77c298d1e10819140d814194ec`。候选 diff：`fd7b56b9a269a2fdf3ddf5aea65a742e52f8efa4f48f1e9fe946ae9338e7661f`。
- Qwen FrozenPatch 原 JSON 文件：`e099d4628c59ce45daaf94a3713be302adb178c0df14d0cf272d442a01612599`；其契约规范化 digest 为 `4ac9734d5c34f439aabecbf02c2db5f818a7c6a500c31ff91ed55fe95a0d1d79`。解码 `core.py`：`6feb87e580bd4cbe789abc42a8cca910305ab01774ced31b177cd06157ccf5fd`。候选 diff：`5d4c4845c010d4a5f3ce930de9ec6eb01db3bb55f4ae3617ed0936dc9a542a3f`。
- Coder 完整 eval log：`fb7d4083b268e55067b54a34dcbb71651d1f56c44706ac49e354b0cb92e44b8b`；Qwen 完整 eval log：`619e4ad8a9972c70209f8a31b99d71f5f0936377e345544fb52a7133f61d8663`。
- 复用的执行核查 JSON：Coder `aab3e3d6bbabb8bb00561c18aaa9ed523ca56fe8e0f386702f34055e19587ada`；Qwen `e88f9a4a85f5e23dcbf214e8c5208c4daa81d88455eda3f3c7c0b214b5f0ef9b`。
- 总回执 `migration_20261003/receipts/r2e-numpy-d805-078079-cpu-v1-20261003.json`：`8ffdc32e6456e776fbbbdfb03b4f8be39f89852cca26023036251fff32821d79`。

保留原候选、原成绩与首失败位置，不放宽现有判据，不重写历史回执。题级摘要应分别记录 Coder 的机制错误与 Qwen 的格式兼容缺口，并保留后续断言未执行这一限制。无需本轮新增 CPU 修复、重复采样或重新验收；未来用途决策不能仅凭这两次二元零分抹去二者局部能力差异。
