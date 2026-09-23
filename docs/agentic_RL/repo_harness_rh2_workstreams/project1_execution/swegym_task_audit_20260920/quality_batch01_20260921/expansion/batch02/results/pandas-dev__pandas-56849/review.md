# pandas-dev__pandas-56849：独立复核

2026-09-21，B2 pandas reviewer，第二阶段。**建议保留为受限静态候选：`state=needs_review`、`scope=static_review`、`intended_use=development_diagnostic`。** 同意主审保留 warning 措辞过严、频率属性漏检及参考身份合并的具体限制；它们尚不是实际候选错分的运行证明。历史 noop/gold 对照成立，不能据此给正式训练、评测或 actor 启用批准。

本文路径除特别说明外相对 `ROOT=${REPO_ROOT}`。`I=runs/swegym_quality_batch02_20260921_v2`，`B=I/public/pandas-dev__pandas-56849/base`，`P=I/private/pandas-dev__pandas-56849`。第一阶段初判 SHA256 为 `cc61dc855bd0f2d3b0f95b5090ae9a52b413a3b35ffea04eb2ace1bbd28cd109`；三题全部封存后，才按协调者统一开放读取本题五份主审/公开成品及 `I/history/pandas-dev__pandas-56849/refs.json` 指向的唯一旧记录。初判未回写。本轮仅静态文件、JSON 和文本计数，未导入项目、运行 pytest、构建、安装、容器、网络或模型，未改源码、测试、gold、参考或 reward。

## 决定性论据复核

| 主张 | 本 reviewer 的原件核对 | 复核判断 |
| --- | --- | --- |
| 公开主例应恢复小写 m 的月末序列 | 题面给出 20 个月末；base `offsets.pyx:4863–4871` 在大小写归一化前查仅含大写 M 的弃用表；`date_range` 调用 `to_offset` | 同意。ME 与 FutureWarning 可从公开弃用映射和旧 M 测试推知，不是全套隐藏新要求。 |
| 唯一 F2P 约束完整 warning 文案及两个日期 | `P/test.patch` 全文；`B/pandas/_testing/_warnings.py:128–180,217–230`。`match` 走 `re.search`，并检查 warning 类别、调用文件等 | 同意有小写 `'m'` 措辞误拒疑点；须称正则匹配，不能称逐字字符串相等。前缀如 `Freq ` 不必导致失败，末尾点也未转义。 |
| expected 的 freq=ME 并不证明实际 freq 被验证 | 新补读 `B/pandas/_testing/asserters.py:181–349` 和 `core/indexes/datetimelike.py:141–175`：类型/dtype、长度、值、名称检查中没有 DatetimeIndex.freq；equals 最终比较 dtype 与 asi8 | 确认主审这一补充。初判表格把带 freq 的 expected 紧邻结果相等，容易被理解为 freq 已受保护；本复核明确修正这一推读，不改封存稿。 |
| 修改旧 invalid 测试只是处理新增 warning | `P/test.patch` 第二处仅增加 `ignore:.*'m' is deprecated.*:FutureWarning`；base `test_to_offset.py:47–90` 仍要求 ValueError，包含 `2h20m`、`-m` | 同意。没有删除非法频率断言；该 filter 的小写约束也会影响输出大写 M 的正常规范化路线。 |
| Gold 恢复通用转换且保留旧行为 | `P/gold.patch` 三处查表改为 name.upper，warning 仍用原 name；`is_period is False` 分支边界未变。初判已读共享调用者及相关 offset/date_range 旧测试 | 同意限定范围内自洽。没有发现具体 gold 回归；不把未穷举的其它别名、Period、闰年和全仓行为都升为硬门。 |
| 426 项执行不等于 420 个独立完整节点评分 | 下述原始摘要行重新作纯文本分组，426 条状态对应 420 个空白截断键；4 组含 10 个完整节点，减少 6 个身份 | 确认身份合并。两份原日志的这些成员全部 PASSED，没有证据推翻这次 0/1 分差。 |

具体合理替代仍是：仅在非 Period 且名称确为旧别名时，先规范化名称、再复用弃用转换；保持 MS/ms 区别、倍数、非法输入和真实月末结果，warning 使用规范名 `'M'`。公开材料没有把输入原大小写规定为唯一 warning 文案。因此主审提出的是有公开依据的潜在误拒，而非仅因不同于 gold 就认定合法。该候选未写入、未编译、未评分，不能记为已证假阴性。

自然部分实现如仅在 date_range 入口处理字面 m、遗漏 `to_offset("m")` 或 `2m`，以及重建正确日期但丢失 freq，能说明观察范围偏窄；目前都只是静态假设。首两个日期、20 期长度、倍数和 freq 分别属于不同观察量，不能把其中一项通过冒充其余均覆盖，也无需因一般未覆盖边界判坏题。

## 执行集合、冻结参考和实际阅读

