# numpy__d89bc4bb 题卡（R2E 单题闭环，统一标准 v1）

**结论：正式评分已确认 2 个 S1 和 1 个 T1。R-c1、R-c2 必做，R-b 同轮做；修订版通过验收并经 Codex 复核之前，本题不进训练。环境侧没有问题，不需要环境修复（R-d）。**

- **版本**：base `a56c4e62`（numpy 1.16.0 开发版）；材料 expected_v0（v3–v7 对本题相同，无材料修订）；当前评分镜像 `sha256:ea786809c49d…`（配方 `r2e_derive_v1+sysconfig_v1`，09-28 在新机器上重建）。
- **暴露范围**：审查者看过 gold、隐藏测试与历史记录，本卡只作开发诊断（`development_diagnostic`）。
- **路径缩写**：`INV` = `runs/r2e_lifecycle_20260929/inv/numpy_d89b`，`DC` = `runs/r2e_lifecycle_20260929/devcheck/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`。

## 1. 题目与用途

**题目**：让 `np.histogram2d` 和 `np.histogramdd` 接受 `density=True`，返回"区间内积分为 1"的概率密度。gold 把 `density` 做成 `normed` 的别名。

**运行证据**：
- 新镜像上 noop 为 0（72/78）、gold 为 1（78/78）。
- devcheck 在正式启动链、agent 身份下全部检查为真：公开测试 6 passed 和 15 passed，两条复现命令都报出题面所述的 `TypeError`。

| v1 用途 | 结论 | 还差什么 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | conditional | 原版可以用，但必须预登记事后审计：<br>① 得 1 的补丁，查是否删掉了 `normed`，归一化是否排除了区间外样本；<br>② 只错 `TestHistogramdd.test_density_non_uniform_1d` 的补丁，查是否只差末位浮点（allclose 成立）。<br>修订版验收后为 yes |
| 训练候选 | conditional（原版为 no） | 原版有 2 个未处理的 S1。R-c1＋R-c2＋R-b 修订版按 §6 验收、经 Codex 复核后才是候选；与 43e333e2 同进训练时要控制重复采样 |
| 留出评测 | conditional | 条件同训练候选；按仓库划分时与 43e333e2 同侧；修订版只能作"标明版本的自建评测"；上游 numpy 1.16 已公开此改动，不能排除预训练见过 |

## 2. 关键需求与测试的对应

| 需求或旧行为 | 公开依据 | 测试与决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| 两个函数都接受 `density`，返回密度（含非等宽格） | 题面；base 中 `normed` 的文档 | 6 个目标键：2D 的 `test_asym`、`test_density`；ND 的 `test_simple`、`test_weights`、`non_uniform_2d/1d` | 覆盖 | noop 下 6 键都是 `TypeError`；gold 三轮全过 |
| 区间外样本不计入，区间内积分为 1 | 题面 Expected Behavior；`twodim_base.py:558-562,590-592` | 没有：所有密度用例都没有区间外样本 | 缺失 → S1（T2b） | `DEG` 78/78 得 1；私有对照积分为 0.75 |
| `normed=True` 仍然可用 | base 两处文档；6 个公开测试 | 没有：隐藏测试把 2D/ND 的 `normed` 全部换成了 `density` | 缺失 → S1（§4 第 4 步） | `REN` 78/78 得 1；私有对照报 `TypeError` |
| ND 结果与一维 `density` 一致 | 公开旧测试（针对 `normed`） | `non_uniform_1d` 用 `assert_equal` 逐位比较 | 过严 → T1 | `ORD` 77/78 判 0，只差一个 0.1 的末位 |
| `density=False`、2D 带权、位置参数兼容 | 一维先例；文档 | 没有，或只间接覆盖 | 缺口 → T3（S2 登记） | — |

## 3. 八方面

八方面都已查，明细见 `analysis_before_history.md` §1。以下未查：
- 模型实际收到的完整消息（devcheck 用的是脚本化提示）；
- 真实模型求解；
- 本题的裸 `pytest`，以及整文件跑公开测试（09-28 没有跑，引用 09-24 历史实测）；
- `install.sh` 的内容；
- 其它 4 题的私有 gold（X1 只按扫描登记）；
- 共用控制面（属 A 线）。

