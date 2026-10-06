# mypy-15184 Coder 首臂：非作者语义与轨迹反证窄审

日期：2026-10-03。按 `review-standards.md §10.4` 担任 Falsifier / Simplifier。已见 gold、私有参考及 R10 上下文，**非 fresh 公开读者**。本报告只核新增 Coder 首臂，不重做 Qwen 审查。

只读本地原件、解码 FP、计算 SHA、读取 tar 成员并静态审查候选及轨迹；未 SSH、运行 CPU、容器、模型、测试或项目代码。唯一写入为本报告，未修改旧报告、证据或共享文件。

## 结论与 finding

**源码和正式执行共同支持本首臂在已规定行为上的语义通过；没有发现需要修题或复验的现存实现／评分缺陷。** 候选只改变 `assert_type` 错误文案的联合格式化，能遍历泛型参数中的同名类型，保留合法断言的判断和表达式返回值。原始正式五参考均真实执行、解析为 PASSED，不以 `raw_reward=1` 单独作为结论。

有一项 **P3：模型自验表述比实际证据宽**。合法断言不报错不能验证“无歧义的错误文案仍简洁”；模型还声称全部既有 assert_type 相关测试通过，而实际选择漏掉其他文件中的 `testTypingSelfAssertType`。这影响对模型验证过程的评价，未推翻本题正式结果：简洁名称由正式 `testAssertTypeFail3` 支持，有效断言和返回值由正式 `testAssertType` 及未改 guard 支持。最低处理是登记实际测试范围与这项推理误用，不改历史轨迹，不要求重跑。

本报告支持 Coder 的**本题、本次、首臂**具体求解结果，不泛化成全部类型分支无回归、跨题能力或重复稳定性。配对回执记录两臂执行已完成；题级语义汇总仍由题主结合两份审查登记，本报告不回写该冻结回执。

## 固定证据与 FP 来源

入口：[配对回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/swe-mypy15184-nested-nominal-v2-20261003_two_model_v1.json)，独立 SHA 为 `f3acea51e02fcf91931d43a10673a0945d543b165d8c87b3242354adb041e6fa`。本臂原件根是 `runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/`。独立核回执列出的本臂 result、attempt、input_check、FP、baseline、report 六文件 SHA／size 全匹配；不把此窄核称为整个配对发布包重验。

- [原 FP](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/attempt/frozen/frozen_patch.json) 的规范化 digest 独立重算为 `20de4d05bea9c2f046e56bf3212c98c85a8f82ba7e74bc32e6ed09991ca45f1a`，文件 SHA 为 `b78832a71c622967f0ff0171bf5defe85ba98374fc411e73a019c39f2c97c1eb`。102 项内容解码 SHA 均与条目声明匹配。
- FP 为 `mypy/messages.py`、四个开发脚本和 97 个 `.mypy_cache` 文件；[原 projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/grading/projection.json) 保留全部 102 项，路径集合完全相等。没有把缓存或脚本数量当作缺陷，也没有声称 grader 已剔除它们。
- [baseline manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/attempt/frozen/baseline_manifest.json) 规范化 digest 为 `fdd59f846a872a5fb2680de446faf5d8a286db2237559c43c8b43874e82df1a5`。baseline tar 恰好 1,422 项，逐项内容与规范化可执行 mode 匹配，无额外项；冻结与评分重建 census 字节相等，baseline 无 `.mypy_cache`、`.pyc` 或 `.so`。
- base 为 `13f35ad0915e70c2c299e2eb308968c86117132d`，实际镜像为 `cda77e2d613176919d3c6fb8a0f1aae952a1f77a5d0170602db93c432867c025`。本臂 diagnostics 使用 `mypy15184-nested-nominal-types-v2`、材料 identity `bf000616fc92f2d7869bdb2039ab1fe0d9167e507a5bb15e6c5987ab033d8053` 和在用五参考。

四脚本的实际功能如下；这些是开发复现文件，不是四套自动断言测试。

