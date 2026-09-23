# iterative__dvc-6954：fresh 公开静态阅读

仅依据指定角色卡和本题 `PUBLIC_DIR`。未运行项目、安装依赖、改动 `base/`、联网或读取私有评分、历史结论、其他题及镜像克隆。下文所有开发命令均为**建议，未执行**；关于原 bug 和成功现象的描述是静态预期。

公开材料已经足够定位核心问题和设计本地复现。主要待验项是实际 actor 环境、依赖及测试收集条件；普通负整数和负浮点数之外的表达式边界没有完整规范，不应据此预设唯一实现。

## 1. 需求表

| 行为 | 要求及保留事项 | 证据与确定性 |
| --- | --- | --- |
| Python 文件中的负参数 | `my_params.py` 中 `my_int = -1` 应被读为数值 `-1`，用于 stage 参数；不能继续误报该参数缺失。 | **明示**：`user_prompt.txt:3-14,28-46`。数值类型的保留由现有读取接口合理推知：`base/tests/unit/dependency/test_params.py:114-153`。 |
| `dvc repro` | 按题面 YAML、输入文件和 Python 参数执行时，stage 应成功运行，生成输出并更新锁文件。 | **明示**：`user_prompt.txt:26-56`。日志是 “Ideally” 的示意，不构成空白、对齐或完整逐字输出契约。 |
| `dvc run` | 通过该命令新建并执行使用负 Python 参数的 stage，也应成功。 | **明示但未给单独 CLI 复现**：`user_prompt.txt:10`；正常查调用者即可补齐：`base/dvc/command/run.py:36-51,54-99`、`base/dvc/repo/run.py:25-35`。 |
| 负数适用范围 | 普通负整数、负浮点数，在已有支持的赋值位置应获得一致读取；例如注解赋值、类属性、`__init__` 中的 `self` 属性，以及现有单层容器的数字元素。 | **合理推知**：题名使用 “Negative numbers”；已有 int/float、dict/list/set/tuple 和这些位置的公开行为见 `base/tests/unit/dependency/test_params.py:118-176`，共用取值路径见 `base/dvc/utils/serialize/_py.py:89-159`。这些不是题面逐项列出的新增测试要求。 |
| 既有参数类型与定位方式 | 保留非负整数/浮点数、字符串、布尔、`None`，以及现有 dict/list/set/tuple；保留点分参数路径、类整体读取和 `self` 筛选，不应把负数变成字符串或绝对值。 | **公开测试约定**：`base/tests/unit/dependency/test_params.py:84-95,114-176`；路径读取见 `base/dvc/dependency/param.py:104-125`。 |
| 参数跟踪与锁文件 | 负数应进入既有参数值结构，参与变化检测和锁文件记录。相同值不应导致无条件重跑；由 `-1` 改成另一个值应作为参数变化处理。 | **合理推知**：`base/dvc/dependency/param.py:64-86,127-138`；`base/dvc/stage/serialize.py:109-125,175-187`；公开 YAML 回归例见 `base/tests/func/test_repro_multistage.py:501-526`。 |
| YAML、其他格式及错误处理 | YAML 已能工作，不能回归；保留 `.py` 后缀路由、默认 `params.yaml` 和既有其他加载器；真正缺失的参数仍报错，语法错误仍走已有解析错误路径。 | YAML 正常是**题面声明**：`user_prompt.txt:14`。其余为**代码/公开测试约定**：`base/dvc/utils/serialize/__init__.py:10-15`、`base/dvc/dependency/param.py:28,91-102,127-138`、`base/tests/unit/dependency/test_params.py:72-111,179-189`、`base/dvc/utils/serialize/_py.py:21-24`。 |
| 参数文件读取方式 | 仍按 AST（Python 语法树）静态读取，不应为读取一个参数而执行整个 Python 文件、导入其中模块或调用用户函数。 | **从现有实现合理推知的兼容边界**：`base/dvc/utils/serialize/_py.py:21-27,89-120,172-181`。题面没有要求把静态提取器升级成 Python 解释器。 |
| 共享读取/更新路径 | `params show` 也使用相同加载器；参数修改依赖同一 AST 转换及行号元数据，应保持原有正数修改等功能。 | **现有调用关系/测试约定**：`base/dvc/repo/params/show.py:50-80`、`base/tests/func/params/test_show.py:37-55`、`base/dvc/utils/serialize/_py.py:30-38,41-86`、`base/tests/func/experiments/test_experiments.py:246-328`。题面并未明确要求拓展所有负数字面量的文本替换能力。 |

