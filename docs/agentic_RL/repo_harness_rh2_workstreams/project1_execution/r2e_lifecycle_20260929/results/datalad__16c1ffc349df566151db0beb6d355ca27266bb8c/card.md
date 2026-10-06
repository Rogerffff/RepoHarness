# datalad `16c1ffc3` 题卡

## 结论

- **处置：S1，状态 `needs_repair`**（静态审查范围）。
- **修订：R-c 必做**，完成前不能进训练。**R-b 建议与 R-c 同批**，但不能单独做。

## 题目与版本

- **题目**：修改 `eval_results`，让声明了 `**kwargs` 的 `result_filter` 收到 API 调用的关键字参数。base 为 `fddce1e754d3`（datalad 0.5.1.dev1）。
- **材料**：现材料没有修订，v3–v8 对本题相同。新机器上的派生镜像为 `sha256:3874afbac47a…`。
- **8 个评分键**：
  - 目标键 1 个：`test_result_filter`；
  - 活的回归键 2 个；
  - 死键 5 个：期望为 FAILED，因 conftest 的 `path` fixture 与装饰器冲突，测试体从不执行，不影响判分。

## v1 用途

- **`problem_localization`：yes。**
- **`capability_comparison`：conditional。** 还差三个条件：
  1. 本机评分的控制面保护时限要放宽到 1200 s；缺省 300 s 会 failed_to_grade。
  2. 如果用现材料，要预登记事后审计，检查得 1 的补丁：
     - 是否吞掉 filter 的异常；
     - 是否无条件地把 kwargs 传给所有 filter；
     - 是否改动了 `datalad/tests/` 或 `.venv`。
  3. 如果用现材料，只因 `sadfilter` 失败、并且属于"把全部参数传给 filter"这种读法的尝试，要单列为争议，原始 reward 保留。
- **`training_candidate`：no（现版本）。** R-c（和 R-b）验收并经 Codex 复核后重评。
- **`heldout_candidate`：no。**

## 关键映射

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据 |
|---|---|---|---|---|
| 带 `**kwargs` 的 filter 收到调用的 kwargs | 题面标题与期望行为 | `greatfilter`：在回调里断言 `'dataset' in kwargs`，外层不看结果 | 只覆盖示例的字面值 | noop 的失败信息与题面逐字一致；吞异常的候选 D 得 1.0 |
| 同一要求的其它实例：其它 kwarg、generator 模式、Dataset 方法调用 | 题面的一般表述；`utils.py:1063-1082`；`dataset.py:441-451` | 无 | 缺失 | — |
| 调用带 kwargs 时，Constraint 和单参数 filter 仍可用 | `create.py:89-91`、`base.py:325-338`、`results.py:66-67`；公开测试 `test_clean.py:39-40`、`test_save.py:119` | 无活键。本可覆盖它的 `test_dirty` 等是死键 | 缺失 | 无条件传 kwargs 的候选 N 得 1.0；行为对照中 N 报 `TypeError` |
| 没给 dataset 时，filter 看不到它 | 题面无；只有渲染器的先例（`utils.py:1048,1050`） | `sadfilter`：`assert_not_in('dataset', kwargs)` | 过严 | C2（补默认值，与上游后来的语义一致）得 0.0 |
| 原有的公开 filter 测试和文档子串 | 公开 `test_utils.py:373-379,400-422` | `test_result_filter` 前半段；`test_eval_results_plus_build_doc` | 覆盖 | gold、C1 得 1.0 |

## 八方面

