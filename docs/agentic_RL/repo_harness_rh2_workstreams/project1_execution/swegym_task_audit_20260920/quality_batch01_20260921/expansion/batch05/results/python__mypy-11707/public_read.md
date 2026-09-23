# python__mypy-11707 公开视角审读

本审读只使用本题公开包与指定公开读者角色卡，未读取私有评分材料、修复、历史或旧结论。以下引用均相对于 `runs/swegym_quality_batch05_20260921_v1/public/python__mypy-11707/`；`public_bundle.json` 是单行 JSON，以 `:1` 加字段名定位。本文没有执行项目导入、复现、测试、安装或构建。

公开材料足以定位调查入口，但存在一项实质性的语义冲突：issue 明示希望 `from a import Y as W` 与 `from a import X as W` 都允许再导出；base 的命令行文档明确说改名的 `from foo import bar as bang` 不会再导出。不能把“消除不一致”自动解释成两者都接受或两者都拒绝，也不能把已有代码当成覆盖 issue 明示预期的授权。

## 1. 需求表

| 需求或兼容边界 | 公开依据 | 确定程度与解释 |
| --- | --- | --- |
| 使用四文件示例，在严格模式关闭隐式再导出后，`d.py` 仍能导入 `c.W`；把 `c.py` 的 `Y as W` 改为 `X as W` 也应被接受。 | `user_prompt.txt:10–70`，尤其 `:46–50`、`:61–70`。 | **issue 明示。** 这是报告者希望的结果，不只是“诊断一致”。两个分支都无类型错误是字面目标。 |
| 实际选项是 `--no-implicit-reexport`，不是标题中的 `--no-explicit-reexport`。 | `user_prompt.txt:3–6,49,56,77`；`base/mypy/main.py:670–673`。 | **可由公开接口确定。** 标题有误称，正文与源码足以消歧，不妨碍复现；没有依据要求新增一个拼错的选项。`--strict` 已把这个选项列为严格检查的一部分。 |
| 普通 `.py` 文件默认允许隐式再导出；关闭后普通无别名导入不应自动对外导出。 | `base/mypy/options.py:172–173`；`base/docs/source/command_line.rst:556–561`；`base/test-data/unit/check-flags.test:1541–1549`。 | **公开仓库可合理推知的旧契约。** 不应为了四文件示例全局打开隐式再导出。 |
| 同名显式别名 `from foo import bar as bar` 与 `__all__` 是已有的显式导出途径。 | `base/docs/source/command_line.rst:568–576`；`base/docs/source/config_file.rst:592–610`；`base/mypy/semanal.py:530–541,1841–1845`；`base/test-data/unit/check-flags.test:1551–1587`。 | **明确旧契约。** 必须保留同名别名、`__all__`、普通文件星号导入受隐式导出开关约束等区别。普通改名别名与同名别名不等价。 |
| 关闭隐式再导出时，改名的 `from foo import bar as bang` 不再导出。 | `base/docs/source/command_line.rst:568–572` 直接举反例；`base/mypy/semanal.py:1844–1845` 只把同名 `as` 标为 public。 | **与 issue 明示预期冲突。** 配置文档 `base/docs/source/config_file.rst:598–599` 和 CLI 帮助 `base/mypy/main.py:672` 的简写“from-as / unless aliased”容易误读，但命令行文档示例已说明限制。 |
| `.pyi` 的普通导入与改名导入默认不再导出，同名别名可导出。 | `base/test-data/unit/check-modules.test:1819–1840` 同时检查 `C as C` 可用、`C as D` 不可用；`:1842–1877,2878–2888` 涉及成员访问与缺失来源；`base/docs/source/config_file.rst:599–600`。 | **明确公开测试契约。** issue 未要求改变 stub 规则。若为 `.py` 扩展别名导出，不应未经说明一并改写 `.pyi` 语义。 |
| 真正的包子模块仍可作为子模块访问，不能把所有非 public 导入一律隐藏。 | `base/test-data/unit/check-modules.test:1879–1911`：包 stub 内 `from . import submod` 后，外部导入子模块、`mod.submod.C()` 均可用；`:1913–1930` 区分子模块中的类是否显式导出。 | **可由现有公开测试推知的兼容边界。** 本题碰到了“类名与子模块名重合”；应同时检查实际模块对象与普通类/别名。 |
| 导入目标的类型和正常使用须保持正确，不能通过把目标变成 `Any` 或只消掉错误消息满足示例。 | `base/mypy/semanal.py:1870–1878,1921–1925,4702–4713`；`base/test-data/unit/check-modules.test:1824–1827,1883–1885,1917–1920`。 | **公开接口与测试可合理推知。** 错误是否出现与导入后符号仍是什么类型是两项观察。 |
| 非包形式也存在错误；是否要让非包形式都通过，以及一般改名导入应扩展到哪些范围。 | `user_prompt.txt:72` 只有一句描述，没有非包文件完整布局；`:70` 的“两者都接受”紧跟包示例。 | **范围仍有解释空间。** 可以构造等价普通模块例子调查，但不能把未给定的每一种非包布局都当明示验收要求。 |
| 错误文本与缓存结果应保持一致的既有含义。 | `base/mypy/semanal.py:1939–1952`；`base/test-data/unit/check-flags.test:1549,1609,1627,1648`；`base/mypy/nodes.py:3239–3242,3277–3280`；`base/test-data/unit/check-incremental.test:5589–5612`。 | **保留既有行为的合理要求。** 原错误已有 `ATTR_DEFINED` 类别；拒绝路径不应无关更名。issue 的“四个源文件”是给定布局下的摘要，不是新输出协议。冷/热缓存的具体结果仍待运行。 |