三类输入须分别理解：

- **Issue 需求**：上述负数读取和 stage 执行行为；报告中的 DVC 2.8.2、Python 3.8.10/Linux 是报告者环境，不是本次环境证明（`user_prompt.txt:58-78`）。
- **Harness 操作指令**：`public_bundle.json:1` 的 `public_hints` 要求探索根因、仅编辑非测试源码、不得修改测试、验证保持窄范围、完成后简述；`allowed_tools` 为 `bash/edit`，目标工作目录为 `/testbed`。这些不是功能验收语义。
- **待验环境声明**：同一字段称 `testbed` conda 环境已激活，`python/pip` 与测试工具已指向它。`environment_brief.md:3-12,20-26` 明确这尚待 actor 验证；不能据此声称环境已可运行。bundle 会写到公开可见路径，未出现在 `user_prompt.txt` 不等于不可见。

“禁止改测试”仍应登记为原操作指令，不能静默忽略。其“所有测试修改都会恢复、永不计分”的理由不是已核实的当前机制；环境说明指出当前没有按测试文件名统一排除，仍有官方文件恢复等限制（`environment_brief.md:20-25`）。若原指令适用，本题可修改非测试解析源码，并运行现有公开测试和临时复现，无明显阻断核心修复；若不适用，可增加负数回归测试，但不能据此推断测试文件的计分/恢复范围。适用性和具体机制是共享输入/运行条件待验项。

## 2. 合理实现范围

合理实现可以在共用值提取逻辑中显式识别带负号的数字，也可以使用受限的字面量求值或其他 AST 辅助函数；可以重构局部辅助函数，也可以维持现有结构。只要满足可观察行为并保持现有类型、赋值筛选、错误处理和行号元数据兼容，不应要求某个新增函数名、某个 AST 分支写法或固定补丁形状。仅在 CLI 层吞掉缺参错误，或对 `my_int`/`my_params.py` 特判，不满足一般行为要求。

真正有约定的名称与输出包括现有 `load_py/parse_py/modify_py` 调用接口、`.py` 格式路由、默认参数文件和点分查找规则；`my_int`、`my_params.py` 和 `my_stage` 是示例名称，非必须特判的常量。参数数值须真实进入读取结果与锁文件，而不是只打印题面成功日志（依据见需求表）。

仍有多种合理解释的边界：

- `+1`、连续符号如 `--1`、对变量取负、任意算术表达式、`not`/`~`、调用函数取得负数，均未由题面规定。支持普通负数字面量不意味着必须支持全部 `UnaryOp`（一元运算节点）或任意表达式。
- 当前容器处理只对直接元素调用取值函数；深层嵌套容器和多目标赋值已有局限（`base/dvc/utils/serialize/_py.py:126-152`）。负数修复无需顺带重设所有容器/赋值语法的支持范围。
- 负数读取修复可能自然改善 `parse_py_for_update`；但其文本替换按旧值字符串匹配（`base/dvc/utils/serialize/_py.py:51-59`），题面没有规定负零、括号、空白、指数写法等所有源代码格式的修改结果。应保留既有公开修改测试，不宜把未说明的格式化能力当成唯一合法实现条件。

这些边界不阻碍普通负数的开发，也不需要先补齐完整语言规范；若验收特别区分这些行为，则需要额外公开语义依据。

## 3. 初态线索与疑义

