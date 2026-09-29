# coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266：公开读者报告

角色：公开读者（静态审查，不解题）。只读了角色卡和 PUBLIC_DIR 下的文件；没有运行项目代码，也没有联网。下文路径都相对于 PUBLIC_DIR，`worktree/` 就是解题者看到的 `/testbed`。

**一句话概括**：题目要求 `get_option("paths")` / `set_option("paths", ...)` 能整段读写 `[paths]` 配置。选项名就是 `"paths"`，不带 `section:` 前缀。base 上，`CoverageConfig.get_option` / `set_option` 只认 `CONFIG_FILE_OPTIONS` 里的 `section:option` 和插件选项，所以 `"paths"` 在两处都落到 `raise CoverageException("No such option: %r" % option_name)`（`worktree/coverage/config.py:439`、`:463`）。`Coverage` 的同名方法只是转发给 `self.config`（`worktree/coverage/control.py:375`、`:400`）。

---

## 1. 需求表

| # | 需求 | 类别 | 依据 |
|---|---|---|---|
| R1 | `Coverage().get_option("paths")` 不再抛异常，返回当前的 paths 配置；没有配置文件时返回空 `OrderedDict` | 明示 | `user_prompt.txt:16-17,27`；默认值见 `worktree/coverage/config.py:231`，构造末尾会重建为 `OrderedDict`（`config.py:542-545`） |
| R2 | `set_option("paths", new_paths)` 不再抛异常；之后 `get_option("paths")` 返回与 `new_paths` 相等的 `OrderedDict` | 明示 | `user_prompt.txt:19-23,27` |
| R3 | 选项名就是 `"paths"`（整段），不是 `section:option` 形式 | 明示（接口由示例固定） | `user_prompt.txt:16,21`；现有 docstring 把 option_name 写成冒号分隔（`control.py:366-368,380-382`，`config.py:417-419,444-446`） |
| R4 | set 是替换语义：设置后得到的就是 `new_paths`，不与旧值合并 | 明示倾向 | `user_prompt.txt:23` 的注释 "Expected to output the new_paths OrderedDict"；其它选项的 set 也是整体 `setattr`（`config.py:426-430`）。示例起点为空，替换和合并在示例里分不出来；只有原来已有 `[paths]` 时才有差别 |
| R5 | configurer 插件可能拿到两种对象：`Coverage` 和 `CoverageConfig`，修复对两者都要生效 | 可推知 | 标题和描述都针对插件（`user_prompt.txt:5,8,34`）；`_init()` 按当前秒的奇偶把 `self` 或 `self.config` 传给 `plugin.configure`（`control.py:270-276`）；插件文档只承诺该对象有 `get_option` / `set_option`（`worktree/coverage/plugin.py:207-219`） |
| R6 | 用 set 设进去的值要真正被 `combine()` 使用（即体现在 `config.paths`），并保持条目顺序 | 可推知 | `combine()` 在调用时才读 `self.config.paths` 构造 `PathAliases`（`control.py:672-680`）；条目顺序影响合并结果（`worktree/tests/test_api.py:470-511`，注释引 issue 649） |
| R7 | 从配置文件读到的 `[paths]`（含 `setup.cfg`/`tox.ini` 的 `[coverage:paths]` 和 TOML）也能通过 `get_option("paths")` 读到 | 可推知 | "retrieve the current paths configuration"（`user_prompt.txt:27`）；读取逻辑见 `config.py:306-310`，`~` 展开见 `config.py:542-545` |
| K1 | 保留：已有 `section:option` 的读写 | 保留（公开测试） | `worktree/tests/test_config.py:330-341` |
| K2 | 保留：未知选项仍抛 `CoverageException("No such option: ...")`，例如 `run:xyzzy`、`xyzzy:foo`、`no_such.plugin:foo` | 保留（公开测试） | `test_config.py:343-353,361-367`；实现在 `config.py:439,463` |
| K3 | 保留：插件选项 `plugin.name:key` 的读写 | 保留（公开测试） | `test_config.py:355-367`；`config.py:432-436,457-460` |
| K4 | 保留：配置文件的 `[paths]` 可以用任意条目名，不会触发 "Unrecognized option" | 保留（公开测试） | `config.py:290-310`；`test_config.py:261-296,474-479,547-550`；`test_api.py:489-511` |
| K5 | 保留：configurer 插件修改 `report:exclude_lines` 的既有流程 | 保留（公开测试） | `worktree/tests/plugin_config.py:9-22`；`worktree/tests/test_plugins.py:874-886` |
| K6 | 保留：`[paths]` 的顺序决定 combine 结果 | 保留（公开测试） | `test_api.py:470-511` |

