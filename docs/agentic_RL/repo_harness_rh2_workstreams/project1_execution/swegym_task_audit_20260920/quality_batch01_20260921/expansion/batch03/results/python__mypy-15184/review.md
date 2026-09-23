# python__mypy-15184 · B3 独立 reviewer 最终复核

结论：保留 `needs_review / static_review`，用途仅 `development_diagnostic`。官方两个消歧 F2P 和一个无歧义 P2P 有公开依据，历史原件的 0/1 分差可解释，未发现具体 gold 错误或误拒证据。**撤回本人封存初判“原 SupportsIndex 示例预期仍失败、gold 后应输出两个限定名”的预测**：完整名称不同不代表这两个结构协议不等价。最终将原例列为待执行的公开复现有效性问题，不以它给 gold 判坏，也不提前给原题复现判 pass。

## 1. 独立性、封存与新增暴露

权威 ROOT=`.`；P=`ROOT/runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184`，Q=同根 `private/python__mypy-15184`。以下源码位置均相对 P/base。本题独立初判 SHA256=`084c547c99c12965f306d90a211e1010f25e25da28c8ebe44f1fe5495c998cd0`；三题整包经协调者于 `2026-09-20T21:51:03.612934Z` 正式封存并放行后，才读取本题 public_read、主审 analysis_before_history、old_findings_delta、card、screening_record 的有关字段，及 I3/history/python__mypy-15184/refs.json 唯一指向的旧单题记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-15184.json`。协调者此前转述主审的协议等价分歧，此时已获结论阅读许可。

独立阶段已见 environment_record 自带 gold/noop 摘要，也已查其精确日志，不能称为结果盲审。未看其它题结果或旧聚合；旧记录内提及其它任务的名字/全仓概括仅作暴露登记，未沿链接读取、未据其裁定关系。封存初判保持原字节。本轮只读文本/JSON/归档成员与计算文件哈希；未执行项目、测试、安装、网络、容器或模型。

## 2. 实质分歧：为什么撤回原例必报错的预测

本人初判将两份 typeshed 中独立的 SupportsIndex 定义和 formatter 的 fullname 分支连在一起，遗漏了诊断之前的等价判定。主审已指出这一点；复读精确 base 后接受该纠正，理由来自源码而非旧评论：

1. `checkexpr.py:3911–3932` 先得到 source/target，只有 `not is_same_type(...)` 才调用失败诊断。gold 没改这一门槛。
2. `subtypes.py:251–267` 的 is_same_type 明确要求双向 proper subtype，并非 TypeInfo/fullname 身份相等。`430–610` 在名义继承不匹配后，仍于 `602–605` 对目标协议调用 is_protocol_implementation，保留 proper_subtype 参数。
3. `typing.pyi:308–312` 与 `typing_extensions.pyi:181–184` 都给出 SupportsIndex 协议及同一个 `__index__(self) -> int` 签名。`nodes.py:3088–3100` 收集协议成员；`subtypes.py:1023–1064` 检查共同成员并进行 proper 方法子类型比较，`1090–1104` 没有要求协议类名称相同。
4. `subtypes.py:1107–1127` 查成员时绑定 self，`typeops.py:1055–1072` 取左侧协议成员走同一逻辑；Callable 比较 `subtypes.py:680–696,1381–1444` 比较参数/返回类型，并不把方法所在模块名作为等价门槛。两份协议的相同无参 bound method 返回 int，有双向相容的静态依据。
5. 原例还有受限 TypeVar。`applytype.py:27–70` 对值列表用 is_subtype 匹配并选合法值，而非要求输入与限制值的类对象相同。这进一步说明不能以 TypeVar 使用 typing_extensions 定义为由直接断言最终失败。未逐条模拟完整泛型推断和 CLI 构建，故不把此局部链称为整个程序执行证明。

因此，在显式采用包内桩、目标 Python 3.10 的条件下，**base/gold 原例都可能无错误，且这个预测比“两边必有诊断”更有源码支持**。若正式观察确为无错误，应记录公开示例已不触发所述缺陷；一般同名名义类的诊断缺陷仍由官方 F2P 的真实失败独立成立。旧单题记录转述的上游评论只是一条二手线索，未打开原 raw hints，不能替代本 base 运行证据。

该纠正也适用于主审 `public_read.md` 的 C3 表格和命令后的固定预期；主审后续初稿、delta、card、record 已正确保留未知。建议协调者最终材料消除这项内部预测冲突。本 reviewer 不修改他人文档，不回写任何初判。

## 3. 需求、全部官方断言和 helper 的复核

独立初判逐项展开的新文件共 28 行、三个 case 及 tuple/typing/array 桩、数据 runner 链仍成立；未发现主审遗漏的额外断言。它们全部是 assert_type **应报错**的负例，P2P3 不能被写成“成功断言回归”。

| 项目 | 判定及依据 |
|---|---|
| F2P1：外部 arr.array[int] 对本地 array | 正确限定为 `array.array[int]` 与 `__main__.array`。两边 TypeInfo 短名均为 array，参数 `[int]` 不消除类名冲突；公开目标和既有 formatter 支持该断言。 |
| F2P2：对本地嵌套 array.array | `__main__.array.array` 是嵌套定义的 fullname；不是只准调用特定 helper 才能产出的隐含约定。 |
| P2P3：对 int | 保留 `array[int]` / `int`，约束无歧义仍用短名，对阻止无条件限定全部类型确有判别力。 |
| fixture/helper | 三例使用仓库 tuple.pyi；typing 最小桩与包内 array typeshed；testcheck 收集新 .test、build 真正检查输入，data 将 E 注释转为预期完整数组，helpers 比较整个诊断。没有 Mock、对象构造次数、内部 helper 名断言。 |
| 未选公开调用者/旧行为 | 已读 check-expressions.test:931–990 的普通成功/失败、返回类型、Literal、泛型、unchecked、union 行为；全部不在本题冻结 P2P。两个 assert_type 入口共同语义分析路径不等于本题都已被实际测试。 |

gold 只将 `messages.py:1658–1664` 的分别 format_type 改成共同 format_type_distinctly，保留错误码、顺序、引号、检查门槛和返回值。共享 helper `2559–2602,2638–2661` 先找两侧短名/fullname 冲突，再递归格式化；type traverser 可进入泛型参数、Tuple、Union、Callable、TypeType。已有赋值/列表等调用者支持复用的公开可发现性。

认可主审的合理替代：在诊断处独立收集双方冲突全名，再分别用现有 formatter/quote 处理，可以满足验收；没有函数调用锁定。旧记录称只有 gold helper 才能通过、`__main__` 无法公开推知，均不成立。不能据此把断言弱化成“两个字符串不同”，或把 helper 名写进题面。也不把未穷举的递归 alias/TypeVar 表示能力擅自提升为任务承诺。

## 4. 覆盖限度、旧发现与关系

主审提出的“只处理顶层 Instance 碰撞”的部分修复是合理静态候选：可以通过官方两条 array 消歧并保住 int 短名，却可能漏掉 `list[a.C]` 与 `list[b.C]` 的内部冲突。公开标题和现成递归机制支持研究该范围；尚未构造/执行候选，不称为已证评分假阳性。它和正向 assert_type 回归缺席都是有限覆盖边界，现阶段不强制第二候选。

旧发现中“无运行/安装证据”已过时；新增文件无末尾换行属事实，但真实收集和执行成功，未见题义或评分影响；“无重复”不能由唯一新文件推得。旧建议一概排除 mypy/test 与 test-data，也不能仅以 gold 不改这些目录作为根据；仍保持 additional_exclusions=[]，不掩盖尚未实证的 helper/config 绕过风险。

本包独立阶段已核的代码包含关系保留：15184 base 的 `messages.py:2519–2521` 已有 15139 gold 的 TypeType 小写选择；15139/15184 两个 1.4 base 的 `meet.py:300–312` 均含先规范化非严格 Optional、后对 Any 判重叠的 10174 关键结构。这只证明所读字节中的代码包含，未查 Git 祖先链，也不等于三题重复或相互泄漏。不能用本包内部代码关系替代具体任务目标审查。

## 5. 执行、解析、冻结参考与交付机制分别记账

本题原 install_wave1 派生镜像为 `sha256:38c3651c72ac2fe7ce40e3cf3e2a6056f8e983fe325d0fed771124e5827a829e`。独立初判已核本题精确输入/spec/镜像身份、9 个离线 wheel pins、原安装命令、prepared manifest 和 source/run refs；此处沿用已验原件，不以主审结论替换。

| 证据账本 | 本题可确认的事实 |
|---|---|
| 实际执行 | gold 原日志 `d57f367c`：11322 收集、11319 未选、3 实际节点通过、rc0；noop `0ecfe8ca`：同样选3，F2P1/2 失败、P2P3 通过、rc1。requirements 和 editable 安装均有原日志成功行；不是从 COPY/ENV 推断。 |
| 解析 | 原 diagnostics 为3键，段外0，missing/skipped 空；不是把 pytest 收集总数算作评分覆盖。 |
| 冻结参考 | grading/raw row 准确对应 F2P2、P2P1；ledger 1行分别 reward1/0、f2p2/2 与0/2、P2P均无失败。 |
| 选择机制 | baseline.tar.gz 历史 spec_vendor 从 test.patch 的所有 case 头提取 `-k`，不是由 F2P/P2P 清单直接确定执行；本题恰好三者一致。 |
| 恢复与投影 | 官方仅新增 check-assert-type-fail.test。base 不存在所以 restored=0，随后 apply_rc=0、test_files=1、setup_ok=1、missing=0；不是保护失败。gold投影仅messages.py，ignored=[]。test_globs为空，不能声称所有测试目录均被恢复。 |

机制证据来自独立阶段按 extractfile 只读的 baseline 归档成员，包括 spec_vendor、prepared_task_face、replay_grade、scoring、swegym_parsers；未使用当前源码替代历史 harness，未解包或执行它们。原 spec 安装/测试命令没有被 recipe/materials/bindings 覆盖，派生镜像只换镜像身份、供给 wheels/ENV。

## 6. 开发环境与评分环境的分别结论

评分环境有真实安装、源码顶层导入 `/testbed/mypy/__init__.py`、grader54322、apply54321、deny_all、2CPU/4GiB、tmp1GiB 和一次 cleanup 成功的证据。它们可支持该次评分的运行条件，不能证明正式 actor 消费了派生镜像、工具消息正确、conda 激活、候选源码/编译扩展加载、写权限或当前离线资产可用。

**固定 grader 的公开行为语义诊断不以正式 actor 全面验收为前提。**未来若获准做 CPU 对照，可在先确认该次 grader 的解释器/导入来源、精确 base/gold 和实际依赖后运行；这不是启动模型开发。进入模型开发再单独完成正式 actor 的镜像、shell、工具、权限、资产和资源验收。主审 card 把“核 actor 后”置于唯一 CPU 优先项之前，建议改成这两条独立门槛；screening_record 的 before a model probe 限定较准确。

镜像当前存在性、wheel payload 恢复仍未核；原 prepared 副本嵌入历史 `/work/...`，将来新 run 必须新建重定位 summary/manifest，不回写历史原件。本轮不安装或探测。

## 7. 最小后续实验与判定标准

优先做一次固定 grader 的 **base/gold 原题程序＋既有 testAssertType 窄组** 对照，同时保留原官方2/1评分作背景。显式目标3.10、使用包内桩并记录实际导入/配置；原题程序预期开放为两种待观察结果：若 base/gold 都无错误，则确认该条件下原例失效；若仍报错，再比较限定名/原错误码，不将诊断退出非零误判为环境失败。窄旧组验证成功、普通失败、Literal、泛型、unchecked、返回类型未退化。

只有原例失效被实测确认后，才考虑版本化修订公开复现；应使用公开可构造的不同模块同名名义类，不照搬隐藏 test.patch、不在题面硬编码 gold helper。泛型内部冲突候选可作为随后校准，当前不强制双候选。本轮均未执行，未产生新成绩/费用，costs 不填估计值冒充观测。

## 8. 剩余范围与建议状态

未查全仓回归、全部共享 formatter 调用者/递归 alias/协议泛型边界、实际原题 CLI、真实 actor、当前镜像与离线包、并发重复、完整 Git/缓存答案资产、真实模型轨迹与成本。公开 base 没有 .git 不证明实际运行环境无答案泄漏。审核文档已暴露私测/gold/结果及旧单题结论，不得进入 solver 输入。

最终建议保留静态开发诊断候选与原例待验问题；不接受旧“唯一路线”的误拒推断，接受主审对协议等价的纠正，并明确记录本人初判错误。状态继续 `needs_review / static_review`；没有任何新 CPU 通过声明。
