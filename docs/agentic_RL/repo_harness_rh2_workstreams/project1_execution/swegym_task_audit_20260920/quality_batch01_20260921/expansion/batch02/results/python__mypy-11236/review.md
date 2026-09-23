# python__mypy-11236 — 独立复核

2026-09-21；独立 reviewer。三题初判全已保存、协调者 SHA 封存后才读主审/公开/旧结论。本题初判 SHA256=`3f6f6ffdfc8db9bfc43914285575d7127ddc2b037e928f6c72f379cd58db7ab0`，保持原字节。

**同意 needs_review / static_review / development_diagnostic，additional_exclusions=[]。** 一个 F2P 内有实质正负约束，不能等同零保护；派生 grader 的 0/1 分差来自目标行为。精确诊断对合法上下文实现有具体约束风险，但未证明唯一 gold 或已发生误拒。修正主审和本人初判的优先顺序：先在固定 grader 做窄语义对照即可，正式 actor 验收是启用条件，非该诊断的前置门。

下文路径以 `${REPO_ROOT}` 为根。U=`runs/swegym_quality_batch02_20260921_v2/public/python__mypy-11236`，P 为同层 private 本题目录；W=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11236`，G/N=`W/{gold,noop}`。

## 逐项实质复核

| 主张 | 复核判断 |
| --- | --- |
| 公开目标可理解 | 基线 `209a7193feb4bbfa38d09232b0a5a916e9d2e605`。函数已有返回注解，问题是接受 `(1,)` 符合 `Union[Tuple[str],Tuple[Literal[1]]]`，不是自动推断无注解签名。`("a",)` 保持合法，Literal 值和 tuple 长度保留约束。期望栏为空不使语义不可知；目标 Python3.7 与实际宿主 Python3.9 是不同层次。 |
| 根因与 gold | `checkexpr.py:3301–3358` 多个同长度 tuple 候选导致不取上下文；`2088–2113` 产生带 last_known_value 的 Instance；`subtypes.py:243–297` 没有该 Instance→Literal 分支。Gold 两行复用 subtype 选项比较 last_known_value；`LiteralType` 比较包含 fallback+value，不能把 Python 的 True==1 当成 Literal[True]==Literal[1]。源码支持目标方向，没有证毕全调用图安全。 |
| 唯一 F2P 的全部语义 | `testLiteralAndInstanceSubtyping` 四个合法 return 位置：标记 True/int 与 False/str 两分支、Final(1,) 和显式 Tuple[Literal[1]]；一条 reveal 显示已声明返回联合。六个错误：Final(2,)、Final(True,)、互换标签和值的两分支、普通 bool() 标签的两分支。后六项阻止任意值/任意 bool/丢失分支关联的接受；不是只看 reveal。已有 bool fixture 和 Final/Literal stub 可读，运行调用真实 build 和完整诊断比较。 |
| 修改旧例不可漏记 | 官方 patch 还修改 `testLiteralFinalGoesOnlyOneLevelDown`（base:2677–2696）：保留原两 reveal，去掉 known-broken 注释；将 force1/force2 的 reveal 包装改为直接调用，移除相应 note，force2 改为无错误。不能把原错误期待当应永久保留的行为。其 case header 未在补丁中，因此实际命令未选到，亦未列冻结 P2P；不得声称 gold 已运行通过这个修改。 |
| 三种范围 | vendor 从补丁抽出的执行选择只有新增 case；冻结 F2P 也只有它、P2P=[]；实际 G/N 各一项。静态阅读的旧 Literal/Final/mutable、tuple 长度/上下文和调用者，比执行集宽，但不是运行保护。N 输出中的省略号是既有 helper 展示截断，完整六 error 来自 test.patch 与完整输出比较源码。 |
| 旧满分假修复主张 | 对右侧 Literal 一概 return True 会破坏 Final(2,)、Final(True,) 等负断言，所以旧“这样也能通过”推断应撤销；不需要运行才能看出其逻辑与期待矛盾。本人初判与主审一致。仍可能存在其它部分实现，不能从推翻一个假说反推 oracle 完备。 |
| 合理替代与精确文案 | 保留 tuple 长度、完整 Union 分支和 Literal fallback 的局部元素比较，是不同于 gold 的合理方向，未实现/重放。上下文方案可能把 incorrect_return1 的 got 由 Tuple[bool,int] 改为 Tuple[Literal[False],int]。本轮新增读 `messages.py:1682–1708`、旧 `check-literal.test:1448–1467,1512–1526`，确认真实 Literal 会这样参与格式化；但没有完整正确候选，故这是具体风险而非已证误拒。只做 tuple 上下文拼接也不自动修好先赋值的 Final，不能把不完整替代叫完整正确解。 |
| 其它部分实现与回归 | 主审 zip-only 漏长度候选有既有长度规则作为反例依据，但重写比较时丢掉原不变量，不是目前已知自然开发结果。可作为后续候选，不把它提升为优先准入门或要求所有覆盖空白逐一实验。Gold 普遍利用 last_known_value，相关 mutable 擦除值得关注；`checker.py:2227–2231`、`erasetype.py:134–151` 有擦除机制，没有已定位的漏擦反例。 |

## 原件层次与历史修正

独立初判已核 G/N `ledger.jsonl:1` 及 `eval_logs/evallog_replay-er19-iw1-python___{74f1c394,32643f4f}.eval.log`。G 目标通过，N 在本应合法位置多出三个诊断；既有六错误仍是期望，评分 1/0 来自完整目标比较，不是缺引用、零解析或安装早退。日志 SHA256 分别 `b3c642eaa547d3305fdbd1c430ac75b056dc7e79e31dbd5035b911b98d56c2d2`、`66b83257ad1498dc45040afb402d02d3f6248a6c8981e1c6d8bcd3ee15b187ba`。

指定派生镜像为 `sha256:853ffff2219f5167a87f7f310b17b8362d098f66745c20d0406c44c2c708edd0`。image.json/build.log 和通用 install_wave1 构建是提供离线 build wheels，不预设实际 pip 都升级到它们。G `:472–548`、N `:458–534` 的真实安装过程支持 editable 成功；Python3.9.19/pytest6.2.5/typing_extensions4.12.2/mypy_extensions0.4.4 与 types-typing-extensions3.7.3 pin 均须按各自含义记录。共同 test-requirements pin 属引用初态，不是本轮新改测试；git show 中祖先提交差异也不当成当前候选改动。

开门后独立读本题旧记录并追到以下精确原件：

- `runs/env_overnight_20260916/L1_mypy_1/dupidx.txt:12,66` 和 `kcheck_all.txt:1–4`。共享 subtypes.py 明确推翻“只有本题改此文件”，但不推出重复。kcheck 只支持一选择器无过选，不提供旧 case 运行成绩。
- 本题精确 stage1 路径不存在；旧记录引用另一题的运行命令不是本题证据，未跟进那条邻题原件，亦不声称本题旧对照是 report-only 的成功。
- 原始 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl:201` 的 id/base/version 对应，14157 字符 hints 全文读。它包含上下文、Final 和已知值比较的讨论，部分建议带条件、存在措辞方向混淆及其它容器争论；不能用作者讨论给某替代证明正确，或把“若别处忘记擦除则 unsafe”改写为已证 gold 不安全。公开包未给这些修复讨论，不意味着 solver 必须猜 gold；公开源码/文档已提供调查路线。未访问讨论中的外链。

