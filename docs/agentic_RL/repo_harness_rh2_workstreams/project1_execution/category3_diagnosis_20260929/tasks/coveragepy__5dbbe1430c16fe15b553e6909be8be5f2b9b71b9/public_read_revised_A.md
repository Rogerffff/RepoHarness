# coveragepy 5dbbe：修订题面 A 的公开读者验收

**总判断：题面已足够清楚，可验收。** 核心行为现在只有一种读法：同一 slug、不同消息的第二条 `once=True` 警告不显示。新增说明和公开文档、代码都一致，也不算泄露。剩下几处没写的边界情况（`slug=None`、once 之后同 slug 的非 once 警告、跨实例）可以交给实现者决定。**这个判断有前提：隐藏测试只断言题面写明的行为。** 作为公开读者，我无法核实这一点。

- 验收日期：2026-09-29
- 身份：公开读者，只看解题者能看到的材料。
- 读过的材料：
  - `rh2/experiments/category3_cloud_20260929/cov5dbbe/revised_statement_A.txt`
  - 镜像 `c3keep/coveragepy_5dbb:src` 中的 `/testbed`，包括源码、`doc/` 和 `tests/`。
- 没有读的材料：`/r2e_tests`、`docs/` 下的其它文件、`cov5dbbe/` 下的其它文件、任何 `runs/` 目录，以及本报告同目录下的其它文件。
- 仓库状态：`git log` 头部为 `8240c58c More issue template options`；`coverage.__version__ == 5.0.2a1`。

---

## (a) 题面要求做什么：我会断言的具体行为

先复现基线。在未修改的 `/testbed` 里运行题面示例，输出为：

```
TypeError: _warn() got an unexpected keyword argument 'once'
```

这与题面的 Actual Behavior 一致。当前签名是 `coverage/control.py:336` 的 `def _warn(self, msg, slug=None)`。

我会断言以下行为。每条都在 `cov = coverage.Coverage(); cov.load()` 之后执行，“stderr”指 `sys.stderr` 的输出。

| # | 行为 | 输入 | 期望输出 |
|---|---|---|---|
| 1 | `_warn` 接受 `once` 关键字，不再抛 `TypeError` | `cov._warn("Warning, warning 1!", slug="bot", once=True)` | 不抛异常 |
| 2 | 第一条 once 警告照常显示，格式不变 | 同上 | stderr 含 `Coverage.py warning: Warning, warning 1! (bot)\n` |
| 3 | 同 slug、不同消息的后续 once 警告不显示（题面核心） | 接着调用 `cov._warn("Warning, warning 2!", slug="bot", once=True)` | 不抛异常；stderr **不含** `Warning, warning 2!` |
| 4 | 同 slug、同消息的重复 once 警告也只显示一次 | 连续两次 `cov._warn("M", slug="s", once=True)` | stderr 中 `Coverage.py warning: M (s)` 只出现 1 次 |
| 5 | 不同 slug 的 once 警告各显示一次 | 在第 1、3 条之后调用 `cov._warn("Other", slug="other", once=True)` | stderr 含 `Coverage.py warning: Other (other)` |
| 6 | 默认行为不变：不传 `once` 时，同 slug 的警告照常重复显示 | `cov._warn("A", slug="x"); cov._warn("B", slug="x")` | stderr 同时含 `A (x)` 和 `B (x)` |
| 7 | `disable_warnings` 仍然优先 | 配置 `[run] disable_warnings = bot`，再调用 `cov._warn("W", slug="bot", once=True)` | stderr 不含 `W` |
| 8 | 旧调用方式兼容，`once` 默认为 `False` | `cov._warn("m")`、`cov._warn("m", "s")`、`cov._warn("m", slug="s")` | 行为与修改前相同 |

第 6 条和第 8 条不是题面明文要求，但公开材料对它们有硬约束：

- 第 6 条：`tests/test_api.py::test_warnings` 期望两条 `module-not-imported`（`xyzzy`、`quux`）都出现；`test_two_getdata_warn_twice` 期望 `no-data-collected` 出现两次。所以 once 只能按调用方选择开启，不能改成默认行为，也不能把现有调用点改成 `once=True`。
- 第 8 条：`CTracer` 按位置参数调用 `warn(msg)`（`coverage/ctracer/tracer.c:605`），`InOrOut` 和 `PyTracer` 用 `warn(msg, slug=...)`。

## (b) 同一 slug、不同消息的两条 `once=True` 警告，第二条是否显示？

**不显示。题面已经写清楚。**

- 新增句子直接回答了这个问题：“once a `once=True` warning has been displayed, later `once=True` warnings with the same slug are not displayed, **even if their message text is different**”。
- 题面示例正是这个场景：slug 都是 `bot`，消息分别是 `warning 1!` 和 `warning 2!`。
- 修订前只有 “displayed only once each”，“each”可以理解为按消息去重。那样示例中的两条都会显示，示例除了复现 `TypeError` 就没有别的意义。新增句子排除了这种读法。