## 2. 合理实现范围

不需要指定一个函数名、变量名、文件布局或精确补丁。公开调用链允许在导入符号可见性计算处局部调整，或把相关判定收敛到内部辅助逻辑；只要对外语义、符号类型、合法子模块导入、`__all__` 和缓存行为一致，这些组织方式都应可接受。也可以同步澄清两处文档与 CLI 帮助，避免“任意 `as` 都算显式导出”的误读。这里未编写修复。

公开材料支持两种不同的需求解释，但它们不能在没有语义裁决时互相替代：

1. **按 issue 的预期扩展普通源文件导出规则。** 四文件示例两种 `c.py` 均通过。需要明确这是对 base 中“只有同名 `as` 才显式导出”的规则变更，并交代普通模块与 stub 的范围；文档应与结果一致。若只改普通 `.py` 的规则，可以保留 `.pyi` 现有公开测试，不能声称所有别名的统一扩展都与旧测试兼容。
2. **按已有仓库契约修复偶然放行。** 两种改名导入都保持不可再导出，同时保留真正子模块与显式导出的合法行为，并解释正确的导出写法。这是根据 base 文档、源码和 stub 测试可以提出的合理维护路线，但它直接不满足 `user_prompt.txt:70` 的字面预期，不能未经澄清宣称已满足 issue。

因此，开发者真正需要的一项共享输入是“本题最终要扩展别名导出规则，还是按现有规则消除偶然放行”。若有现成的公开 issue 澄清，可仅补这段不含未来修复的公开内容；无须提供隐藏测试或标准补丁。仅改文档不能消除已报告的行为不一致；仅改四文件示例的名字或添加 `__all__` 是使用方绕行，不是库本身的修复。将所有导入视为 public、屏蔽诊断、或丢失实际类型，都不应算满足兼容边界。

已有命名约定确实包括 `--no-implicit-reexport`、配置键 `implicit_reexport`、`__all__` 和“相同导入名/别名”的比较。内部 helper 名称与算法没有公开固定约定。

## 3. 初态线索与疑义

**定位入口充足。** 题面给了四个文件的全部内容、命令、预期、报错位置及仅替换一行的对照。最小示例不依赖第三方业务库、网络服务、模型或数据集。阅读已有调用者即可进入下面的路径，这属于正常调查，不是题面缺陷：