调查入口完整：题面给出 stage YAML、Python 参数内容、输入文件命令和 `dvc repro`，没有复现必需的附件或外部数据（`user_prompt.txt:26-46`）。从缺参错误能定位 `ParamsDependency.get_hash()`，它读取后比较实际键与请求键（`base/dvc/dependency/param.py:127-138`），再追到 `.py` 加载器（同文件 `91-102`；`base/dvc/utils/serialize/__init__.py:13-15`）。

高置信静态根因线索：负数字面量在 Python AST 中带一元负号节点，而 `_get_ast_value` 仅处理 `ast.Num/Str/NameConstant`，其他值抛 `ValueError`（`base/dvc/utils/serialize/_py.py:172-181`）；外层捕获此错误后略过赋值（`89-120`）。这解释了“存在赋值却被报告缺失”。此处是静态分析，未执行 AST 探针或复现确认。`dvc run → stage.run → save_deps → dep.save → get_hash` 的公开调用关系可查（`base/dvc/repo/run.py:28-35`、`base/dvc/stage/__init__.py:455-470,518-548`、`base/dvc/dependency/param.py:140-155`）；重现流程复用 stage 执行（`base/dvc/stage/__init__.py:409-431`）。

公开测试已有 Python 参数读取入口，但已读的相关测试没有直接覆盖负数字面量；它们可验证兼容性，不能单独证明 bug 已修复。最小新增验证可用临时参数内容，不必编辑测试文件。需要阅读加载器、调用者、锁文件序列化与 fixtures 是正常开发调查，不是题面缺陷。

真正可能阻碍运行的缺口是 actor 实际解释器、依赖、CLI 安装来源、pytest 插件与写权限是否齐备。`base_identity.json:5-15` 声明导出 551 个跟踪项，未遗漏 LFS 指针或 gitlinks，但没有 Git 元数据；这支持无需追索子模块材料，不证明真实容器包完整。没有发现核心复现必需的公开外链缺项。README 和贡献指南的外链未导入包（`base/README.rst:89-94,224-225`、`base/CONTRIBUTING.md:1`），现有源码、依赖声明和测试足够起步，暂不需要补读外链或公开祖先历史。

## 4. 开发需求表

所有命令均为**建议，未执行**，供后续 actor 在真实环境核验；不是在本静态 `base/` 上运行的记录。复现写入独立临时目录，源码与公开测试仍以真实 `/testbed` 为准。

