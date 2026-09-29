# conan-io__conan-13403 公开静态阅读

## 题面先验记录

在阅读源码前，根据 `user_prompt.txt` 记录：用户要在构建目录内、对该处的 `configure.ac` 执行 `Autotools.autoreconf()`，不应为此更改 recipe 的 `source_folder`。用户已经尝试在外部 `chdir(self, self.build_folder)`，但观察到方法仍寻找别处的文件。合理旧行为是无参数调用仍在源码目录执行；原有 autoreconf 参数与 toolchain 配置应继续生效。题面没有规定新增参数名称、参数顺序、相对路径基准或异常形式，也没有承诺单靠外层 chdir 就必须生效。`configure(build_script_folder=...)` 是用户给出的 API 类比。

公开提示 `public_bundle.json.public_hints` 声明只修改 NON-TEST 源码、不得修改测试文件，允许窄范围测试，并声称 `/testbed` 与已激活的 conda `testbed` 环境。该提示是否实际交付给 actor 为 unknown。这里的静态审查禁执行边界来自派发卡，不是题目的附加修复要求。

## 公开源码消解的疑问

以下路径均相对本题 `PUBLIC_DIR/base/`；PUBLIC_DIR 为 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13403`。

1. **根因可静态定位。** `conan/tools/gnu/autotools.py:101-111` 的 `autoreconf(self, args=None)` 没有目录参数，且无条件进入 `chdir(self, self._conanfile.source_folder)`，再调用 recipe 的 `run`。`conan/tools/files/files.py:289-304` 的 `chdir` 实际执行 `os.chdir(newdir)`，在 finally 中恢复原目录。因此用户的外层 chdir 会被内层 source_folder 切换覆盖，所述故障与公开代码相符；这不是执行复现。
2. **相对路径已有一致性参照。** 同文件 `configure:36-59` 将非空 `build_script_folder` 与 `source_folder` 做 `os.path.join`；没有值则使用源码目录。故新参数若沿用该语义，相对路径应以源码目录为基准；在题面 Linux 环境中传入绝对 build_folder 则可指向构建目录。该推导来自既有 API 与 Python 路径规则，题面未把它规定为唯一接口。
3. **默认行为与参数兼容值得保留。** `Autotools.__init__:16-34` 从 generators_folder 的 toolchain 参数文件取配置。`autoreconf:108-111` 组合默认 toolchain 参数及调用参数，目录修复不需要改变组合方式。原签名接受首个位置参数作为 args；若将目录参数放在 args 前面，会存在破坏旧位置调用的风险，虽本次阅读的旧测试只使用无参数和 `args=` 调用。
4. **目录选项应只改变 autoreconf 的执行目录。** 相比之下，configure 是通过脚本完整路径调用，并未主动改变当前工作目录。合理修复不必改 configure、recipe 的 source_folder、make/install 或整个布局模型。继续使用已有 chdir 上下文可保留正常返回及异常情况下的目录恢复。
5. **初始化前提独立于本 bug。** `conan/tools/build/__init__.py:63-85` 会在找不到 `conanbuild.conf` 或 `[toolchain]` 节时报错。题面简略示例没有提供 generate 阶段，但这不足以认定其真实 recipe 缺配置；需要复现时补足此公开前提。

## 旧测试给出的覆盖与限制

- `conans/test/unittests/tools/gnu/autotools_test.py:9-26` 的 `test_source_folder_works`：写 toolchain 参数，使用 `ConanFileMock`，断言 configure 指向源码子目录及默认源码目录。此测试支持相对基准和默认行为，但完全没有验证 autoreconf 的工作目录。
- `conans/test/functional/toolchains/gnu/autotools/test_basic.py` 的 `test_autotools_option_checking`（约 248-301）在 `basic_layout` 配方中先 autoreconf，再 configure/make，体现无参数调用的既有使用方式。
- 同文件 `test_autotools_arguments_override`（约 304 起，本次阅读到 375 行）将 toolchain autoreconf 参数设为 `--verbose`，调用 `autoreconf(args=['--install'])`，断言输出含 `--install`、不含默认 `--force`。目录修复应避免破坏该路径。
- 同文件的 Linux/Darwin skip 条件及 `@pytest.mark.tool("autotools")` 说明功能测试有平台和系统工具前提。`conans/test/conftest.py:67,266-332,348-390` 将 autotools 检查映射到 autoconf 可执行文件，缺工具可失败、显式禁用可跳过；通过 autoconf 的存在检查不等于 autoreconf/automake/编译器整个链条均已可用。
- 已读测试没有覆盖构建目录、源码子目录的 autoreconf、新参数位置兼容、外层目录恢复、异常恢复和带空格目录。这些是可由公开行为导出的验证维度，不代表已见隐藏测试。

## 合理实现范围与保留的不确定性

可在 `Autotools.autoreconf` 增加可选目录参数并说明路径基准，默认仍指向源码目录，传绝对路径允许构建目录，保留 args 及 toolchain 配置。采用与 configure 相同的 `build_script_folder` 名称并保持 args 的已有位置，是一种可解释的兼容设计；也可采用另一明确目录参数或等价的显式目录入口。公开题面不能唯一决定参数命名与顺序，更不能据此推断 gold。

不建议简单删除内部 chdir 令所有调用服从当前目录：这虽然可能让题面片段运行，却会改变正常 source_folder 默认行为。目录不存在时是否继续让 `os.chdir` 抛错、是否支持 None/空字符串相同默认语义、Windows 路径/子系统边界是否另行处理，题面没有要求新规则；以现有 API 约定为基线是最小风险选择。未取得完整真实 recipe、configure.ac 内容、日志或实际执行栈，无法确定用户项目是否另有构建问题。

## 开发需求表

下列命令仅是将来在获得授权的实际 actor 工作树中的最小验证建议，本轮均未运行；表内 `/testbed` 是公开声明的目标位置，不是本轮 ROOT。新行为探针使用上面建议的 `build_script_folder` 接口，若选用其他 API 应相应替换。

| 操作 / 资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
|---|---|---|---|
| 获取实际消息、工具权限及初始源码状态 | public_hints、environment_brief.md | 实际消息、bash/edit 可用性、初始修改规则、HEAD/status/diff 均 unknown；静态 base 身份由 base_identity.json 声明 | 在 actor 中 `pwd`、`git -C /testbed rev-parse HEAD`、`git -C /testbed status --short`；核对规定起点及允许初始变更，不能仅凭 commit 判定整个初态 |
| 读取/修改非测试源码 | autotools.py:101-111；public_hints | 导出文件可读；实际 actor 对源文件的写权限 unknown | `test -r /testbed/conan/tools/gnu/autotools.py` 与 `test -w /testbed/conan/tools/gnu/autotools.py`；均成功才支持该文件读写，源码 diff 应仅包含获授权修复 |
| Python、依赖及本地源码导入 | setup.py 的 python_requires>=3.6；requirements.txt；requirements_dev.txt 的 pytest>=6.1.1,<7 | 实际解释器、conda 激活、依赖及导入来源 unknown，题面 3.6.8 是报告者环境 | `python --version`、`python -m pytest --version`；从 /testbed 运行 `python -c "import conan; print(conan.__file__)"`，应指向待修工作树，不能仅证实安装包可导入 |
| toolchain 文件与可写临时目录 | Autotools.__init__；load/save_toolchain_args；旧单测 | 静态代码显示前提；实际 generators_folder、配置和临时写权限 unknown | 以下公开探针在临时目录创建最小配置；构造 Autotools 不应报缺配置，退出后目录应恢复 |
| 保持 configure 旧行为 | test_source_folder_works | 测试源码可见，运行结果 unknown | `python -m pytest -q conans/test/unittests/tools/gnu/autotools_test.py`；旧断言通过，但单独通过不能证明本 bug 已修复 |
| 明确指定目录并保留默认及 args | 题面；autoreconf 与 configure 实现 | 当前静态源码没有目录入口；任何修复后行为 unknown | 执行下方纯 Python mock 探针；应分别记录源码、源码子目录、构建目录，并保持 `autoreconf --verbose --install` 和 cwd 恢复；无需真实 Autotools 二进制 |
| 实际 GNU 工具链功能回归 | test_basic.py 的两个相关功能测试和 tool 标记 | Linux/工具版本仅来源声明；autoreconf/autoconf/automake/make/C++ 编译器、profile、缓存写权限均 unknown | 先 `command -v autoreconf autoconf automake make gcc g++`，再 `python -m pytest -q conans/test/functional/toolchains/gnu/autotools/test_basic.py -k 'option_checking or arguments_override'`；预期选中测试实际通过，skip 不能当通过 |

可供未来运行的最小 mock 探针（不修改仓库测试文件，不执行系统 autoreconf）：

```sh
python - <<'CHECK'
import os
import tempfile
from conan.tools.build import save_toolchain_args
from conan.tools.gnu import Autotools
from conans.test.utils.mocks import ConanFileMock