- `base/mypy/fastparse.py:903–914` 保留导入名与别名，生成 `ImportFrom`；`base/mypy/nodes.py:393–409` 将节点交给 `visit_import_from`。
- `base/mypy/build.py:755–785` 会检查导入名字是否对应文件中的子模块，并加入依赖；`:3124–3140` 调用语义分析。`base/mypy/semanal_main.py:66–85,299–331` 最终进入 `refresh_partial`；`base/mypy/semanal.py:389–422` 遍历顶层语句并应用 `__all__`。
- `base/mypy/semanal.py:1817–1885` 解析来源模块和符号、决定 `module_public`，再由 `process_imported_symbol` 写入符号表。`:1895` 的隐藏判定取决于导入全名是否在 `self.modules` 中，`:4702–4713` 将可见性存入新符号。
- 在题面布局下，存在 `a.X` 子模块而没有 `a.Y` 子模块；即便被导入的值是类或别名，其全名是否撞上模块表仍可能不同。这一分支是与报告现象直接吻合的静态线索，不是已运行确认的根因。不得仅凭包名判断导入值实际是什么；真正子模块的可见性有上述公开测试保护。
- 后续 `from c import W` 在 `base/mypy/semanal.py:1870–1878` 检查 `module_hidden`，报错实现位于 `:1927–1955`。`base/mypy/nodes.py:3138–3142` 区分 `module_public`（星号导入）和 `module_hidden`（不对外导出）；两者不能混用。限定名访问也在 `base/mypy/semanal.py:4351–4375,4389–4418` 检查可见性。

**初态版本不能只按报告者环境认定。** 报告者用 mypy 0.910、Python 3.10、Manjaro（`user_prompt.txt:74–80`）；指定 base 的 `base/mypy/version.py:8` 为 `0.920+dev`。`base_identity.json:3–15` 声明导出了指定 commit 的 1747 个跟踪 blob，且无 gitlinks、LFS 未实化指针或导出的 Git 元数据。这说明当前公开源码是什么，不证明报告者输出在真实 actor 中已重现。需要在指定 base、actor 解释器上先记录两种示例的初态。

**真正未决与一般开发工作分开：**

| 项目 | 判断 |
| --- | --- |
| issue 预期与当前文档规则冲突 | 会影响“正确结果是什么”；应在共享需求层登记，不能由测试通过替代语义说明。 |
| 真实 Python、conda 激活、依赖版本、源码与编译产物优先级、actor 写权限 | 运行条件未核验；可能阻碍实际导入或测试，需要窄 CPU 验证。不是公开材料已经证明的故障。 |
| 现有测试没逐字包含该四文件例子 | 常见新增回归场景，不妨碍定位；已有 flags/stub/submodule 测试提供相邻兼容边界。 |
| 非包例子的完整内容缺失 | 不阻碍主四文件例子；会影响其精确扩展范围。可先用等价普通模块调查，不能冒充报告者的原始非包复现。 |
| 阅读模块解析、可见性与类型信息 | 正常代码调查，公开源码已经提供入口。 |
| 外链与祖先历史 | README/开发指南包含外链，但这次所需的选项文档、安装说明和测试使用方法在本地已有；没有发现必须联网才能理解主例的资产缺口。未访问外链、历史或共享镜像。 |

**issue、harness 指令、环境声明分别记录。** `public_bundle.json:1/problem_statement` 重复 issue；`public_hints` 要求探索并修改 NON-TEST 源码、禁止改测试、允许窄测试、最后简述停工，这是原操作指令；“testbed conda 已激活”“bash 已在 /testbed”属于待验环境声明。`environment_brief.md:20–26` 明确要求核对原禁止改测试指令本次是否适用，并说明“全部测试改动恢复、永不计分”不能代表当前机制：目前没有按测试文件名统一排除，仍有官方文件恢复等具体限制。本审读不判断哪些文件会恢复，也不自行解除原指令。

