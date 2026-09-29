# orange3__50f6a758 题卡（R2E，统一标准 v1）

R2E 私有主审，2026-09-29。路径缩写同 `old_findings_delta.md`：`LC/` = `runs/r2e_lifecycle_20260929/`，`INV/` = `LC/inv/orange3_50f6/`，`DC/` = `LC/devcheck_rev/unrev/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e/`，`PRIV/`、`PUB/` 为本题私有包与公开包。

**结论**：处置为 `needs_repair`（scope 为 static_review）。**修订 R-b + R-c 必做**；做完并验收之前，本题只能用于问题定位。

- **T1（误拒合理解）**：唯一目标键逐字要求一种名单格式——超过 5 个名字时只列前 4 个，再写 "and N other"。满足全部公开要求的 K1（把名字全部列出）实跑得 0。
- **S1（T2b）**：退化候选 K2（加载了数据就不警告）实跑 48/48、得 1；K3（文件里有定义匹配上就不警告）、K4（不检查 numeric 段）也都得 1。
- **链路条件**：在本机做正式评分，须把控制面保护时限放宽到 1200 s。缺省的 300 s 下，noop 和 gold 都是 `failed_to_grade`。

## 1. 题目与版本

- **目标**：`OWColor._parse_var_defs` 读取配色定义文件时，文件里有、数据里没有的变量要给出警告（`owcolor.py:661-719`）。base 在 `:700-703` 静默跳过；gold 收集这些名字，拼成一条消息，插到 "Invalid definitions" 警告的最前面。
- **材料**：expected_v0，无修订（v3–v11 对本题相同）。48 个键全部期望 PASSED。唯一目标键是 `TestOWColor.test_load_ignore_warning`；其余 47 个键中，46 个与公开测试逐字相同。
- **当前环境**：新机派生镜像，配方 `r2e_derive_v1+sysconfig_v1`（`sha256:f5573c5a…`）。在 1200 s 时限下，noop 得 0（只差目标键）、gold 得 1（`LC/budget_v5/ledger_{noop,gold}.jsonl:8`）。

## 2. 关键映射与实跑

| 需求 / 旧行为 | 公开依据 | 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| 未用变量要警告（示例形态：无数据、只在 categorical 段） | 题面 `user_prompt.txt:6-7, 21-22` | `test_1.py:796-820` | 覆盖 | noop 0 / gold 1 |
| 警告要点名是哪些变量 | `:22` | 同上，逐字子串匹配（含截断规则） | **冲突（过严）** | K1 得 0，失败在 n=6 那一轮、`:820` |
| 加载了数据 / 混合文件 / numeric 段也要警告 | 题面的一般表述 | 无 | **缺失** | K2、K3、K4 都得 1 |
| 匹配上的定义照常生效 | base `owcolor.py:698-712` | 只在全部匹配的文件上测过 | 部分 | C-deg 结果待回 |
| 公开旧断言："var not" 不警告 | `test_owcolor.py:885-888` | 隐藏版已删 | P6 | gold 下在 `:888` 失败（`DC/private_control.json`） |

候选实跑结果：正式评分用本机 1200 s 时限；私有探针见 `INV/pcheck_probe_*.json`。探针四例是：
- a：加载 iris 后读题面示例；
- b：加载 iris 后读混合文件；
- c：不加载数据，只在 numeric 段写一个未用变量；
- d：全部定义都匹配（不应警告）。

| 候选 | 正式评分 | 探针 a / b / c / d |
| --- | --- | --- |
| noop | 0 | 挂 / 挂 / 挂 / 过 |
| gold | 1 | 过 / 过 / 过 / 过 |
| K1（名字全列，不截断） | **0** | 过 / 过 / 过 / 过 |
| K2（有数据就不警告，退化候选） | **1** | 挂 / 挂 / 过 / 过 |
| K3（混合文件不警告） | **1** | 过 / 挂 / 过 / 过 |
| K4（只查 categorical 段） | **1** | 过 / 挂 / 挂 / 过 |
| C-deg（复核提出：弹框后直接 `return`） | 待回（预计 1） | 待回（预计只挂 b） |

