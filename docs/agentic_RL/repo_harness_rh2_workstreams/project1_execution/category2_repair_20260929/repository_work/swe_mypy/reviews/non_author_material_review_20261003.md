# SWE mypy 两题：非作者静态材料窄核

2026-10-03。审查身份：Codex 非作者，已接触历史 gold、私有测试与对照证据，**不是 fresh 公开读者**。

结论：10174 的新增不重叠比较 case 与私有负对照在限定范围内可接受；15184 的 a.C/b.C 题面修订可接受，没有解法泄漏。15184 的评分护栏建议只把 `testAssertType` 作为必要新增参考，另外四项保留开发回归；最新 `p2p_basis.md` 已允许这一取舍，因此本轮没有新增阻塞 finding，也不把五项同组选择自动批准为五项评分要求。负对照是否确被原评分接受、被新评分拒绝仍待 CPU 证据。

## 范围与身份

检查入口为 [preparation.md](../preparation.md)、两题 `revision_proposal.json`、对应公开／私有材料，以及最新 [p2p_basis.md](../python__mypy-15184/p2p_basis.md)。仅按需要读取精确 base 的测试、文档、收集器代码和历史公开复现原件。10424／17071 未重审、未修改。

审查材料身份：

- 10174 `revision_proposal.json`：`sha256:74406d354804569b79eb6cf3a3510ad4b054f837af2595c00f6c873a77ad249e`。
- 15184 `revision_proposal.json`：`sha256:e959404ab20483ae1edc4d951bc545fc9f0e827ac2377447a3f98e74c4086592`。
- 15184 `p2p_basis.md`：`sha256:30ff3298c54db9255c97292c9118ba01bfcfd7f93fc18f81d76b588d9ac2d067`。

本轮只做文本／JSON／摘要／AST检查，以及内存中的 unified diff 重放。未运行作者生成器、项目或维护测试、mypy、pytest collect；未 SSH、启动容器、安装或下载。只新增本报告，创建前确认不存在并排他写入。重点为测试有效性、公开要求一致性、节点来源和材料身份，不是 A~N 全量集成审查；正式环境、安装、清理及运行时行为未验。

## 10174：在同一开关下保留真实不重叠诊断

材料：[revision_proposal.json](../python__mypy-10174/revision_proposal.json)、[added_case.test](../python__mypy-10174/private/added_case.test)、[effective_test.patch](../python__mypy-10174/private/effective_test.patch)、[私有负对照](../python__mypy-10174/private/disable_non_strict_comparisons.patch)。

公开题面只要求消除 `--no-strict-optional --strict-equality` 下 `Optional[Any]` 的误报；这不等于禁用严格比较。公开 base `docs/source/command_line.rst:562–580` 明确说明 strict-equality 应拒绝不重叠比较及成员检查。base `test-data/unit/check-expressions.test:2764–2769` 已有 `1 in ('x', 'y')` 应报错的 tuple case。新增 case 第1–6行复制这个已有输入、预期与桩，只增加 `--no-strict-optional` 并使用新 case 名，未引入新协议要求或其它运算。

父材料标明 base `c8bae06919674b9846e3ff864b0a44592db888eb`。本轮核对公开 `base_identity.json`、公开／grading bundle 的 base 一致性及登记文件摘要；baseline `check-expressions.test` 实际摘要为 `faf0a2a1512eba689901ec6a4df57bc1be9183d2616f6846c8dc9ada181884ec`，与提案一致。未重新验证全部 base tree 或容器源码身份。

对该 baseline 在内存中分别重放原 `test.patch` 和新 `effective_test.patch`：新结果恰好等于原结果插入新增 case，其它内容不变；原 `testOverlappingAnyTypeWithoutStrictOptional` F2P 和两个 `testUnimportedHintAny*` P2P 正文逐字相同。新 case 在 base 原件不存在，正式消费者必须同时采用有效补丁和新增参考，不能只向原 base 的 selector 追加名字。