original = os.getcwd()
with tempfile.TemporaryDirectory() as root:
    source = os.path.join(root, 'source')
    sub = os.path.join(source, 'nested')
    build = os.path.join(root, 'build with spaces')
    os.makedirs(sub)
    os.makedirs(build)
    os.chdir(root)
    try:
        save_toolchain_args({'configure_args': '', 'make_args': '',
                             'autoreconf_args': '--verbose'})
        cf = ConanFileMock()
        cf.folders.set_base_source(source)
        cf.folders.set_base_build(build)
        cf.folders.set_base_generators(root)
        seen = []
        cf.run = lambda command: seen.append((os.getcwd(), command))
        at = Autotools(cf)
        for folder, expected in [(None, source), ('nested', sub), (build, build)]:
            os.chdir(build)
            if folder is None:
                at.autoreconf(['--install'])
            else:
                at.autoreconf(args=['--install'], build_script_folder=folder)
            assert seen[-1] == (expected, 'autoreconf --verbose --install')
            assert os.getcwd() == build
        print('directory and argument checks passed')
    finally:
        os.chdir(original)
CHECK
```

该探针只验证命令交给 recipe.run 时的 cwd 与参数，不证明 GNU 工具生成 configure 成功；真实构建目录验收还需在目标目录准备有效 configure.ac/Makefile.am 等项目输入。后者用户未完整提供。网络、容器、SSH、GPU 或模型资源不是该局部目录选择逻辑的固有前提，本轮也未探测其可用性。

## 已读范围及证据边界

- 全文读：派发卡、public_reader.md；本题 user_prompt.txt、public_bundle.json、environment_brief.md、base_identity.json；base/conan/tools/gnu/autotools.py；base/conan/tools/build/__init__.py；base/conans/test/unittests/tools/gnu/autotools_test.py；base/pytest.ini；base/conans/test/README.md；base/conans/requirements.txt、requirements_dev.txt；base/conans/test/conftest.py；base/conans/test/functional/toolchains/conftest.py。
- 部分读：files.py:280-310（核心为 chdir）；mocks.py:104-143（ConanFileMock 初始化和 run）；test_basic.py:1-70、235-375。对 autotoolstoolchain.py 的 autoreconf_args 和 setup.py 的 Python/安装依赖字段只做 rg 命中读取，没有读周边实现。
- 搜索：公开 base 文件路径清单（输出截断，不等于逐个读过文件）；gnu 工具及测试目录中 autoreconf/build_script_folder 命中；requirements/conftest/README 路径定位。其他命中的测试只看到匹配行，未阅读主体。曾尝试读取 base/conftest.py，该导出路径不存在，随后读了实际 conans/test/conftest.py；这不构成 actor 镜像缺文件证据。
- 未读：私有材料、gold、隐藏测试、历史、其他题或角色结果；未访问任何源码内外链，未读公开包之外的项目文件。没有运行/导入项目、测试、安装、网络、容器或修改源/测试文件。
- base_identity 声明 base commit 为 `55163679ad1fa933f671ddf186e53b92bf39bbdb`，无导出 git 元数据；它只证明公开静态范围的来源声明，不能代替 actor 身份、运行资产或环境验核。不宣称训练资格、实际 actor 资格或测试成功率。
