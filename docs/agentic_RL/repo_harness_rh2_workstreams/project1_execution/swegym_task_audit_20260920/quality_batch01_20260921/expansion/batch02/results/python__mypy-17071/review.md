# python__mypy-17071 — 独立复核

2026-09-21；独立 reviewer。先完成并封存三题初判，再按协调者统一开门阅读主审/公开/历史。本题初判 SHA256=`f6e3083d06de800eb1525ade5de9fac5e4d159e5cb4b437ae35361550b2ca638`，原字节不变。

**同意 needs_review / static_review / development_diagnostic，additional_exclusions=[]。** 派生 grader 的真实 0/1 证据可靠，公开需求可以调查，尚无已证错误修复满分或正确修复被拒。保留 TypeIs 的范围差异，但其仓库依据足够明确，不把这个差异或共享 visitor 的全部覆盖空白自动设为拒收门槛。修改主审及本人初判的实验排序：固定 grader 上的窄语义对照不必等待正式 actor 资格验收。

下列路径以 `.` 为根。U=`runs/swegym_quality_batch02_20260921_v2/public/python__mypy-17071`，P 为同层 private 本题目录；W=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-17071`，G/N=`W/{gold,noop}`。

## 决定性主张与八方面覆盖

| 项目 | 复核结果与证据边界 |
| --- | --- |
| 公开目标与材料 | 基线 `4310586460e0af07fa8994a0b4f03cb323e352f0`。callback 的 TypeGuard[T] 应是外层返回 T 的合法来源，且保留 str 推断与真正未绑定 T 的错误。缺导入、T 定义及缩进能按公开惯例补齐，不是猜隐藏行为。题面重复是真实呈现问题，不导致双份要求或不可解。 |
| 根因与 gold | `checker.py:1422–1439,7389–7396` 收集参数 TypeVar；`typetraverser.py:83–87` 原只遍历参数、普通返回和 fallback；`types.py:1802–1803` 将 guard/is 目标另存，普通返回为 bool。Gold 补遍历两字段，源码链支持修复遗漏。局部 CollectArgTypeVarTypes override 也是合理路线；未运行，不能声称必过或一定更安全。 |
| 全部新增 F2P | 两个镜像 case 分别用 TypeGuard/TypeIs：object 实参、失败 guard 分支 raise、成功路径 return x，唯一显式 note 为 str；整份输出比较还要求签名与返回不新增 error。is_str 的 pass 是静态输入，测试未执行它，不构成运行时空实现绕过。已有 exception fixture 与 typing_extensions stub 定义所需名字，不能因 runtime typing_extensions4.8.0 推断 TypeIs 测试缺件。 |
| P2P 与三种范围 | TypeGuardIsBool 的三次 reveal 保护参数/变量/属性的 bool 表示；TypeIsUnionIn 的三次 reveal 保护 true/false/合流的 str/int/Union。两新增加这两旧例，既是实际四个执行 item，也是冻结 2 F2P+2 P2P，但选择来自 test.patch case 正则，引用来自 grading，不能泛化为同一来源。旧 unbound/generic/alias/higher-order 用例和共享 visitor 调用者已静态读，未实际运行。 |
| 具体漏判假设 | 冻结四例没有真正未绑定返回 T 的负例。全局关闭检查，或见任意 guard callback 就放行、未检查同一变量身份的部分实现，可能留下错误接受；这是有公开 `check-generics.test:1593–1621` 和 unbound 规则支持的待验候选，不是已发生满分漏洞。正例中 noop 的 str 推断原本已正确，不能将 gold 的作用误说为新增了泛型推断。 |
| 合理范围/误拒 | public reader §1/§2 承认题面只提 TypeGuard，同时源码已有 TypeIs 的并行表示、约束和旧测试；本人追加核读 `constraints.py:1020–1037` 确认并行约束推断。故同时补两字段有公开依据；“只补 TypeGuard 一定是完整正确解，被第二 F2P 拒绝就是误拒”仍未成立。若采用只修显式 issue 的较窄契约，范围分歧仍需显式裁定，分数实验本身不能决定这个规范问题。 |
| gold 回归影响 | 公共 visitor 会影响变量冻结、namespace、位置设置、实例收集/消息和 mixed traverser；已有两个 P2P 不能单独认证全部影响。主审将其列为影响范围而非“这些代码完全没被执行”是准确的。无具体回归反例时，不要求先把六类消费者所有测试跑绿。 |
| 开发、边界与用途 | 普通 Python 源码和窄类型检查即可推进，未见外部服务/GPU 前提。实际 actor 条件、完整可见面、真实求解轨迹及成本仍未知。test_globs=()；官方仅恢复两份 .test，gold/合法 collector 源码路线可投影。静态候选不等于正式训练/评测或 ready_for_probe。 |

## 原运行和历史原件

独立初判已核 G/N `ledger.jsonl:1` 与日志 `eval_logs/evallog_replay-er19-iw1-python___{9334e4a9,2965a84e}.eval.log`：G 四过，N 两新增失败、两 P2P 通过；N 两失败均额外 UNBOUND_TYPEVAR，原本已 reveal str。对应 reward 1/0，解析四项且无缺引用/跳过/全局失败，不能用一般 rc1 规则淡化这两个真实目标失败。

两日志 SHA256 为 `0c3a93d8b6e408f077e7c0850360e3bea27df194b2b2db402c69c1ca2f769022`、`157f289d953f20635d3aebd663e2932d8dc7c6eab52f32815ebae558ec8f5148`。派生镜像 `sha256:65be15358f008d20c0dd256c9e70e3f09c85154113ea04875f1a71e98ed751fe` 固定；image.json/build.log、通用构建脚本与真实安装段相互对应。实际 Python3.12.4、pytest8.1.1、typing_extensions4.8.0、setuptools68.2.2；离线轮子目录里存在新版本不等于实际安装版本。Editable 安装成功由中间日志证实，不能仅用安装末尾 rc0。

主审指出原命令受 pyproject 的 -nauto 影响，实际 11 workers；我同意，不改写成 -n0。账本导入 `/testbed/mypy/__init__.py`，不等于已穷尽 typetraverser/checker 的编译模块遮蔽可能。运行身份为 derived grader/54322，apply_user=agent/54321 不认证正式 public-image actor。

开门后已读 I2/history 精确 refs 所指旧记录，并独立追到：

- `runs/env_overnight_20260916/L1_mypy_2/prescan.json` 和 `kscan.json` 仅本题对象。前者 stage1=null、gold/empty=NO_LOG，后者列四引用并无过选；本题精确 stage1 路径不存在。旧“无执行”描述不能覆盖后来的 09-19 原件，也不能据旧报告造出本题 stage1 成绩。
- 原始 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl:226`，id/base/version 相符。issue 是 819 字符重复两次；473 字符 hints 是两个相同段落，中间换行。只能确认源记录已有重复，不能由本题推出提取器具体故障或全池重复率。hints 说 1.9 仍复现并猜 TypeGuard 内部未被检查，是线索，未访问其外链。
- 旧 helper 绕过建议追加核 `U/base/mypy/test/helpers.py:107–139` 和 `testcheck.py:192–195`：比较数组后 pytest.fail 是真实断言链，直接 return 会影响该链；但无候选投影/真实评分原件，不称已验满分。它是评分控制面问题，和“错误取消 unbound 诊断”的语义候选分开。

