# conan-io__conan-15422：公开视角审查

本审查仅依据角色卡与指定 `PUBLIC_DIR`。路径、行号均相对公开包；代码判断是静态阅读结果，所有下列开发命令均为**建议，未执行**。未运行项目代码、安装依赖、修改 `base/`，也未读取私有评分材料、gold、旧结论或其它题。

公开材料足以找到特性缺口和最小调查入口：生成器的 `_build_preset_fields()` 目前只返回名称、配置引用等公共字段，不写 `jobs`。仓库已提供 `tools.build:jobs` 与 CPU 数默认值，因此值的来源有较强的公开约定；题面未明确的是不同 CMake 生成器的适用范围及部分边界值。环境是否能导入、运行测试、调用 CMake 仍未验证。

## 1. 需求表

| 行为或约束 | 公开依据 | 判断层级与解释 |
|---|---|---|
| Conan 生成的 `CMakePresets.json` 应在 `buildPresets` 中设置并行构建用的 `jobs`，供安装后直接调用 CMake 使用 | `user_prompt.txt:3–31` | **明示。**修复目标是生成的预设；仅改变 Conan 自己调用 CMake 的命令行，不能满足示例使用方式。 |
| 保留 `name`、`configurePreset`，在示例中增加数值 `jobs` | `user_prompt.txt:12–28` | **明示。**`jobs` 是指定的 JSON 键，示例是数值 `16`；没有要求固定为 16，也未把 `conan-relwithdebinfo` 规定为所有配置的恒定名称。 |
| 任务涉及 `conan install` 后直接运行 `cmake --build ... --preset ...` | `user_prompt.txt:3,31`；`base/conan/tools/cmake/toolchain/toolchain.py:187–195,231–232` | **明示目标，入口由源码可推知。**`CMakeToolchain.generate()` 调用 `write_cmake_presets()`，是调查入口，不要求改所有构建工具。 |
| 显式配置并行度时尊重 `tools.build:jobs`；未配置时采用 Conan 的可用 CPU 默认值 | `base/conans/model/conf.py:55`；`base/conan/tools/build/cpu.py:8–28,31–54`；`base/conans/test/integration/tools/cpu_count_test.py:8–23` | **可由公开仓库合理推知，题面未指定实现方法。**既有 helper 返回整数，读取配置并使用 cgroup/CPU 检测后备值。固定 16 或忽略已有配置缺乏依据；默认值也不能被静态写死为容器说明中的 2。 |
| 继续保留预设命名、默认前缀与布局定制能力 | `base/conan/tools/cmake/toolchain/toolchain.py:161–162`；`base/conan/tools/cmake/presets.py:176–229`；`base/conans/test/functional/toolchains/cmake/test_cmake_toolchain.py:615–669` | **现有接口与公开测试约定。**默认前缀为 `conan`，名称还受构建类型与布局变量影响。内部函数名称不是题面要求，但已存在的对外行为应保留。 |
| 多配置预设保留 `configuration`，重复生成替换同名条目；不同配置追加；单配置无布局时覆盖原文件 | `base/conan/tools/cmake/presets.py:54–83,176–187`；`base/conans/test/integration/toolchains/cmake/test_cmaketoolchain.py:538–660` | **现有代码与公开测试约定。**新增字段应适用于正常生成及再次安装路径，不应破坏原有条目管理。题面未要求每次安装重算其它已有配置的并行度。 |
| 继续保留用户自有预设、包含关系以及测试预设的语义 | `base/conan/tools/cmake/presets.py:47–53,194–199,238–284,318–330`；`base/conans/test/functional/toolchains/cmake/test_presets_inherit.py:9–93` | **可合理推知的兼容要求。**不能覆盖非 Conan 生成的文件；用户预设通过 include/inherits 使用生成结果。此次 issue 没有要求给 `testPresets` 增加并行度或改变测试运行方式。 |
| 哪些 CMake generator 应带 `jobs` | 题面只报告 Ubuntu 环境，未写 generator：`user_prompt.txt:34–44`；`base/conan/tools/cmake/cmake.py:11–24`；`base/conan/tools/cmake/toolchain/blocks.py:237–252`；`base/conans/test/unittests/tools/cmake/test_cmake_cmd_line_args.py:22–45` | **存在多种解释，但已有兼容性线索。**现有 CMake helper 对 Makefiles/Ninja 添加 `-j`，排除 NMake；Visual Studio 的并行度另有 `/MP` 与 MSBuild 设置。不能仅从标题断言所有 generator 必须无条件写入相同字段，也不能把这些命令行测试直接当成新 JSON 字段的完整规范。 |
| 零、负数、无 generator、Xcode 等边界行为，以及是否允许按生成器省略字段 | `base/conan/tools/build/cpu.py:25–28` 只声明整数检查；`base/conan/tools/cmake/cmake.py:13–19` 使用真值判断；`base/conan/tools/cmake/utils.py:2–5` 将 Visual/Xcode/Multi-Config 判为多配置 | **仍未唯一规定。**本次阅读没有找到直接约束这些新预设行为的公开测试。多配置与“是否能并行”不是同一分类，例如 `Ninja Multi-Config` 同时落入既有 Ninja 选择逻辑。 |

