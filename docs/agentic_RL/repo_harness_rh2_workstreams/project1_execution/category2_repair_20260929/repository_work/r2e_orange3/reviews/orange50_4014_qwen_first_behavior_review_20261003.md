# Orange50 / Orange4014：Qwen 首轮行为分析独立窄核

2026-10-03。非作者核查。**两份新增作者七维分析与实际原件一致，未发现必修修订；本轮窄核完成。** 原 reward=1 及候选符合当前公开要求的结论，按既有独立执行与语义审查范围承接。两题均只有一次实际 Qwen 首轮，Coder 尚未执行，请求按作者封存状态保持 claimed；这不表示整题或两模型首轮完成，不授予稳定能力、训练或留出资格。

本轮只读已回收轨迹、原 adapter 输出、gateway 请求/响应、attempt、正式 report 和 terminal snapshot，并对照两份新作者 md/json。复用各题原独立报告的 43 项执行检查以及 baseline/FrozenPatch、封闭原件和候选语义核查，没有重复这些审计，没有 CPU/GPU/SSH、候选或新测试执行。只新增本报告和同名 JSON；作者原件、既有 sealed 报告、共享文件及队列状态未改。

## 被审版本与承接范围

| 题目 | 作者 Markdown SHA256 | 作者 JSON SHA256 |
| --- | --- | --- |
| [Orange50 作者分析](../tasks/50f6a758/probe_qwen_first_analysis_20261003.md) | `7add6cb374875f5daa7fa7f8082913bf67eeaac7a49af1c6f2707291b23fc05b` | `3e03200a96b83037b41854f5564f7fa6af50ae148df5e8c31287a28b674472a2` |
| [Orange4014 作者分析](../tasks/4014f248/probe_qwen_first_analysis_20261003.md) | `02d18e3234322e24461ccd92938de405813a364a5b6191cf06d4f61c00eecdd1` | `f7e354d446e8ec40c2c13c54f31219d51ea8c19a44d18ab87a59b8e08041ba53` |

两份 SHA 均实际核对。作者 JSON 的 `new_behavior_independent_review_complete=false` 是生成时状态，本轮不回写它；本次接收结论另记于此报告。

复用 [50 原执行/语义独立报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q15_orange50_qwen36_a1_execution_semantic_review_v1.json)，JSON SHA `e76588ce04a4da831ce5c9a88eaa3e8426f143865e2c052c6a98e249da7b8d1d`；[4014 原报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q15_orange4014_qwen36_a1_execution_semantic_review_v1.json)，SHA `12bf75a1d0b4939886dde2bb1695b6bfcacb07a5e43cb5c1e0676652a745d613`。两者均 43 项检查、无 failed check，原结论均为本次执行完整、原 reward=1、公开语义受支持且保留证据限制。本轮不把它们扩成穷尽语义证明或训练合同通过。

下列事件行均为对应 `attempt/harness/trajectory.jsonl` 的一基行号。50 原件 266 行，SHA `89206ddcb5a4edc2b5334a87f587530c89dcab5fcfa60a9d6d15c2c1a28af250`；4014 原件 **403 行**，SHA `b5ae2114fdb81e0128f166d292db0223594acb58dd52e6c28c3cf1e5a9bf77f5`。具体工具 ID、结果 SHA 和原件引用保存在[同名 JSON](orange50_4014_qwen_first_behavior_review_20261003.json)。

## Orange50：七维新增事实

1. **方法。** 34→38 读取源码，thinking 44 从静默 `continue` 识别缺警告，104→108 的唯一 Edit（`toolu_5bf30710c399b40c`）在 `var is None` 时向现有 `warnings` 加入真实变量名，随后仍跳过未用定义。分类与数值共用循环、有效定义原流程保留，源码机制与原语义审查一致。没有硬编码 foo/bar、改仓库测试或评分控制。44 曾提到改变旧断言，但实际没有改测试；一次源码 Edit 不等于所有思考都没有旁支。

2. **定位与反馈。** 题面已给函数、症状及旧测试冲突，brief 已给测试入口，不能把这次记为无提示盲定位。首轮 11→19 的完整测试 Read 与 15→20 的 find/grep 后，34→38 读完整模块。52→58 的五个 selector 为 5 PASS，68→72 的旧冲突方法在 base 为 1 PASS。86→90 的新增 foo/bar 脚本实际因未弹 warning 失败；104→108 修改后，122→126 同例通过。这支持“用修前失败、修后同例反馈检验修法”，未见错误源码 Edit 后再改回来。

3. **工具。** 实际 15 次工具：Read 3、Bash 11、Edit 1，均有真实结果。两个 `is_error=true` 分别是 86→90 的预期缺陷复现和 158→162 的旧公开 888 冲突，不能计为两次修法错误或基础设施故障。原工具记录未见网络、gold、隐藏测试、私有 grader 或未来 Git 读取；这不排除模型先验记忆。临时 `/tmp` 脚本最后删除，仓库测试与控制面无修改的结论承接原审查，缓存变化边界仍保留。