- 若禁止改测试适用：可以调查并修复非测试源码，运行已有窄测试；常规新增/更新回归测试的路线受限。题面临时复现是否允许应遵守本次实际指令，不能通过把回归文件换个名字绕过限制。
- 若该禁令不适用：可按 `base/CONTRIBUTING.md:101–107` 与 `base/test-data/unit/README.md:8–47` 添加针对四文件碰撞及对照的回归用例，但仍需遵守具体官方文件恢复规则，不能保证任何测试改动都参与评分。

这一差异是共享输入/运行条件问题；源代码修复路线本身未被静态材料证明受阻。公开 bundle 会进入解题工作区可见路径；字段未出现在静态 `user_prompt.txt` 不等于 actor 无法读到。

## 4. 开发需求表与最小验证

本节所有命令均为 **建议，未执行**，供后续真实 actor 的 CPU 验证使用；不表示本次审读获准执行。命令针对真实 `/testbed`，不是本机静态导出目录。以下预期均为源码/公开测试推断或报告者陈述。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 尚待核验或最小缺口 | 最小命令及预计现象 |
| --- | --- | --- | --- | --- |
| 从指定源码导入 mypy；兼容的 Python 解释器 | `base/setup.py:8–10,195–202`；`base/mypy/__main__.py:6–12,33–34`；`base/mypy/fastparse.py:49–83` | `environment_brief.md:8–12` 只声明工作流、actor 与默认资源，要求实际验证；public_hints 的 conda 激活不是证明。 | Python 版本、`sys.executable`、加载的模块路径、运行依赖是否可导入；报告者 Python 3.10 不是 actor 已安装证明。 | C1（建议，未执行）。应成功导入并显示 `/testbed` 对应模块；缺包、加载到另一份安装或旧编译扩展需要先处理。 |
| 运行依赖与可重复的开发安装 | `base/mypy-requirements.txt:1–4`；`base/test-requirements.txt:1–17`；`base/pyproject.toml:1–6`；`base/CONTRIBUTING.md:28–35` | 不假定公网可下载依赖，解释器/系统包写权限尚待核验（`environment_brief.md:9–12`）。 | `typing_extensions`、`mypy_extensions`、`tomli`，按 Python 版本需要的 `typed_ast`；测试还需兼容 pytest 6 与 xdist 等。包清单与离线 wheel 资产未提供。 | 先用 C1/C3 识别实际缺口；有本地依赖资产且需要安装时，C5（建议，未执行）。不需要为本题重装最新 mypy。 |
| 四文件复现及对照；临时目录可写 | `user_prompt.txt:10–72` | workspace/home 被声明可写，tmp 配额为默认值且本题未验（`environment_brief.md:9–12`）。 | 真实 actor 的创建文件与缓存写权限；无业务服务或远程资产需求。 | C2（建议，未执行）。报告中的初态为 Y 版报 `d.py:1` 不显式导出、X 版无错误；base 实际结果待记录。修复后的统一方向取决于第 2 节语义裁决。 |
| 内置 typeshed 和单测 fixtures | `base/setup.py:70–73`；`base/test-data/unit/README.md:53–77`；`base/mypy/test/config.py:10–17` | 这里只提供源码导出；镜像资产读取与内容仍需验证。 | 本地静态包中已确认 `builtins.pyi`、`typing.pyi`、`VERSIONS` 和 module/tuple/list fixtures 文件存在；未做完整资产或 actor 访问校验。 | C2/C3（建议，未执行）会实际读取这些资产；预计不需要子模块拉取。`base_identity.json:10` 为无 gitlinks。 |
| 现有 flags/stub/子模块/缓存回归测试 | `base/test-data/unit/check-flags.test:1541–1648`；`base/test-data/unit/check-modules.test:1819–1939,2878–2917`；`base/test-data/unit/check-incremental.test:5589–5612`；`base/mypy/test/testcheck.py:42,56–58,118–140,197–227` | 无测试执行证明；默认 CPU/内存不等于本题验收已测。 | pytest、自定义 data 插件和 xdist 能否收集；临时目录可写；不需要 GPU 或模型服务。 | C3（建议，未执行）。正常 base 预期满足已有断言；修复后应继续满足约定的兼容断言。通过这些旧测试不能单独证明主例已修复。使用 `-n0` 覆盖默认 `-nauto`。 |
| 语义分析旧用例：同名 as 与普通文件默认导出 | `base/test-data/unit/semanal-modules.test:825–864`；`base/mypy/test/testsemanal.py:23–55,65–100` | 同上，仅静态测试材料。 | 同一 pytest 环境，范围可以很小。 | C4（建议，未执行）。预计已有用例通过；用于防止改变默认 `.py` 与 `.pyi` 的差别。 |
| 若改文档，构建 HTML | `base/docs/README.md:7–28`；`base/docs/requirements-docs.txt:1–2`；`base/docs/Makefile:5–8,52–55` | 未声明 Sphinx/theme 已安装；不假定公网可补依赖。 | Sphinx 4.x、sphinx-rtd-theme 1.x 与可写构建目录；只在文档路线需要。 | C6（建议，未执行）。预计生成 HTML；不要求联网 linkcheck。源码语义调查不以完整文档构建为前置。 |

