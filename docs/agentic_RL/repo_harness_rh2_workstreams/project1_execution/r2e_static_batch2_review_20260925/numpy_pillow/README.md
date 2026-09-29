# R2E 第二批独立复核：两道 NumPy、两道 Pillow

2026-09-25，Codex 独立语义与证据复核。**主要运行事实成立；两项 P2 口径问题建议在本轮汇总时修正，另两项范围/分类澄清不阻塞当前诊断用途。** 没有修改题面、隐藏测试、实现、既有报告或历史证据；未启动 Docker、SSH、联网或全库测试，未提交。

## 1. 范围与结论

本报告中的路径简写：

- `B`：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925`。
- `R`：`runs/r2e_actor_20260925`；`G`：`R/grader`；`C`：`R/grader_cands`。
- `V`：`runs/r2e_static_prep_20260924/v3`；`PUB(iid)`：`V/public/<iid>/worktree`；`PRI(iid)`：`V/private/<iid>`。
- 下表短 ID 均对应题号，不跨题复用候选名。

| 题目 | 独立复核结论 | 证据边界 |
| --- | --- | --- |
| numpy `5e8301c2` | C-C 只放宽第二个维度为 1 的方向，仍获 35/35；gold 对 BLAS 收缩的单例维不完整；C-A 已覆盖私有检查中的两类失败且仍获 35/35 | 评分、私有后检成立；不能把“gold 过不了”用作公开需求的边界 |
| numpy `a5ea773e` | B、C、RC2、RC3 均获 32/32，却分别漏复制或破坏公开 docstring 约定的升维；A 无条件复制的替代实现获 32/32，已检查六种输入均正确 | 未发现本次合理候选被误拒；只证明所测候选和输入，不证明所有合理实现都能通过 |
| pillow `3a61c9e9` | W1/W2/W3/W5 均获 71/71，GIF、C 层 alpha、非恒等映射、源图保持分别有反例；C1 与 gold 在已测场景一致 | W5 连题面恒等映射的原始 RGBA 内容也未保住；原有打印命令不能直接当语义通过判定 |
| pillow `3ac9396e` | K2、K4b、C6 均获 11/11；C6 把整数读回类型改成 `IFDRational` 的回归成立；gold 的 LONG→SHORT 变化成立，但不等于已证明 gold 有缺陷 | 非零分母范围须结合公开文档说明；本地原函数另确认 K4b 连其它 tag 的零分母也未修 |

读取了四题的公开题面、公开读者需求表、初判/题卡/独立复核的相关论据、结构化记录的 issues/disposition，及相关原始源码、隐藏断言、候选补丁、评分与后检原件。历史轮材料仅用于分辨引用层次，未重复全部旧轮对账、跨题扫描和 81 条全账。

本次深审 A/E/F/G/H/M/N：行为、测试区分力、公开约束、真实评分入口、事实来源、诊断判定及环境身份；B/I 用于限定 reward 的用途和修订分期。C/D/J/K/L 没有新增治理、所有权、实现结构或性能改动，不另设平台审计或测试门。原分数保留；本报告不批准训练/评测准入。

## 2. 已独立重核的证据

复现命令（只读原件，输出仅写本目录）：

```sh
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/numpy_pillow/audit_evidence.py
```

产物：`audit_evidence.py`、`evidence_audit.json`。

- **27 条正式评分全部对上**：NumPy 5e83 的 3 条、NumPy a5ea 的 8 条、Pillow 3a61 的 7 条、Pillow 3ac9 的 9 条。逐条复算候选与原日志 SHA256，按现有 `r2e_parsers.py` 的原函数重解析测试段并与当前 `expected_output.json` 逐键比较；reward、命中数均与账本相符。评分用户均为 uid 54322、网络 `deny_all`，测试段完整，清理记录均成功；所查候选无测试样路径。
- **28 份私有后检**逐份读取。除 np5 的 base `extra2_none.json` 外，均能按实际 image ID 与候选文件名对应本批正式评分；np5 本批没有 noop 正式行，未伪造这项关联。原输出与汇总的主要语义结果一致。
- 正式评分的 patch/log 摘要闭合。私有 JSON 大多只记录 image ID、补丁路径、clean apply 和命令输出，没有记录补丁摘要；因此身份结论是“路径、候选内容及行为相符”，不能写成私有执行补丁的摘要也已核实。这个局限**不推翻本次窄结论，也不要求为本轮新增哈希系统**。
- `private_control_full.py:1-4,24-40` 明确是 root、不联网的一次性容器。早期 np5 `gold/CC/CA.json` 未直接记录 user/network，其 runner 调用见 `G/b2_numpy5e83.sh:9-12`，不能把它们当 agent 开发命令。`devcheck/.../orig/` 是真实 CC + 桩命令的 agent 执行，尚不是模型自主解题。27 条评分是正式评分代码回放，也不能自动升级为真实 actor 求解闭环。
- 本地仅执行 Pillow 3ac9 原件中的 `TagInfo`、`IFDRational`、`_setitem` 与字段编解码函数。候选补丁严格按原 hunk 在内存应用，逐行核对上下文；没有导入当前 Pillow 替代旧版本。该探针不是整图保存/重载，证据级别为 `test_only` 的原函数路径。

## 3. 可行动发现

### NP-1 · P2：不能把原始满分解释为“题面那一例修好了”

**当前行为与位置**：`B/README.md:70` 把全批满分统一解释成“题面那一例修好了”，并建议 §2 的脚本与命令都可复用。Pillow 3a61 的现有证据已经否定这项保证。

**违反的不变量**：评分通过只证明给定 verifier 的观测满足期望。若 verifier 的参考对象可在调用中被改变，就不能推出示例的初始对象或预期语义被保留。

**证据**：

- `PRI(pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07)/hidden_tests/test_1.py:607-614` 在 `remap_palette` 调用之后，才读取原图的 `palette.palette` 作比较。
- `C/pillow_3a61_W5_mutate_source_to_rgb.patch:9` 先执行 `self.putpalette(self.getpalette("RGB"))`，丢弃源 RGBA alpha。
- `G/ledger_p3a61_W5_mutate_source_to_rgb.jsonl:1` 为 71/71、reward 1；独立重解析一致。
- `G/private_public_b2/p3a61_W5_mutate_source_to_rgb.json:9-10,16-17` 显示 `same_palette_bytes: True`、`rgba_render_equal: True`，但源图与结果都已是 RGB、768 字节。调用前题面建立的是 RGBA、1024 字节。这不是成功保留原调色板。

**影响**：会把“过了断言”误计为最低限度的语义成功。若直接按原命令 rc 或输出的 equality 布尔量汇总后检，W5 仍会被放行。现有 review 已正确指出这一点（`B/results/pillow__3a61.../review.md:111-116,132-143`），总入口不应覆盖掉这个限制。

**建议分期**：本轮汇总口径修正；不改历史 reward。以后实际启用诊断时，再把“可复用命令”变成有明确比较规则的后检。

**最小复现/验收**：无需新容器，读取上述账本与 JSON 即可复核。汇总应改为“reward=1 表示当前评分映射匹配；语义成功须另证”。Pillow 后检要在调用前保存源 palette/渲染快照，并验证源图未变；gold/C1 应通过，W2/W3/W5 应分别因渲染、非恒等映射或源对象变化失败，W1 由 GIF 往返检查拒绝。不得只查 rc=0 或调用后的两对象相等。

### NP-2 · P2：NumPy 的 gold 失败不能用来划定公开修复范围

**当前行为与位置**：`B/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/card.md:49`、`analysis_before_history.md:175` 写“不建议加 tensordot/多操作数断言：gold 过不了，属于扩大需求”；`review.md:154` 又以上游 #10930 被单列作支持。

**违反的不变量**：合理解与测试覆盖由公开任务和公开 API 约定判断；gold 是候选/参考实现，不能反过来限定题意。上游用两个 issue 修复的历史，也不能限制当前 R2E 公开描述的范围。

**证据**：公开 `V/public/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/user_prompt.txt:7-8` 泛指 `optimize=True` 与 singleton dimensions，未排除求和维度、BLAS 或一维输入。最小反例只需两个输入，不需要争论多操作数：`np.einsum('i,i', [2., 3.], [4.], optimize=True)`。本 base 默认值就是 True（`PUB(...)/numpy/core/einsumfunc.py:1062`）。

`G/numpy5e83_extra/extra2_numpy__5e8301c2b36097dd8be5a12.json` 已证明 gold 的默认调用抛 `shape-mismatch for sum`，`optimize=False` 返回 20.0；对应 C-A 文件返回 20.0。`G/numpy5e83_extra/gold.json` 中显式 `optimize=True` 的矩阵收缩也报同错。正式评分 gold 与 C-A 都是 35/35。

**影响**：会把一个已有公开依据、已经实测的覆盖缺口收窄成必须先扩大题意才能讨论的事项，倾向保留 gold 式部分修复。报告同时称 gold “修不全”，也与“这类输入在题意外”的硬结论不一致。

**建议分期**：本轮修正论据，不要求立即改题或重跑。将“双操作数、单例求和维的普通优化调用”与更广的多操作数/路径规划边界分开；前者不能仅因 gold 不通过就排除。是否改 reward 测试仍按既有用户决定和材料修订流程办理，这与是否存在公开语义依据是两回事。

**最小复现/验收**：用现有两份 extra2 原件和显式 optimize 的原件即可。修订建议需列出不同测试选择的真实后果：仅补交换顺序时 gold/C-A 通过、C-C 失败；若加入上述公开语义检查，旧 gold 应失败、C-A 应通过。不能为了保持旧 gold=1 而把失败输入自动判为范围外，也不能把 C-A 在少量检查通过泛化为所有广播形式已完整验证。

## 4. 不阻塞本轮的澄清

### O-1 · P3：LONG→SHORT 是已证实行为变化，尚不是已证实 gold 缺陷

`B/README.md:73` 及 `project1_execution/env_data_eval.md:220` 把 Pillow 3ac9 的整数类型码变化与另三题的实际异常/挂起并列为“gold 自身有缺陷或回归”。

已证事实是：未指定类型的 tag 65000=5，base 编码 LONG(4)、gold 编码 SHORT(3)，二者都读回整数 `(5,)`；见 `G/private_public_b2/p3ac9_ir_{none,pillow__3ac9396e8c991e7baab66187af2a35c3}.json`。公开文档 `PUB(pillow__3ac9396e...)/docs/handbook/image-file-formats.rst:503-518` 说明字段类型自动识别，没有承诺未知整数必须编码成 LONG。base 的 `_setitem:504-508` 已存在“小整数选 SHORT”分支，只是此前不可达。

因此可以登记“编码宽度/类型码变化，兼容影响未证明”，不宜计作第四个已证明 gold 缺陷。**这不否定另三题已证实的 gold 缺陷。** C6 是另一件事：它把 int 变成 `IFDRational`，原 API 的值类型改变；原件后检与本地字段探针均确认。`IFDRational(5,1) == 5` 为真，因此只查等值抓不住 C6，读回类型检查合理。避免固定 `tagtype==4` 的理由应是公开契约未固定整数编码宽度，而非“否则 gold 过不了”。

最小验收：汇总分开这两项；gold 标为行为变化，C6 仍标为已证实回归；保留原始分数。无需新增实验或修改题目。

### O-2 · 范围建议：Pillow 不应把“其它 tag”与“非零分母”一并当题外

`B/results/pillow__3ac9396e.../card.md:18` 把“非零分母、其它未注册标签”统一列为题面范围外；`review.md:13,79-81` 则认定检查非零分母必须先改题面。建议澄清成三层：

1. 题面明示：tag 41988 的 0/0 往返及 `[0]` 形状。K1/K1b/K2/K4b 都满足已测例子；K3 分母变 1、K4 变标量，拒绝有公开依据。
2. 同一零分母问题换未注册 tag：题面描述是“rational metadata values with a denominator of zero”，41988 是示例，不能只凭 tag 不同就判题外。本地原函数探针已确认 `65000=IFDRational(0,0)`：K4b 仍选 LONG，原字段 writer 抛 `struct.error`；gold/K1/K2 选 RATIONAL 并还原 0/0。这只是字段路径的新验证，不冒充整图真实保存结果。
3. 非零分母 1/2：issue 的中心是零分母，但公开文档的 IFDRational 自动识别约定更广。K2 在这里失败已被真实后检证明；应说明它是“满足显式零分母条件、未恢复一般类型推断”的窄修复。是否把这一项纳入本题的 reward，可以由用户选择；不能仅以示例没写 1/2，直接断言一定需要扩大公开题面。

这项建议不阻塞当前静态诊断用途，不要求本轮补题或改分。若以后决定补测，先明确哪一层算验收；不把 K2 与仅登记一个 tag 的 K4b 混为同一种缺陷。

## 5. 后检、补测与合理解的最小边界

| 题目 | 可保留的诊断/候选结论 | 最小注意事项 |
| --- | --- | --- |
| NumPy 5e83 | 交换操作数、双操作数 singleton 收缩能区分 C-C/gold/C-A | 有非整数输入时允许合理舍入误差；不能把 BLAS helper/路径本身变成验收要求 |
| NumPy a5ea | 六种全 1 reps/输入形状的现有后检能区分 gold/A 与 B/C/RC2/RC3/D | shape 依据公开 docstring `shape_base.py:796-807`；复制应检查实际变异隔离或内存不共享，不只看对象身份；`may_share_memory=True` 一般只是可能共享，本次候选源码与简单连续数组使共享结论成立 |
| Pillow 3a61 | 非恒等 RGBA 重排、渲染、GIF 往返均有公开函数或调用者依据 | 先快照；部分映射不固定 Python palette 总长度或未使用项的 alpha；gold/C1 的不同补齐方式都可合理 |
| Pillow 3ac9 | C6 的 int→IFDRational 回归、K3/K4 的失败语义均已明确 | 保留值及值类型，不强迫未知小整数为 LONG；类型码 5/10 在已测 0/0 场景都得分，不代表两者所有正负范围均等价 |

“没有发现本批合理候选被误拒”可以保留。“所有合理实现都不会误拒”不能由这些有限候选和“隐藏测试是公开测试加示例”推出：公开测试本身是否依赖实现细节仍须独立判断。本切片没有找到需要新增误拒计数的候选。

## 6. 交给主审的共享项与停止条件

- `B/README.md:72` 从 orange3 的 Python 3.7m 链接失败推广为 NumPy/Pillow 所有 C 扩展都不能重建，证据不足。本切片两道 Pillow 的评分和私有日志都是 Python 3.9.21；NumPy 是 3.7.9。编译器/解释器/链接参数不同，不能从共享配方推出同一失败。**交主审与环境切片裁决**；本报告只确认“这四题评分均跳过安装”，没有运行重建。
- 私有后检身份记录的限制已如实标明。当前文件、补丁及行为足以支持已测窄结果，不为此另设本轮闸门。
- `card.md`、`screening_record.json` 的实跑前字段与第二步 review 有时不同，批次 README 已明确它们是时点快照。本报告不要求回写封存初判；当前摘要必须采用已实跑证据。
- **停止条件已满足**：四题主要候选结论、27 条评分与关键私有后检已核；NP-1/NP-2 可凭现有证据修正汇总。其余只登记或澄清；不因还能构造输入反例而继续扩大本轮。后续正式 actor、训练 reward 修订和跨题划分由原任务主审/用户处理。