| 路径 | 内容与实际使用 | 解码 SHA-256 |
| --- | --- | --- |
| `a.py`、`b.py` | 各定义 `class C: ...`，提供两个不同模块中的同名类 | 两者均 `e5110afd389ace599b1c5a315222f25bf630090b9f48e9de99be571f09ee9ae2` |
| `t.py` | 参数 `a.C` 对 `b.C` 的故意不匹配断言；修前后分别得到 `C/C` 与 `a.C/b.C` | `d0fb0cb8946b91dcb8da41a0465825e7362f28162efbb3f106094cdaf0cb6b4b` |
| `correct.py` | 参数 `a.C` 对 `a.C` 的合法断言，运行无错误 | `9733f479d73a8d2fa2ae2580b019cf08b46b4c1ba6060458f27f9e803035b02b` |

## 源码反证与不同分支的真实边界

候选 `mypy/messages.py` SHA 为 `2ca8bce8da916a44cf9ef4e598085f1dcd9575a0bf1c4cba71869f6f0ebe330f`。与原 tar 中同文件比较，唯一实现改动位于 `assert_type_fail`（1658 行起）：把两个独立 `format_type` 调用替换为 `format_type_distinctly(source_type, target_type, options=self.options)`，用其返回的两个字符串发出同一错误。错误位置和 `codes.ASSERT_TYPE` 保留，helper 本身未改。

| 反证方向 | 所核代码与实际结果 | 可下的结论 |
| --- | --- | --- |
| 只修外层名字 | `find_type_overlaps`（2584–2602 行）共同处理两类型；`CollectAllInstancesQuery`（2574–2576 行）调用父 visitor，`typetraverser.py:80–81` 遍历 `Instance.args`；`format_type_inner:2365–2369, 2423–2424` 递归沿用同一 fullnames 集合。正式嵌套 F2P 通过 | 支持 `List[a.C]`／`List[b.C]` 内层消歧，排除在用 top_only 缺陷 |
| 无条件拒绝合法断言 | `checkexpr.py:3911–3932` 未改，仍只在 `not is_same_type(...)` 时发错，保留 Literal 处理并返回 `source_type`；公开合法脚本与正式有效 P2P 均通过 | 不存在已知 bad 控制的合法断言误报；正式 P2P 的返回值 reveal 仍正确 |
| 一律输出全名 | fullname 只用于短名冲突集合；formatter 从 verbosity 0 开始，字符串已不同时即停止。正式简洁 P2P 保持 `array[int]`／`int` | 支持本参考的无歧义简洁行为，不由合法脚本的“无报错”推导文案 |
| 影响其他格式分支 | visitor 也遍历 Callable 参数／返回、Tuple、TypedDict、Union、TypeType 及非递归 alias；原 `format_type_inner` 对这些分支继续递归。联合 helper 可能在两文案仍相同时升到 verbosity 1，例如 callable 参数显示细节 | 改动范围是 `assert_type` mismatch 文案；类型相等性与其他消息调用方未改。不能把五参考或表达式开发 suite 写成这些分支全部输出不变 |

这里没有找到可复现的新回归。最后一行保留源码行为范围和测试覆盖边界，不新增理论反例或运行门槛。对特定未覆盖分支的通用正确性，当前材料不能给出穷尽证明。

## 正式五参考与缓存／脚本影响

[原始 eval](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/grading/eval_logs/evallog_gpu1003-mypy15184-coder-_d0af9ee3.eval.log) 485 行为 `pytest -n0 -rA` 加五个完整参考，没有宽 `-k`；497–502 行逐项 PASSED，并显示 `5 passed in 0.58s`。独立解析 Test Output 段得到恰好五个不同节点，与正式命令和 [diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/grading/eval_logs/evallog_gpu1003-mypy15184-coder-_d0af9ee3.diagnostics.json) 四分区相等；FAILED、missing、skipped、额外节点均为 0。