## 4. 问题与证据（均为当前 CPU 实跑）

1. **S1，T2b（退化探测命中）**：
   - `DEG` 在 gold 的修改位置改用"含离群格的整张直方图"作分母。
   - 正式评分 78/78，得 1（`INV/ledger_DEG.jsonl:1`）：补丁已应用，78 键都执行了，日志完整。
   - 它违反题面"integral over the range is 1"：私有对照积分为 0.75，gold 为 1.0（`INV/pcheck_DEG_*.json`）。
2. **S1，§4 第 4 步**：
   - `REN` 把 `normed` 直接改名为 `density`，得 1（`INV/ledger_REN.jsonl:1`）。
   - 改名后 `normed=True` 抛 `TypeError`（`INV/pcheck_REN_REN.json`），破坏了文档写明、公开测试也在用的接口。
3. **T1，误拒合理解**：
   - `ORD` 满足全部公开要求，只是把除法顺序换成"先除总数，再除格宽"，却判 0。
   - 唯一不符键是 `TestHistogramdd.test_density_non_uniform_1d`：断言在 `test_2.py:744`，报 "mismatch 25.0%"，两个数组打印出来都是 0.1（`INV/logs_ORD/…eval.log:38-54,134-135`）。
   - 私有对照：`[0.1, 0.1, 0.09999999999999999, 0.1]` 对 `[0.1]*4`，allclose 成立。
4. **T3，登记为 S2**：`density=False`、2D 带权、位置参数兼容都没有隐藏断言。
5. **X1，跨题关系**：
   - 43e333e2 的初始工作树逐字包含本题 gold 的全部 25 行，以及本题的新测试名。
   - 本题初始工作树包含 18b7cd9d、2f4a9650、5e8301c2、d805e9b6 的修复（来自扫描）。
6. **解题侧条件**（历史已记，本轮 devcheck 复核）：
   - `/testbed` 须在 `sys.path` 上，测试要用 `python -m pytest`，环境里没有 pip。
   - 整文件跑 `test_histograms.py` 会出现 21 个与本题无关的 nose-setup ERROR。

另外，`DEP`（沿一维先例把 `normed` 标为弃用）78/78 得 1。这说明评分对"是否弃用 `normed`"保持中立，不存在 P5 类冲突。

## 5. 建议与下一步

- **处置**：scope 为 `static_review`，state 为 `needs_repair`。这里要修的是测试，不是环境。
- **独立复核**：尚未进行。
- **唯一优先下一步**：协调者实施 R-c1＋R-c2＋R-b，按 §6 的矩阵跑 6 次正式评分（gold、noop、`DEG`、`REN`、`ORD`、`DEP`），然后交 Codex 复核。

## 6. 修订建议（v1 §5，已预授权；可执行 diff 见附录）

| 模板 | 公开依据 | 改动 | 对应的触发候选 |
| --- | --- | --- | --- |
| R-c1 | 题面 Expected Behavior；`twodim_base.py:558-562,590-592`；`histograms.py:585-586,607-613` | `test_1.py` 的 `TestHistogram2d` 和 `test_2.py` 的 `TestHistogramdd` 各加一个 `test_density_outliers`：输入含区间外样本；ND 版同时覆盖带权与不带权；断言都用容差 | `DEG` |
| R-c2 | `twodim_base.py:563-565`、`histograms.py:848-855`；公开测试 `test_twodim_base.py:207-231` 等；提示中"不要改测试文件" | 两个文件各加一个 `test_normed_still_accepted`：`normed=True` 返回与 `density=True` 相同的密度；放行三类弃用告警；不测两者同时传入的情况（base 上没有公开依据） | `REN` |
| R-b | "与一维结果逐位相同"只是运算顺序带来的约束，没有公开依据 | `test_density_non_uniform_1d` 中的 `assert_equal(hist, hist_dd)` 改为 `assert_allclose` | `ORD` |