**有多种合理解释的点**（题面都没说）：

- **A1 返回活对象还是副本**：`get_option("paths")` 可以返回 `config.paths` 本身（原地修改立即生效），也可以返回副本。现有其它选项返回的是属性本身（`config.py:452-455`）。`tests/plugin_config.py:13-17` 的写法是"取出、原地改、再 set"，两种语义都兼容。
- **A2 set 时的值处理**：是否复制、转成 `OrderedDict`、校验类型（比如传普通 `dict`、`None`、值不是 list），都没有约定。题面只给了 `OrderedDict` 输入。
- **A3 set 时是否做 `os.path.expanduser`**：构造时只对配置文件读到的值展开一次（`config.py:537-545`），set 进来的值要不要展开没有约定。这只影响含 `~` 的值。
- **A4 是否支持单条目名**，例如 `"paths:source"`。base 上它会进入插件分支，因为 `plugin_name="paths"` 不在 `plugins` 里，最后抛错（`config.py:457-463`）。题面没有要求。
- **A5 不带冒号的其它未知名字**（例如 `"xyzzy"`）：自然的推断是继续报 "No such option"，与 K2 一致；但公开测试没有覆盖不带冒号的情况。
- **A6 文档是否更新**：docstring（`control.py:363-400`、`config.py:414-450`）、`worktree/doc/config.rst:218-249`、`worktree/CHANGES.rst:24-31` 的 Unreleased 条目都可以改，也可以不改；公开测试不检查。

## 2. 合理实现范围

下面只列应当接受的做法和必须满足的约束，不给修复。

- **实现位置**：
  - 在 `CoverageConfig.get_option/set_option`（`config.py:414-463`）里识别 `"paths"`，`Coverage` 的转发会自动受益。
  - 也可以把"整段型选项"抽象成通用机制。
  - 以上两种都满足 R1-R6。
  - **只改 `Coverage.get_option/set_option`**（`control.py:363-400`）也能让题面示例通过。但插件拿到 `CoverageConfig` 时仍会失败，这取决于 `int(time.time()) % 2`（`control.py:276`），大约一半的运行会碰到，与题目的插件动机（R5）不符。我认为这是最容易出现的"示例通过、实际不完整"的实现。
- **值语义**：
  - set 时存原对象、浅拷贝、深拷贝或转成 `OrderedDict(value)` 都符合题面，前提是 `get_option("paths")` 返回与传入值相等、顺序一致的 `OrderedDict`。
  - 返回普通 `dict` 虽然与 `OrderedDict` 比较相等，但与题面 "return the updated `OrderedDict`"（`user_prompt.txt:27`）字面不符。另外仓库仍声明支持 Python 2.7/3.5（`worktree/setup.py:28-35,122`），在这些版本里普通 dict 不保证顺序，与 R6 冲突。
- **命名**：`"paths"` 已由题面固定。额外支持 `"paths:<name>"` 属于可选扩展，不应作为要求。
- **错误信息**：题面只要求 `"paths"` 不再报错。其它名字要保持 `No such option: %r` 格式，因为 K2 的公开测试用正则匹配这条消息。
- **任何实现都必须满足的结构约束**：
  - `CONFIG_FILE_OPTIONS` 每项的第二个元素，在 `from_file` 和 `_set_attr_from_config_option` 里都会按 `":"` 拆成两段（`config.py:293`、`:403`）。不带冒号的条目会让读取任何配置文件时出现拆包错误。
  - `from_file` 会对 `CONFIG_FILE_OPTIONS` 中出现过的每个 section 做未知键检查（`config.py:290-304`）。如果 `paths` 这个 section 进入这张表，`[paths]` 下的任意条目名（`source`、`other`、`mapping` 等）都会被判成 "Unrecognized option"，破坏 K4。
  - `read_coverage_config` 在构造末尾会重建 `config.paths`（`config.py:542-545`），而 `combine()` 读的是 `self.config.paths`（`control.py:673-678`）。如果把值存到别的地方，两者要保持一致，否则 R6 失效。
