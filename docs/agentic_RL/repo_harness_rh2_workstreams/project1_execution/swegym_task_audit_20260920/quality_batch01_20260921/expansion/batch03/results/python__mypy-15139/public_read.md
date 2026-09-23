# python__mypy-15139：fresh 公开要求静态审查

本题公开材料足以定位诊断显示的调查入口。主要未定项是最终命名政策及其覆盖范围：题面明确允许“统一别名”和“沿用源码别名”两条路线，没有指定唯一输出。公开代码又存在 Python 版本及强制大写选项的约定，不能把旧测试中的 `Type[...]` 直接当作默认输出必须维持不变的证据。以下均为静态阅读；没有运行项目、导入项目模块、安装依赖、测试或构建。

审查输入：角色卡 `roles/public_reader.md`（协调者指定的完整路径）与本题 `PUBLIC_DIR`。下列相对路径均相对于本题公开包。`base_identity.json:2-17` 声明提交为 `16b936c15b074db858729ed218248ef623070e03`，导出 1360 个跟踪条目，无 gitlinks、未物化 LFS 指针或 Git 元数据；这些是包内记录，不是本次对实际容器的验证。

## 1. 需求表与信息层次

| 行为或约束 | 判定层次 | 公开依据与含义 |
|---|---|---|
| 消除 `type`、`builtins.type`、`Type` 在错误和 note 中的混用困惑 | 明示 | `user_prompt.txt:3-21` 给出 `x: type[type]` 与 `reveal_type(type[type])`，列出三种拼法；请求改善显示一致性。 |
| 可以统一选择一个别名，也可以沿用代码中的别名 | 明示、存在多种合理实现 | `user_prompt.txt:18-21` 明确为 OR，没有指定必须使用小写、必须使用 `typing.Type`、必须保留 import 重命名或必须完全消除模块限定名。 |
| 同时检查 reveal note 与常规错误显示 | 明示场景，可定位实现入口 | `base/mypy/checkexpr.py:3936-3949` 调用 `MessageBuilder.reveal_type`；`base/mypy/messages.py:1630-1642` 使用 `TypeStrVisitor`，但不可索引错误调用 `format_type`（`:410-424`）。只改变其中一条路径可能仍留下题面指出的混用。 |
| 保留类型含义、类型参数和正常的类型检查结果 | 可由仓库及问题范围合理推知 | `base/docs/source/kinds_of_types.rst:600-607,670-675` 说明 `type[C]` 表示 C 或其子类的类对象；`base/mypy/types.py:2747-2759` 区分 `Type[C]` 与精确类构造器 callable。题目是命名显示问题，没有要求合并这些内部类型或改变推断。 |
| 不把“不可索引”改为成功，或为了消除错误而把类型变成 Any | 可由问题范围合理推知 | 题面将不可索引错误作为命名混用的展示位置，未请求实现新的索引能力（`user_prompt.txt:6-21`）；旧公开测试仍检查类似错误（`base/test-data/unit/check-generics.test:503-505`、`base/test-data/unit/pythoneval.test:1789-1804`）。应先确认指定 base 的实际复现结果；这里不声称已复现。 |
| 考虑 Python 版本与强制大写设置 | 既有实现和测试约定，非题面唯一答案 | `base/mypy/options.py:358-364`：Python 3.9 起且未强制大写时 `use_lowercase_names()` 为真；更早版本为假。`base/mypy/main.py:737-739` 注册隐藏的可反向切换选项。`base/test-data/unit/check-lowercase.test:2-44` 已验证 tuple/list/dict/set 的大小写切换。合理修复应解释如何兼容此政策，不应把题面中的“一种别名”机械理解为取消所有配置。 |
| 保留一般 reveal 的全限定名和错误中的同名消歧能力 | 可由现有接口合理推知；与题面“everywhere”有边界疑义 | `base/mypy/types.py:2992-3008` 的 Instance 打印器通常使用 fullname；错误格式化器会在需要时选 fullname（`base/mypy/messages.py:2409-2415`），并专门识别同名不同类型（`:2583-2601,2637-2655`）。统一 `Type`/`type` 大小写并不自动等于所有场景去掉 `builtins.`。 |
| 是否连固定文本、调试表示、裸 `type`、别名重命名都必须统一 | 仍有多种合理解释 | 题面没有细分；另有固定的 `Cannot instantiate type "Type[...]"`（`base/mypy/messages.py:1646-1649`）和语义分析诊断（`base/mypy/typeanal.py:561-570`）。它们扩大了“everywhere”的可能范围，但不是题面列出的直接复现。 |