同意主审撤销旧“缺 hints 无法正确解”“P2P 空所以无保护”“测试强制唯一实现”“gold 确定不安全”的论证；保留精确诊断与广泛擦除安全性的具体未知。原修改旧 case、原题 CLI/flags 和更广回归未运行，不将静态同向写成已过。

## 开发与评分边界

两侧运行属于 derived grader/rh2grader/54322，candidate.apply_user=agent/54321 不等于 formal actor 开发验证；后者仍用 public image。模块来自 `/testbed/mypy/__init__.py` 不完整排除 subtypes/checkexpr 被编译模块遮蔽。公开源码、stub 和本地临时文件可支持普通 Python 开发；没有已知外部服务/GPU 前提。actor 的 shell、算法模块来源、可写目录和资产可见面仍待验。

`prepared_task_face.py:312–338` 的 test_globs=()，官方精确恢复 check-literal.test，gold subtypes.py 和合法 checkexpr 路线可投影。未触及 helper/fixture 不因文件名自动恢复或剔除；没有依据新增目录级 exclusions。评分只对冻结引用计分，正常完整 pytest 中非引用失败/rc1 不自动变 reward0；启动、收集等全局失败另判。当前这次 N 的失败确在冻结 F2P，不能反过来用该规则弱化它。

没有实际 actor 全可见面、工具/网络取答案或 helper 绕过验证；正常 gold/noop 的 runner digest 不等于控制面普遍安全。本人已读同包三题私有材料与后续公开源码中的祖先修复，不是盲解；共享文件不是去重结论。真实求解、训练收益、重复稳定性和成本未知，审查产物不交 solver。

## 唯一优先下一实验

**在已核的 install_wave1 固定派生 grader 上，对题面单元素 Union 的完整原例做 base/gold 对照，并附 `(2,)`、`(1,999)` 两个独立拒绝输入。** 它直接验证合法例与同一公开注解的值/长度边界；保留题面 Python3.7 目标和明确 flags，记录实际模块来源。以现有冻结 0/1 为评分锚，不先扩充奖励引用，也不要求先构造 zip-only 假修复。

正式 actor 身份、依赖、开发写权限和答案隔离，应在启用实际 solver/正式任务前单独验收；固定 grader 窄语义实验只依赖其自身代码、解释器、材料和输入可解释，故不必等完整 actor 核验。该顺序修正同时约束主审下一步与本人封存初判。之后按具体结果选择官方修改旧 case 或完整上下文替代的诊断对照，不把每个尚未执行的回归列成硬门。本轮未执行实验、未改源码/材料/oracle，不称 ready_for_probe。

## 阅读与暴露

独立初判前 environment_record 仅看键名；10308 获准 materials decision 在同上下文暴露，已披露。开门后读本题 public_read 需求/路线段（1–57）、完整主审 analysis/delta/card、screening 的状态/主要问题/规则/处置和必要引用、本题 history 精确旧记录与上述原件。未把 public reader 后续命令、主审全文引用列表或全日志哈希视作内容全读；既有日志只读身份/恢复/安装/目标结果段。没有读其它题/包、B1/B2 聚合或 CPU 队列。此次只有静态文本/JSON/哈希及写 review，未执行项目、测试、安装、容器、联网、SSH 或模型，未修改初稿或主审产物。