- 除了"在 get/set 里对 `paths` 做特殊分支"或与之等价的通用机制，我想不出本质不同的实现路径。

## 3. 题面质量与初态线索

### 题面质量（R2E 自动生成的题面）

1. **是否泄露修法**：示例代码是修复后应当能跑通的用法。它固定了接口（名字 `"paths"`，值是"名字到路径列表"的 `OrderedDict`），但没有给出实现。"the `paths` option is not recognized"（`user_prompt.txt:8`）把问题指向选项查找逻辑，属于正常的提示强度，不算直接泄露。
2. **报错能否从 base 源码读出**：能。set（`config.py:439`）和 get（`config.py:463`）都用 `"No such option: %r" % option_name` 抛 `CoverageException`。这个类定义在 `worktree/coverage/misc.py:325`，完整名 `coverage.misc.CoverageException`，与 `user_prompt.txt:32` 一致。
   - **小偏差**：题面说异常在"attempting to set"时抛出（`user_prompt.txt:29-33`），但按示例顺序，最先失败的是第 16 行的 `cov.get_option("paths")`，`set_option`（第 21 行）根本执行不到。
   - base 上 get 和 set 都会失败，这个偏差不影响开发。
3. **示例在 base 接口下是否说得通**：说得通。
   - `Coverage()`、`get_option`、`set_option` 都存在（`control.py:99,363,377`），`OrderedDict` 也与内部类型一致（`config.py:231`）。
   - 注释 "Should output an empty OrderedDict"（`user_prompt.txt:17`）有两个前提：当前目录下没有带 `[paths]` 的配置文件，并且没有设置 `COVERAGE_RCFILE`。
   - 在 `/testbed` 下，`.coveragerc` 和 `pyproject.toml` 都不存在；`worktree/setup.cfg` 和 `worktree/tox.ini` 全文没有 `coverage:` 段。
   - `worktree/metacov.ini` 末尾虽然有 `[paths]`，但只有 `COVERAGE_RCFILE` 指向它时才会被读。
   - 所以静态推断成立；容器里的环境变量未知。
4. **标题与示例的落点不同**：标题说 "via Plugins"，示例却只用 `Coverage` 对象。插件实际可能拿到的是 `CoverageConfig`（`control.py:270-276`），题面没有提，但读一下调用处就能发现，不算缺陷。
5. 题面对 A1-A6 都没有说明。其中 A1 和 A2 会影响行为细节，但都不阻碍开发。

### 调查入口

- 搜 "No such option" 会直接定位到 `config.py:439,463`。
- `control.py:363-400` 是转发层。
- `control.py:267-276` 和 `plugin.py:74-87,207-219` 说明 configurer 机制。
- `tests/test_config.py:330-367` 是现成的 get/set 用例写法；`tests/plugin_config.py` 是 configurer 插件样例。
- `control.py:645-680` 和 `tests/test_api.py:470-511` 说明 paths 如何被消费。

公开材料足以定位和复现问题，没有真正阻碍开发的信息缺口。

### 初态线索