- 期望映射新增 4 个键，都为 PASSED，合计 82 键；新键不与现有键重名。
- 父版本：expected_v0，隐藏测试树 `b55abfbe…`。
- 四个触发补丁的 sha256 前缀：`DEG` 59b72fc0，`REN` 021f87da，`ORD` fe60bdb9，`DEP` ba35cc03。

**验收矩阵**（"修订前"一列是 09-28 的实跑结果，其余为预计）：

| 候选 | 修订前（实跑） | R-c＋R-b 之后（预计） | 这一行验证什么 |
| --- | --- | --- | --- |
| gold | 1（78/78） | 1（82/82） | 正对照 |
| noop | 0（72/78） | 0（74/82） | — |
| `DEG` | 1（78/78） | 0（两个 `test_density_outliers` 失败） | 漏判被纠正 |
| `REN` | 1（78/78） | 0（两个 `test_normed_still_accepted` 失败） | 漏判被纠正 |
| `ORD` | 0（77/78） | 1（82/82） | 误拒被纠正 |
| `DEP` | 1（78/78） | 1（82/82） | 不误拒"弃用 `normed`"的读法 |

- 另需核对：新键不撞键、没有 unexpected 键；保存新旧版本、修订理由与四个触发补丁；最后由 Codex 复核。
- 不需要用户决定，三处改动都在 R-b / R-c 模板之内。
- 可选的 T3 扩展（覆盖 2D 带权）另行登记，不在本轮。

## 7. 进探针还差什么

按派发要求没有读本批 README §3。下表按 v1 §2 与八方面协议 §5 的探针候选条件逐条列出，协调者可以对照 README §3 映射。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 公开要求可追溯，参考测试可解释 | 已满足（analysis §4–§5） | — |
| 当前镜像上 noop 0 / gold 1 | 已满足（09-28 新镜像） | — |
| 解题侧公开开发路径（正式启动链、agent 身份） | 已满足（09-28 devcheck，用脚本化桩端点） | — |
| 已知的 S1 / T1 已经处理 | 未满足：修订待实施与验收 | 协调者实施并实跑；Codex 复核 |
| 若修订前就进探针：预登记事后审计（§1 的两项） | 未写入探针计划 | 协调者 |
| 独立复核 | 未做 | 新会话 reviewer |
| 模型实际收到的完整消息、Qwen adapter 链路、真实模型求解 | 未验证（批次级） | A 线 / 协调者 |
| X1 登记与采样控制 | 已登记；采样控制待写入训练计划 | 训练设计 |
| 整文件公开测试噪声的解读规则 | 已登记（有历史实测） | 探针分析者 |

---

## 附录：修订 diff（相对当前隐藏测试，评分时路径为 `r2e_tests/`；已在草稿副本上用 `git apply --check` 验证，语法检查通过）

### R-c1＋R-c2

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -273,6 +273,34 @@
         assert_array_equal(H, answer)
         assert_array_equal(xe, array([0., 0.25, 0.5, 0.75, 1]))
 
+    def test_density_outliers(self):
+        # Values outside the bins are not tallied; density=True still makes
+        # the integral over the binned range equal to 1.
+        x = array([0.5, 1.5, 1.5, 2.5, 10.0, -3.0])
+        y = array([0.5, 0.5, 2.5, 2.5, 10.0, 1.0])
+        bins = [[0, 1, 3], [0, 2, 3]]
+        H, xed, yed = histogram2d(x, y, bins, density=True)
+        area = np.outer(np.diff(xed), np.diff(yed))
+        assert_array_almost_equal((H * area).sum(), 1.0)
+        counts = histogram2d(x, y, bins)[0]
+        assert_array_almost_equal(H, counts / counts.sum() / area)
+
+    def test_normed_still_accepted(self):
+        # The documented `normed` keyword keeps returning the density
+        # (a deprecation warning is acceptable).
+        x = array([1, 2, 3, 1, 2, 3, 1, 2, 3])
+        y = array([1, 1, 1, 2, 2, 2, 3, 3, 3])
+        bins = [[1, 2, 3, 5], [1, 2, 3, 5]]
+        with np.testing.suppress_warnings() as sup:
+            sup.filter(DeprecationWarning)
+            sup.filter(PendingDeprecationWarning)
+            sup.filter(np.VisibleDeprecationWarning)
+            H = histogram2d(x, y, bins, normed=True)[0]
+        answer = array([[1, 1, .5],
+                        [1, 1, .5],
+                        [.5, .5, .25]])/9.
+        assert_array_almost_equal(H, answer, 3)
+
 
 class TestTri(object):
     def test_dtype(self):