拟节点格式有静态依据：0.820 的 `mypy/test/data.py:559–566` 由 `DataSuiteCollector` 直接生成 case，未加数据文件 collector 层；`testcheck.py:110–111` 确认套件为 `TypeCheckSuite`。所以提案的 `mypy/test/testcheck.py::TypeCheckSuite::testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional` 形状合理；仍不能由静态字符串把 `node_id_verified_by_collection=false` 改为已验证。

负对照在 `dangerous_comparison()` 现有 strict-equality 检查后，对所有非 strict-optional 比较直接返回 False。对于新输入，这会在目标不重叠判据前退出；原 F2P 没有预期错误，而原两个 P2P 是未导入 Any 的提示，静态上不约束此分支。gold 只调整 `meet.py` 中 Any 与 Optional 简化的先后关系，没有移除 int／str 的不重叠要求。因此原误报消除与真不重叠保护有独立依据。负对照补丁在精确 source 文本上可重放且 AST 有效；**原评分可能得1、新评分应得0是待测预期，未登记为实测误奖。**

结论：本轮范围、base内容和拟 selector 可接受。正式接入后应真实收集／执行／解析原三键与新增键，并以 noop／gold／负对照验证0／1／0，拒绝原因须是新增不重叠诊断缺失，不能是安装、应用或收集失败。

## 15184 R-f：名义类复现有效，gold 仍应报类型错误

材料：[公开题面](../python__mypy-15184/public/problem_statement_v1.txt)、[公开 bundle 草案](../python__mypy-15184/public/public_bundle_draft.json)、[statement diff](../python__mypy-15184/private/problem_statement.diff)。

旧 SupportsIndex 程序在历史 actor 原件 `runs/task2_swegym_dev_20260925/runs/mypy15184/orig/captures/mcve.out` 输出 Success；它没有触发登记的短名歧义。新材料使用独立模块 a、b 各定义 C，再对 a.C 表达式请求 b.C；这个名义类型不匹配有明确诊断要求。历史同目录 `mcve_ambiguous.out` 第1–2行输出 `"C", not "C"` 和 Found 1 error；私有 gold 对照 `runs/task2_swegym_dev_20260925/runs/private/python__mypy-15184_gold.json` 的同名结果输出 `"a.C", not "b.C"` 和 Found 1 error。

本轮还读取历史命令 `rh2/experiments/task2_swegym_dev_20260925/commands/python__mypy-15184.json`：`mcve_ambiguous` 先执行 mypy，再以 `! grep -q 'of type "C", not "C"' out.txt` 判输出。**helper 的 rc0 表示后一个输出检查成功，不能代表 mypy 退出0。** 新题面第29行明确仍报告 mismatch；新的 CPU 计划第29行也要求分别记录真正 mypy 返回码和诊断。这一要求正确。

题面三代码块与 `public/reproduction/{a.py,b.py,t.py}` 一致，均能 AST 解析。相对原 public bundle，仅 `problem_statement` 与其 SHA 变动，其它字段逐项一致；新 bundle canonical digest 与提案相符。题面只说明输入、错误消息和应有语义，没有出现修复 helper／函数、源码补丁、私有 case 名或评分参考。删除原协议结构等价的开放讨论，没有把它改成新的协议相等性要求。无歧义诊断保持简洁由原官方 `testAssertTypeFail3` 已保护；合法调用保持成功、保持表达式类型由公开文档和公开旧测试提供依据。

结论：R-f 静态核可接受，正式评分材料不因题面-only操作变化；仍需要未见私测／gold 的新公开读者、正式 public 版本绑定和实际 solver 消息核对。本报告不能代替这三项。

## 15184 R-c：核心正向护栏够用，四项兼容回归不必一律入评分

原三参考位于新增文件 `check-assert-type-fail.test`：Fail1／Fail2 保护同名失败诊断，Fail3 保护无歧义简洁失败诊断。三者的 `assert_type` 都应报错；名称中的 P2P 只表示改前改后测试通过，**不表示其中包含成功的 assert_type 调用**。因此既有护栏对失败消息够用，对“有效调用仍成功”不够用。