- **工作树组成**：`worktree_manifest.json` 显示 `initial_diff` 为 0 字节，即工作树就是 base 提交 `17204597c33d` 的跟踪文件，加上未跟踪的 `run_tests.sh`。
- **不在工作树里的东西**：`install.sh` 存在于镜像中但没有包含进来（`untracked_missing`）；`.venv`、编译产物（`*.so`、`*.egg-info`）和隐藏测试也不在工作树里。
- **评分入口**：`worktree/run_tests.sh` 运行 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests/` 不在工作树中，解题者跑不了，对理解题意没有影响。
- **与本题无关的既有小瑕疵**：`CONFIG_FILE_OPTIONS` 里有 `('sort', 'report:sort')`（`config.py:379`），但 `__init__` 没有 `self.sort` 默认值（`config.py:201-213`）。因此默认配置下 `get_option("report:sort")` 会抛 `AttributeError`，而不是 `CoverageException`；`worktree/coverage/summary.py:106` 用 `getattr(..., None)` 绕开了它。只有解题者自测时"遍历所有选项"才会碰到，不属于本题需求。
- **`public_hints` 分三类**：
  - **题目需求**：修复这个 issue，只改非测试源码（"edit NON-TEST source files to fix the issue"）。
  - **给解题者的操作指令**：
    - 先探索、找根因再修。
    - 不要改仓库测试文件。
    - 测试要跑得窄。
    - 在 `/testbed` 下用 `python -m pytest`。
    - 完成后简短总结并停止调用工具。
  - **环境事实声明**：
    - 仓库在 `/testbed`，bash 已经在这个目录。
    - `/testbed/.venv` 是运行环境，`python` 和测试工具都已指向它。
    - 没有网络。
    - `pip` 可能不可用；`environment_brief.md:11` 说得更具体：pip 有，但不能出网，装不了新包。
    - 由另一组测试判分。`public_bundle.json` 的 `allowed_tools` 是 `bash`、`edit`。
  - **对合法解法的影响**：
    - 不能靠修改 `tests/plugin_config.py`，或在 `tests/` 里加插件来"修"。
    - 复现脚本应放在 `tests/` 之外，比如 `/tmp`。
    - `python -m pytest` 会读 `setup.cfg` 的 `addopts`（见第 4 节 D4），这会影响本地测试能否直接跑起来，但不影响修复本身。

## 4. 开发需求表

所有命令都是**建议，未执行**，可以在 `/testbed` 下原样运行。

| # | 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 |
|---|---|---|---|---|
| D1 | 用 .venv 的 Python 3.7 导入 `/testbed` 下的 coverage 源码 | `public_hints`；`environment_brief.md:10` | 已实测声明解释器路径和版本（3.7.9） | coverage 在 .venv 里是 editable 安装还是拷贝安装未知，因为 `install.sh` 不在工作树里。在 `/testbed` 下用 `python -c` 或 `python -` 运行时，`sys.path[0]` 是当前目录，总会导入工作树的代码；在别的目录运行则取决于安装方式 |
| D2 | 复现并验证 get/set（主命令，能区分修复前后） | 题面示例；`config.py:414-463`；`control.py:363-400` | 只需要 D1 | 无 |
| D3 | 走一遍 configurer 插件的端到端路径 | `control.py:267-276`；`plugin.py:207-219`；`tests/plugin_config.py` | D1，加上可写的临时目录 | 插件拿到哪个对象随当前秒的奇偶变化，需要 D2 做确定性的补充 |
| D4 | 跑公开回归测试 | `worktree/setup.cfg:1-2`：`addopts = -q -n3 --strict --no-flaky-report -rfe --failed-first`；`worktree/requirements/pytest.pip`：pytest 4.6.6、pytest-xdist 1.30.0、flaky 3.6.1、mock 3.0.5、unittest-mixins 1.6、hypothesis；`tests/test_config.py:7` 有 `import mock`；`tests/coveragetest.py:19-22` 用了 `unittest_mixins` | 只说明有 pip、不能出网、装不了新包；**没有列出已安装的包** | 见表后说明 |
| D5 | （可选）验证 set 进去的 paths 被 `combine()` 使用 | `control.py:645-680`；`worktree/coverage/data.py:55-120`；`worktree/coverage/sqldata.py:550-576`；`test_api.py:470-511` | 需要可写临时目录：`/tmp` 有 1 GiB（`environment_brief.md:12`） | 如果 `/tmp` 是符号链接，别名匹配可能对不上（`worktree/coverage/files.py:162-165` 用了 realpath），结果会偏离预期 |
| D6 | 网络、外部服务、GPU | 本题不需要 | 不能出网 | 无 |
| D7 | C tracer 扩展 | `worktree/coverage/ctracer/` 只有源码，`*.so` 被 `.gitignore` 排除 | 未说明 | 是否已编译未知。本题只涉及配置，退回到 PyTracer 即可，不受影响 |

D4 的缺口说明：

- 未知 pytest-xdist、flaky、mock、unittest-mixins、toml 是否装在 .venv 里。
- `run_tests.sh` 同样在 `/testbed` 调 pytest，会读到同一份 `addopts`，间接说明 xdist 和 flaky 大概率已装。这是推断，未验证。
- `toml` 是可选 extra（`setup.py:97-99`）。如果没装，`test_config.py` 里 5 个 TOML 用例在 base 上就会失败，与本题无关。

### D1 环境核对（建议，未执行）

```bash
(cd / && python -c "import sys, coverage; print(sys.version.split()[0], coverage.__file__, coverage.__version__)")
```

- **editable 安装时预期**：`3.7.9 /testbed/coverage/__init__.py 5.0.5a0`（版本号来自 `worktree/coverage/version.py:8`）。
- **路径在 `site-packages`**：说明是拷贝安装，在 `/testbed` 之外运行的脚本看不到修改。
- **报 ImportError**：说明 .venv 没有安装 coverage，只能在 `/testbed` 下运行。

下面各条命令都固定在 `/testbed` 下运行，或显式把 `/testbed` 放进 `sys.path`，所以不受安装方式影响。

### D2 主命令：通过公开 API 区分修复前后（建议，未执行）

```bash
cd /testbed && python - <<'EOF'
from collections import OrderedDict
import coverage
print("coverage from:", coverage.__file__)
for label, obj in [("Coverage", coverage.Coverage()), ("CoverageConfig", coverage.Coverage().config)]:
    try:
        print(label, "before:", repr(obj.get_option("paths")))
        new_paths = OrderedDict()
        new_paths["magic"] = ["src", "ok"]
        obj.set_option("paths", new_paths)
        print(label, "after:", repr(obj.get_option("paths")))
    except Exception as exc:
        print(label, "ERROR:", type(exc).__module__ + "." + type(exc).__name__ + ":", exc)