## 3. 八方面：已查与未查

- **已查**：
  - 公开需求：题面、提示、brief、公开读者稿。
  - 材料：公开与隐藏测试逐行 diff，gold 能应用，各处哈希一致。
  - 测试：目标键逐行追读；47 个回归键按类读过。
  - 误拒：K1 已实跑。
  - 回归与 gold：`_parse_var_defs` 唯一的调用者是 `load()`；gold 没有实质问题。
  - 开发条件：devcheck 用真实 CC + 桩、agent 身份、正式启动路径，检查项全部为真。
  - 交付：只改一个文件，投影正确。
  - 题目关系：跨题扫描结果已用 grep 核实。
- **未查**：
  - 模型实际收到的题面渲染：devcheck 发给模型的用户消息是 devcheck 指令，不是题面。
  - 不带 Qt 前缀跑测试会怎样。
  - 真实模型求解（清单 33–36 项）。
  - 通用控制面：引用 A 线结论。

## 4. 问题

| 编号 | 问题 | 严重度 / 去向 | 证据层次 |
| --- | --- | --- | --- |
| T1 | 名单格式没有公开依据：逗号、"and"、引号，以及超过 5 个名字时只列 4 个 | 误拒 → R-b | 当前 CPU：K1 正式评分为 0 |
| T2 | 第 3 步退化候选 K2 得 1（T2b）；第 4 步 K3、K4 得 1；第 2 步：全部实例都与示例的输入形态相同（T2c） | S1 → R-c | 当前 CPU：正式评分 + 私有探针 |
| T3 | 两处没有断言：一是未用变量的 rename 不参与重名检查（R7），二是"先校验、后弹警告"的顺序 | S2，登记 | 源码推断 |
| P4 | 题面说的 TypeError 是测试自身的伪影，应用本身不报这个错 | 登记；R-f 可选 | noop 日志 `:54-57`；devcheck 复现结果 |
| P6 | 公开旧断言与正确修复冲突 | 登记；探针分析按 P6 解读 | devcheck 下的私有 gold 对照 |
| X1 | 本题 gold 与目标测试出现在 `c3fb72ba`、`f5026689` 两题的公开初态里 | 登记；控制重复采样 | 跨题扫描 + grep |
| E3（链路） | 缺省 300 s 时限下，noop / gold 都 `failed_to_grade` | 本机放宽到 1200 s；根因交 A 线 | `LC/env_verify/ledger_l1_*:7` |

gold（G1）：没有实质问题。只有未用变量时对话框标题仍是 "Invalid definitions" 这类小瑕疵，不影响判断。

## 5. v1 四项用途

- `problem_localization`：**yes**。
- `capability_comparison`：**conditional**。缺 R-b + R-c 的验收：按现有材料，合理解 K1 得 0、退化解 K2 得 1，分数不能反映能力。另外，本机评分须放宽到 1200 s。
- `training_candidate`：**conditional**。除上一条外，还缺 Codex 复核；S2（T3）与 X1 已登记。
- `heldout_candidate`：**conditional**。修订后只能作"标明版本的自建评测"；按仓库划分时，要与 `c3fb72ba`、`f5026689` 放在同一侧；本审查已接触过 gold 和隐藏测试。

## 6. 修订（必做，一轮完成）与验收

- **R-b（针对 T1）**：放宽 `test_load_ignore_warning` 中关于名单的断言。
  - 保留"空文件不警告"，保留通过 `QMessageBox.warning` 第 3 个位置参数取警告正文的方式。
  - n≤2 时，每个名字都必须出现在警告里。
  - n≥3 时，至少点名一个，并写出没列出的名字有几个。
  - 删掉关于逗号、"and"、截断的逐字子串。
  - 公开依据：题面 `:22`。