三层信息不能混在一起：

- **Issue 目标**就是上表的显示一致性；报告环境为 mypy 0.961、CPython 3.10.4、Windows 10、无 flags/config（`user_prompt.txt:23-27`）。该环境不是指定 base 的版本证明；公开源码 `base/mypy/version.py:7-11` 已是 `1.4.0+dev`。
- **Harness 操作指令**位于 `public_bundle.json:1` 的 `public_hints`：探索代码、只编辑非测试源文件、禁止修改测试、可窄范围运行测试、完成后短总结。`allowed_tools` 为 bash/edit，工作目录声明为 `/testbed`。
- **环境事实声明**包括 conda `testbed` 已激活和工具已指向它；它们仍待 actor 验证。`environment_brief.md:3-12,20-26` 明确这是静态渲染，未核验实际模型消息、shell、资源和依赖。bundle 会写入可见路径，字段没有出现在 `user_prompt.txt` 不代表不可读。

## 2. 合理实现范围

可接受的路线不只一种：

1. **规范化显示**：在既有版本/选项政策下，统一类对象类型的显示拼法。以 3.9+ 默认小写、兼容旧目标版本和强制大写设置为政策，公开仓库支持最充分；但这不是题面写死的唯一目标。将两个打印入口分别调整、抽取共用规则，或经其他内部结构得到相同语义的结果，都不应因代码形态不同被排除。
2. **保留输入拼法**：题面明确允许。公开语义分析已把 `typing.Type` 与受支持的 `builtins.type` 归约为 `TypeType`（`base/mypy/typeanal.py:549-570`），其自身字段只有 item（`base/mypy/types.py:2775-2792`），当前打印器也说明不保留原格式（`:2939-2949`）。因此这条路线可能需要额外来源信息，并处理由推断生成而非显式注解的类型；复杂度较高不使其失去题面授权。
3. **全局规范化为另一种明确别名**：题面文字允许选择别名；若选择与既有版本/配置政策不同的政策，必须明确说明其作用域及兼容影响，不能仅因不同于某个未公开参考实现而否定。也不能忽略本仓库已经明确的强制大写开关语义。

有证据的输出约定包括 `Revealed type is "..."` 的 note 形式（`base/mypy/messages.py:1630-1632`）、错误中通常对类型加引号的接口（`:2604-2634`）、嵌套类型结构与参数含义，以及同名类型消歧。题面没有给新输出快照；例如是否接受 note 中 `type[builtins.type]`、错误中 `type[type]` 仍保留限定名差异，公开材料不能唯一决定。不能把“全部必须逐字符变成某个字符串”包装成明示要求。

旧测试应结合运行配置解读：`base/mypy/test/testcheck.py:128-131` 会对文件名不含 `lowercase` 的类型检查测试强制旧拼法；`base/mypy/test/testpythoneval.py:50-58` 也传入强制大写参数。因此 `check-generic-alias.test:84-114` 中 Python 3.9 的 `Type[builtins.int]`、`check-classes.test:3989-4019` 的类对象 reveal，支持兼容旧显示路径，不能证明 3.9+ 默认命令行必须显示大写。已读 `check-lowercase.test` 仅覆盖 tuple/list/dict/set，未提供本问题 `TypeType` 新行为的精确公开验收。

本审查没有写修复，也没有依据参考补丁推测唯一实现。

## 3. 初态线索与疑义

调查入口明确：完整的小例子、所报环境、指定 base、两个消息入口及其共同内部类型均可从公开包获得。两条显示路径中的 `Type[...]` 是可见的固定拼法：`base/mypy/messages.py:2519-2526` 与 `base/mypy/types.py:3188-3189`。错误路径对子类型使用短名而 reveal 的 Instance 使用 fullname，能静态解释题面混用的来源，但尚不是经过执行验证的根因结论。正常查调用者、确认类型对象在两种上下文中的表示，是开发工作，不是题面资料缺陷。