| 操作/资产/服务 | 公开依据 | 环境说明支持层级 | 缺口 | 最小命令及静态预期 |
| --- | --- | --- | --- | --- |
| Python、DVC 与解析器导入 | `base/setup.cfg:21-31,35-78` 声明 Python ≥3.7，列出 `funcy`、YAML/TOML 等依赖；`base/dvc/__init__.py:6-9` 导入会初始化日志；`base/dvc/utils/serialize/__init__.py:4-8` 会加载多种格式。 | hints 声称 conda 已激活；`environment_brief.md:12` 要求另验。 | 实际 Python 版本、包版本、导入来源未知；不能把标准库 `ast` 的可用性等同于整个项目可导入。 | **建议，未执行**：在 `/testbed` 运行 `python -c 'import sys, dvc; from dvc.utils.serialize import parse_py; print(sys.executable, sys.version, dvc.__file__, dvc.__version__)'`。应导入当前 checkout，若 `ModuleNotFoundError` 等则先归因环境。 |
| 解析层最小 bug 验证 | `base/dvc/utils/serialize/_py.py:21-27,89-120,172-181`。 | 仅提供源码，没有实际导入/执行证据。 | 需在 actor 环境确认静态推断。 | **建议，未执行**：下方 A。原始代码预期输出 `{}` 并在断言处失败；修复后输出包含 `my_int: -1` 并成功退出。 |
| 本地 Git、shell、stage 文件与可写临时目录 | `user_prompt.txt:26-46`；`base/README.rst:52-55,75-79`；原报告无 remotes（`user_prompt.txt:75`）。 | `/testbed`、可写 workspace/home 是 profile 声明；CPU/内存、tmp 配额未逐题核验（`environment_brief.md:8-12`）。 | `git`、`dvc` 可执行文件、所选临时路径写权限、CLI 是否指向本次源码待验。 | **建议，未执行**：`git --version`、`dvc --version`，随后下方 B。修复后 `b.txt` 与 `a.txt` 一致，锁文件记录 `my_int: -1`；原始代码预期缺参错误和非零退出。 |
| `dvc run` 通路 | `base/dvc/command/run.py:54-99`、`base/dvc/command/stage.py:166-173`、`base/dvc/repo/run.py:25-35`。 | 只说明工具与工作目录，无 CLI 运行证据。 | 除 CLI 及本地写入能力外，不需要新资产。 | **建议，未执行**：在另一个已 `git init`/`dvc init`、含同样 `a.txt` 与 `my_params.py` 的空临时 repo 执行 `dvc run -n my_stage -d a.txt -o b.txt -p my_params.py:my_int 'cat a.txt > b.txt'`。预期同 B；不要复用已有同名 stage 造成无关覆盖问题。 |
| pytest 收集与读取回归 | `base/setup.cfg:117-139` 声明 pytest、xdist 等；`base/tests/dir_helpers.py:302-345` 需要 `worker_id` fixture；`base/tests/conftest.py:6-8` 导入共用 fixtures。 | 测试工具预装仅为 hints 声明。 | 即使只选本地测试，收集也会导入 `tests/remotes` 中多种模块（`base/tests/remotes/__init__.py:5-38`），具体附带导入依赖未逐项核验；缺插件/包不能直接记作产品 bug。 | **建议，未执行**：`python -m pytest --collect-only -q tests/unit/dependency/test_params.py`，再运行 `python -m pytest -q tests/unit/dependency/test_params.py`。应收集并通过既有类型、缺参等测试；当前公开测试通过也不能替代 A/B 的负数断言。 |
| 展示、锁文件与重现兼容性 | `base/tests/func/params/test_show.py:37-55`、`base/tests/func/test_run_multistage.py:231-274`、`base/tests/func/test_repro_multistage.py:477-526`。 | 未验证 fixtures 和本地进程运行；默认资源非实测。 | 需 DVC 本地缓存/状态库和临时目录可写；窄测本身不要求云账号、远端存储或数据集。 | **建议，未执行**：`python -m pytest -q tests/func/params/test_show.py::test_show_py tests/func/test_run_multistage.py::test_run_params_default tests/func/test_run_multistage.py::test_run_params_custom_file tests/func/test_repro_multistage.py::test_repro_multiple_params`。既有展示、锁定和变化检测应通过。 |
| 共用更新路径回归（若改动影响该路径） | `base/dvc/utils/serialize/_py.py:30-86`、`base/dvc/repo/experiments/__init__.py:363-384`、`base/tests/func/experiments/test_experiments.py:246-328`。 | 未验证 Git 提交、实验临时目录与子进程。 | 相比解析层测试，额外需要 Git 操作和实验环境；不应为此要求全仓测试运行。 | **建议，未执行**：`python -m pytest -q tests/func/experiments/test_experiments.py::test_update_py_params`。应保持原正数/类属性更新及非法 Python 错误行为。 |
| 仅在安装缺失时的本地构建/安装 | `base/pyproject.toml:1-6` 使用 setuptools/setuptools_scm 并写版本文件；`base/setup.cfg:28-30,164-166`；`base/setup.py:1-3`。 | 不假定公网下载可用；解释器目录写权限待核对（`environment_brief.md:9-12`）。 | 当前无锁定依赖清单/预装包实测；静态导出无 `.git`，不能保证 setuptools_scm 在导出目录构建。 | **建议，未执行；仅实际 checkout 有版本元数据且构建依赖已备齐时**：`python -m pip install --no-index --no-build-isolation --no-deps -e .`。应使 CLI 指向当前源码；若缺包/版本元数据，应补受支持的预装资产或运行记录，不联网拉最新版、不伪造版本来源。已正确安装则无需此步。 |