diff --git a/r2e_tests/test_2.py b/r2e_tests/test_2.py
--- a/r2e_tests/test_2.py
+++ b/r2e_tests/test_2.py
@@ -743,3 +743,33 @@
         hist_dd, edges_dd = histogramdd((v,), (bins,), density=True)
         assert_equal(hist, hist_dd)
         assert_equal(edges, edges_dd[0])
+
+    def test_density_outliers(self):
+        # Values outside the bins are not tallied; density=True still makes
+        # the integral over the binned region equal to 1, with and without
+        # weights.
+        x = np.array([0.5, 1.5, 1.5, 3.0, -1.0, 0.5, 9.0])
+        y = np.array([0.5, 0.5, 2.5, 2.5, 0.5, -2.0, 9.0])
+        w = np.array([1.0, 2.0, 1.0, 3.0, 4.0, 5.0, 6.0])
+        bins = ([0, 1, 4], [0, 2, 3])
+        area = np.outer(np.diff(bins[0]), np.diff(bins[1]))
+        for weights in (None, w):
+            counts, _ = histogramdd((x, y), bins=bins, weights=weights)
+            hist, _ = histogramdd((x, y), bins=bins, weights=weights,
+                                  density=True)
+            assert_almost_equal((hist * area).sum(), 1)
+            assert_allclose(hist, counts / counts.sum() / area)
+
+    def test_normed_still_accepted(self):
+        # The documented `normed` keyword keeps returning the same density
+        # as `density=True` (a deprecation warning is acceptable).
+        v = np.arange(10)
+        bins = np.array([0, 1, 3, 6, 10])
+        with suppress_warnings() as sup:
+            sup.filter(DeprecationWarning)
+            sup.filter(PendingDeprecationWarning)
+            sup.filter(np.VisibleDeprecationWarning)
+            hist_normed, edges = histogramdd((v,), (bins,), normed=True)
+        hist, _ = histogram(v, bins, density=True)
+        assert_allclose(hist_normed, hist)
+        assert_equal(edges[0], bins)
```

### R-b（须在上一段之后应用）

```diff
diff --git a/r2e_tests/test_2.py b/r2e_tests/test_2.py
--- a/r2e_tests/test_2.py
+++ b/r2e_tests/test_2.py
@@ -741,7 +741,7 @@
         bins = np.array([0, 1, 3, 6, 10])
         hist, edges = histogram(v, bins, density=True)
         hist_dd, edges_dd = histogramdd((v,), (bins,), density=True)
-        assert_equal(hist, hist_dd)
+        assert_allclose(hist, hist_dd)
         assert_equal(edges, edges_dd[0])
 
     def test_density_outliers(self):
```

### 期望映射新增键（均为 PASSED）

`TestHistogram2d.test_density_outliers`、`TestHistogram2d.test_normed_still_accepted`、`TestHistogramdd.test_density_outliers`、`TestHistogramdd.test_normed_still_accepted`

### 新用例的手算结果

- **2D 用例**：区间内 4 个点，计数 [[1,0],[1,2]]，面积 [[2,1],[4,2]]。gold 积分为 1；`DEG` 用全部 6 个样本作分母，积分为 4/6。
- **ND 用例**：
  - 不带权：区间内计数 [[1,0],[1,2]]；带权：[[1,0],[2,4]]；面积 [[2,1],[6,3]]。
  - gold 两种情况积分都为 1。
  - `DEG` 用全部 7 个样本作分母时积分为 4/7；用全部权重 22 作分母时为 7/22。
- **noop 对新键**：两个 `test_normed_still_accepted` 在 base 上通过，两个 `test_density_outliers` 失败，所以 noop 为 74/82。