关键疑义及影响：

- **大小写与限定名范围**：题面把 `type` 和 `builtins.type` 也列为不一致，现有一般显示规则又有意区分短名/fullname。仅统一 `Type`/`type` 是否已满足“everywhere”，需要接受多种合理解释或由协调者补充只含公开需求的说明。它不会阻止实现最小显示改进，但影响何种结果算完成。
- **源码别名路线的兜底规则**：同一个类型来自 `Type`、`type`、import 重命名、推断或多个模块时，如何选显示名称没有规定。现有测试可解释旧行为，不能替代新政策。
- **问题报告与 base 版本不同**：所报 0.961 与 base 的 1.4.0+dev 不同；实际 actor 应先运行最小案例，不能把老报告输出当作当前容器实测。未发现这要求恢复 0.961、安装 Windows 或下载未来代码；这里关注的是指定 base。
- **测试编辑指令适用性**：若原“禁止改测试”仍适用，源代码显示修复有明确可编辑入口，但不能新增/更新测试快照；原测试可用于检查兼容路径，新行为可用临时命令行输入核对。若不适用，合理开发可新增/更新相关公开测试。是否有某些官方文件被恢复，仍需协调者核对当前具体机制。`environment_brief.md:20-26` 已说明“所有测试修改都会恢复、永不计分”不再代表统一机制；这不授权自行取消原禁止指令，也不构成判题目不可用的依据。
- **真正可能阻断执行的缺口**：actor 的解释器/依赖可用性、源码是否被已编译的 `.so` 遮蔽、typeshed 和测试资产是否存在、可写临时目录，以及必要时的离线依赖供应。当前只有声明；应做最小 CPU 验证。不能据缺证据断言环境坏了。

当前未发现必须从公开外链补回的附件或关键内容。README 和文档中的网页链接未访问；相关类型语义、安装方法、测试入口已有本地资料。公开祖先历史没有导出，本次没有识别必须依赖它才能理解需求的理由；未请求或访问共享镜像克隆。

## 4. 开发需求表与建议命令