历史原件为 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-3/ledger.jsonl` **第 11 行 noop、第 12 行 gold**；对应日志同目录 `eval_logs/evallog_replay-f216-baseline01-w_1d6b2dfa.eval.log`（N）和 `...w_2a3467af.eval.log`（G）。第一阶段已核安装、目标失败/通过、账本和收尾；第二阶段补核全部摘要状态的身份分组。

| 集合 | 本题事实 |
| --- | --- |
| 实际历史执行 | 两个官方测试文件共 426 collected；noop 425 passed/1 failed，gold 426 passed。 |
| 冻结评分参考 | 1 F2P + 419 P2P，共 420 键；noop F2P 0/1、gold 1/1，P2P 两侧均 419/419，reward 0/1。 |
| 本 reviewer 实际读过 | 全 test.patch、唯一 F2P、完整 `test_to_offset.py`；初判记载的 date_range 弃用/边界/负向范围、fixture/helper 和调用者。第二阶段补读上述两个比较 helper 及 `test_date_range.py:1258–1274` 的 custom-business-day 测试，复读 offset 参数正文。未逐体审阅其余全部 419 P2P，也未运行额外 Period 或全仓回归。 |

四个合并组分别是 custom-business-day 同一带时区起点的 2 例、`test_to_offset[2h` 的 3 例、`test_to_offset_whitespace[2` 的 2 例、`test_to_offset_whitespace[` 的 3 例。完整节点在 N:3729–3730、3814/3816–3817、3864–3868 与 G:3404–3405、3489/3491–3492、3539–3543 均为 PASSED。已读对应正文分别检查营业日日期、分钟组合和空白解析；不是无意义的名称重复。

当前 `rh2/src/repoharness2/envpack/swegym_parsers.py:44–55` 只取行首状态摘要，以空白切出的第二词作键并后写覆盖。其结果取决于**有效摘要行顺序**，不能用测试执行先后替代，也不能由合并直接推导某失败一定被通过覆盖。当前源码说明机制；旧 run 的真实结果由旧账本/日志支持，未把当前源码认证成旧 runner 的同字节快照。

## 环境、交付和控制面

同意主审区分正式 public-image actor/54321 和历史 grader/54322。后者在 deny_all、2 CPU/4 GiB 下实际完成 editable 安装；G:3067–3069 有 offsets 的 Cython、C 编译及链接证据，不能只看最后卸载 pytest-qt 的 rc。账本观察到 `/testbed/pandas/__init__.py` 和目标 dev 版本；没有独立打印 offsets 扩展的实际加载文件，不补写这种观察。历史约 42 秒 gold 安装、6 秒测试和内存峰值只适用于该 grader 运行。

正式 actor 仍需在其真实入口核解释器、checkout/扩展来源、可写 build 与加载修改后 `.pyx` 的能力；`apply_user` 仅是提交应用身份。这是模型启用条件，不能由评分容器成功代替；本题核心复现不需远程服务、GPU、外部数据或运行期公网。

当前 `prepared_task_face.py` 的 `test_globs=()`，官方恢复仅 `pandas/tests/indexes/datetimes/test_date_range.py` 和 `pandas/tests/tslibs/test_to_offset.py`，从 base 恢复后再应用 test.patch。合法 `.pyx` 修改可投影；`additional_exclusions=[]`。普通完整 pytest 会话 rc=1 不是自动 reward=0，仍要看冻结参考，零解析/全参考缺席/全局故障由 scoring/manager 另判。未恢复的 helper、conftest、配置及 stdout parser 属已知控制面范围，本轮没有利用实验证据，也不自行添加全局排除。

## 历史差异、独立暴露与取舍

同意主审撤回旧记录中“freq 已断言”“warning 严格字符串全等”“ME/FutureWarning 完全隐藏”及将普通前缀必然判错的说法；Period 不是本题必须同步修复的目标。旧运行成本、建议命令、泄漏扫描和同仓关系标签都不能代替当前证据。精确旧记录来自 `env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-56849.json`；本 reviewer 未复读主审后来追到的 stage1 整套原日志，其决定性对照已由本题 baseline 原件独立核实。

主审在本题初稿封存且历史开放后披露一次有界越界读取：对多题 `collide_detail.json` 使用 head，看见开头 `{`、48106 键以及 `scoring_keys_with_collision: 2`，随即停止并上报。按披露记录该事实；不把它追溯到封存初稿，不再打开该聚合，也不推断后来更换的新 48106/53958 主审看过同样内容。本 reviewer 第一阶段看过授权 environment_record 的环境摘要，未跟进质量历史；第二阶段才读本题旧质量结论。

本 reviewer 的跨题权限另有具体原件证据：56849 base 的 `cast.py:634–639` 已含 48106 的分类分支，`api/typing/__init__.py` 已含 53958 的两个类型导出。这是跨版本答案暴露关系，三题并非同一缺陷。主审未核跨题关系的限制是诚实边界，不由本 reviewer 的额外阅读反推主审已知。本上下文不可交给盲解 solver；真实镜像/Git 资产或预训练是否泄漏仍未知。

**唯一优先下一步：采纳主审的固定 grader 规范化候选对照，替换我初判中优先做通用 actor Cython 启用的顺序。** 在冻结官方 patch/参考下，使用上述保留真实月末行为、发规范名 M warning 的正常源码实现；先以独立公开语义检查核 20 期月末、倍数和 MS/ms/非法输入边界，再取官方验收及 RH2 分数，并记录实际编译和加载来源。若语义正确却仅因 warning 大小写被拒，才把潜在误拒升级为实证；若实现本身破坏边界，则不能归罪于 oracle。这个对照较通用环境复验更能区分本题具体验收问题；actor 核验留在正式启用前，不把两套方案同时列为本题当前必测。

上述是未来 CPU 建议，尚未执行；也未承诺修改验收、题面或 reward。当前三层证据分别是历史 grader 实跑、当前静态机制判断、未来拟议实验，真实模型求解和 token/费用均未知。受限静态候选结论不等于质量完备或正式准入。
