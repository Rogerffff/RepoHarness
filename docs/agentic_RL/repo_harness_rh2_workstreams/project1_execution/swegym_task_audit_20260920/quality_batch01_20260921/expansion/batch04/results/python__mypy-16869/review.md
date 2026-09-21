# python__mypy-16869 — 解封后独立复核

2026-09-21。角色为 B4 独立 reviewer。明确解封后仅新读本题 `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`，以及 `runs/swegym_quality_batch04_20260921_v1/history/python__mypy-16869/refs.json` 指定的唯一 own 旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-16869.json`。未追读其中引用的其他题或聚合。继承独立初稿的只读、无项目执行限制；本阶段仅写本文件。

封存核验：独立初稿 SHA256 为 `f5d4b7cee8609ba714c6b049c045d7d5f0a67a62581cadeba0c50ec491b12a56`；主审初稿为 `0e9064f9f2f19653995f7717c2e894b3d4b8a172d5744166b29029f47341d3f0`；公开稿为 `46fc57ff7a95e8801f87f43d7daafb9d514cc23423922904882e985646928ed8`。读取时与记录值相符。未回写任一稿件。证据路径简称沿 `reviewer_initial.md`，根为 `.`。

## 建议与分歧

**可列“受限静态开发诊断候选”**，保留 `needs_review / static_review / development_diagnostic`。不主张把尚未证实的 Unpack 误拒疑点设为进入该静态候选名单的前置阻断：公开目标可定位，base 的目标故障和 gold 的窄修复已有真实 RH2 对照；两种主要 AST 路径都被输出断言覆盖；当前未发现必须拒绝题目的材料错配或已发生的 gold 回归。

“受限”需要写清：当前六例奖励只反映固定输出与已查回归，不能把所有 0 分当成不会修复，更不能自动用于模型优劣、训练或正式评测判断。若模型产出语义等价但拼写不同的 stub，必须单独审查；真实 actor 消息、解释器、修复镜像消费与可见资产仍待验证。这不是 `ready_for_probe` 或立即运行许可。

与主审的**事实判断基本一致**，差别主要在处置表述：主审将等价输出 CPU 对照列为最先动作，我认可该实验值得优先，但不认为当前证据要求先完成它才能将本题列为上述受限静态候选。若后续用途要求直接把原始 reward 当作正确性标签，则应先完成评分语义诊断。两个用途不能混称。

## 逐项复核

| 主张 / 旧结论变化 | 复核结论与证据 |
| --- | --- |
| base 缺 StarExpr 打印是当前题的真实故障，gold 命中根因 | 同意。初稿已独立核源码 `stubgen.py:308–340,749–758`、`visitor.py:483–484` 和 N:434–525；两 F2P 是同一 join/NoneType 原因。G:462–468 实际六项通过，不是仅依据 gold 差分或 parser 标签。版本名称差异未使故障错配。 |
| 全部 2 F2P / 4 P2P 已核，覆盖两模式、两解包语法及 object 行为 | 同意。主审表与独立表一致；两个新增 Unpack 用例在 base 已通过；WithImport 由 `-k` 子串选中。六例不是全仓回归，新增 skip 在历史 Python 3.12.4 条件下没有触发。 |
| check24 应由旧 pass 收窄为 unknown，Unpack 存在具体误拒疑点 | 同意。仅断言外部文本不能推出所有正确实现均被接受。新增核读公开 `S/test-data/unit/check-typevar-tuple.test:98–121`：仓库明确接受普通和两种混合 Unpack 泛型，并检查实例类型；它强化了替代路线的公开依据。`helpers.py:107–139` 会拒绝拼写差异，但完整合法候选尚未执行，所以尚非已观测 false reject。 |
| gold 原 `_Ts` 仍可能生成缺声明的草稿；不应直接判 gold 未修 crash | 同意。独立追过 `visit_assignment_stmt:826–834`、`get_init:1125–1126` 和 `is_private_name:767–780`；默认省略是既有规则。公开草稿定位和 private 选项限制了扩张需求的依据。需要保留这项输出限度，但不可用“gold 同样省略”证明任意类型信息丢失都可接受。 |
| 名称/混合参数及共享打印器回归不足 | 同意其有限覆盖事实，反对把“未覆盖”直接说成已验证错误解满分或 gold 回归。check25/26 的 issue 注释目前明确这一范围，适当。普通 Generic/TypeVar 旧例比机械要求全仓回归更能解释最小检查。 |
| 旧 check3、29 的 pass 撤回；23 仍可 pass | 同意。3 是真实 rendered 消息，29 是真实 actor 资产/泄漏；完整题面、无显式答案链接均不充分。23 的核心需求清楚与这两项无冲突。当前 record 3/24/29=unknown，没有混淆原清单语义。 |
| 旧必须加 `-n0`、低版本 skip 当前阻断不再沿用 | 同意限定结论。实际 11 workers、6 items 和成功/目标失败对照不支持本题必须先改官方命令；但单次历史完成不证明所有稳定性。实际 Python 3.12.4/no skip 排除了本次伪通过，未审共享 parser 对人为 skip 的普遍安全性。 |
| grader 离线安装已验，actor 消费/权限仍未知 | 同意。ledger 的补丁 apply 用户 agent 与评分用户 rh2grader 是不同角色。派生镜像只新增离线 wheels，当前目标镜像可用性、summary 路径、payload 缺口仍在；不能沿用旧 ready_for_probe。 |
| 官方恢复不覆盖合理源码交付 | 同意。两个官方路径均为测试/helper；`mypy/stubgen.py` 在 gold projection 中保留。归档入口和原日志支持此具体判断；不扩张成所有候选路径或控制面安全已验。 |
| 同文件关系不能据此建立重复簇/强制切分 | 同意。获准旧记录本身称不同缺陷；未读另一题，不可让旧索引引用替代关系验证。未追读跨题链接。 |

公开读稿在未见私有材料时独立指出了 `_Ts` 范围和 Unpack 等价路线；这支持其不是由 hidden expected-output 倒推出的新要求。公开读稿不是动态验证，也不证明所有替代候选可行。

## 对自己独立初稿的一处修正

独立稿用过“默认导入入口/模式”的表述，容易误指题面 `stubgen test.py` 会 import 复现模块。解封后按公开读稿提示重新查 `S/mypy/stubgen.py:1396–1425`：文件/目录输入走 `create_source_list`（1414–1421）；只有 `-m/-p` 且无 `no_import` 时才进入 runtime import（1403–1412）。因此本题实际缺口应写成**原样 `_Ts` 的默认文件 CLI 未直接重放**；不能把运行期导入额外依赖当作原例必须前提。其余对星号路径、语义分析与私有过滤的判断不变。保留原初稿以展示此次修正，不回写。

## 唯一 CPU 方案复核

接受主审将 Unpack 合法候选加入同一轮定点对照，取代两份互不相干的实验清单；该轮包含我独立稿优先要求的原例 base/gold 对照。新增公开类型检查用例提供了更具体的替代语义依据，因此优先验证接受性有价值。建议只明确以下判别矩阵，不现在执行，也不预先改题：

| 状态 | 原 `_Ts` 默认文件命令 / `--include-private` | 公开名 Ts、普通 Generic、混合参数及导入 | 原 RH2 六例 |
| --- | --- | --- | --- |
| base | 预期观察原目标 TypeError，而非要求 base 不崩溃 | 记录既有可用路径 | 已有 0/2 F2P、4/4 P2P 可作既有对照；条件改变时另记 |
| gold | 核无目标 crash，单列默认私有声明省略与 include-private 差异 | 核递归打印未丢参数/名称 | 既有六通过是锚点，不能借此免除新条件身份核验 |
| 冻结 Unpack 候选 | 核相同 crash 目标；不要额外要求它解决 gold 也未解决的既有私有过滤 | 用可形成完整 stub 的公开名或 include-private 变体检查语法、类型参数语义、顺序及必要导入；候选有影响时检查冲突/别名 | 在同配方/脚本/参考集下评分；只有失败归因为等价拼写时才确认误拒 |

这里的关键不是“pyi 可 parse”一个条件：须保留可变参数语义，正常 Generic/显式 Unpack 不退化。`BaseStubGenerator.add_name:607–615` 确有在 `defined_names` 冲突时加下划线 alias 的设施，但不能据 helper 存在就保证所有候选导入正确。若候选自身错误，实验只能否定该候选；不能由一个候选失败证明所有等价替代解都不可行。若原 `_Ts` 在 gold 仍出现不同故障，应先归因该新事实，再讨论评分修改。

执行前仍须准备可达 summary、已核身份的派生镜像或明确等价重建条件。正式 actor 验证是运行条件要求，不能由这轮 grader 对照冒充完成。以上为一个候选接受性实验方案，不是同时强制制造正负两个对抗补丁。

## 结构化收口建议与边界

record 的 state/scope/use、未知项、空 additional_exclusions/revision_refs 与正文一致；不需要另造 schema。协调者可在未封存 record 中增加本复核的 facts_ref/hash、改 reviewer_status，并明确“受限静态开发诊断候选”与原始 reward 的解释限制。check27 的 pass 应继续保留现有“限交付与目标路径”的注释；不得在汇总时删去范围并写成 gold 全面正确。issue 的 P2 级别只表示疑点成立时可能影响评分解释，不代表已实证高影响缺陷。

本次没有新增运行结果、模型表现或费用观测；未改任何源码、测试、评分标准或封存材料。复核结束时再核独立初稿 hash 不变。
