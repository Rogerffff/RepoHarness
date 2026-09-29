# numpy d805e9b6 题卡（R2E 单题闭环，按统一标准 v1）

2026-09-29，私有主审。依据文件：`analysis_before_history.md`（读历史前的初判）、`old_findings_delta.md`、`screening_record.json`；运行证据见附录 B。

## 1. 题目、版本与结论

- **题目**：numpy `d805e9b6`，base 为 `25e3ebf4`。要求一维的大掩码数组在 str / repr 里像普通数组一样摘要显示，例如 `[0 -- -- ..., 1997 1998 1999]`，被省略的值用省略号标出。修复只涉及 `numpy/ma/core.py`。
- **版本**：
  - 材料为 `expected_v0`，没有修订（v3–v5 对本题逐字相同）。
  - 新派生镜像 `c080fc6b…`（配方 `r2e_derive_v1+sysconfig_v1`）上：noop 0、gold 1。
- **处置**：`needs_repair`（scope 为 `static_review`）。**R-c 必须做**：S1 已由正式评分确认。
- **v1 四项用途**：

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 新镜像上 noop 0 / gold 1；devcheck 13 项检查全部为真 |
| 能力比较 | conditional | R-c 落地之前，凡是得 1 的补丁，都要跑预先登记的两条事后审计：n=500 应全量显示，n=100000 应摘要为 `[0 1 2 ..., 99997 -- --]`（脚本 `runs/r2e_lifecycle_20260929/inv/numpy_d805/private_check_6_3.py`）。原始 reward 与语义结果分开记录。另有一项池级条件：模型实际收到的消息与 adapter 链路尚未验证 |
| 训练候选 | no | 还差三步：R-c 实施并按 §4 验收、Codex 复核、独立复核。三步都完成后可以改为 yes（S2、X1、P4 都已登记） |
| 留出评测 | no | 目前有未修的 S1；修订后也只能作为标明版本的自建题，并且要按仓库整组留出（见 X1） |

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖情况 | 执行证据 |
| --- | --- | --- | --- | --- |
| 示例的 repr 逐字等于 Expected | 题面第 11–25 行 | `test_str_repr`（`test_1.py:454-461`） | 覆盖，但只有这一个例子 | noop 失败、gold 通过，共 3 次 |
| C1：其它大的一维数组也要摘要 | 标题；Expected 的一般表述 | 无 | **缺失（T2c）** | K-DF 得 1.0，但 n=100000 时只显示 100 个值，没有省略号 |
| C2：有省略就必须有省略号；元素数不超过阈值时全量显示 | Expected 第 20 行；`set_printoptions` 对 threshold 的文档；`core.py:3797-3798` 截角注释；1.11 发布说明 | 无 | **缺失** | K-DE 得 1.0，但 n=500 时每个值显示两次；K-DC 得 1.0，但 n=500 时丢了 400 个值 |
| 模板、mask 行，以及小数组 / 结构化 / mvoid 的打印保持不变 | 公开旧测试 | 同一个键的前半段，以及 8 个打印类回归键 | 覆盖 | 228 个回归键 3 次运行结果一致 |

## 3. 问题与证据

| 编号 | 严重度 | 内容 | 证据层次 | 去向 |
| --- | --- | --- | --- | --- |
| T2c | S1 | 唯一的核心断言就是题面示例的字面值 | 静态（确定） | R-c 第 1 处 |
| T2b | S1 | 退化候选 K-DE（把截取量写死为 750）得 1.0 | 当前 CPU：正式评分加私有核对 | R-c 第 2 处 |
| 第 4 步 | S1 | 部分修复 K-DC、K-DF 都得 1.0，并在其它实例上违例 | 当前 CPU | 同一轮 R-c |
| G1 → T3 | S2 | gold 在 threshold 大于 1500 时仍会静默丢值；多维没有改（题外） | 静态加仿真 | 登记、抽查 |
| T3 | S2 | 子类打印不在评分范围内 | 静态 | 登记 |
| P4 | — | 题面 Actual 块与 base 的实际输出不符 | devcheck 的复现输出 | 登记；可选 R-f |
| X1 | — | 同仓另外 5 题的初态里含本题答案；本题初态里含 a5ea773e 的答案 | 扫描加 grep 核对 | 登记 |
| E3（通用） | — | 隐藏测试依赖候选可以修改的 `numpy/ma/testutils.py` | 静态 | 交 A 线；事后审计时标记改动它的补丁 |