公开 base `13f35ad0915e70c2c299e2eb308968c86117132d` 的 `docs/source/error_code_list.rst:884–896` 明确有合法 `assert_type([1], list[int])` 与错误类型断言对照；`check-expressions.test:931–942` 的 `testAssertType` 同时检查合法 int／Literal 调用、失败诊断以及返回表达式的 int 类型。这是新增一条必要正向参考的直接公开依据。

| 拟选 case | 精确 base 位置 | 窄核结论 |
| --- | --- | --- |
| `testAssertType` | `check-expressions.test:931–942` | 推荐进入 P2P：一个 case 已覆盖合法调用、失败语义和返回类型，直接拒绝无条件报错负对照。 |
| `testAssertTypeGeneric` | 同文件第944–956行 | 可保留开发回归；检查合法泛型推断与上下文，未检查泛型内部同名类型消歧。 |
| `testAssertTypeUncheckedFunction` | 同文件第958–967行 | 可保留开发回归；该调用本来应失败，对无条件报错负对照没有新的决定性判别力。 |
| `testAssertTypeUncheckedFunctionWithUntypedCheck` | 同文件第969–978行 | 可保留开发回归；同样是原有失败诊断，不是缺少的合法调用护栏。 |
| `testAssertTypeNoPromoteUnion` | 同文件第980–990行 | 可保留开发回归；有合法 union 断言，但当前没有证明需要在核心正向 case 外再设独立评分门槛。 |

五个 case 都在所登记 base 文件中，case 名唯一、文件 SHA及每个正文 SHA均重算相符；没有新造输入或改这些旧 case。拟节点包含 `.test` 文件层也有静态依据：1.4 `mypy/test/data.py:687–722` 在套件与 case 之间增加 `DataFileCollector`。但最终真实节点、额外 suite、实际解析结果仍待 collect；不能按提案五行直接登记已执行五项。

[负对照](../python__mypy-15184/private/gold_but_always_reject_assert_type.patch) 保留 gold 的消息消歧补丁，只将 `visit_assert_type_expr()` 的 `not is_same_type(...)` 条件改成恒真。原三个失败调用本来就进入该分支，静态上消息不变；合法 int 调用新增报错，会与 `testAssertType` 的公开预期冲突。补丁在两份精确 base source 上可文本重放、AST 有效，没有改测试、selector 或 runner；但是否真正原评分1、新评分0仍须正式执行，不能靠补丁形状记成已证明。

建议正式冻结时采用原F2P2＋原P2P1＋核心新增P2P1，共4个参考键；其它四项可单独执行、记为开发回归。若不选择该最小集合，作者应说明各额外评分参考要关闭什么独立缺口，不能只用“同组”或 `-k` 命中解释必要性。当前 `p2p_basis.md:11–19` 已明示另外四项可取舍、尚未定为必须，因此这属于本轮审查建议，**不是已发布材料的范围错误**。选择最小集合后须同步提案和 CPU 计划中的“五个／8个”计划值；本轮没有直接编辑它们。

`testAssertTypeGeneric` 中 `Gen[int]` 的合法调用不等于泛型内部名称歧义测试。最新依据明确没有新增后者 case 或评分参考。该静态疑问保持待 CPU 窄校准；未验证前不把它强行纳入当前验收，不自动扩大公开题面，也不将它写成已证漏判。

## 停止条件与交接

两份提案中的全部 `path/sha256/bytes` 引用已静态核对，父 public／grading canonical digest 一致，公开题面与 bundle 一致。作者本地检查与本次静态证据都不代表 CPU、正式发布或实际 consumer 接收。

本次限定审查完成，无新增阻塞 finding、无新增候选、无公共代码修改。10174 继续配对有效补丁与新增参考；15184 采用上述最小护栏建议并同步草案，再按已有 CPU 计划验证两题 noop／gold／负对照。实际 mypy 退出码、collect／执行／解析键、材料身份及最终公开交付仍须真实记录。10424／17071 保持封板；训练／留出资格未增加。