4. **并行。** 首次生成的 `msg_2c17cec8a10164cbb6b73cb8` 确有 Read `toolu_10bbd2eec1aeeb18` 和 Bash `toolu_1e0be2c05ec3bfcb` 两个请求；raw adapter 第 1 行、SSE 第 1 响应及轨迹 11/15 相互一致。15 次生成中工具数为一次 2、十三次 1、一次 0，最大组为 2。这证明成组提出操作；工具只有返回时间、没有起止区间，实际重叠、执行层并行支持与节省时间未知，不能评估稳定并行能力。

5. **验证。** 176→180 仅断言 warning 正文含 `var not`，没有断言 rename 输出；194→198 才有有效 rename 保留的断言。该综合脚本的 **8 PASS = 5 项新增需求 + 3 项继承 fixture**，另有 3 SKIP。五项覆盖 foo/bar、未用 numeric、有效/未用混合且不误报有效名、仅有效定义无警告、rename 与未用定义共存。212→216 原公开全文实际为 46 PASS / 1 FAIL / 3 SKIP，失败是最后 888 的 `assert_not_called`，前面 duplicate/name-swap 检查已经走过。这是题面明确接受的冲突，不能记作补丁缺陷，也不能说公开全文全通过。命令经 `tail` 且无 pipefail，工具成功不单独证明 pytest RC0。正式原评分 48/48、test RC0 和 3 条未计分 skip 分列承接；installation SKIPPED、安装 RC=null 保留，mock 检查不等于完整真实 UI 交互证明。

6. **效率。** 作者的 token、请求和各阶段时间均与原字段一致。完整测试/模块读取带入较多上下文，五 selector 在 52、140、248 跑了三次；230 重读改后源码、清理后再跑同组测试期间没有新源码修改，存在可避免重复。194 的综合检查增加了有效覆盖，不能把所有额外验证都称浪费。局部读取、合并复现和避免无变化重复是过程建议，未实测节省量。

7. **结束与稳定性。** 262 的最终回复准确保留旧 888 冲突，266 为 success / `end_turn` / `completed`，未见预算截断、length、压缩或缺评分。只支持这一个 Qwen 样本正常完成且语义受支持；Coder 完成 0 次、计划 1 次是 pending，不是失败率，也没有两模型比较或稳定性结论。

## Orange4014：七维新增事实

1. **方法。** 201→205 唯一 Edit（`toolu_67e49dfac3ebbc1c`）在 `split_eq_freq` 两个返回处对原中点结果应用 `list(numpy.unique(points))`，原计数算法与 `low < high` 断言保留。219→223 实际 Cython/GCC/link/copy，237→241 新进程近值复现得到 `[1, 1.0000000000000004]`。原五项 native FrozenPatch 和正式 27/27 支持修法，按原语义审查的有限有序输入与回归范围承接；显示标签 `1 - 1` 不等于数值区间无效。未发现需要强制四箱或任意单箱退化的根据。

2. **定位与纠错。** 题面/brief 已给模块、复现与构建入口。53→57 读取 pyx 后，63 初步提出重复中点；71→75 实际 AssertionError，85→89 显示相等中点和 False 区间。109 **误把数组默认打印当成 distribution 舍入、np.unique 将原值视同**；113→117 的逐值 repr 明确四个输入互异，123 纠正，127→131 再核后两个中点相等。误读在源码 Edit 前消解，没有据此舍入输入；不能写成一路正确，也不能以只 Edit 一次掩盖推理回头。选择 Python/Cython 修法位置及 unique/dict 的重复讨论属于实际额外工作。

3. **工具与原生开发。** 实际 26 工具：Read 4、Bash 21、Edit 1；唯一 tool_error 是 71→75 的 base 缺陷复现。219→223 的 `python setup.py build_ext --inplace 2>&1` 无 head/tail 管道，完整 Cython、编译、链接、复制输出与成功结果支持真实 build=0。五项原生工件为 pyx、生成 c、源码 so、build/lib so 和 o，两个 so 字节相同的结论承接原审查。没有仓库测试/依赖/控制修改或可观察隐藏答案通道的结论亦按原范围承接。

4. **并行。** 27 次生成为二十六次单工具、一次无工具最终回复，最大组为 1。未观察到成组多工具或实际并行，但缺工具起止记录，不能据单次串行推断模型不会并行或执行层不支持。潜在可并行的只读操作只能作为过程建议。