同意主审撤销“局部 override 一定更安全/一定过”“共享文件唯一所以非重复”等超证据结论。不同题使用不同文件不足以完成家族审查；本人封存初判已披露本包后续版本含另两题祖先修复，不能由这种关系认定同题或独立留出。

## 保留的分歧与唯一下一实验

TypeIs 的范围是规范判断，不宜独占首轮 CPU，也不应仅因未在 issue 字面出现就给题目加硬门。现有公开表示/约束/旧用例支持两者一致处理；允许局部 collector 和公共 visitor 两条路线。只有在明确定义“TypeGuard-only 已满足任务”并取得其独立正确性与冻结拒绝证据后，才可称具体误拒。

**唯一优先下一实验：在已核的 install_wave1 固定派生 grader 上，对补全的公开 TypeGuard 原例做 base/gold 对照，同时加入一个回调只含 U、外层直接返回另一 T 的真正未绑定负例。** 正例预期 base 有题面诊断、gold 消除；负例在两侧均应保留类型变量错误。沿用已有四引用 0/1 作为评分锚，记录实际代码/解释器来源即可。它直接确认公开目标与“只要有 guard 就不报错”的语义边界，成本小于展开全部 visitor 测试。

正式 actor 的 public image、agent/54321、开发写权限/依赖及答案可见面应在启用真实求解前验收；这些不是固定 grader 上检查 oracle 的前置条件。主审和本人初判先做正式 actor 的顺序应调整，不能把可独立推进的诊断绑成串行门。随后是否做部分实现冻结得分、局部替代或共享 helper probe，应按首项结果与责任边界决定，不机械排全套缺口。本轮未执行任何实验、未改输入/评分/排除规则。

## 隔离与实际阅读

初判环境记录只查看顶层键；同上下文已读三题 gold/隐藏测试及 10308 获准材料 decision，已在初判披露。统一开门后读本题 public_read 的需求/范围段（1–57）、完整主审 analysis/delta/card、screening 的状态和决定性 issue/规则/处置，及本题旧记录、精确原始行和索引对象。未把 public reader 的未重读命令段、40 项重复引用或全日志哈希当成逐行内容阅读。未读其它题/包、B1/B2 汇总或 CPU 队列。所有既有 pass 是原日志重读，不是本次重跑；此次仅静态阅读/JSON/hash/写 review。正式泄漏、安全性、盲解、训练价值和成本未知，报告不交 solver。