| 方面 | 已查 | 未查 / 发现 |
|---|---|---|
| 公开需求 | 题面、提示、`eval_results` 及其调用者 | 模型实际收到的完整消息 |
| 材料与初态 | 各材料相互对应；noop 失败位置与题面一致；devcheck 在 base 上复现了原例 | — |
| 测试是否测到要求 | 8 个键全部读过 | §4 的第 2、3、4 步都命中 |
| 是否误拒合理解 | C2 | C2 被误拒（T1） |
| 回归与 gold | 旧式 filter 的兼容性 | 旧式 filter 没有回归保护；gold 对拿不到签名的可调用对象有罕见回归（仅静态推断，T3） |
| 开发条件 | devcheck 全部检查为真（CC 2.1.205 + 桩端点，agent 身份） | 不需要网络和构建；带装饰器的公开测试在 pytest 下有 5 个 ERROR，属于噪声 |
| 交付与评分 | 投影只含 `datalad/interface/utils.py` 一个文件 | 测试辅助在评分时不重置，属于通用的控制面风险（E3，交 A 线） |
| 题目关系 | 两份跨题扫描，外加手工核对同仓公开包 | X1：与 `58ba5165`、`19f5b450`、`9ba5de09` 相关，两份扫描都漏报 |

## 问题与证据

| 编号 | 问题 | 证据 |
|---|---|---|
| S1（T2c） | 核心断言只用了示例的字面值 | 静态阅读 |
| S1（T2b） | 退化候选 D 得 1.0（8/8） | 日志里有 4 条被吞掉的断言；行为对照中题面原例返回 `RESULT []`，gold 返回 4 条 |
| S1（第 4 步） | 候选 N 得 1.0 | `filters_backcompat` 在 N 下报 `TypeError: __call__() got an unexpected keyword argument 'dataset'`；gold 打印 `BACKCOMPAT_OK` |
| T1 | 合理解 C2 被判 0.0 | 失败点正是 `sadfilter`，它收到的是 `{'number': 4, 'dataset': None}` |
| T5 | 5 个死键 | 对判分无害；可选 R-a |
| E3 | 评分与启动开销大 | 缺省 300 s 控制面保护超时；可信 setup 153–222 s；解题侧启动约 434 s |
| 仅登记 | X1、P4、G1→T3 | — |

不需要环境修复。

## 修订建议（v1 §5；草案见附录 B）

**R-c（必做）**
- 在 `hidden_tests/test_1.py` 新增两个测试：
  - `test_result_filter_gets_call_kwargs`：检查同一要求的非示例实例，并在测试外层断言收到的参数值和过滤结果；
  - `test_result_filter_plain_callables_with_call_kwargs`：Constraint、`&` 组合和 lambda 在带 kwargs 的调用下仍得 `[0, 2]`。
- 在 expected 中增加这两个键，均为 PASSED。
- 公开依据见上面的关键映射表。

**R-b（建议同批）**
- 把 `sadfilter` 改为 `assert_equal(kwargs.get('dataset'), None)`。
- 只能与 R-c 一起上：单独放宽会放过"固定传 `dataset=None`"的错误候选 F。
- 复核若认定这是 P5（任务目标层面的分歧），就撤回 R-b，交用户决定。

## 验收矩阵

现材料一列是实跑结果；修订后一列是预期（R-c 与 R-b 同批）。

| 候选 | 现材料（实跑） | 修订后预期 |
|---|---|---|
| noop | 0（7/8） | 0 |
| gold（正对照） | 1（8/8） | 1 |
| C1（替代正对照） | 1（8/8） | 1 |
| C2 | 0（7/8，`sadfilter`） | 1；只上 R-c 时仍为 0 |
| D | 1（8/8） | 0：`gets_call_kwargs` 收到的 kwargs 为空 |
| N | 1（8/8） | 0：`plain_callables` 报 `TypeError` |
| F（可选） | 未跑；预计 0（被 `sadfilter` 挡住） | 0（缺 `number`）；只上 R-b 时预计为 1 |

- **独立复核**：尚未进行。
- **唯一优先的下一步**：协调者按附录 B 同批实施 R-c 和 R-b，在放宽时限下跑上表的 6 次验收评分（F 可选），然后交 Codex 复核。

## 剩余事项与探针就绪差距

按派发规定，我没有读本批 README；以下按 v1 §2 和已有证据列出。如果 README §3 还有其它条款，请协调者补做对照。