`user_prompt.txt:6` 的“至少有时默认 1”是报告者观察，不能升级为所有 CMake 生成器的统一默认事实。目标是正确传递并行度，不是保证任意项目都能获得某个倍数的加速。

## 2. 合理实现范围

从公开材料可接受的实现可以在生成 build preset 时求取并行度，也可以在上游求值后传入生成过程，或抽取内部公共辅助逻辑。只要最终 JSON 的受支持构建预设正确反映用户配置/既有默认值，并保持上述公开行为，就不应要求修改某个特定函数签名、导入位置、私有 helper 名称或固定代码形状。JSON 键顺序和示例排版没有被题面规定。

沿用现有 Makefiles/Ninja 的并行策略、对 NMake/Visual Studio 等做有依据的兼容处理，是公开仓库支持的一种合理方向。采用更广的 CMake preset 支持范围，也不能仅因它没有复刻旧的 `-j` 分支而否定；但需要说明兼容性，尤其是 Visual Studio 已经存在 `/MP` 并行编译的情况。当前包不足以把任一跨平台策略宣布为唯一答案。

可以确定的外部约定是 `buildPresets[*].jobs` 的字段位置、整数配置来源、预设名称与配置关联保持一致。不能把只给用户建议手动编辑 JSON、只改变 Conan 的 `CMake.build()` 命令行、或只设置无关环境变量视为实现了题面所要求的生成字段。

本包没有完整 CMake preset schema/各 generator 的并行行为文档。若验收依赖 Xcode、Visual Studio、NMake 或 `jobs=0` 等精确边界，应请求协调者补充对应历史版本的公开规范或公开讨论内容，不能由审查者自行检索未来 PR。对 Unix Makefiles/Ninja 的普通正整数路径，现有材料已足以开展实现，不需要等待这种补充。

## 3. 初态线索、疑义与旧提示拆分

初态路径清楚：`CMakeToolchain.generate()` → `write_cmake_presets()` → `_CMakePresets.generate()` → `_contents()` 或多配置追加分支 → `_build_preset_fields()`。两条生成路径当前都不添加 `jobs`（`base/conan/tools/cmake/toolchain/toolchain.py:231–232`；`base/conan/tools/cmake/presets.py:15–19,54–68,85–104,189–192`）。这是静态可见的缺口，不代表已经实际复现慢构建。

题面没有给完整 recipe、CMakeLists、安装命令或 generator，但公开测试提供了生成 recipe、运行 `install`、读 JSON 的范例；默认 generator 的选择也可查到：配置优先，其次 recipe，随后按编译器推断，普通非 MSVC/MinGW 情况返回 `Unix Makefiles`（`base/conan/tools/cmake/toolchain/toolchain.py:234–270`）。这些缺项不妨碍最小字段复现，属于正常阅读调用者的工作；若要复现报告者的实际耗时和后端选择，则仍缺其完整项目及环境。

现有公开测试可用于检查预设命名、追加/覆盖和继承，但本次检索的 CMake 单元与集成测试没有直接断言新增 `buildPresets[*].jobs`。旧测试通过不能单独证明此 feature 已实现；应另用字段复现检查显式值，并检查未配置时是否使用既有 CPU 默认逻辑。