**环境**：新镜像上的环境条件都已满足，不构成阻塞。已登记的解题侧条件：`/testbed` 要在 sys.path 上、没有 pip、断网。

## 4. 修订（R-c，必须做）与验收

- **改动**：只改隐藏测试 `r2e_tests/test_1.py` 里的 `TestMaskedArray.test_str_repr`，在示例断言之后追加两处（diff 见附录 A）。`expected_output.json` 不变，仍是 229 个键，键集严格相等。
  1. **第 1 处**：n=100000，末尾两个值被掩，断言 `str(a) == '[0 1 2 ..., 99997 -- --]'`。
  2. **第 2 处**：n=500，`a[1:50]` 被掩，断言输出里没有 `...`，而且 token 恰好依次是 `0`、49 个 `--`、`50` 到 `499`。
- **验收**：在修订版上各跑 1 次正式评分，预期如下。

| 候选 | 预期结果 | 若为 0，应失败在哪里 |
| --- | --- | --- |
| gold | 1 | — |
| K-A5b | 1 | — |
| noop | 0 | 示例断言 |
| K-DE | 0 | 第 2 处的 token 断言（修订后文件第 477 行） |
| K-DC | 0 | 第 2 处的 token 断言（第 477 行） |
| K-DF | 0 | 第 1 处（第 468 行） |

  私有核对已经在同一镜像上给出了逐项一致的结果（附录 B），这次正式评分用于确认。验收之后交 Codex 复核，并保存新版本、父版本（当前 v3–v5）、修订理由，以及触发反例 K-DE、K-DC、K-DF。
- **修订后仍受保护的要求**：示例的 repr、C1、C2、模板与小数组打印。
- **不做**：自定义 printoptions 和多维数组的断言。题面没有这样要求，gold 也通不过。

## 5. 八方面：已查与未查

- **已查**：公开需求、材料与初始问题、测试映射、误拒、回归与 gold、开发条件、交付边界、题目关系（细节见分析稿 §10）。
- **未查**：
  - 模型实际收到的消息；
  - 约 220 个非打印类回归键，只看了名称；
  - install.sh 没有读（历史记录称它不含修复）。

## 6. 复核、分歧与唯一下一步

- **需要复核的分歧**：独立复核尚未进行。请复核者重点判断 R-c 第 2 处采用的读法。
  - 本审的读法："元素数不超过阈值时全量显示"，这有公开依据。
  - 另一种读法（K-DG）："只要被截过就一律摘要"，唯一的依据是私有常数 100。
  - 如果复核认定两种读法都有依据，第 2 处改为待用户决定的 P5，第 1 处照做。
- **审查过程更正**：主审原稿中的 K-A5 得 0，原因是补丁自身有错（在 `numpy/ma/core.py` 里 `max` 指的是 `numpy.ma.max`），不是误拒。正对照改用 K-A5b：协调者只改了这一行，主审核对 diff 后认可。
- **唯一下一步**：按 §4 实施 R-c，并跑验收矩阵。

## 7. 探针就绪差距

按协调者的限制，本审没有读本批 README §3。下表按 v1 §2 与环境卡 §2 列出，协调者可再对照 §3。

| 条件 | 状态 | 由谁补 |
| --- | --- | --- |
| 新镜像上的 actor devcheck（真实 CC、agent 身份、正式 profile、断网） | 已满足，13 项全真 | — |
| 新镜像上的正式 noop 0 / gold 1 | 已满足 | — |
| 公开开发路径可用（复现、公开测试、耗时） | 已满足：复现在 base 上 rc 为 1、应用 gold 后为 0；公开测试 229 passed，1.7 s | — |
| 交付路径正确（projection 只含 `numpy/ma/core.py`） | 已满足：gold 与 5 个候选都验证过 | — |
| 测试能区分核心行为（没有未处理的 S1） | **未满足** | 协调者实施 R-c 并验收；Codex 复核 |
| 独立复核 | **未做** | 协调者派发 reviewer |
| 如果在 R-c 之前先进探针：对得 1 的补丁做事后审计 | **待登记** | 协调者，用 `private_check_6_3.py` 的两条核对 |
| 模型实际收到的消息 / Qwen adapter 链路 | 未验证（池级问题） | A 线 |
| P4 题面修订 | 可选，不阻塞 | 协调者，等 R-f 机制实现后 |

