# coveragepy `97997d2c` 修订方案（R-c）

2026-09-29 · 修订执行者（Claude，单题闭环试行，统一标准 v1 §5 预授权模板）。

**状态：修订草案已在新派生镜像上试跑，验收全部符合预期；待 Codex 复核。** 正式修订单、pins 与派生镜像材料步骤由协调者落地。试跑工具不是正式评分，差别见 §6。

路径约定（均相对仓库根）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/`，其中 `PUB/worktree/` 就是解题者的 `/testbed`；
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/`；
- `CANDS` = `runs/r2e_actor_20260925/grader_cands/`；
- `trials/` = 本目录下的试跑结果。

## 0. 结论

- **模板与范围**：R-c，一轮修订。只在隐藏测试 `r2e_tests/test_1.py` 里新增 3 个测试，期望映射由 44 键变为 47 键：新增 3 键均为 PASSED，原 44 键不变。
- **"替换还是合并"**：核对公开依据后，**替换有直接的公开依据，合并没有肯定性的公开依据**（§2）。所以它不属于 v1 §3 P5 所说的"两种读法都有依据"，按任务说明把替换断言一并补上。
  - 这是本题最需要 Codex 聚焦复核的一点。
  - 如果复核认定合并也有依据，退路见 §2.3，只需改一行，G1、G2 两处不受影响。
- **试跑结果**：
  - 新派生镜像 `sha256:418dca92…`，配方 `r2e_derive_v1+sysconfig_v1`。当前材料下 noop 为 mismatch、gold 为 match，环境正常。
  - 修订后：gold 得 1；合理替代解 A1 得 1；noop 得 0。
  - W1、W2、M 在当前材料下都得 1，修订后都得 0，而且各自只在对应缺口的那个新键上失败；负对照 N1 仍是 0。

## 1. 要修的三处缺口（按 v1 §4 判定，均为 S1）

| # | 缺口 | 触发反例（09-25，当前材料，正式评分） | v1 §4 | 公开依据 |
|---|---|---|---|---|
| G1 | 目标键只经 `Coverage` 对象读写。configurer 插件拿到的另一种对象 `CoverageConfig` 没有测 | W1（只改 `control.py` 转发层）得 1，44/44（`runs/r2e_actor_20260925/grader/ledger_cov9799_W1_control_layer_only.jsonl`） | 第 4 步：同一核心要求的另一实例上违反公开要求 | 标题 "Unable to Modify 'paths' Configuration via Plugins"（`PUB/user_prompt.txt:5`），以及 :8、:34；插件拿到的对象是 `[self, self.config][int(time.time()) % 2]`（`PUB/worktree/coverage/control.py:270-276`）；`configure(config)` 的 config 是"带 get_option / set_option 的对象"（`PUB/worktree/coverage/plugin.py:213-216`） |
| G2 | 设进去的值是否被 `combine()` 使用，没有测 | W2（值存到旁路属性 `_paths_override`）得 1（`ledger_cov9799_W2_side_attribute.jsonl`） | 第 3、4 步：作用在无关对象上 | `Coverage.set_option` 文档写明 "`value` is the new value for the option"，并说这个调用 "has the same effect as this configuration file"（`PUB/worktree/coverage/control.py:384-395`）；[paths] 用于 combine，多组按顺序匹配（`PUB/worktree/doc/config.rst:223-235,246-247`）；`combine()` 读的是 `self.config.paths`（`control.py:672-678`） |
| G3 | 只从空起点做一次往返（即题面示例的字面值）。"取回配置文件里的 [paths]"与"set 是替换"都没测 | M（set 分支改为 `self.paths.update(value)`，即合并）得 1（`ledger_cov9799_M_merge_paths.jsonl`） | 第 2 步：只用示例字面值 | 取回：题面 "Expected to retrieve the current paths"（`PUB/user_prompt.txt:16`）和 "should successfully retrieve the current paths configuration"（:27）。替换：见 §2 |

## 2. "替换还是合并"的公开依据核对

### 2.1 支持替换的依据

1. **题面示例注释**（`PUB/user_prompt.txt:23`）：`print(cov.get_option("paths"))  # Expected to output the new_paths OrderedDict`。即 set 之后，get 得到的就是所设置的 new_paths。
2. **set_option 的通用契约**：
   - `Coverage.set_option` 文档（`PUB/worktree/coverage/control.py:384-395`）写明 "`value` is the new value for the option"，并举例说明 `cov.set_option("run:branch", True)` "has the same effect as this configuration file"。
   - 套用到 "paths" 这个选项：新值就是整段 [paths]，效果等同于配置文件里写了这样一段 [paths]。
   - `CoverageConfig.set_option` 的文档同样写 "`value` is the new value for the option."（`config.py:421`）。
