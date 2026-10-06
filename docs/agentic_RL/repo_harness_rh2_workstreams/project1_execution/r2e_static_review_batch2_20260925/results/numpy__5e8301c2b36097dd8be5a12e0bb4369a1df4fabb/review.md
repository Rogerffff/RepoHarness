# numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb：独立复核（第二步）

2026-09-25 · 独立复核者。第一步的封存稿是同目录的 `reviewer_initial.md`，本步没有改动它。本步读了公开读者产物、主审的三份产物和历史引用，也读了协调者新给的正式评分和私有容器执行结果。我没有运行项目代码或容器，也没有修改原件。

**路径简写**：沿用初稿的 `PUB`、`PRI`、`HT`、`EF`、`DEV`，另加以下几个。
- `GR` = `runs/r2e_actor_20260925/grader`
- `CANDS` = `runs/r2e_actor_20260925/grader_cands`
- `PR` = `public_read.md`
- `A` = 主审的 `analysis_before_history.md`
- `OD` = `old_findings_delta.md`
- `SR` = 主审的 `screening_record.json`
- `LATER1` = `runs/r2e_static_prep_20260924/v3/public/numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d/worktree`
- `LATER2` = `runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/worktree`

## 0. 结论

**同意的部分**
- 同意主审的处置：`needs_review`，理由是静态候选待 actor 验证；用途注记"reward 1 只说明题面这一例修好了"也同意。
- 以下条目保留：I2（gold 只是部分修复）、I3（报错文案里两个尺寸颠倒）、I4（跨题包含）、I5（真实消息没捕获）、I6（`/testbed` 外的脚本导入不了 numpy，提示里没写）、I7（`run_refs` 截断，旧 reason 文字过时）。

**两条静态主张已升级为执行证据**

新运行的共同条件：`GR/ledger_np5_{gold,CC,CA}.jsonl` 各 1 行；派生镜像 `d0b59d8b…`；配方 sha `0da821a1…`，与 R-f 相同；隐藏测试树 `d8853bba…`，即当前材料；三次运行都是 `exit_code 0`，没有清理失败。

| 候选 | 评分 | 私有容器手动命令 | 说明什么 |
| --- | --- | --- | --- |
| C-C（只放宽一个方向） | 35/35，reward 1 | `order_swap` 仍抛题面原句（`GR/numpy5e83_extra/CC.json`） | I1 的"漏测"不再只是静态推断，已经执行确认 |
| C-A（gold + 执行期 BLAS 守卫） | 35/35，reward 1 | `tensordot_path` 输出 `True` | "更完整的修复不会被误拒"已经执行确认（限这一实现） |
| gold | 35/35 | — | 我初稿里"devcheck 用的镜像上没有隐藏测试评分"这一缺项已经关闭 |

**需要修改的地方（都是精度问题，不改变处置）**
- **M1：跨题"逐字"的说法要收窄。** 两道后续题公开的 `test_einsum.py` 里确实有 gh-10343 块，但下标改成了 `'ij,ij->j'`。形状和期望值与本题相同，语义等价，但不是逐字相同。块后面紧接着还有上游 #10930 的 BLAS 广播测试。§2 第 9 行给出行号。
- **M2：我初判的 D 与 C-A 不等价。** C-A 得 1 已经回答了决策问题；但 D 独有的路径切换没有被执行覆盖，见 §3。
- **M3：`A:30`、`A:81` 说"正常输入不会触发新增分支"。** 这只对 C-A 成立。`A:80` 提到的"照上游 `broadcast_indices` 做法"的变体，在正常的 n=1 输入上会触发，不宜与 C-A 并列成同一个候选。
- **M4：I1 的范围要拆开。**
  - R3（与操作数顺序无关）和 R4（`optimize` 的其它取值）可以从公开材料推知，是范围内的覆盖缺口。
  - R5 和 R6 被公开读者判为"仍有多种合理解释"（`PR:22-23`）。它们应记成"范围未定"，加上 gold 部分修复（I2），不宜算作与 R3 同一条覆盖缺陷。
- **M5：几处证据层次要更新。** `SR` check 24、check 25、I1，以及 `card.md` §4 写的"静态推断，待实跑"，应改为引用本批执行证据。

**新发现的事实：加强 I2，但不改处置。** 后续题里上游写的 #10930 测试给了一个更简单的 gold 未修情形：`np.einsum('i, i', np.array([2., 3.]), np.array([4.]), optimize=True)`。见 §4 第 1 条。