## 附录 A：R-c diff（隐藏测试）

已在 v3 隐藏测试的副本上做过 `git apply --check`，应用后能通过 AST 解析，测试函数仍是 229 个。diff 的 sha256 是 `1092cedb…`；应用后文件的 sha256 是 `ea62cd09…`。

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -459,6 +459,23 @@ class TestMaskedArray(TestCase):
             '             mask = [False  True  True ..., False False False],\n'
             '       fill_value = 999999)\n'
         )
+
+        # A large 1d array other than the issue example is summarized too:
+        # the data shows the leading/trailing items with an ellipsis, and
+        # masked values at the end are shown as `--`.
+        a = np.ma.arange(100000)
+        a[-2:] = np.ma.masked
+        assert_equal(str(a), '[0 1 2 ..., 99997 -- --]')
+
+        # Below the default summarization threshold (1000 items) a 1d masked
+        # array is printed in full: no ellipsis, and no value is dropped or
+        # repeated.
+        a = np.ma.arange(500)
+        a[1:50] = np.ma.masked
+        s = str(a)
+        assert_('...' not in s)
+        assert_equal(s.replace('[', ' ').replace(']', ' ').split(),
+                     ['0'] + ['--'] * 49 + [str(i) for i in range(50, 500)])
 
     def test_pickling(self):
         # Tests pickling
```

## 附录 B：运行证据

私有核对的列含义：
- n500 一列：显示的 token 数，以及 token 是否恰为预期序列。
- n1e5 一列：输出是否恰为 `'[0 1 2 ..., 99997 -- --]'`。

| 候选 | 正式评分（当前材料） | 私有核对 n500 / n1e5 | 引用 |
| --- | --- | --- | --- |
| noop | 0.0（228/229） | 100 个，不符 / 不符 | `runs/r2e_lifecycle_20260929/env_verify/ledger_l0_noop.jsonl:6`；`pcheck_none.json` |
| gold | 1.0（229/229） | 500 个，相符 / 相符 | `ledger_l0_gold.jsonl:6`；`pcheck_gold.json` |
| K-DE（退化候选） | 1.0（229/229） | **1000 个**，不符 / 相符 | `runs/r2e_lifecycle_20260929/inv/numpy_d805/ledger_KDE.jsonl:1`；`pcheck_KDE.json` |
| K-DC | 1.0（229/229） | **100 个**，不符 / 相符 | `ledger_KDC.jsonl:1`；`pcheck_KDC.json` |
| K-DF | 1.0（229/229） | 500 个，相符 / **不符（只有 100 个值）** | `ledger_KDF.jsonl:1`；`pcheck_KDF.json` |
| K-A5（主审原稿） | 0.0（228/229）：ValueError，补丁自身错误 | n500 相符，之后抛错 | `ledger_KA5.jsonl:1`；`pcheck_KA5.json` |
| K-A5b（正对照，协调者修正、主审认可） | 1.0（229/229） | 500 个，相符 / 相符 | `ledger_KA5b.jsonl:1`；`pcheck_KA5b.json` |

- 以上候选补丁的原文在 `cands/`，都由 agent/54321 以 `git_apply` 应用，projection 只含 `numpy/ma/core.py`。
- **devcheck**：`runs/r2e_lifecycle_20260929/devcheck/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/orig/attempt.json`。13 项检查全部为真；Claude Code 版本 2.1.205；8 条命令共 18.6 s。
- **gold 私有对照**：`private_control.json`。其中 diag_sizes 为 True/7、False/500、False/500、False/1000、True/43，与分析稿的预测一致。