3. **既有选项的做法**：
   - 所有内置选项的 set 都是 `setattr` 整体替换（`config.py:426-430`）。
   - 公开的 configurer 插件样例修改列表选项的写法是"取出 → 修改 → 整体 set 回去"（`PUB/worktree/tests/plugin_config.py:13-17`，对应公开测试 `tests/test_plugins.py:879-886`）。这种写法以"set 就是替换"为前提。
4. **顺序语义**：多组 paths 按顺序匹配，第一个命中的生效（`doc/config.rst:246-247`）。只有在替换语义下，插件才能重排或删除已有条目；合并（`update`）只能在末尾追加，不能删除。

**佐证**（不属于本题的公开面，只说明替换不是 gold 碰巧的选择）：
- 同仓后来版本的 `Coverage.set_option` 文档写明 `"paths"` "will replace the entire `[paths]` section"（`runs/r2e_static_prep_20260924/v3/public/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/worktree/coverage/control.py:426-427`）；
- 上游后来的目标测试也是从非空起点出发断言替换（同一工作树的 `tests/test_config.py:339-361`）。

### 2.2 支持合并的依据

- **题面第 27 行**是唯一可引的文字："return the updated `OrderedDict` containing the new paths"。
  - "updated"和"containing"在替换语义下同样成立：替换后的映射也"包含新的 paths"，也是"更新后的"。
  - 这句话不排斥替换，也没有说旧条目应该保留。
- **标题**里的 "Modify ... via Plugins" 与两种语义都相容：替换语义下，插件用"get → 修改 → set"来修改。
- **公开包里没有**任何文档、API 或旧测试说 set_option 对映射型选项做合并。
  - 插件选项 `plugin:key` 是按单个键写入的（`config.py:432-436`）。它对应的是"写单个条目"，不是"整段 set 时合并"的先例。

### 2.3 判断与退路

**判断**：替换有直接的公开依据（题面第 23 行的示例注释，加上 set_option 的通用契约）；合并只有不排斥它的中性措辞，没有肯定性依据。所以这里不是 v1 §3 P5 所说的"两种读法都有依据"，按任务说明补上替换断言。

与 09-25 各方意见的关系：
- 公开读者在隔离阅读下判为"明示倾向替换"（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/public_read.md:16`）；
- 复核者（同目录 `review.md` §5 D1）和 Codex 第二批复核（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/README.md:94`）都倾向替换；
- 只有主审当时记为"规格歧义"。

本判断与前三者一致。

**不另做 R-f**：替换语义已经由公开 API 文档给出（§2.1 第 2 条），题面补句不是解题必需。

**退路**（只在 Codex 复核认定合并也有公开依据时使用）：
- 把 G3 测试的最后一行 `self.assertEqual(cov.get_option("paths"), new_paths)`，换成两种读法都成立的 `self.assertEqual(cov.get_option("paths")["magic"], ['src', 'ok'])`；
- M 随之得 1，"替换还是合并"改为按 P5 交用户决定；
- G1、G2 与这一分歧无关，保持不变。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`。私有原件是 `PRIV/hidden_tests/test_1.py`，父版本 sha256 为 `acae864f…`。
- **修订类别**：`hidden_test_text_replace`，一处替换。
  - `old` 是原文件第 353–355 行：`self.assertEqual(cov.get_option("paths"), new_paths)`、一个空行、`def test_tweak_error_checking(self):`。这段文本在文件中恰好出现一次。
  - `new` 在原目标测试 `test_tweaks_paths_after_constructor` 之后、`test_tweak_error_checking` 之前，插入下面 3 个方法；原两行保持不变。
- 精确的 old/new 文本见 `revision_draft.json`。按草案生成的修订后文件 sha256 为 `b4824fe1…`，正式版本以协调者落地的材料为准。

```python
    def test_tweaks_paths_on_config_object(self):
        # R2E revision (2026-09-29): configurer plugins may be handed the
        # CoverageConfig object instead of the Coverage object, so "paths"
        # must be readable and settable there too.
        cov = coverage.Coverage()
        config = cov.config
        self.assertEqual(config.get_option("paths"), OrderedDict())

        new_paths = OrderedDict()
        new_paths['remote'] = ['/local/src/', '/remote/src/']
        config.set_option("paths", new_paths)

        self.assertEqual(config.get_option("paths"), new_paths)
        self.assertEqual(cov.get_option("paths"), new_paths)

    def test_tweaks_paths_used_by_combine(self):
        # R2E revision (2026-09-29): a [paths] value set with set_option is
        # used when combining data, like the [paths] section of a config file.
        data = coverage.CoverageData(".coverage.machine1")
        data.add_lines({"/remote/src/pkg/mod.py": dict.fromkeys(range(10))})
        data.write()

        cov = coverage.Coverage()
        new_paths = OrderedDict()
        new_paths['source'] = ['/local/src/', '/remote/src/']
        cov.set_option("paths", new_paths)
        cov.combine()

        self.assertEqual(sorted(cov.get_data().measured_files()), ["/local/src/pkg/mod.py"])

    def test_tweaks_paths_replaces_config_file_paths(self):
        # R2E revision (2026-09-29): get_option("paths") retrieves the current
        # [paths] configuration, and set_option("paths", new_paths) makes
        # new_paths the new value of the option.
        self.make_file(".coveragerc", """\
            [paths]
            first =
                /first/1
                /first/2
            second =
                /second/a
                /second/b
            """)
        old_paths = OrderedDict()
        old_paths['first'] = ['/first/1', '/first/2']
        old_paths['second'] = ['/second/a', '/second/b']
        cov = coverage.Coverage()
        self.assertEqual(cov.get_option("paths"), old_paths)

        new_paths = OrderedDict()
        new_paths['magic'] = ['src', 'ok']
        cov.set_option("paths", new_paths)

        self.assertEqual(cov.get_option("paths"), new_paths)