C1，建议，未执行；工作目录 `/testbed`，最小导入与来源检查：

```bash
python -c 'import sys, mypy.main, mypy.semanal; print(sys.executable); print(sys.version); print(mypy.main.__file__); print(mypy.semanal.__file__)'
```

C2，建议，未执行；在真实 `/testbed` 发起，先按题面内容在获准的独立临时目录放置四个文件。以下命令的工作目录须为该四文件示例根目录，`PYTHONPATH` 保证使用 `/testbed` 源码。先用 `c.py = from a import Y as W`，再只替换为 `from a import X as W` 分别记录结果；不要改官方测试文件。

```bash
PYTHONPATH=/testbed python -m mypy --strict --no-implicit-reexport .
```

若实际环境有默认配置或缓存，应另记录隔离结果；C2b，建议，未执行，同一临时目录：

```bash
PYTHONPATH=/testbed python -m mypy --config-file=/dev/null --strict --no-implicit-reexport --no-incremental --cache-dir=/dev/null .
```

C2 的初态成功标准是可靠记录报告中的不对称是否在指定 base 上存在，不是要求原 bug 在初态通过。后续回归还应检查同名别名/`__all__` 明示导出和真实子模块；临时文件的创建权限及“禁止改测试”指令适用范围须由实际工作流落实，本审读未创建这些文件。

C3，建议，未执行；工作目录 `/testbed`，仅一个测试模块内选取相关用例（包含大小写不同的已有名称）：

```bash
python -m pytest -n0 -q mypy/test/testcheck.py -k 'NoImplicitReexport or NoReExport or ReExportChildStubs or ReExportAllInStub or ExplicitReexportImportCycleWildcard'
```

C4，建议，未执行；工作目录 `/testbed`：

```bash
python -m pytest -n0 -q mypy/test/testsemanal.py -k 'FromImportAsInStub or FromImportAsInNonStub or ImportAsInStub'
```

C5a、C5b，建议，未执行；工作目录 `/testbed`。这是仓库记载的开发安装方式，只在真实环境确实缺依赖、写权限及依赖来源允许时采用，不假定公网可用，也不建议无条件执行：

```bash
python -m pip install -r test-requirements.txt
python -m pip install -e .
```

C6，建议，未执行；工作目录 `/testbed`，只在修改文档且构建依赖已可用时：

```bash
make -C docs html
```

本题的最小验证不需要全仓测试、Python 2.7 运行程序、mypyc C 编译器、SSH、GPU、容器管理或模型调用。`base/test-data/unit/README.md:87–90` 提及 Python 2.7 是广泛测试环境说明，不能据此把 Python 2.7 当成本题几个纯类型检查用例的必需资产；`base/setup.py:77–85` 表明 mypyc 编译是可选路径。没有为未运行的命令填入通过结果或资源实测数值。