以下命令**全部为建议，未执行**，面向真实 actor 的 `/testbed` 工作区；不是让本次静态审查去运行。优先先导入和单题复现，再跑相关公开测试。无需 GPU、外部 API、数据库或模型推理服务来执行这个显示问题的最小开发验证；这是从已读本地 CLI/测试入口推知的需求范围，不是整仓资源认证。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小命令与预期现象 |
|---|---|---|---|---|
| Python 解释器与当前源码导入 | `base/setup.py:223-236` 要求 Python ≥3.7 与运行依赖；题面用 3.10；`base/mypy/__main__.py:9-15,36-37` 是模块入口 | `public_hints` 声称 conda 已激活；`environment_brief.md:9-12` 要求 actor 验证 | 实际版本、可执行文件、导入路径、预编译扩展是否遮蔽源码未知 | **建议，未执行**：D1。成功应显示解释器及 `/testbed` 下的模块路径，且无导入错误；若落到 site-packages 或 `.so`，要确认修改是否生效。 |
| 运行时依赖和 typeshed | `base/mypy-requirements.txt:2-5`；`base/setup.py:81-84,223-228`；公开包有 `mypy/typeshed/stdlib/builtins.pyi:144-188`、`typing.pyi:156-175` | base 是跟踪文件导出；不证明真实镜像已装依赖/可读资产 | typing_extensions、mypy_extensions、按 Python 条件启用的 tomli/typed_ast 版本未知 | **建议，未执行**：D1、D2。成功应能加载模块并类型检查，不出现缺模块或 typeshed 找不到。 |
| 最小静态复现 | `user_prompt.txt:6-10`；`base/test-data/unit/README.md:137-154` 支持 `python -m mypy -c`；`base/docs/source/command_line.rst:104-113,244-253` 支持隔离 config/目标版本 | bash/edit 与 `/testbed` 仅为公开配置说明 | base 上的真实 stdout、退出状态未测 | **建议，未执行**：D2。按静态源码预计旧行为会保留 note 的 `Type[builtins.type]` 及错误中的 `Type[type]`，并可能仍有题面的 Any note；具体行号、完整消息和当前 base 行为须实测。此命令含预期类型错误，非零退出不能直接认作环境故障。 |
| 版本与选项兼容性 | `base/mypy/options.py:358-364`；`base/test-data/unit/check-lowercase.test:2-44`；`base/test-data/unit/check-generic-alias.test:3-20,46-63,84-114` | 未提供已执行证据 | 默认与强制大写路径的预期政策、源码别名路线的兜底仍需落实 | **建议，未执行**：D3。在选用版本规范化路线时，3.9+ 默认应采用选定现代拼法，强制大写及旧目标版本应保持相应兼容；不应改变参数含义。旧 base 可能全部仍打印 Type，故这是行为对照而非全都应成功的新行为断言。 |
| 窄范围公开测试及临时写入 | `base/CONTRIBUTING.md:73-95`；`base/test-data/unit/README.md:122-135,181-189`；`base/pytest.ini:21-24` 默认并行；`base/mypy/test/config.py:16-19` 使用临时目录 | 2 CPU/4 GiB、tmp/home 限额仅为默认 profile；实际未验证 | pytest/插件依赖、临时写权限及资源峰值未知 | **建议，未执行**：D4。`-n0` 限制为单进程；初态应按旧快照工作，修复后应保留未要求改变的路径。快照差异需区分预期显示变化和实际回归，不可靠修改测试逻辑规避。 |
| 安装/构建（仅确有需要） | `base/CONTRIBUTING.md:39-45` 给测试依赖与 editable 安装；`base/pyproject.toml:1-18` 是构建依赖；`base/setup.py:88-96,179-180` 默认不编译 mypyc | 网络不保证能访问公网；解释器/系统包写权限须核对（`environment_brief.md:9-12`） | 离线依赖资产、安装权限未知 | **建议，未执行**：D5。已有可运行源码时不需安装或编译；离线 editable 安装仅在构建依赖已满足时应成功。缺依赖应补预装或离线 wheel，不能假定联网 pip 可用。 |

D1 — 最小导入与路径核对（建议，未执行）：

```bash
cd /testbed
python -c 'import sys, mypy, mypy.messages, mypy.types; print(sys.version); print(sys.executable); print(mypy.__file__); print(mypy.messages.__file__); print(mypy.types.__file__)'
python -m pip check
```

D2 — 对题面程序做静态检查，不执行被检查程序（建议，未执行）：

```bash
cd /testbed
python -m mypy --config-file= --python-version 3.10 --no-site-packages --no-incremental --cache-dir=/dev/null -c $'x: type[type]\nreveal_type(x)\nreveal_type(type[type])'
```

这里显式设目标版本并禁用配置/第三方包搜索，目的是减少 actor 默认解释器、项目配置与包发现造成的偏差；不是宣称原报告用过这些 flags。`--no-incremental` 仍可能写缓存，故另设 cache-dir（文档 `base/docs/source/command_line.rst:747-754`）。此显示问题不要求运行 `x` 或执行 `reveal_type` 的 Python 运行时代码。

D3 — 别名、版本和强制大写对照（建议，未执行）：

```bash
cd /testbed
python -m mypy --config-file= --python-version 3.9 --no-site-packages --cache-dir=/dev/null -c $'from typing import Type\nx: type[type]\ny: Type[type]\nreveal_type(x)\nreveal_type(y)'
python -m mypy --config-file= --python-version 3.9 --force-uppercase-builtins --no-site-packages --cache-dir=/dev/null -c $'from typing import Type\nx: type[type]\ny: Type[type]\nreveal_type(x)\nreveal_type(y)'
python -m mypy --config-file= --python-version 3.8 --no-site-packages --cache-dir=/dev/null -c $'from typing import Type\ny: Type[type]\nreveal_type(y)'
```

D4 — 公开测试，先小范围再按修改范围追加（建议，未执行）：