```

**设计说明**

- **G1 直接使用 `cov.config`**，这正是 configurer 插件可能拿到的对象之一。
  - 不走"插件 + `time.time()` 奇偶"的路径，所以测试不依赖时间，也不需要 mock 时间。
  - 最后一行确认：经 `CoverageConfig` 设置的值，在 `Coverage` 这一侧也能读到。
  - 取值没有用题面示例的 `magic`。
- **被 G1 拒绝、但判为不合理的写法**：只改转发层，同时把 `control.py:276` 改成"总是把 `self` 传给插件"。那段代码的注释（`control.py:272-275`）说明随机二选一是有意为之，与本题"`paths` 选项不被识别"（`user_prompt.txt:8`）无关。请 Codex 一并核对这一点。
- **G2 用行为断言**，即真实 `combine()` 的路径重映射，不断言内部属性 `config.paths`。
  - 所以"把值存在别处、但让 combine 用上它"的实现同样能通过。
  - 写法参照公开的 `tests/test_api.py:470-511`（`test_ordered_combine`），但路径改用绝对的假路径，避免依赖临时目录的 realpath。
- **G3 从 `.coveragerc` 里的两条 [paths] 起步**：
  - 先断言 get 能取回配置文件里的值（对应题面第 16、27 行的 "retrieve the current paths configuration"）；
  - 再 set，并断言 get 等于 new_paths（替换，见 §2）。
  - 两条旧条目都与新条目不同名，所以合并实现会多出 `first`、`second` 两项。
- **不改的部分**：原目标测试 `test_tweaks_paths_after_constructor`（就是题面示例本身）和其余 43 个回归键都不改。
- **不要求的细节**：`assertEqual` 对普通 dict 也成立，所以不要求返回 `OrderedDict` 类型；不要求返回同一个对象，也不要求 `~` 展开或类型校验。A1 返回副本并做了 `expanduser`，照样通过。

## 4. 期望映射的逐键变化

| 键 | 修订前 | 修订后 |
|---|---|---|
| `ConfigTest.test_tweaks_paths_on_config_object` | 无 | PASSED（新增） |
| `ConfigTest.test_tweaks_paths_used_by_combine` | 无 | PASSED（新增） |
| `ConfigTest.test_tweaks_paths_replaces_config_file_paths` | 无 | PASSED（新增） |
| 其余 44 键 | PASSED | 不变 |

- 键集合由 44 变为 47。三个新键与已有键没有重名：它们在同一文件、同一个类 `ConfigTest` 下，方法名都是新的。
- 修订后的完整期望映射见 `revision_draft.json` 的 `expected_after`。父版本 `PRIV/expected_output.json` 的 sha256 为 `2388143c…`。

## 5. 验收计划与试跑结果

- **运行条件**：
  - 镜像 `sha256:418dca922724d01da398cd1c025ecc7c88e7223aeab06d665af89a7517c01caf`，配方 `r2e_derive_v1+sysconfig_v1`；
  - 以评分用户 uid 54322 运行，不联网；
  - 每个候选跑 1 次，测试段约 4–9 秒。
- **补丁的 sha256 前缀**：gold `0a9c0747`、W1 `51acee3f`、W2 `8a2b34e3`、A1 `8cd48b49`、M `b7e1a4d6`、N1 `612d0e7b`，与 09-25 账本一致。

| 候选 | 补丁 | 应得分 | 应失败的键 | 试跑结果 | 文件 |
|---|---|---|---|---|---|
| 环境确认：noop（当前材料） | — | 0 | 原目标键 | mismatch，只有 `test_tweaks_paths_after_constructor` 失败，原因是 `No such option: 'paths'` | `trials/env_noop_current.json` |
| 环境确认：gold（当前材料） | `PRIV/gold.patch` | 1 | — | match，44/44 | `trials/env_gold_current.json` |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | match，47/47 | `trials/rev_gold.json` |
| noop | — | 0 | 原目标键加 3 个新键 | mismatch，正是这 4 个键，原因都是 `No such option: 'paths'` | `trials/rev_noop.json` |
| A1：合理替代（set 时复制成 OrderedDict 并做 expanduser，get 返回副本） | `CANDS/coveragepy_9799_A1_copy_and_expand.patch` | 1 | — | match，47/47 | `trials/rev_A1.json` |
| W1：只改转发层（原先得 1） | `CANDS/coveragepy_9799_W1_control_layer_only.patch` | 0 | `test_tweaks_paths_on_config_object` | mismatch，只有这一个键；`CoverageException: No such option: 'paths'` | `trials/rev_W1.json` |
| W2：旁路属性（原先得 1） | `CANDS/coveragepy_9799_W2_side_attribute.patch` | 0 | `test_tweaks_paths_used_by_combine` | mismatch，只有这一个键；`['/remote/src/pkg/mod.py'] != ['/local/src/pkg/mod.py']` | `trials/rev_W2.json` |
| M：合并（原先得 1） | `CANDS/coveragepy_9799_M_merge_paths.patch` | 0 | `test_tweaks_paths_replaces_config_file_paths` | mismatch，只有这一个键；实际返回 first、second 加 magic（`test_1.py:408`） | `trials/rev_M.json` |
| N1：回归负对照（原先得 0） | `CANDS/coveragepy_9799_N1_config_file_option.patch` | 0 | 原 28 个读配置文件的键，加上新的替换键 | mismatch，29 个键：与 09-25 的 28 个键逐一相同，另加新替换键（它也要读 `.coveragerc`） | `trials/rev_N1.json` |

**对照 v1 §5 的 R-a / R-b / R-c / R-e 验收**：

- 正对照为 1、noop 为 0：满足。
- 本次要纠正的误判已被纠正：W1、W2、M 由 1 变为 0，而且各自只在对应缺口的新键上失败。
- 已知相关的错误候选仍为 0：W1、W2、M、N1 都是 0。
- 合理替代解没有被误拒：A1 得 1。
- 公开核心要求有直接断言：见 §7。
- 保存新版本、父版本、理由和触发反例：见本文 §1、§3、§4，以及 `revision_draft.json`。
- Codex 复核：待做。

## 6. 与正式评分的差别、未做的事

- **试跑工具与正式评分的差别**（见 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py` 文件头）：
  - 不做基线重建比对；
  - 不核对隐藏测试树与入口摘要；
  - 权限布置简化为把整个 `/testbed` 交给评分用户。

  所以定稿后要按正式材料重跑正式评分的 gold 和 noop，并至少再跑 W1、W2、M 中的一个，确认结果不变。