## 5. 实际阅读范围与暴露限制

完整打开了：指定 `roles/public_reader.md`（唯一包外输入）；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`；以及 `base/README.md`、`base/CONTRIBUTING.md`、`base/docs/README.md`、`base/test-data/unit/README.md`、`base/pytest.ini`、`base/conftest.py`、`base/test-requirements.txt`、`base/mypy-requirements.txt`、`base/build-requirements.txt`、`base/pyproject.toml`、`base/setup.cfg`、`base/tox.ini`、`base/docs/requirements-docs.txt`、`base/mypy/__main__.py`、`base/mypy/version.py`、`base/mypy/test/config.py`。

按片段打开了以下文件（为实际范围，不声称通读）：

| 相对路径 | 打开的行段 |
| --- | --- |
| `base/docs/source/command_line.rst` | 545–585 |
| `base/docs/source/config_file.rst` | 580–626 |
| `base/docs/Makefile` | 1–82 |
| `base/mypy/main.py` | 655–682 |
| `base/mypy/options.py` | 160–180 |
| `base/mypy/semanal.py` | 385–425、509–548、1770–2047、4351–4429、4675–4758 |
| `base/mypy/nodes.py` | 367–421、3120–3193、3228–3283 |
| `base/mypy/fastparse.py` | 32–90、891–920 |
| `base/mypy/build.py` | 697–805、3117–3152 |
| `base/mypy/semanal_main.py` | 66–173、288–342 |
| `base/mypy/test/testcheck.py` | 1–245 |
| `base/mypy/test/testsemanal.py` | 1–105 |
| `base/mypy/test/helpers.py` | 1–65、333–391 |
| `base/mypy/test/data.py` | 1–75 |
| `base/setup.py` | 1–108、160–209（末行） |
| `base/test-data/unit/check-flags.test` | 1530–1660 |
| `base/test-data/unit/check-incremental.test` | 5570–5612（末行） |
| `base/test-data/unit/check-modules.test` | 1785–1950、2870–2925 |
| `base/test-data/unit/semanal-modules.test` | 768–866 |
| `base/mypy/typeshed/stdlib/VERSIONS` | 1–20 |

还对本题 `base/mypy`、`base/docs`、`base/test-data` 做了 `implicit_reexport`、`module_public` 等相关关键词搜索，并对上述导入/测试文件做了局部关键词搜索；检索命中不等于通读文件。`base/mypy/checkexpr.py`、`base/mypy/server/astdiff.py`、`base/mypy/semanal_shared.py`、`base/test-data/unit/semanal-symtable.test` 只见相关搜索命中；`base/mypy/checkmember.py` 仅作为搜索目标，未通读。初次文件名检索列出了本题多项测试/README/安装文件，未据此打开无关测试。静态 `is_file/stat` 仅确认了 typeshed 的 builtins/typing/VERSIONS、lib-stub builtins 与 module/tuple/list fixtures 存在及大小；未读取这些 stub 全文。

未查：角色卡父目录、B5 交接/manifest/inventory、其他题、私有材料、gold、旧结论、Git 历史、远程网页、外链附件、真实镜像、actor shell、任何执行日志或模型消息。没有运行项目代码/测试、安装依赖、网络访问、容器/SSH/GPU/模型操作、源码修改或提交；没有 quota/reset 调用或创建子 agent。唯一写入是本指定结果文件及其必要结果目录。

`user_prompt.txt` 是静态模板渲染，`base/` 是源码导出而非完整运行容器（`environment_brief.md:3–6`）。默认 profile 与资源描述不是本题运行证明；实际消息注入、环境激活、依赖可导入、资产权限与测试成功都仍待 actor 验证。未发现私有材料暴露，但这仅是本次遵守阅读约定的声明，不是文件权限隔离或预训练无污染证明。