```bash
cd /testbed
python -m pytest -n0 -q mypy/test/testcheck.py::TypeCheckSuite::check-lowercase.test
python -m pytest -n0 -q mypy/test/testcheck.py::TypeCheckSuite::check-generic-alias.test
python -m pytest -n0 -q mypy/test/testcheck.py -k 'testTypeApplicationCrash or testTypeConstructorReturnsTypeType'
python -m pytest -n0 -q mypy/test/testpythoneval.py -k testTypeAliasNotSupportedWithNewStyleUnion
```

最后一条为包含完整 typeshed 的 PythonEvaluationSuite；其公开实现先类型检查，只有无错误且无输出时才执行程序（`base/mypy/test/testpythoneval.py:75-94`）。此特定旧用例期待类型错误；不是要求一般使用者直接运行题面 Python 程序。旧大写快照因测试 runner 强制大写而可能在合理修复后保持不变。以上选择不宣称覆盖隐藏验收或整个仓库。

D5 — 已有依赖但确需建立源码安装时（建议，未执行）：

```bash
cd /testbed
python -m pip install --no-index --no-build-isolation --no-deps -e .
```

这条命令不会补足缺失的运行/构建/测试依赖；仅用于依赖已在镜像或 actor 环境中满足的情况。运行时修改无须 mypyc/C 编译。若编译扩展遮蔽源码，应按实际容器条件处理后重新核对路径，而不是把一次导入成功误作源码修复已被加载。

## 5. 阅读范围与限制

实际打开全文或带上下文片段的文件：

- 包元数据：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。
- 安装及测试说明：`base/README.md`、`base/CONTRIBUTING.md`、`base/setup.py`、`base/pyproject.toml`、`base/pytest.ini`、`base/conftest.py`、`base/test-requirements.txt`、`base/mypy-requirements.txt`、`base/build-requirements.txt`、`base/test-data/unit/README.md`。
- 类型/命令文档：`base/docs/source/kinds_of_types.rst`、`base/docs/source/builtin_types.rst`、`base/docs/source/command_line.rst`。
- 源码：`base/mypy/messages.py`、`base/mypy/types.py`、`base/mypy/options.py`、`base/mypy/typeanal.py`、`base/mypy/checkexpr.py`、`base/mypy/main.py`、`base/mypy/version.py`、`base/mypy/__main__.py`。
- 测试 runner/辅助代码：`base/mypy/test/testcheck.py`、`base/mypy/test/testpythoneval.py`、`base/mypy/test/helpers.py`、`base/mypy/test/testtypes.py`、`base/mypy/test/config.py`。
- 公开测试片段：`base/test-data/unit/check-lowercase.test`、`base/test-data/unit/check-generic-alias.test`、`base/test-data/unit/check-generics.test`、`base/test-data/unit/check-classes.test`、`base/test-data/unit/check-python39.test`、`base/test-data/unit/pythoneval.test`。
- 类型存根片段：`base/mypy/typeshed/stdlib/builtins.pyi`、`base/mypy/typeshed/stdlib/typing.pyi`。

另在本题公开包内列举文件名，并对 `base/mypy`、`base/test-data` 中相关类型显示符号/字符串做只读 `rg` 搜索；搜索返回了 type visitor、测试辅助代码、其他测试和最小存根的少量匹配行，未把这些文件当作完整读过。`base/docs/source/runtime_troubles.rst`、`base/mypy/nodes.py`、`base/mypy/test/data.py` 等参与过定向搜索；只对实际返回的匹配行作阅读。尝试查找 `check-type-type.test` 时该文件不存在，随后按实际公开文件名定位，未推断为缺失必需资产。

未查：私有评分材料、gold、旧结论、其他题、角色卡父目录、项目调查、聚合资料、镜像克隆、任何仓库历史、联网内容，以及真实 actor 容器。没有修改 base；唯一交付文件为本 `public_read.md`。保存及文件校验属于文档操作，不是运行项目或验证候选修复。

`user_prompt.txt` 仅为静态渲染；base 导出不是完整运行容器。没有声称实际模型收到的消息、真实资源、conda 激活、依赖、测试通过或开发条件已验证。未接触本题私有材料；fresh 是本次协作阅读约束，不是文件权限隔离或预训练无污染证明。