- **稳定性**：每个候选只跑了 1 次。新测试不依赖时间、随机数或网络（G1 有意绕开了 `time.time()` 的奇偶分支），属于确定性测试。
- **文件副作用**：新测试把 `.coveragerc` 和 `.coverage.machine1` 写在 `CoverageTest` 的临时目录（`$TMPDIR/coverage_test/…`）里，不碰 `/testbed`。
- **本次没有处理**：
  - K5（configurer 插件修改其它选项的既有流程）和 K6（[paths] 顺序决定 combine 结果）不在隐藏集里，gold 也没有碰到这两条路径，不属于本次的缺口；
  - 真实模型解题没有做。

## 7. 修订后仍受保护的公开要求（需求 → 断言）

| 公开要求 | 断言 |
|---|---|
| R1：get 默认返回空的 OrderedDict | 原目标键 `test_1.py:347`；G1 键（经 `CoverageConfig`） |
| R2：set 之后 get 返回新值 | 原目标键 `:353`；G1 键；G3 键 |
| R5：插件拿到 `CoverageConfig` 时同样可用 | G1 键 |
| R6：设进去的值被 combine 使用 | G2 键 |
| R7：能取回配置文件里的 [paths] | G3 键的第一处断言 |
| R4：set 是替换 | G3 键的最后一处断言 |
| K1–K4 回归：`section:option` 读写、未知选项报错、插件选项、[paths] 条目名任意 | 原 43 个回归键，未改动 |

## 8. 边界自查

- **没有扩大需求**：三处断言都落在题面标题、期望行为和公开 API 文档的一般表述上（§1、§2）。
- **没有为保住 gold 而放宽**：没有删改任何原有断言。
- **没有复制 gold 的输出当期望**：新键的期望 PASSED 来自公开要求；gold 通过是验收结果，不是期望的来源。
- **没有越界改动**：没有改题面，没有改生产代码，也没有写 `s2_r2e` 下的正式修订单和 pins。