| 输入类别 | 内容与依据 | 本次解释 |
|---|---|---|
| Issue 需求 | `user_prompt.txt:3–48`；`public_bundle.json:1` 的 `problem_statement` | 功能请求及报告者环境；与 harness 操作说明区分。没有必要外部附件，未访问任何外链。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints`：只改非测试源码、不要改测试、缩小测试范围、完成后简述停止；`allowed_tools` 为 bash/edit | 原指令应登记，不能因为旧机制说明过期就擅自忽略。若适用，本题核心功能可改非测试源码并用临时命令验证，不见必须修改测试文件才能完成的障碍；若不适用，则正常补充回归测试也是合理开发方式。 |
| Harness 机制说明 | 同字段声称测试文件会恢复、测试修改永不计分；`environment_brief.md:18–24` 明确指出当前不再按测试文件名统一排除，仍有具体官方文件恢复限制 | 不把“所有测试修改永不计分”作为已核实机制。哪些文件受影响、原禁改测试指令是否进入实际输入，由协调者核实；这是共享输入/运行条件问题。 |
| 待验环境事实 | `public_bundle.json:1` 声称 `/testbed`、已激活 `testbed` conda 环境；`environment_brief.md:3–12,24` | 镜像名和 digest 是标识信息，不是运行证明。未确认 shell 实际位置、Python 激活、依赖、CMake 工具或 actor 权限。 |
| 可见性 | `environment_brief.md:3–4,23–24` | `user_prompt.txt` 是静态渲染；bundle 会放到实际公开路径。`public_hints` 未显示在该文本中，不等于解题者不可见，也不能认定其已经进入 system message。 |

本题不需要公网、模型/GPU服务、Artifactory 账户或远程包来完成最小字段复现。若真实运行缺 Python 包或 CMake 工具，在不允许任意公网下载的条件下就需要预装/离线资产；这会影响开发条件，但不是题目要求本身含混。

## 4. 开发需求表

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口与建议的最小验证 |
|---|---|---|---|---|
| 用 actor 身份定位 Python、工作目录与可写临时目录 | `public_bundle.json:1`；`environment_brief.md:8–12` | 声明 `/testbed`、agent/54321、工作区/home 可写及默认配额；尚未逐题验证 | 执行下面 C0（建议，未执行）。预期 Python、pip 属于同一可用环境，工作目录是目标源码；临时目录可写。不能只由 conda 名字推断依赖齐全。 |
| 导入 Conan、预设代码和测试辅助类 | `base/setup.py:48–56,105–118`；`base/pyproject.toml:1–3`；`base/conans/requirements.txt:1–9`；`base/conans/requirements_dev.txt:1–6`；`base/conans/requirements_server.txt:1–4` | 只有旧提示声称环境已激活；无包清单或导入证据 | C1（建议，未执行）。运行依赖包含 requests、PyYAML、Jinja2 等；公开测试还导入 mock、WebTest、bottle 和服务器辅助代码（`base/conans/test/utils/tools.py:20–51`）。缺包时应预配锁定/兼容包或离线 wheel；网络限制下不假定 pip 可下载。`python_requires>=3.6` 是包元数据，不能据此声称所有代码在任意 3.6+ 环境已兼容。 |
| 仅生成并读取 JSON 的原缺口复现 | `base/conans/test/integration/toolchains/cmake/test_cmaketoolchain.py:40–49,614–660`；`base/conans/test/utils/tools.py:398–431` | 提供静态源码、临时空间资源声明；无运行证据 | C2（建议，未执行）。本地无依赖 recipe，显式 Unix Makefiles 和 jobs=2，无须启动编译器、访问包仓库或运行 CMake。初态预计生成成功但缺 `jobs`，断言失败；修复后整数值为 2。 |
| 检查既有 CMake 并行命令与配置覆盖 | `base/conans/test/unittests/tools/cmake/test_cmake_cmd_line_args.py:10–45`；`base/conans/test/integration/tools/cpu_count_test.py:8–23` | 公开测试可见，pytest/依赖可执行性未知 | C3（建议，未执行）。预期相关现有测试通过；它们验证原接口，不能替代 C2 的新增字段断言。 |
| 检查单/多配置预设及原有生成接口 | `base/conans/test/integration/toolchains/cmake/test_cmaketoolchain.py:538–660`；`base/conans/test/unittests/tools/cmake/test_cmake_presets_definitions.py:13–55` | 纯 Python 的公共验证入口可见，尚未执行 | C4（建议，未执行）。预期保留原命名、配置数量、覆盖/追加逻辑。此类测试不要求实际 Windows 编译器；profile 中的 MSVC 信息用于生成数据。 |
| 实际执行 configure/build 与用户预设继承 | `base/conans/test/functional/toolchains/cmake/test_presets_inherit.py:9–93`；`base/conans/test/conftest.py:68–104,269–335,351–393` | 未证明存在 CMake、Make/Ninja、C/C++ 编译器或匹配的 tool 配置 | 可选 C5（建议，未执行）。此测试要求标记的 CMake 3.23 路径；Linux 默认 `/usr/share/cmake-3.23.5/bin`。配置目录缺失可能由 conftest 直接判失败，即使 PATH 另有 cmake；禁用标记也可能导致跳过。需区分环境失败和源代码失败。预期构建并运行示例，输出 `Hello World Debug!` 与 `Hello World Release!`。 |
| CPU 数读取与默认值 | `base/conan/tools/build/cpu.py:31–54`；`environment_brief.md:11–12` | 声明默认 2 CPU，但没有当前 cgroup 文件/实际 Python 检测值 | C6（建议，未执行）。预期拿到当前环境的整数值；应在 actor 条件下检查 cgroup 与 helper 结果。没有依据要求必须打印 2、16，或承诺编译速度提升比例。 |

下面命令都在真实 actor 的 `/testbed` 执行，**建议，未执行**。无需在此静态导出的 `base/` 执行。

**C0：环境定位及临时写入（建议，未执行）。**

```bash
cd /testbed
id
pwd
command -v python
python -c 'import os, sys, tempfile; print(sys.executable); print(sys.version); print(os.environ.get("CONDA_DEFAULT_ENV")); d = tempfile.TemporaryDirectory(); print(d.name); d.cleanup()'
python -m pip --version
```

**C1：最小导入与依赖一致性（建议，未执行）。**

```bash
python -c 'from conan.tools.cmake.presets import write_cmake_presets; from conan.tools.build import build_jobs; from conans.test.utils.tools import TestClient; print("imports ok")'
python -m pip check
```

如缺依赖，公开安装入口见 `base/README.md:58–64,90–104`；应先由协调者提供适合 actor 的环境/离线包，而非假定具备 sudo 或公网。`pip check` 可报告包依赖冲突，但不能证明所有 CMake 工具可用。

**C2：通过 install 路径复现缺少 `jobs`（建议，未执行）。**

```bash
python - <<'PY'
import json
from conans.test.assets.genconanfile import GenConanfile
from conans.test.utils.tools import TestClient