**关于这个问题，我找不到第二种合理读法。** 可能出现分歧的只是相邻问题，第二条都照样不显示：

1. **被抑制的警告是否记入 `cov._warnings`？** 题面只说 “not displayed”。`_warnings` 是“A record of all the warnings that have been issued”（`control.py:207-208`）。现有 `disable_warnings` 分支在 `append` 之前就 `return`（`control.py:341-343`）。如果照 “As with `disable_warnings`” 类推，自然结论是不记录，但题面没有明说。如果隐藏测试检查 `len(cov._warnings)`，这里会有风险。
2. **once 状态的作用范围**：见 (d)。

## (c) 新增说明与公开文档、代码是否一致

**一致，没有发现矛盾。** 逐项核对如下。

| 题面表述 | 公开依据 | 结论 |
|---|---|---|
| “a warning is identified by its `slug`”，并称这一点 “As with `disable_warnings`” | `control.py:341`：`if slug in self.config.disable_warnings: return`，只按 slug 匹配，不看消息 | 一致 |
| “the short name shown in parentheses after the message” | `control.py:346-347`：`msg = "%s (%s)" % (msg, slug)`；`doc/cmd.rst` 中的警告列表都写成 `... (no-data-collected)` 这种形式 | 一致 |
| 用 slug 指称警告 | `doc/config.rst:156-158`：“Warnings that can be disabled include a short string at the end, the name of the warning.”；`_warn` docstring：“For warning suppression, use `slug` as the shorthand.” | 一致。公开文档从不使用 “slug” 一词，只说 “name of the warning”，题面括号里的解释把两套说法接上了，这是必要的 |
| `disable_warnings` 用法 | `doc/cmd.rst:182-187` 给了 `disable_warnings = no-data-collected` 的例子 | 一致 |

有两点可以从公开材料理解，但读者需要多想一步。它们不是矛盾：

- **“As with `disable_warnings`” 修饰的是“按 slug 识别”，不是“抑制范围”。** 有读者可能把它读成“once 警告显示后，这个 slug 等同于被加入 `disable_warnings`”，于是之后同 slug 的**非 once** 警告也被吞掉。题面后半句的主语是 “later `once=True` warnings”，按字面只约束 once 警告，所以这种读法是过度延伸。但它与示例并不冲突，见 (d) 的实测。
- **`slug=None` 的警告在 `disable_warnings` 下无法识别。** 配置里是字符串列表，`None in [...]` 恒为假，所以无 slug 的警告不能被禁用。照 “As with `disable_warnings`” 类推，无 slug 的 once 警告没有身份。题面没说这时该怎么办，见 (d)。

`doc/` 里没有 `_warn` 的公开文档（`grep -rn '_warn\b\|slug' doc/` 无结果），所以不存在“文档说一套、题面说另一套”的情况。`Collector.__init__` 的 docstring（`collector.py:90-92`）说 `warn` 是 “taking a single string message argument and an optional slug argument”。它描述的是传给 tracer 的回调，题面不要求改它。

## (d) 题面未说明、实现时必须做选择的地方

我在一次性容器里用两种都符合题面字面要求的实现对照实测（运行时 monkeypatch，不改仓库文件）：

- **实现 A**：每个实例维护一个“已显示的 once slug”集合，只对 `once=True` 的调用生效。
- **实现 B**：once 警告显示后，把 slug 并入实例的禁用列表。

两者在题面示例上结果相同：`warning 1!` 显示，`warning 2!` 不显示，不同 slug 各显示一次。分歧点如下。

| 未说明点 | 实现 A 的结果 | 实现 B 的结果 | 我的意见 |
|---|---|---|---|
| once 之后，同 slug 的**非 once** 警告 | 显示（`Warning 3 non-once (bot)`） | 不显示 | 交给实现者。题面字面只约束 once 警告，A 更贴字面；B 也说得通 |
| 非 once 之后，同 slug 的**第一条** once 警告 | 显示（题面说的是 “once a `once=True` warning has been displayed”） | 显示 | 两种实现一致，问题不大 |
| `slug=None` 的 once 警告 | 可以选择总是显示、按消息去重，或把 `None` 当作一个 slug | 把 `None` 并入禁用列表后，**之后所有无 slug 的警告，包括非 once 的，都被吞掉**（实测 `noslug NON-once C` 消失） | 交给实现者，但 B 的这个副作用有害：`"No contexts were measured"`、`"[run] note"`、插件相关警告都没有 slug。如果隐藏测试覆盖这一点，题面必须补充 |
| 跨 `Coverage` 实例 | 按实例隔离，新实例的 `slug="bot"` once 警告照常显示（实测 `second instance (bot)` 显示） | 同样按实例隔离 | 交给实现者。按实例隔离与 `config`、`_warnings` 都挂在实例上的做法一致，是自然选择。做成类级或模块级全局状态会造成测试顺序依赖，属于较差但并非不可能的读法 |
| 被抑制的警告是否记入 `_warnings` | 不记（与 `disable_warnings` 分支一致） | 不记 | 交给实现者，默认按 `disable_warnings` 类推 |
| 是否把现有调用点（如 `pytracer.py:230` 的 `trace-changed`）改成 `once=True` | 不改 | 不改 | 题面没要求。改 `module-not-imported`、`no-data-collected` 会让公开测试失败（见 (a)）。另外公开测试辅助函数 `tests/coveragetest.py:267` 的 `capture_warning(msg, slug=None)` 不接受 `once`，内部调用点一旦传 `once=True`，就会让用到 `assert_warnings` 的测试报 `TypeError` |