**未解决的分歧**：与主审没有实质分歧。仍然开放的事项如下：
- 是否加交换顺序的断言，由用户或协调者决定；
- R5 算不算本题范围，由用户决定；
- D 和 C-D 都没有执行；
- actor 侧：真实首条消息、真实求解、候选的真实交付。

**最小后续实验**
- 如果采纳交换顺序断言的修订：在修订后的材料上同批跑 gold、noop、C-C、C-A，各 1 次，预期分别是 1、0、0、1。
- 如果不修订：静态结论不再需要新的 CPU 实验；下一步是 actor 验证，并捕获首条真实消息。
- 可选：把 D 单跑一次。

## 1. 本步读取范围

**本题产物（OUTPUT_DIR 下）**
- `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md` 全文。
- `screening_record.json`：全部字段。

**历史引用**
- `refs.json` 列出的全部 8 项：
  - 环境轮本题的 `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json`：只看了涉及本题的 `testbed_must_be_on_sys_path` 和 `no_pip_in_venv` 两族；
  - `decisions.md`：只 grep 了 E06、E09、E10、E11 和本题相关的行；
  - `results_20260924.md`；复现脚本；
  - `packages/p2/README.md`：只读了开头 40 行，含本题那一行。
- 旧记录引用的原始探针 `runs/r2e_env_repair_20260924/p2/dev_probe/numpy__5e83…/dev_probe.json`：只看了 `IMPORT_FROM_TMP*`、`REPRO_*`、`WHICH_pip*`、`WRITE_*`、`PUBLIC_RUN_TAIL` 这几个键。
- 没读：`followups.log`、`bare_pytest.log`、`pubtests` 日志、`reconcile.json`。所以 `OD` #15 中关于 `install.sh` 摘要的那条，我没有独立核对。

**协调者的新证据**
- `GR/ledger_np5_{gold,CC,CA}.jsonl`（各 1 行）。
- 三份 eval 日志（`GR/eval_logs/*_{1ba5a2f8,5a3c4a01,1e1eb3cd}.eval.log`）：只看了头部和 summary 行。
- `GR/numpy5e83_extra/{gold,CC,CA}.json`、`GR/stdout_np5_*.log`、`GR/b2_numpy5e83.sh`。
- `CANDS` 下的两个补丁和 `numpy_5e83_extra_commands.json`。核对结果：两个补丁的 sha256 分别是 `f1fb782a…` 和 `63198523…`，与账本的 `candidate.patch_sha256` 一致。

**同仓其它题的公开包**
- `LATER1`、`LATER2` 的 `numpy/core/tests/test_einsum.py`：grep 并读了 gh-10343 块和 #10930 块。
- 7 道 numpy 题 `setup.py` 中的版本行。

**本题工作树**
- grep 了 `numpy/{core/tests,lib/tests,tests}/__init__.py` 是否存在，以及生产代码中对 `einsum` 的引用。

**没读**
- 本批的 README、`assignments.json`、`actor_devcheck.md`、`grader_candidates.md`；
- 首批审查目录、Codex 复核目录；
- 其它题的私有包。

## 2. 主审决定性主张逐项核对