- **R-c（针对 T2）**：在同一个测试里追加一段。
  - 输入：加载 iris，再读混合文件——`iris` 改名为 species，categorical 段有未用的 foo，numeric 段有未用的 bar。
  - 断言：警告点到 foo 和 bar；输出的 class_var 已改名。
  - 这组输入在私有探针 b 上实跑过：gold、K1 通过，K2、K3、K4 失败。
- **材料改动**：键集合不变（仍是 48 键，`expected_output.json` 不改）。按既有材料修订机制实施，即把隐藏测试里唯一一处旧片段替换为新片段，全文见附录 A。
- **验收矩阵**（本机 1200 s）：gold 1、K1 1、noop 0、K2 0、K3 0、K4 0、C-deg 0。可再加一个"不点名"的错误候选 K5，应为 0。最后交 Codex 复核。
- **已做的本地核对**：只对消息字符串做了纯字符串模拟，没有运行项目代码。结果：放宽后的 R-b 断言接受 gold、K1、带牛津逗号的全列表、排序后截断这几种写法，拒绝不点名的写法；原断言除 gold 外全部拒绝。

## 7. 复核

独立复核的初判与本稿一致（T1、S1、P4）。复核另外提出了 C-deg，已纳入验收用的错误候选；它的正式评分与探针结果还没回来。

## 8. 剩余事项

1. **链路条件**：本机正式评分须把控制面保护时限放宽到 1200 s（只放宽时限，评分语义不变）。根因是 orange3 的 `/testbed` 约 2 GB，chown 触发 overlay copy-up（`setup_cost` 族，交 A 线）。新机实测可信 setup 用时 279–497 s。
2. C-deg 的正式评分与探针结果待回。
3. R-f（针对 P4）可选：把 "Actual Behavior" 改成在 base 上核实过的症状——不弹警告，未用变量的定义被静默忽略。代价是题面对 `QMessageBox` 这一通道的间接提示会减弱。
4. 登记项：T3、P6、X1。
5. 未核实项：题面的实际渲染；不带 Qt 前缀时的现象。

## 9. 探针就绪差距

按派发规则我没有读本批 README §3，下表按 v1 §2 与定义文档中 `ready_for_probe` 的条件整理。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 公开开发路径（agent 身份、正式启动链） | 已满足（devcheck 全部为真，v9 任务面） | — |
| 当前材料下 noop 0 / gold 1，且原因可解释 | 已满足（1200 s） | — |
| 评分依据可信：不误拒合理解，退化解不得分 | **未满足**（T1、S1） | 协调者实施 R-b + R-c，Codex 复核 |
| 修订后材料的正负对照 | **未满足** | 协调者按 §6 的矩阵实跑 |
| 本机运行条件 | 已知，需配置为 1200 s | 协调者在探针批次里配置；根因交 A 线 |
| 独立复核收口 | 进行中（C-deg 待回） | 复核者、协调者 |
| 题面实际渲染 | 未核，不阻断 | 探针首跑时顺带核对 |

**唯一优先的下一步**：按附录 A 实施 R-b + R-c，然后在本机（1200 s）跑 §6 的验收矩阵。

## 附录 A：修订草案（`PRIV/hidden_tests/test_1.py`，评分时的路径是 `r2e_tests/test_1.py`）

- 修订后文件的 sha256：`f21ca9b349c35b32081de19718017517a425ff8fb9a8581d3460ce9008f1ae21`。
- 在本地临时目录生成；整份文件能通过 Python 语法解析，但没有运行。
- 旧片段是 `test_1.py:796-820`（整个 `test_load_ignore_warning` 函数），在文件中唯一出现。