| 条件 | 状态 | 谁来补 |
|---|---|---|
| 解题侧开发路径 | 已满足（devcheck 全部检查为真） | — |
| 现材料上 noop 为 0、gold 为 1 | 已满足（新机器，放宽时限，各 1 次；另有历史 2 次） | — |
| 评分时限（链路条件） | 未满足：缺省 300 s 会 failed_to_grade。探针条件须写明 1200 s，或由 A 线解决 `chown -R` 过慢 | A 线 / 协调者 |
| 解题侧启动开销约 434 s | 已知，但没有拆分，会影响回合预算的估计 | A 线 |
| 题目质量 | 未满足：S1 未修 | 协调者实施 R-c（和 R-b），Codex 复核 |
| 若在修订前就进探针 | 需要预登记事后审计，并把争议单列（见"v1 用途"） | 协调者 |
| 独立复核 | 未完成 | 本批 reviewer |
| 真实模型求解 | 未跑；清单第 33–36 项由探针本身回答 | 探针 |

## 附录 B：可执行修订草案

- B.1–B.3 的路径相对 `PRIVATE_DIR`（材料树根）。B.1 和 B.2 可以各自单独应用，也可以按任意顺序先后应用。
- 三份补丁都已在原材料上通过 `git apply --check`，修订后的 `test_1.py` 通过了 `py_compile`。
- B.4 是可选的验收候选，与读历史前初判附录 A 里的候选一样，在 base 工作树根目录应用。

### B.1 R-c：新增两个测试（`rev_rc.patch`）

```diff
diff --git a/hidden_tests/test_1.py b/hidden_tests/test_1.py
index b961d0d..70dc79e 100644
--- a/hidden_tests/test_1.py
+++ b/hidden_tests/test_1.py
@@ -433,2 +433,56 @@ def test_result_filter():
         return True
     Test_Utils().__call__(4, result_filter=sadfilter)
+
+
+def test_result_filter_gets_call_kwargs():
+    # a filter that accepts **kwargs gets the keyword arguments of the API
+    # call -- not only `dataset` -- also in generator mode and when the
+    # command is called as a Dataset method (all arguments become keyword
+    # arguments); the filter's decision is honored
+    seen = []
+
+    def kwfilter(res, **kwargs):
+        seen.append(kwargs)
+        return res['somekey'] in (1, 3)
+
+    for rtype in ('list', 'generator'):
+        del seen[:]
+        assert_equal(
+            [r['somekey'] for r in Test_Utils().__call__(
+                number=4, dataset='awesome', return_type=rtype,
+                result_filter=kwfilter)],
+            [1, 3])
+        ok_(seen)
+        for kw in seen:
+            assert_equal(kw.get('number'), 4)
+            assert_equal(kw.get('dataset'), 'awesome')
+
+    del seen[:]
+    ds = Dataset('/does/not/matter')
+    assert_equal(
+        [r['somekey'] for r in ds.fake_command(4, result_filter=kwfilter)],
+        [1, 3])
+    ok_(seen)
+    for kw in seen:
+        assert_equal(kw.get('number'), 4)
+        ok_(kw.get('dataset') is ds)
+
+
+def test_result_filter_plain_callables_with_call_kwargs():
+    # filters that do not accept **kwargs -- Constraints (as used for the
+    # class-level default filter of `create` and for the --report-status /
+    # --report-type command line options) and plain one-argument callables
+    # (e.g. datalad.interface.results.is_ok_dataset) -- keep working when
+    # the API call has keyword arguments
+    ds = Dataset('/does/not/matter')
+    for filt in (
+            EnsureKeyChoice('somekey', (0, 2)),
+            EnsureKeyChoice('status', ('ok',)) & EnsureKeyChoice('somekey', (0, 2)),
+            lambda x: x['somekey'] in (0, 2)):
+        assert_equal(
+            [r['somekey'] for r in Test_Utils().__call__(
+                4, dataset='awesome', result_filter=filt)],
+            [0, 2])
+        assert_equal(
+            [r['somekey'] for r in ds.fake_command(4, result_filter=filt)],
+            [0, 2])
```

### B.2 R-b：放宽 `sadfilter`，只与 B.1 同批（`rev_rb.patch`）