| # | 主审主张（出处） | 我的核对 | 判定 |
| --- | --- | --- | --- |
| 1 | 隐藏测试 = 公开测试文件加 8 行；15 个目标键检查的是同一个输入、同一对断言（`A:11`、`A:38-47`） | 我第一步做 diff 也得到同样结论：`HT` 与公开 `test_einsum.py` 只差 483–490 行 | 确认 |
| 2 | noop 两轮都是 20/35，gold 两轮都是 35/35，两轮日志归一化后逐字相同；M3 两次都是 35 passed（`A:12-16`） | 与我第一步一致。M3 是来源镜像上的独立 runner，主审在 `SR` check 22 中单独列出，没有与 RH2 的结果混用 | 确认；证据分层正确 |
| 3 | 覆盖面窄，C-C 和 C-D 静态上都能得 1（`A:17-18`，I1） | C-C 已执行：`GR/ledger_np5_CC.jsonl` 35/35；`CC.json` 的 order_swap 返回 rc 1，报 `einsumfunc.py:712` 的原句 | C-C 这部分已由执行确认；C-D 仍是静态推断 |
| 4 | 没有过严；更完整的修复也能得 1（`A:20`、`A:30`，`SR` check 24） | C-A 已执行：35/35；`CA.json` 中 tensordot_path 为 `True`，order_swap 输出 `[10. 10.]` | 确认（执行），但只限 C-A 这一实现，见 §3 |
| 5 | gold 是部分修复：`tensordot` 情形和三操作数情形仍报 `shape-mismatch for sum`（`A:115-118`，I2） | 两份证据：私有对照 pr3；`GR/numpy5e83_extra/gold.json` 中 tensordot_path 在 `einsumfunc.py:1124` 调 `tensordot`，于 `numeric.py:1289` 报错。两份都来自 root 身份的一次性容器，但这是纯计算，与运行身份无关 | 确认（执行） |
| 6 | gold 报错文案里两个尺寸颠倒，上游后续版本也保留了同样写法（`A:119`） | 私有对照 pr3 末行可证；`LATER1/numpy/core/einsumfunc.py:876-878` 的写法相同 | 确认 |
| 7 | gold 附带一处小放宽：同一操作数内 `'ii'` 配 (1,3) 时，直接调 `einsum_path` 不再报错（`A:120`，`SR` check 26） | 按 gold 逻辑推演成立：第一个 `i` 记为 1，第二个 `i` 把它改记为 3，不报错 | 静态同意，未执行 |
| 8 | 生产代码里没有别的 `einsum`/`einsum_path` 调用者（`A:31`） | grep 结果只有：`add_newdocs.py` 的文档、`core/__init__.py` 的导出、`numeric.py:1079` 的 docstring、`linalg/linalg.py:279` 的 See Also、`polynomial/polynomial.py:1214,1281` 的注释 | 确认 |
| 9 | 本题 gold 新增行和隐藏断言块逐字出现在 43e333e2、d89bc4bb 的公开工作树里（`A:143-147`，`SR` check 5，I4） | gold 新增行确实逐字出现（我第一步已 grep）。gh-10343 块（`LATER1/.../test_einsum.py:500-507`、`LATER2/...:486-493`）用的是 `'ij,ij->j'`，`p`、`q` 的形状和 `[10.]*2` 与本题相同。紧接着 `LATER1:508-522`、`LATER2:494-508` 是上游 #10930 的测试 | 修改措辞：gold 行逐字相同，断言块语义等价但不逐字；另补 #10930 这一事实 |
| 10 | 反向包含关系与各题版本（`A:144`、`A:148-151`） | 由 `setup.py` 核对版本：18b7cd9d 为 1.13，2f4a9650 为 1.14，d805e9b6 为 1.12，a5ea773e 为 1.10，d89bc4bb 为 1.16，43e333e2 为 `python_requires>=3.8`。行为抽查两处，与我第一步一致 | 确认。与主审一样，反向没有逐行核对 |
| 11 | 旧记录第 5 条："裸 pytest 会失败"的依据在本题不成立（`OD:16`） | `numpy/core/tests`、`numpy/lib/tests`、`numpy/tests` 下都有 `__init__.py`。按 pytest 的 prepend 导入模式，会把 `/testbed` 加进 `sys.path`（静态推断） | 同意"依据被推翻、结论未核实" |
| 12 | 旧记录第 4 条 / I6：放在 `/testbed` 外的脚本导入不了 numpy，提示里没写（`OD:15`） | `dev_probe.json` 中 `IMPORT_FROM_TMP_RC=1`（ModuleNotFoundError），`REPRO_OUTPUT` 首行是 `IMPORT_PLAIN=fail`；`public_hints` 只说 "run them from /testbed with `python -m pytest`" | 确认。证据来自环境轮探针（agent 身份，经 `docker exec`），不是正式链；主审已如实标注 |
| 13 | 旧记录第 17 条：环境轮的 reason 文字过时（`OD:28`） | 历史 `screening_record.json` 的 state 已是 `environment_qualified`，reason 仍写"只差 R13" | 确认 |
| 14 | check 31：只改断言函数拿不到分 | 目标键失败在 `HT:487` 调 `np.einsum` 时就抛出异常，发生在断言之前 | 同意 |
| 15 | 证据与环境分层（`SR` recipe_ref、`A:125`） | 主审把几类证据都分开写了：`b72f0fc4`（R-f 和 rerun2 的评分）、`d0b59d8b`（devcheck 和私有对照）、M3 来源镜像、root 身份的一次性容器 | 确认。建议在 recipe_ref 里补上本批在 `d0b59d8b` 上的三次评分 |