```diff
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -797,28 +797,45 @@
     def test_load_ignore_warning(self, msg_box):
         self.widget._parse_var_defs(dict(categorical={}, numeric={}))
         msg_box.assert_not_called()
+
+        def shown_text():
+            msg_box.assert_called()
+            return "\n".join(call[0][2] for call in msg_box.call_args_list)
 
         no_change = dict(renamed_values={}, colors={})
-        for names, message in (
-                (("foo",),
-                 "'foo'"),
-                (("foo", "bar"),
-                 "'foo' and 'bar'"),
-                (("foo", "bar", "baz"),
-                 "'foo', 'bar' and 'baz'"),
-                (("foo", "bar", "baz", "qux"),
-                 "'foo', 'bar', 'baz' and 'qux'"),
-                (("foo", "bar", "baz", "qux", "quux"),
-                 "'foo', 'bar', 'baz', 'qux' and 'quux'"),
-                (("foo", "bar", "baz", "qux", "quux", "corge"),
-                 "'foo', 'bar', 'baz', 'qux' and 2 other"),
-                (("foo", "bar", "baz", "qux", "quux", "corge", "grault"),
-                 "'foo', 'bar', 'baz', 'qux' and 3 other")):
+        all_names = ("foo", "bar", "baz", "qux", "quux", "corge", "grault")
+        for n in range(1, len(all_names) + 1):
+            names = all_names[:n]
+            msg_box.reset_mock()
             self.widget._parse_var_defs(dict(
                 categorical=dict.fromkeys(names, no_change),
                 numeric={}))
-            self.assertIn(message, msg_box.call_args[0][2])
+            text = shown_text()
+            missing = [name for name in names if name not in text]
+            if n <= 2:
+                # as in the issue's example: every unused variable is named
+                self.assertEqual(missing, [], text)
+            else:
+                # a long list may be shortened, but it must name some of the
+                # variables and say how many it left out
+                self.assertLess(len(missing), n, text)
+                if missing:
+                    self.assertIn(str(len(missing)), text)
 
+        # with data: a file that mixes used and unused definitions in both
+        # sections reports the unused ones and still applies the used ones
+        self.send_signal(self.widget.Inputs.data, self.iris)
+        msg_box.reset_mock()
+        self.widget._parse_var_defs(
+            {"categorical": {"iris": {"rename": "species"},
+                             "foo": {"renamed_values": {}}},
+             "numeric": {"bar": {"colors": "linear_viridis"}}})
+        text = shown_text()
+        self.assertIn("foo", text)
+        self.assertIn("bar", text)
+        out = self.get_output(self.widget.Outputs.data)
+        self.assertEqual(out.domain.class_var.name, "species")
+
     def _create_descs(self):
         disc_vars = [DiscreteVariable(f"var{c}", values=("a", "b", "c"))
                      for c in "AB"]
```

每个候选修订后应在哪条断言上失败：
- noop：n=1 那一轮的 `assert_called`；
- K2、K3：有数据那一段的 `assert_called`；
- K4：`assertIn("bar", text)`；
- C-deg：class_var 改名那条断言；
- K5（不点名）：n=1 那一轮的 `missing == []`。

gold 与 K1 应全部通过。验收时逐个核对失败行，确认各候选挂在预期的位置。

## 附录 B：证据索引

- **正式评分**：
  - `LC/env_verify/ledger_l1_{noop,gold}.jsonl:7`（300 s，超时）；
  - `LC/budget_v5/ledger_{noop,gold}.jsonl:8`（1200 s）；
  - `INV/ledger_K{1,2,3,4}_budget1200.jsonl`；
  - 日志 `INV/logs_K1/evallog_replay-r2e-inv-50f6-K1-0_9e2e4112.eval.log:55-58, 115-120`；K2、K3、K4 日志的 `:63`（目标键 PASSED）与 `:82`（48 passed）。
- **私有探针**：`INV/pcheck_probe_{none,gold,K1,K2,K3,K4}.json`，脚本 `INV/pcheck_probe.sh`。
- **devcheck**：`DC/devcheck.log`；`DC/orig/captures/{env,env_import,repro_unused_vars_warning,public_owcolor_tests_except_conflict,public_no_rename_conflict}.out`；`DC/private_control.json`。
- **候选补丁**：`OUT/cands/orange3_50f6_{K1,K2,K3,K4,Cdeg}.patch`。
- **旧环境审查及其核对**：见 `old_findings_delta.md`。
- **前稿**：`analysis_before_history.md`（读历史前封存，未改）。