5. **验证。** 255→259 TestEqualFreq 为 3 PASS，269→273 全 test_discretize 为 26 PASS。283→287 对普通阈值、少 distinct、100→4 有实际 assert，近值段只是打印。297→301 test_preprocess 完整 footer 为 18 PASS；`head` 管道返回码不独立证明 pytest RC。315→319 实际是普通 1..8/n4，注释虽称 close，输出普通 `[2.5,4.5,6.5]`；329→333 为 `[1,1+eps,2..9]`/n4，输出 `[1.5,4.5,6.5]`并断言区间。这两段不构成计数分支精度失败的修前/修后对照，该覆盖来自原正式 r089 语义审查。343→347 常数案例和 385→389 最后近值 True 比较为打印，不能冒作新增 assert；371→375 是无源码再改情况下的重复 26 PASS。

   brief 要求的 `extension.__file__` **没有直接打印**；build、新进程行为和变化 so 支持更新工件，但不替代直接加载路径证明。grader installation SKIPPED、RC=null、compile_probe=null，直接应用五项原生工件，**没有独立 source-only 重建**。作者准确保留这些验证不足，当前没有具体缺陷可以据此改写 raw1 或补跑覆盖原事实。

6. **效率。** 原始指标与作者一致。逐值 repr、函数中点与修后检查可合并，357 再读已改 pyx、371 再跑完整 26 项且无新源码 Edit，存在可避免重复。必要 native build 与修前/修后新进程复现仍有作用；补直接路径及计数分支精度断言比继续重复普通全套更有信息。建议没有实测成本或节省量。

7. **结束与稳定性。** 399 最终回复准确描述重复中点、两返回修法及公开测试结果，403 为 success / `end_turn` / `completed`。未观察截断、length、压缩或缺评分；最高单次输入 34,247 不能验证 196K 长负载。仅一次 Qwen，Coder pending；保留原 reward=1，不构成整题完成、稳定能力或模型排名。

## 指标独立核对与时间边界

| 指标 | Orange50 | Orange4014 |
| --- | ---: | ---: |
| 累计输入 / 输出 tokens | 400073 / 5814 | 641074 / 10290 |
| 最高单次输入 / 输出 tokens | 33774 / 1139 | 34247 / 1279 |
| CC turns / generation / 全 HTTP | 16 / 15 / 17 | 27 / 27 / 28 |
| count_tokens HTTP | 2 | 1 |
| solve / CC总时长 / CC API，秒 | 65.689 / 62.223 / 37.825 | 86.681 / 83.279 / 65.000 |
| gateway generation 请求时长之和，秒 | 37.380 | 64.337 |
| actor trusted_init，秒 | 221.011 | 203.903 |
| actor attempt 起止墙钟，秒 | 326.138970 | 328.047051 |
| grader总时长 / wrapper测试段，秒 | 252.068 / 5.001 | 199.618 / 2.471 |
| candidate TEST marker区间，秒 | 3.789 | 1.450 |
| 派发后 job 起止墙钟，秒 | 579.587722 | 529.055722 |

token 汇总独立从 generation 响应 usage 加总并核 terminal 字段，count_tokens 请求不混入 generation。累计输入重复含各轮历史，不能记作峰值上下文。输出 usage 含 thinking。CC API、gateway `seconds_total` 都含请求/服务等待与传输口径，不是纯 GPU 计算，两个数不强行当同一个计时器。`CC costUSD` 只是元数据估算，不能记为自托管账单。

从首 generation 请求到 50 首 Read 返回为 1.351406 秒、同组 find 返回 1.588406 秒、源码 Read 2.519406 秒、Edit 返回 26.009406 秒；4014 首 find 1.041926 秒、Python模块 Read 1.501926 秒、pyx Read 2.958926 秒、Edit 返回 43.704926 秒。作者表中舍入值准确，且正确标明包含生成、派发、工具和返回；没有工具开始时间，不能拆出纯工具或纯定位时间。

派发后总墙钟独立按 `terminal_snapshot.job.started_at/ended_at` 核算，actor 起止取 attempt，solve 是其子阶段；整个作业约九分钟不能当模型解题九分钟。grader 的 queue_wait=0 只限评分管理器，派发前候槽未知。wrapper、TEST marker、pytest正文各有边界，diagnostics 未提供的细分 phase 仍为 null，不补造时间。

## 有效结论与保留限制

新增作者分析核查通过、necessary_fixes=[]。两次真实 Qwen 的方法、反馈纠错、工具结果、验证和效率结论均有具体事件支持；过程改进建议合理但未测其收益。原 50 两行 warning 修法及 4014 两返回去重修法的语义结论按既有审查承接，原始评分不改。

实际 GPU 镜像与 CPU 验收镜像分列，身份/公开交付按原执行审查承接；有限资源采样有 CPU throttle，不能证明完整峰值、最低资源或全程无干扰。Qwen 是作业前 capture、固定 revision、只读模型 mount 与下载 manifest 支持的端点谱系，不是物理 GPU 权重哈希证明；HTTP revision/checksum=null、weight_version 默认、manifest 宣称40而列37等限制仍有效。原 env_qualification 缺失和 typed 材料字段 null 未由行为分析补齐，gateway first-byte 1800 与 common.py sock_read 900 也不能合称全链1800。

两请求按作者封存状态仍 claimed、Coder 尚未执行。本报告没有 ACK、清活动指针或改写总账；只封这两份新增行为分析的独立接收结论。