## 3. C-A 与我初判的 D 是否等价：不等价

| 维度 | C-A（已执行，`CANDS/numpy_5e83_CA_gold_plus_blas_guard.patch:26-29`） | D（我初判提出，未执行；即上游写法，见 `LATER1/numpy/core/einsumfunc.py:857-950`） |
| --- | --- | --- |
| 在哪里判断 | `einsum()` 的收缩循环里，执行时看实际数组形状 | `einsum_path` 里，规划时记录哪些标签尺寸为 1，并传给中间结果 |
| 什么时候关掉 BLAS | 被求和的标签在两侧的长度不同 | 被求和的标签在任一参与收缩的操作数中长度为 1，包括两侧都是 1 的情况 |
| 正常输入会不会触发 | 不会 | 会。helper 里 `do_opt=True` 的 i4/u4/f8/c8 四个键（`HT:506/510/526/533`）在 n=1 那一轮会触发。例如 `HT:317` 的 `"ij, j"`（a 为 (4,1)，b 为 (1,)），原本走 `tensordot`，会改走 `c_einsum` |
| 结果 | 广播情形的输出与 D 相同 | 数值与原来相同（数据是小整数，两条路径都精确），静态预测仍是 35/35 |

**结论**
- 在 gold 的尺寸校验之后，只要两侧长度不同，必然有一侧为 1。所以 C-A 会关 BLAS 的情形，D 一定也会关；反过来不成立。
- C-A 得 1，回答了"修好 `tensordot` 变体的更完整修复会不会被判 0"这个问题。
- D 额外切换到 `c_einsum` 的那些收缩，没有执行证据；风险低。但 D 就是上游的写法，模型可能凭记忆写出来，所以值得可选地单跑一次，成本约 20 s。

## 4. 反查主审可能没想到的范围

1. **gold 未修的最简单情形。**
   - 上游后续测试（`LATER2/.../test_einsum.py:494-499`）用的是 `np.einsum("i, i", x, y, optimize=True)`，其中 `x=[2., 3.]`，`y=[4.]`。
   - 按本题 base 推演：`_can_dot` 在 `EF:342` 处因为两侧输入相同返回 True，于是走 `tensordot`；gold 之后仍会报 `shape-mismatch for sum`。
   - base 默认 `optimize=True`（`EF:1062`），所以 gold 之后，不传 `optimize` 的一维点积 `np.einsum('i,i', x, y)` 同样会报错。
   - 证据级别：静态推断，与已执行的 `'ij,jk->ik'` 情形同一路径，未单独执行。
   - 这条加强了 I2 的用途注记，不改变评分结论。
   - 上游把这类情形单独立为 #10930，也支持主审的做法：不经用户决定，不把 R5 并入本题。
   - 同一段里还有一句 "all-ones array was bypassing bug (ticket #10930)"（`LATER2:501`），印证了 `PR:55` 和 `A:89` 的判断：全 1 输入的区分力弱。
2. **如果采纳交换顺序的断言。**
   - 把它放进现有 `check_einsum_sums` 的 gh-10343 块，键集合不变，期望映射也不用改。
   - 数据保持全 1 或整数值。原因：比较用的是精确相等的 `assert_array_equal`；如果换成非整数随机数，走 `tensordot` 和走 `c_einsum` 的正确修复可能因舍入顺序不同而被误拒。
   - 修订后需要重跑 gold、noop、C-C、C-A。gold 的交换顺序情形已在 `GR/numpy5e83_extra/gold.json` 实测输出 `[10. 10.]`。
3. **探针或训练分析时加诊断标签。**
   - 对 reward 为 1 的补丁，另跑 `CANDS/numpy_5e83_extra_commands.json` 里的两条命令，结果只作标签。
   - 这样可以区分"只修了原例"（C-C 类）和"没修 `tensordot` 变体"（gold 类）。
   - 按第二批补充规则 1，原始 reward 不改。
