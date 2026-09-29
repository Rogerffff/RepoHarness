# coveragepy__97997d2c：静态审查卡

2026-09-25 · 私有主审 · 详细证据见同目录的 `analysis_before_history.md`（初判）与 `old_findings_delta.md`（历史对照）。

## 1. 目标、版本与用途

- **仓库版本**：coverage.py 5.0.5a0，base `17204597`。
- **题目**：让 `get_option("paths")` / `set_option("paths", v)` 能整段读写 `[paths]` 配置。configurer 插件拿到的对象有两种（`Coverage` 与 `CoverageConfig`），两种都要能用。
- **gold**：在 `CoverageConfig.get_option` / `set_option` 开头各加一个 `"paths"` 特判。
- **评分**：共 44 个键，全是 PASSED。只有一个目标键，其余 43 个与公开 `tests/test_config.py` 逐字相同。
- **建议用途**：`development_diagnostic`，静态候选，待 actor 验证。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一验证 |
|---|---|---|---|---|
| get 默认返回空；set 之后 get 得到新值（经 `Coverage` 对象） | 题面示例 | `ConfigTest.test_tweaks_paths_after_constructor`（唯一目标键） | 覆盖 | noop 在 get 处抛 `No such option: 'paths'`；gold 得 1（RH2 两次、M3 两次） |
| 插件拿到 `CoverageConfig` 时同样可用 | 标题 "via Plugins"；`control.py:271–276`；`plugin.py:207–219` | 无 | 缺失 | 实跑 W1 |
| set 的值被 `combine()` 使用 | `control.py:673–678`；`doc/config.rst` 的 `[paths]` 一节 | 无 | 缺失 | 实跑 W2 |
| 替换而非合并；配置文件读入的 `[paths]` 能经 get 取回 | 示例注释；"current paths configuration" | 无（测试从空起点开始） | 缺失（替换 / 合并属规格歧义） | 上游后来的目标测试（在 `ea6906b0` 工作树里）覆盖了这两点 |
| `section:option` 读写、未知选项报错、`[paths]` 条目名任意 | 公开 `tests/test_config.py` | 43 个回归键 | 覆盖 | noop 与 gold 都通过；用 N1 做负对照 |

## 3. 八方面：已查与未查

- **公开需求**：题面、源码、调用者、公开旧测试都查了。模型实际收到的消息没有捕获，记 unknown。
- **材料与初态**：哈希一致；gold 与上游 diff 逐字节相同；noop 的失败位置与题面一致。
- **测试是否测到要求**：目标键追完全链，5 个相关回归键逐条读过，其余通读。存在覆盖不足，见问题 1。
- **误拒**：没发现缺少公开依据的约束。合理替代解 A1 待实跑确认。
- **回归与 gold**：gold 满足全部公开要求（私有 gold 对照 pr1_1、pr4_2、pr7_7）。
- **开发条件**：
  - devcheck 在正式链上实测了：解释器、开发式安装、pip、无网络；三条复现命令能区分修复前后。
  - 用 `-o addopts=""` 跑 `tests/test_config.py`，43 passed。
  - 默认 addopts 的原命令形式，由旧探针在同一派生镜像上实测可用（跑的是另一个公开文件）。
  - devcheck 里 pr5_* 的 rc=4 是伪影：核对命令加了 `-p no:cacheprovider`，与 `setup.cfg` 里的 `--failed-first` 冲突。不是环境缺陷。
- **交付与评分**：投影、段内解析、独立 runner 结果一致。共享控制面问题只记适用：隐藏测试导入候选可改的 `tests/coveragetest.py`，评分时 pytest 读候选可改的 `setup.cfg`。
- **题目关系**：见问题 2。真实模型相关检查（清单 33–36）未做。

## 4. 问题

1. **目标测试覆盖不足**（清单 25）
   - 事实：唯一的目标键只经 `Coverage` 对象、从空起点做一次往返。
   - 后果：只修转发层的实现（W1）和把值存到旁路属性的实现（W2），按静态推断都会得 1，可能把不完整的修复记为成功。
   - 不受影响：gold 与评分确定性。
   - 证据级别：静态推断，高把握；待当前 CPU 实跑。
2. **同族关系与跨题暴露**（清单 5）
   - 与 `f5eb5f21` 的初始工作树逐字节相同。
   - 本题的修复和加强版目标测试已经在 `ea6906b0` 的初态里。
   - 本题初态包含 `5dbbe143`（测试辅助部分已核实）和 `016af5f6`（只有机械比对）的修复。
   - 影响：训练与评测必须按同族划分。
   - 证据级别：直接比对公开包。

**环境修复**：没有。环境轮认定 `environment_qualified` 时的条件（expected_v0 + `r2e_derive_v1` + 默认 profile）就是当前条件。

## 5. 候选（请用正式评分实跑）

- **W1（部分实现，预期 1）**
  - 改法：只改 `coverage/control.py` 的 `Coverage.get_option` / `Coverage.set_option`，各在开头加 `if option_name == "paths":` 分支——get 返回 `self.config.paths`，set 执行 `self.config.paths = value` 后 return。`coverage/config.py` 不动。
  - 预期：reward 1，44/44，没有不符的键。得 1 即确认问题 1。
- **W2（旁路存储，预期 1）**
  - 改法：只改 `coverage/config.py`。`CoverageConfig.set_option` 开头加 `if option_name == "paths": self._paths_override = value; return`；`get_option` 开头加 `if option_name == "paths": return getattr(self, "_paths_override", self.paths)`。
  - 预期：reward 1，44/44。`combine()` 不会用到设置的值。
- **A1（合理替代解，预期 1）**
  - 改法：只改 `coverage/config.py`。`set_option` 开头把 `value` 复制成 `collections.OrderedDict`，每个路径做 `os.path.expanduser`，赋给 `self.paths` 后 return；`get_option` 开头返回 `collections.OrderedDict(self.paths)`（副本）。
  - 预期：reward 1，44/44。
- **N1（负对照，预期 0）**
  - 改法：只在 `coverage/config.py` 的 `CoverageConfig.CONFIG_FILE_OPTIONS` 列表末尾加 `('paths', 'paths')`。
  - 预期：目标键 PASSED。凡是成功读入配置文件的回归键都 FAILED，静态推断共 28 个，例如 `ConfigTest.test_config_file`、`ConfigFileTest.test_config_file_settings`。原因是 `where.split(":")` 拆包失败。
- **M（可选，预期 1）**：set 改成 `self.paths.update(value)`，其余同 gold。测试从空起点开始，无法区分替换与合并。

## 6. 建议、复核与下一步

- **处置**：`needs_review`，理由是静态候选待 actor 验证，scope 为 `static_review`。
- **使用条件**：
  - 不修订也能作诊断题使用。
  - 要作为能区分插件路径的 reward，可以按问题 1 补强目标测试。这属于改测试标准，需用户决定。
  - 通过的真实解要检查补丁是否改在 `CoverageConfig`。
  - 与同族题放在同一划分。
- **与历史的分歧**：环境结论全部一致。本卡新增两项问题；旧 R03 的"输入 pass"改为 unknown，旧 conda 措辞已过时。
- **独立复核**：尚无。
- **唯一优先下一步**：实跑 W1。