c = TestClient()
recipe = (GenConanfile()
          .with_settings("os", "arch", "compiler", "build_type")
          .with_generator("CMakeToolchain"))
c.save({"conanfile.py": recipe})
c.run('install . -s build_type=RelWithDebInfo '
      '-c tools.cmake.cmaketoolchain:generator="Unix Makefiles" '
      '-c tools.build:jobs=2')
data = json.loads(c.load("CMakePresets.json"))
p = data["buildPresets"][0]
print(p)
assert p["name"] == "conan-relwithdebinfo"
assert p["configurePreset"] == "conan-relwithdebinfo"
assert type(p.get("jobs")) is int and p["jobs"] == 2, p
PY
```

这一建议采用包中现有 TestClient/GenConanfile 方式，在临时目录写最小 recipe，不修改已有测试文件。对本题预期 Linux actor，原版预计最后一个断言失败并显示无 `jobs` 的字典；若先出现 ImportError、权限或配置加载错误，应先排查环境，不能把它登记为原 feature 失败。字段检查不测实际并行任务数。

**C3：已有并行配置相关测试（建议，未执行）。**

```bash
python -m pytest -q conans/test/unittests/tools/cmake/test_cmake_cmd_line_args.py
python -m pytest -q conans/test/integration/tools/cpu_count_test.py
```

**C4：已有预设兼容性测试（建议，未执行）。**

```bash
python -m pytest -q conans/test/unittests/tools/cmake/test_cmake_presets_definitions.py
python -m pytest -q conans/test/integration/toolchains/cmake/test_cmaketoolchain.py -k 'test_cmake_presets_singleconfig or test_cmake_presets_multiconfig'
```

**C5：可选真实构建与预设继承检查（建议，未执行；先满足工具依赖）。**

```bash
cmake --version
make --version
c++ --version
python -m pytest -q conans/test/functional/toolchains/cmake/test_presets_inherit.py::test_cmake_presets_with_user_presets_file
```

该公开测试内含 configure/build 与运行命令（`base/conans/test/functional/toolchains/cmake/test_presets_inherit.py:74–93`），通过可验证真实构建兼容性，但没有测量并行执行数。无需为了字段修复运行全部 functional suite，也无需真实 Artifactory。

**C6：读取既有默认并行度（建议，未执行）。**

```bash
python - <<'PY'
from conan.tools.build import build_jobs
from conans.test.utils.mocks import ConanFileMock
print(build_jobs(ConanFileMock()))
PY
```

可在 C2 的临时 recipe 中去掉显式 jobs 配置，再对照该环境的既有默认逻辑检查生成值。CPU 环境可能随运行条件变化，不能用另一台机器的观测作恒定期望。以上所有成功/失败现象均为依据源码的预计，未作为实测结果。

## 5. 阅读范围与限制

实际打开：

- 角色卡 `public_reader.md`；公开包 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- 安装/测试文档：`base/README.md`、`base/.github/CONTRIBUTING.md:1–113`、`base/conans/test/README.md`、`base/setup.py`、`base/pyproject.toml`、`base/pytest.ini`、`base/conans/requirements.txt`、`base/conans/requirements_dev.txt`、`base/conans/requirements_server.txt`。
- 相关实现：`base/conan/tools/cmake/presets.py` 全文；`base/conan/tools/build/cpu.py` 全文；`base/conan/tools/cmake/utils.py` 全文；`base/conan/tools/cmake/layout.py:1–90`；`base/conan/tools/cmake/cmake.py:1–100,180–235,260–285`；`base/conan/tools/cmake/toolchain/blocks.py:205–270`；`base/conan/tools/cmake/toolchain/toolchain.py:1–70,150–295`；`base/conans/model/conf.py:46–63`。
- 测试与辅助：`base/conans/test/unittests/tools/cmake/test_cmake_presets_definitions.py`、`base/conans/test/unittests/tools/cmake/test_cmake_cmd_line_args.py`、`base/conans/test/integration/tools/cpu_count_test.py`；`base/conans/test/integration/toolchains/cmake/test_cmaketoolchain.py:1–60,460–665`；`base/conans/test/functional/toolchains/cmake/test_presets_inherit.py:1–93`；`base/conans/test/functional/toolchains/cmake/test_cmake_toolchain.py:1–35,550–670,775–855`；`base/conans/test/conftest.py:1–393`；`base/conans/test/functional/toolchains/conftest.py`；`base/conans/test/utils/mocks.py:1–115`；`base/conans/test/utils/tools.py:1–80,369–437`；`base/conans/test/assets/genconanfile.py:1–115`。

另在公开包内列过文件名，对 CMake、build CPU、配置及公开测试检索过 `buildPresets`、`tools.build:jobs`、`build_jobs`、preset、parallel 等关键词。较宽的文件列表/搜索输出发生过截断；关键引用均随后通过定点读取确认，不宣称完整审阅所有命中。尝试查找的 `base/conans/test/functional/toolchains/cmake/test_presets.py` 不存在，实际继承测试在 `test_presets_inherit.py`。`test_cmaketoolchain.py` 的单元测试文件只做相关词检索，未完整阅读。

未查：完整仓库所有源码/测试、`base_identity.json` 内容、真实 `/testbed` 或镜像、包安装结果、编译器与 CMake 二进制、actor 配额/权限、实际模型消息、完整官方验收、公开祖先历史、CMake 外部规范及任何未来历史。当前证据不要求导入祖先历史。

`environment_brief.md:3–6` 明确规定该包只是静态渲染与 base Git 跟踪文件导出，不能当成完整运行容器。阅读隔离是遵守角色约定的结果，不是文件权限隔离证明，也不是预训练无污染证明。本次未发现或读取本题私有材料。

关键未知：跨 generator/边界值的精确验收范围；当前原禁改测试指令及官方文件恢复规则的具体适用方式；真实 actor 的 Python、依赖、CMake 工具路径和可写条件。最小字段开发入口已能由公开材料确定。