| 正式 case | 分区 | 结果与行为 |
| --- | --- | --- |
| `check-assert-type-fail.test::testAssertTypeFail1` | 原 F2P | PASSED；`array.array[int]` 与 `__main__.array` 消歧 |
| `check-assert-type-fail.test::testAssertTypeFail2` | 原 F2P | PASSED；`array.array[int]` 与 `__main__.array.array` 消歧 |
| `check-assert-type-fail.test::testAssertTypeFailNestedNominalTypes` | 新 F2P | PASSED；泛型参数内 `a.C`／`b.C` 消歧 |
| `check-assert-type-fail.test::testAssertTypeFail3` | 原 P2P | PASSED；保持简洁 `array[int]`／`int` |
| `check-expressions.test::testAssertType` | 新增已有 P2P | PASSED；合法 `int/int`、`Literal[42]/Literal[42]` 无误报，返回 reveal 保持 `builtins.int` |

完整节点前缀均为 `mypy/test/testcheck.py::TypeCheckSuite::`。前四 case 的 PASSED 是诊断匹配预期，不匹配断言仍须产生 mypy 类型错误。

可信 setup 真实恢复公开 `check-expressions.test` 至 base SHA `f541a8781c01edf4a27209cc1569e61d1d8a4741c3d4bc381548d0b1239ce3b9`，再应用私有新文件 patch；apply RC0、预期/实际两测试文件齐全，保护 2 文件／6 目录，缺失及不规则为 0。候选四脚本没有改测试、fixture、conftest 或 helper。

97 缓存与脚本保留在供应里，但正式普通 case 在 `testcheck.py:133–140` 关闭 incremental，并设置 `cache_dir=os.devnull`；`mypy/test/data.py:328–333` 为每 case 建临时目录并切换 cwd。静态缓存 metadata 中 `a`／`b` 指向模型 API 临时复现目录，`correct` 指向开发脚本，均是该调用生成的类型缓存；未见影响正式预期诊断的证据。不能仅凭它们存在判污染或让本臂失效。

eval 459–469 行真实 editable 构建和安装成功，ERR trap 没有失败记录，安装未跳过、日志完整；正式 candidate/test RC 均 0。安装两命令没有独立逐条数值 RC，不能只用最后 RC0冒称逐条证实。观测包入口为 `/testbed/mypy/__init__.py`，runner 前后 digest 一致；没有 pytest 进程内目标 `messages.py` loader 的独立采样，保留该边界。manager 创建/移除 1/1、open/supply/cleanup_failures 空且 cleanup_ok；`resource_facts=null`、`env_qualification=absent` 不被本语义审升格成资源或训练资格验收。

## 定位、纠错与公开验证轨迹

[原轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-mypy15184-coder-a1/attempt/trajectory.jsonl) 共 24 次工具调用及对应结果：Bash 14、Read 5、Write 4、Edit 1。工具结果行号如下。

| 阶段／调用 | 具体观察 | 评价 |
| --- | --- | --- |
| 1–10：定位与理解 | 先宽 find／grep，再读取 messages.py、定位 `assert_type_fail`、`format_type_distinctly`、`find_type_overlaps` 和旧单类型 formatter | 找到已有共同 formatter 并核联合 overlap 原因，采用局部修法。初次 Read 输出 2,552 行／114,235 字符，之后又定位短读，有明显可压缩的读取成本 |
| 11–16：复现与单次修改 | 建三个公开复现文件；14／167 行修前 RC1 为 `C/C`；15 仅一次 Edit；16／193 行修后 RC1 为 `a.C/b.C` | 两个 `is_error=true` 是预期 mismatch，模型正确解释，未当环境故障 |
| 17–19：合法断言 | correct 脚本成功；19／228 行精确公开 `testAssertType` 单项 PASSED | 验证合法断言，未通过这次脚本验证简洁错误文案；该推理误用见 P3 |
| 20：表达式 suite | 243 行工具只展示持久化输出预览；归档原文件完整记录 179 个不同 PASSED，结尾 `179 passed in 4.41s` | 实际 suite 成功有原件，不能只读预览就泛称全仓库成功 |
| 21：API 重验 | 256 行 `mypy.api.run` 返回诊断 `a.C/b.C`，stderr 空、exit_status 1；外围 Python 正常退出 | 再次复核同一顶层目标；不是嵌套消歧或无歧义负例的新覆盖 |
| 22–23：选择器纠错 | `-k assert_type` 在 271 行 RC5、0 items／no tests ran；随后 `-k testAssert` 在 286 行选中 11 项并全通过 | 一次真实自验调用错误，已更正。11 项含五个 expression assert_type case 和六个普通 assert 相关 case，不是 11 个 assert_type 专项 |
| 24：差异核对 | 299 行 git diff 仅显示 tracked messages.py 改动 | 能核 tracked 实现；新增四脚本及缓存由 frozen census／FP 记录，不能由该 diff 推导工作区仅一文件 |