4. **base 的 docstring 自相矛盾。** 签名行写 `optimize=False`（`EF:823-824`），正文说默认是 True，代码默认值也是 True（`EF:869`、`EF:1062`）。公开读者已经指出（`PR:53`），主审没有提。这不影响评分，但可能让解题者误以为不传 `optimize` 的调用不受影响。
5. **R4 仍有残余松动。** 只特判 `optimize is True` 的实现也能拿分，加了交换顺序断言之后依然如此。题面字面写的就是 `optimize=True`，不建议为此再加断言，记下即可。
6. **报错全文 grep 不到。** 这句报错在源码里被拆成两行（`EF:710-711`），搜整句找不到，要搜 `Size of label`（`PR:47`）。我初稿说"可直接 grep 到"，措辞需要收窄；定位难度仍然很低。

## 5. 方法检查

- **是否先看答案、再把隐藏要求说成"显然"：没有发现。**
  - R3 是公开读者在接触私有材料之前独立列出的"可推知"要求（`PR:20`）。
  - 隐藏断言中的 `[10.]*2` 和"结果等于 `optimize=False`"，分别对应公开读者的 R1、R2（`PR:18-19`）。
  - C-A 的做法就是公开读者 §2 列的第 1 类合理实现（`PR:33`）。
  - 主审"题面不泄漏修法"的判断，与 `PR` §3.1 一致。
- **公开读者的疑义能否从公开材料消除。**
  - R5、R6 的范围疑义不能消除。但隐藏测试不检查这两项，C-A 实跑也得了 1，所以它们不影响合理解得分。
  - pytest 版本、pytest-env 插件、`.so` 是否存在这几项，已由 devcheck 和评分日志消除：pytest 7.4.4、env-1.0.1，numpy 从 `/testbed/numpy` 导入。
- **"可探针"是否与剩余条件分开：分开了。** 主审没有写 ready_for_probe；`SR` 的 check 3、16、33 都标为 unknown。同意。
- **修订是否扩大需求：没有。** 交换顺序断言属于 R3，可从公开材料推知，不扩大需求。主审不加 `tensordot`/多操作数断言、交用户定范围，我同意；#10930 被上游单列，也支持这一点。
- **是否把"环境已验"当成"质量合格"：没有。** 主审保留了环境轮的 `environment_qualified`，但限定为环境口径；本次静态审查的处置另外记录。同意。
- **是否只在核对旧结论：不是。** 主审在读历史之前已独立完成需求—测试映射（`A`）；读历史后逐条对照，并新增了 N1–N6（`OD:36-41`）。

## 6. 相对我初判的更正与更新

- **镜像缺项已关闭。** gold、C-C、C-A 在 `d0b59d8b` 上都是 35/35。noop 没有在这个镜像上跑，但 devcheck 的 pr1（agent 身份）已在该镜像上复现原错，不需要补跑。
- **候选预测。** C（即 C-C）预测得 1，已由执行确认。D 的思路由 C-A 部分确认；两者的差别见 §3。
- **跨题关系补充。** 两道后续题的公开初态里，除了 gold 新增行，还有本题隐藏断言的改名版本，以及 #10930 的测试。
- **措辞收窄。** "报错可直接 grep 到"改为"搜 `Size of label` 可定位"。
- **候选 E（出错时回退到 `c_einsum`）。** 没有跑，价值低，不再建议。

## 7. 建议主审记录做的最小改动（都不改结论）

1. `SR` check 25 和 I1：
   - 证据改为本批执行证据：C-C 正式评分 35/35（`GR/ledger_np5_CC.jsonl`）；私有容器 order_swap 报原错（`GR/numpy5e83_extra/CC.json`）。
   - "R3–R6 缺覆盖"改为"R3、R4 缺覆盖；R5、R6 范围未定（见 I2）"。
2. `SR` check 24：补上 C-A 的 35/35（`GR/ledger_np5_CA.jsonl`），以及 tensordot_path 输出 `True`。
3. `SR` check 5、I4，以及 `card.md` 的题目关系行：写明 gold 新增行逐字相同；隐藏断言块下标改名、语义等价；另有 #10930 的测试。
4. `SR` 的 recipe_ref 或引用处：补上 `d0b59d8b` 上 gold、C-C、C-A 三次评分。
5. `A` §4 的 C-A 条目：把"照上游 `broadcast_indices` 做法"写成独立候选 D，并注明它在正常的 n=1 输入上也会触发。
6. `disposition.reason`：补一句"测试偏松已由 C-C 实跑证实；原始 reward 保留，建议给通过的补丁附诊断标签（§4 第 3 条）"。