EOF
```

修复前预期（原 bug）：

```
coverage from: /testbed/coverage/__init__.py
Coverage ERROR: coverage.misc.CoverageException: No such option: 'paths'
CoverageConfig ERROR: coverage.misc.CoverageException: No such option: 'paths'
```

修复后预期（按题面）：

```
coverage from: /testbed/coverage/__init__.py
Coverage before: OrderedDict()
Coverage after: OrderedDict([('magic', ['src', 'ok'])])
CoverageConfig before: OrderedDict()
CoverageConfig after: OrderedDict([('magic', ['src', 'ok'])])
```

判读：

- 如果只有 `Coverage` 两行成功、`CoverageConfig` 仍报错，说明只改了转发层（见第 2 节）。
- 如果 `after` 打印成 `{'magic': ['src', 'ok']}`，说明返回的是普通 dict，与题面字面不符。
- `before` 为空的前提见第 3 节"题面质量"第 3 点。

### D3 端到端 configurer 插件（建议，未执行）

```bash
cd /testbed && python - <<'EOF'
import os, sys, tempfile, textwrap
import coverage
plugin_dir = tempfile.mkdtemp()
with open(os.path.join(plugin_dir, "paths_configurer.py"), "w") as f:
    f.write(textwrap.dedent("""
        from collections import OrderedDict
        import coverage

        class Plugin(coverage.CoveragePlugin):
            def configure(self, config):
                print("configure() got:", type(config).__name__)
                paths = OrderedDict(config.get_option("paths"))
                paths["magic"] = ["src", "ok"]
                config.set_option("paths", paths)

        def coverage_init(reg, options):
            reg.add_configurer(Plugin())
        """))