**总体意见：这些点应当交给实现者决定。题面不必再补，前提是隐藏测试只断言 (a) 第 1 至 5 条（最多加上第 6、7 条）。** 如果隐藏测试还断言了上表任何一行（尤其是“once 后的非 once 警告”或 `slug=None`），就必须在题面补一句，否则实现 A 和实现 B 中必有一个被误判。

可选的微调措辞（不阻塞验收）：在 Expected Behavior 末尾补一句 “This only affects calls that pass `once=True`, within a single `Coverage` object; other warnings behave as before.” 这一句同时锁定作用范围和非 once 行为，也不暴露测试细节。

## (e) 是泄露，还是必要澄清？

**我判断为必要澄清，不是泄露。** 理由：

1. **它回答的歧义是题面自己的示例造成的。** 修订前的示例已经用了“同 slug、不同消息”。题面只写 “only once each”，实现者就无法判断示例的期望输出。补上“按 slug 识别”是在补全示例的语义，没有引入新场景。
2. **它是 API 层面的行为规格，不涉及测试手段。** 它没有提到如何捕获 stderr、断言哪段字符串、测试函数名或用了哪些辅助函数，也没有给出 “Warning, warning 2!” 之外的新字面量。
3. **它没有指示实现方式。** 没有说“加一个列表”“并入 `disable_warnings`”，也没有说状态存在哪里。“As with `disable_warnings`” 只是借用户已知的配置项来类比识别键，而这个识别键在公开代码里能直接查到（`control.py:341`）。
4. **它有一点“精确描述了测试会检查的那个场景”的味道。** 但这个场景本来就在示例里，任何合格的问题描述都应该说清示例的期望输出，所以不构成额外的信息优势。

## (f) 如果只写一个修复（思路，未改代码）

```
1. 在 Coverage.__init__ 中加 self._once_warned = set()（与 self._warnings 放在一起）。
2. 签名改为 def _warn(self, msg, slug=None, once=False)，docstring 补一句
   "If `once` is true, only show this warning once (determined by the slug)."
3. 保留原来的 disable_warnings 早退分支，放在最前面。
4. if once: key = slug if slug is not None else msg   # 无 slug 时退化为按消息去重
5.          if key in self._once_warned: return        # 不显示、不记入 _warnings
6.          self._once_warned.add(key)
7. 其余输出逻辑（append、拼 "(slug)"、pid 前缀、写 stderr）完全不变。
8. 不改任何现有调用点；可顺手把 tests/coveragetest.py 的 capture_warning 签名
   补上 once=False，避免以后内部调用传 once 时让 assert_warnings 报 TypeError。
```

对这个思路（去掉第 4 行的 msg 回退、按 slug 去重的版本）做过实测：用运行时 monkeypatch 把 `Coverage._warn` 换成候选实现，再在同一进程里运行公开测试：

```
docker run --rm --network none ... c3keep/coveragepy_5dbb:src \
  -c "cd /testbed && .venv/bin/python /probe.py -o cache_dir=/tmp/pc -n 0 \
      tests/test_api.py tests/test_testing.py tests/test_html.py"
# exit=0；143 passed in 6.77 seconds
```

示例输出为 `Coverage.py warning: Warning, warning 1! (bot)`，没有 `warning 2!`，与 (a) 第 1 至 5 条一致。这只说明它没有破坏公开测试，并与我对题面的理解一致。**是否通过隐藏测试未验证。**

---

## 最重要的 3 条意见

1. **核心歧义已消除。** “同 slug、不同消息”的第二条 `once=True` 警告不显示，这一点由新增句子加上 “even if their message text is different” 明确锁定。对这个问题找不到第二种合理读法。
2. **新增说明与公开材料一致，属于必要澄清，不是泄露。** 按 slug 识别与 `_warn` 的实现（`control.py:341`）、`doc/config.rst` 的 “name of the warning”、`doc/cmd.rst` 中的 `(slug)` 显示格式都对得上。它补全的是示例本身的语义，不涉及测试手段或实现方式。
3. **两处边界情况是实现自由，但隐藏测试不应断言它们。** 一是 once 之后同 slug 的非 once 警告，二是 `slug=None` 的 once 警告。实测两种都合理的实现在这两点上结果相反，“并入禁用列表”式实现还会吞掉之后所有无 slug 的警告。如果隐藏测试覆盖了这两点，应在题面补一句“只影响传 `once=True` 的调用、按 `Coverage` 实例生效，其余警告行为不变”。