```diff
diff --git a/hidden_tests/test_1.py b/hidden_tests/test_1.py
index b961d0d..a7f5afc 100644
--- a/hidden_tests/test_1.py
+++ b/hidden_tests/test_1.py
@@ -431,3 +431,5 @@ def test_result_filter():
     def sadfilter(res, **kwargs):
-        assert_not_in('dataset', kwargs)
+        # no dataset was given in the call: the filter must not be handed
+        # one (the argument may be absent or None)
+        assert_equal(kwargs.get('dataset'), None)
         return True
```

### B.3 expected 增加两个键，随 B.1（`rev_expected.patch`）

```diff
diff --git a/expected_output.json b/expected_output.json
index 325e99f..107caf0 100644
--- a/expected_output.json
+++ b/expected_output.json
@@ -6,5 +6,7 @@
     "test_paths_by_dataset": "FAILED",
     "test_save_hierarchy": "FAILED",
     "test_get_dataset_directories": "FAILED",
-    "test_filter_unmodified": "FAILED"
+    "test_filter_unmodified": "FAILED",
+    "test_result_filter_gets_call_kwargs": "PASSED",
+    "test_result_filter_plain_callables_with_call_kwargs": "PASSED"
 }
\ No newline at end of file
```

### B.4 可选验收候选 F：固定传 `dataset=None`（`cand_F.patch`）

F 是故意写错的候选：它给带 `**kwargs` 的 filter 固定传 `dataset=None`，与调用无关。用途是证明 R-b 不能单独上。

```diff
diff --git a/datalad/interface/utils.py b/datalad/interface/utils.py
index 7c35619..b4cc2e4 100644
--- a/datalad/interface/utils.py
+++ b/datalad/interface/utils.py
@@ -991,6 +991,20 @@ def eval_results(func):
             incomplete_results = []
             # inspect and render
             result_filter = common_params['result_filter']
+            # (wrong on purpose) filters that accept **kwargs get a fixed
+            # dataset=None, independent of the API call
+            _result_filter = result_filter
+            if result_filter:
+                try:
+                    _filter_takes_kwargs = any(
+                        p.kind == inspect.Parameter.VAR_KEYWORD
+                        for p in inspect.signature(result_filter).parameters.values())
+                except (TypeError, ValueError):
+                    # no introspectable signature (e.g. some builtins)
+                    _filter_takes_kwargs = False
+                if _filter_takes_kwargs:
+                    def _result_filter(res):
+                        return result_filter(res, dataset=None)
             result_renderer = common_params['result_renderer']
             result_xfm = common_params['result_xfm']
             if result_xfm in known_result_xfms:
@@ -1025,9 +1039,9 @@ def eval_results(func):
                         # first fail -> that's it
                         # raise will happen after the loop
                         break
-                if result_filter:
+                if _result_filter:
                     try:
-                        if not result_filter(res):
+                        if not _result_filter(res):
                             raise ValueError('excluded by filter')
                     except ValueError as e:
                         lgr.debug('not reporting result (%s)', exc_str(e))
```

## 附录 C：证据索引

下文 `N:` = `runs/r2e_lifecycle_20260929/`。

- **缺省时限复验**：`N:env_verify/ledger_l2_noop.jsonl`、`ledger_l2_gold.jsonl` 第 2 行，结果为 `grading_control_surface_protect_timeout_after_300s`。
- **放宽时限复验**：`N:budget_v5/ledger_noop.jsonl`、`ledger_gold.jsonl` 第 1 行。
- **候选正式评分**：`N:inv/datalad_16c1/ledger_{D,N,C1,C2}_budget1200.jsonl` 第 1 行，日志在 `logs_*/`。
  - D 日志：`:119-122`、`:139-142`（被吞的断言），`:144-153`（汇总）；
  - C2 日志：`:129-153`（`sadfilter`）；
  - C1 日志：`:113`（行号后移）。
- **行为对照**：`N:inv/datalad_16c1/pcheck_*.json`。
- **devcheck**：`N:devcheck/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/orig/attempt.json` 和 `captures/*.out`；gold 对照在 `private_control.json`。
- **分析与改判**：`analysis_before_history.md`（读历史前初判，候选全文在附录 A）；`old_findings_delta.md`（旧结论核对）。