sys.path.insert(0, plugin_dir)
cov = coverage.Coverage(data_file=None)
cov.set_option("run:plugins", ["paths_configurer"])
cov.start()
cov.stop()
print("paths after start:", repr(cov.get_option("paths")))
EOF
```

- **修复前预期**：
  - 先打印 `configure() got: Coverage` 或 `configure() got: CoverageConfig`，取决于当前秒的奇偶（`control.py:276`）。
  - 然后 `cov.start()` 抛出 traceback，最后一行是 `coverage.misc.CoverageException: No such option: 'paths'`。
- **修复后预期**：打印 `configure() got: ...` 之后，再打印 `paths after start: OrderedDict([('magic', ['src', 'ok'])])`。
- `data_file=None` 让数据只留在内存里，不会往 `/testbed` 写 `.coverage`（`control.py:180-184`）。
- 如果实现只改了转发层，这条命令的结果会随秒数变化，可以隔几秒多跑几次。

### D4 公开回归测试（建议，未执行）

```bash
cd /testbed && python -m pytest tests/test_config.py
cd /testbed && python -m pytest tests/test_plugins.py -k ConfigurerPluginTest
cd /testbed && python -m pytest tests/test_api.py -k test_ordered_combine
```

如果报 `unrecognized arguments: -n3` 或 `--no-flaky-report`，说明 xdist 或 flaky 没装。这时加 `-o addopts=""` 清掉 `setup.cfg` 里的 addopts：

```bash
cd /testbed && python -m pytest -o addopts="" -rfe tests/test_config.py
```

预期：

- 修复前后都应当通过。这些用例不读写 `"paths"` 选项，所以**不能区分修复前后**，只用来守住 K1-K6。
- 建议改动前先跑一次基线，以区分环境问题和修复造成的失败：
  - 如果 `toml` 没装，以下用例可能在 base 上就失败，属于环境问题，不是修复造成的：`test_toml_config_file`、`test_toml_parse_errors`、`test_environment_vars_in_toml_config`、`test_tilde_in_toml_config`、`test_unknown_option_toml`。
  - 如果 `mock` 或 `unittest_mixins` 没装，整个文件会在收集阶段报 ImportError。

### D5 可选：set 进去的 paths 是否被 combine 使用（建议，未执行）

```bash
cd /testbed && python - <<'EOF'
import os, sys, tempfile
sys.path.insert(0, "/testbed")
from collections import OrderedDict
import coverage
os.chdir(tempfile.mkdtemp())
data = coverage.CoverageData(".coverage.1")
data.add_lines({os.path.abspath("ci/girder/g1.py"): dict.fromkeys(range(10))})
data.write()
cov = coverage.Coverage(config_file=False)
new_paths = OrderedDict()
new_paths["girder"] = ["girder/", "ci/girder/"]
try:
    cov.set_option("paths", new_paths)
except Exception as exc:
    print("set_option ERROR:", exc)
cov.combine()
print(sorted(os.path.relpath(f) for f in cov.get_data().measured_files()))
EOF
```

- **修复前预期**：先打印 `set_option ERROR: No such option: 'paths'`，然后打印 `['ci/girder/g1.py']`（没有应用别名）。
- **修复后预期**：`['girder/g1.py']`。`ci/girder/` 被映射成 `girder/`，与 `test_api.py:487-498` 第 1 种情况是同一机制。
- 所有文件都写在新建的临时目录里。

## 5. 阅读范围

实际打开的文件：

- 角色卡 `r2e_static_review_batch2_20260925/roles/public_reader_r2e.md`。
- `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`。manifest 只看了顶层字段和 `tests/` 的文件列表，没有打开其中指向 PUBLIC_DIR 以外的路径，例如 `initial_diff.source`。
- `worktree/coverage/`：
  - 全文：`config.py`、`plugin_support.py`、`tomlconfig.py`、`optional.py`、`version.py`。
  - 部分：`control.py`（1-420、500-560、640-726，以及 grep）、`plugin.py`（1-240）。
  - 只看 grep 结果和片段：`env.py`、`misc.py`、`summary.py`、`files.py`、`data.py`、`sqldata.py`、`cmdline.py`。
- `worktree/tests/`：
  - 全文：`test_config.py`、`plugin_config.py`、`conftest.py`、`__init__.py`。
  - 部分：`test_plugins.py`（1-110、860-900，以及 grep）、`test_api.py`（455-524，以及 grep）、`coveragetest.py`（17-126）。
  - 只看导入或 grep：`helpers.py`（导入部分）、`test_cmdline.py`（grep）。
- `worktree/` 下其它文件：
  - 全文：`run_tests.sh`、`setup.cfg`、`tox.ini`、`requirements/pytest.pip`、`metacov.ini`、`.gitignore`。
  - 部分：`CHANGES.rst`（1-80）、`doc/config.rst`（36-105、190-259）、`doc/cmd.rst`（258-300）。
  - 只看 grep：`setup.py`、`igor.py`。

没有查的范围：

- `worktree/lab/`、`perf/`、`ci/`。
- `doc/` 的其余文件、`coverage/htmlfiles/`、`coverage/ctracer/` 的 C 源码、其余测试文件。
- 上游仓库的后续提交、隐藏测试、gold 补丁和任何私有材料。

限制：

- `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获到的模型实际消息。
- `worktree/` 不是完整的运行容器：缺 `.venv`、编译产物、`install.sh` 和隐藏测试。上面所有"修复前 / 修复后预期"输出都是读代码推出来的，没有实际运行。
- 没有验证模型的实际消息、容器资源和已安装的包，也没有验证任何开发条件。