完整表达式输出来自 `attempt/cc_home.tgz` 的 `tool-results/bow8w20ap.txt`；本审直接读 tar 成员，未执行或解包到工作区。该成员 SHA 为 `70e8e38ea1d003adaa52e816d96c6fcc61382da3fc4b7e4182a62d5f5a577070`，179 个不同 PASSED 与 179 items／summary 相符。表达式 suite 的五个 assert_type case 和后续 11 项部分重叠，不能相加扩大验证分母。

轨迹 220 行把合法断言成功列作“unambiguous names remain concise”的依据；这不成立，因为该调用没有产生文案。304／308 行最终“全部既有 assert_type 相关测试通过”也应收窄：本选择器没有覆盖 baseline `check-selftype.test::testTypingSelfAssertType`，更没有穷尽所有含 `assert_type` 的 case。本报告登记 **所选公开开发范围未见回归、正式五参考通过**。不把一次空选择误记为通过，也不把已更正的选择错误变成仍待运行的阻塞项。

模型没有主动增加嵌套同名类型开发例，也没有无歧义 mismatch 开发例；对这两项的本次运行支持来自正式新 F2P 和原 P2P。候选 helper 的递归机制补充因果解释，不能倒写成模型自己运行了这些例子。

## 并行、效率与最小接续

24 次工具调用逐条发生，每个含工具的消息只有一个 tool_use；没有工具或子代理并行。实际并行发生在公开 suite：20、22、23 三次 pytest 使用默认 xdist 的 12 workers，分别收集 179、0、11 项；精确单项与正式五参考使用 `-n0`。空选择也启动了 12 workers并用时 3.06s，是可避免的调用成本，不是基础设施异常。

可并行或批量的是定位之后的独立只读区段，以及完成复现文件后的合法／不匹配诊断核查；源码 Edit 必须等待原因定位，修后验证必须等待 Edit。最小效率改进是一次读取相关函数区段、用准确节点名或正确大小写选择器；小范围测试可沿公开建议使用 `-n0`。本次实际已经快速结束，不能在没有对照计时的情况下宣称这些选择必然加速多少。

attempt 记录 solve 52.738s；Claude Code result 记录 25 turns、总 duration 49.153s、API duration 32.280s、正常 end_turn且无 permission denial。CC 报告累计输入 864,729 tokens、输出 3,051 tokens；输入是多请求累计，不是单请求 context。宽 Read 与重复定位显示可减少上下文运输，但一次记录不能证明模型间效率排序、稳定吞吐或资源成本；API 与总 duration 的差也不能直接等同于独占工具运行时间。

复用既有 [R10 反证条件](non_author_15184_r10_falsifier_20261003.md)：同版 noop／gold／bad／top_only 为 0／1／0／0，分别针对未消歧、有效断言误拒与只修外层。当前五键、材料和行为与其一致，未发现新的具体评分漏洞，不重做矩阵。

停止条件已满足：已核 FP／baseline／102 路径供应、唯一实现改动、四脚本实际用途、递归与 guard、正式五参考、开发输出原件、选择纠错及表述边界。**最低接续为题主记录 P3 自验范围并合并执行／语义审查；无新增修题或复验依赖。** 只有新的实际失败或材料身份变化才按影响接续，不追加 metadata、全套测试、CPU、模型或训练准入要求。