A：**建议，未执行**，在真实 `/testbed` 中运行，直接复核公开示例，不修改测试文件。

```bash
python - <<'PY'
from dvc.utils.serialize import parse_py
actual = parse_py("my_int = -1\n", "my_params.py")
print(actual)
assert actual == {"my_int": -1}
PY
```

还可用相同入口观察普通负浮点数、注解赋值、类属性和已有容器中的负数；这些是合理补充覆盖，应与非字面量表达式的未定义边界分开。

B：**建议，未执行**，保留题面 `dvc repro` 的复现形状。应先用上述导入检查确认 `dvc` 指向当前 checkout；临时目录仅承载用户 repo。

```bash
repro_dir=$(mktemp -d)
cd "$repro_dir"
git init
dvc init
cat > dvc.yaml <<'YAML'
stages:
  my_stage:
    cmd: cat a.txt > b.txt
    deps:
    - a.txt
    outs:
    - b.txt
    params:
    - my_params.py:
      - my_int
YAML
printf '%s\n' 'my_int = -1' > my_params.py
printf '%s\n' dummyString > a.txt
dvc repro
cmp a.txt b.txt
python - <<'PY'
from dvc.utils.serialize import load_yaml
lock = load_yaml("dvc.lock")
assert lock["stages"]["my_stage"]["params"]["my_params.py"]["my_int"] == -1
PY
```

**建议，未执行**：成功后再执行一次 `dvc repro`，预期跳过未变化 stage；随后将 `my_int` 改为 `-2` 再执行 `dvc repro`，预期识别参数变化且锁文件值变为 `-2`。这些预期来自既有参数状态/锁文件语义，不是已运行结果。

## 5. 阅读范围与限制

实际全文打开：指定 `roles/public_reader.md`；本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`；以及以下 `base/` 内文件：

- 文档/配置：`README.rst`、`CONTRIBUTING.md`、`setup.cfg`、`setup.py`、`pyproject.toml`。
- 源码：`dvc/__init__.py`、`dvc/version.py`、`dvc/utils/serialize/_py.py`、`dvc/utils/serialize/__init__.py`、`dvc/utils/serialize/_common.py`、`dvc/dependency/param.py`、`dvc/repo/run.py`、`dvc/command/run.py`。
- 公开测试/fixtures：`tests/unit/dependency/test_params.py`、`tests/func/params/test_show.py`、`tests/conftest.py`、`tests/basic_env.py`、`tests/remotes/__init__.py`。

实际局部打开：`base/tests/func/experiments/test_experiments.py:230-335`；`base/tests/dir_helpers.py:1-134,302-370`；`base/dvc/stage/__init__.py:409-433,455-474,508-551`；`base/dvc/stage/serialize.py:82-125,170-192`；`base/tests/func/test_run_multistage.py:220-296`；`base/tests/func/test_repro_multistage.py:477-528`；`base/dvc/repo/params/show.py:48-84`；`base/dvc/repo/experiments/__init__.py:363-384`。

还在本题范围用 `rg --files` 查看路径，并用 `rg` 检索参数/序列化相关词；由搜索结果读取了 `base/dvc/repo/reproduce.py`、`base/dvc/stage/loader.py`、`base/dvc/dependency/__init__.py`、`base/dvc/command/stage.py`、`base/tests/func/test_repro.py` 等匹配行，未将这些文件全部通读。搜索也覆盖本题 `base/tests`/`base/dvc`，以及指定 README、配置、fixtures；搜索命中不等于已验证全部语义。

未查：实际容器、actor 消息/权限/资源/包列表、完整测试依赖导入树、全仓测试、外部贡献文档、公开祖先历史、私有评分与恢复文件范围。`user_prompt.txt` 是静态渲染文本，`base/` 是指定 commit 的跟踪文件导出，均不能证明实际模型消息、运行资源或开发条件已经验收（`environment_brief.md:3-16,20-26`）。fresh 只描述本次按协作范围隔离阅读；不是文件权限隔离或预训练无污染证明。本次未见本题私有材料，未另派子代理。
