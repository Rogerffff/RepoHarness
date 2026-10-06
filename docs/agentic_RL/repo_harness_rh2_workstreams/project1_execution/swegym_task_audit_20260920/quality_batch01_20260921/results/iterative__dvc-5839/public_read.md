**iterative__dvc-5839：公开材料静态审查**

审查对象是公开包所列的 base_commit daf07451f8e8f3e76a791c696b0ea175e8ed3ac1。下文路径均相对 PUBLIC_DIR；源码路径以 base/ 开头。仅阅读角色卡和本题公开包，没有读取私有评分材料、gold、其它题、旧结论或 Git 历史，没有联网、运行项目代码、安装依赖、执行测试或修改 base。这里的“预计”是静态推断，不是运行结果。

公开材料足以定位题述问题，并将主要行为约定缩小为“让 CLI 选项按现有小数位语义影响表格输出”。题面单独保留了两种 precision 解释，但现有 CLI 帮助、格式化代码和公开测试都支持普通十进制的小数点后位数。实际容器可导入、可复现和可运行测试尚待验证。

**1. 需求表**

| 行为 | 公开依据 | 明确程度及审查判断 |
|---|---|---|
| dvc metrics show --precision n 应影响显示精度 | user_prompt.txt:3、8、12–20；base/dvc/command/metrics.py:250–258 | 题面明示。本例默认与 precision=8 显示相同，是需要消除的现象；不意味着对任意已足够短的数字，改变 n 都必须改变输出。 |
| precision 表示普通数值小数点后 n 位，默认 5 位 | base/dvc/command/metrics.py:11、32–38、254–255；base/tests/unit/command/test_metrics.py:303–333 | 仓库有明确帮助文字和数值测试。n=4、7 以及默认 5 的具体舍入值已公开约定；按科学计数法尾数的小数位重新解释同一个选项，会改变这些既有语义。 |
| 科学计数法输入同样适用精度选择 | user_prompt.txt:12–42；base/dvc/repo/metrics/show.py:48–59、81–91；base/dvc/utils/serialize/_yaml.py:23–31 | 题面明示输入，但未定唯一字符串形式。现有路径将 YAML 读为数值，再按 float 舍入，不保留原输入记法。按现有语义，precision=8 的两个数值应约为 0.00001483、0.00000001；是否显示为 1.483e-05、1e-08 属于呈现方式。实际 YAML/表格依赖行为仍待执行确认。 |
| 默认行为继续使用 5 位，已有调用者继续有效 | base/dvc/command/metrics.py:20、32–38；base/tests/unit/command/test_metrics.py:313–317；base/dvc/command/repro.py:22–24；base/dvc/command/experiments.py:538–541 | 公开仓库可合理推知的兼容要求。没有改变默认值、把 precision 变成必填参数，或改变 repro/experiments 默认显示的需求。 |
| 普通表格与 Markdown 表格应遵守同一 precision 选项 | base/dvc/command/metrics.py:92–98、234–238；base/dvc/utils/diff.py:88–107；base/tests/unit/command/test_metrics.py:354–372 | 公开仓库可合理推知。两种格式走相同数据格式化入口，区别是表格格式和 Markdown 末尾换行。当前公开测试没有直接验证 Markdown 与自定义 precision 的组合。 |
| JSON 与底层 metrics 数据保持原有数值输出 | base/dvc/command/metrics.py:79–90；base/dvc/repo/metrics/show.py:96–144；base/tests/func/metrics/test_show.py:17–30、108–119 | 兼容要求来自现有分支：JSON 直接序列化原数据，precision 属于表格显示。没有公开要求让 --show-json 的数值也舍入，或修改指标文件。 |
| 保留表头、嵌套键、修订列、整数与零值、缺失值等显示 | base/dvc/command/metrics.py:40–69；base/dvc/utils/diff.py:94–105、110–120；base/tests/unit/command/test_metrics.py:224–300、336–372 | 现有接口和精确字符串测试已约定：Path/Revision、点分嵌套键、排序后的指标列、缺失值 —、0 与 0.0 等。本题没有要求重设计这些格式。 |
| 保留 metrics diff 的既有精度行为 | base/dvc/command/metrics.py:108–138、157–162、326–334；base/tests/unit/command/test_metrics.py:133–154 | 公开仓库可合理推知；diff 已向其格式化入口提供 precision，且公开测试约定默认与自定义舍入。它是相关行为参照，不是题面新增功能。 |
| 顶层标量、precision=0/负数等边界 | base/dvc/command/metrics.py:35–38、54–57、250–258；base/tests/unit/command/test_metrics.py:246–253；base/tests/func/metrics/test_show.py:17–22 | 仍有未明示范围：顶层标量被直接转字符串，已有标量测试未带 precision；题述字典型样例不能证明必须一并改标量。0 和负数可被当前 int 参数接受，现有 round 路径也能处理；没有新增拒绝它们或把 0 当默认值的依据。边界应保留兼容，但不能声称题面逐项要求过。 |

题面“Version (1)”第一张表中的 mse=0.001e-09（user_prompt.txt:27–35）与下一张表的 0.00000001 并不等值：前者是 10^-12，后者是 10^-8。按样例值保留八位小数，后者符合现有语义。这一笔误不应作为必须逐字匹配的数值要求。题面的“Version (2)”及其偏好（:25、38–42）是报告者提出的另一种可能设计，并未明确要求新增选项或改成尾数精度。

**2. 合理实现范围**

可接受实现应把 CLI 的 precision 选择落实到现有指标表格语义，并保留未指定选项时的行为。公开契约不要求特定内部变量名、关键字/位置参数风格，也不要求采用某个固定函数拆分；保留当前帮助、数值结果及已有输出契约的不同内部组织方式都应有接受空间。本审查不提供修复代码或猜测标准补丁。

科学计数法与定点形式若表示同一个舍入后的数值，题面均给出了接受方向；不能仅由 issue 锁定 e 的拼写、尾零位数或所有空格。但也不能据此随意更改已有公开测试明确锁定的表格字符串，例如把普通的 0.0 全部改成 0.00000。base/dvc/utils/diff.py:94–100 使用 tabulate、disable_numparse=True，未建立“所有数字固定补足 n 位”或“统一改为科学计数法”的约定。

把 --precision n 改成 n 个有效数字，或把科学计数法尾数保留 n 位作为唯一行为，与现有帮助和公开精度测试不一致；若要引入这种功能，需要额外明确的产品要求，不能据报告者的疑问直接判为本题必需。当前公开材料没有要求新的 CLI 名称、输出列或文件格式。

**3. 初态线索与疑义**

- 调查入口足够具体：题面给出命令、两个完整 YAML 数值、默认/precision=8 的实际输出及报告时版本。源码可沿 metrics 参数定义（base/dvc/command/metrics.py:250–258）、CmdMetricsShow.run（:76–105）、_show_metrics（:14–69）、table（base/dvc/utils/diff.py:88–107）追踪。
- 静态可见的关键不一致是：CLI 定义了 precision，而 CmdMetricsShow.run 调用 _show_metrics 时未提供该值（base/dvc/command/metrics.py:92–98）；helper 已有 precision 参数及默认值（:20、32–38）。这是有力调查线索，尚不是已执行的复现证明。无需外部历史或未来修复对象即可发现。
- 公开测试解释了为什么现有测试通过仍不足以证明问题消失：test_metrics_show_precision 直接调用 helper（base/tests/unit/command/test_metrics.py:303–333）；命令测试 test_metrics_show 不传 --precision，且只检查 metrics 数据查询调用（:103–130）。应另用真实 CLI 样例检查选项生效。
- “Add some metrics”未给完整建仓/登记命令，但这只是正常查代码可补齐的步骤。显式 targets 支持未登记的 metrics 文件，且公开测试涵盖未初始化 DVC/无仓库读取（base/dvc/command/metrics.py:72–73、199–206；base/tests/func/metrics/test_show.py:108–122、171–176）。可用临时本地文件复现，不必取得用户的模型、S3 数据或训练流程。
- 报告环境是 Windows 10、Python 3.8.7、DVC 2.0.17（user_prompt.txt:53–65）；base/dvc/version.py:9 标识基线版本 2.0.18。版本差异应记录，但给定源码仍存在对应调查线索；当前材料不足以断言为 Windows 专属问题，也没有显示必须取得 Windows 或 NTFS 资产。
- 贡献文档和完整安装指南仅为外链（base/CONTRIBUTING.md:1；base/README.rst:88–92、200–206），本包没有其正文，未联网访问。现有帮助、setup.py 和公开测试足以开展本题的局部调查，暂不需要协调者补充外链内容或祖先历史。
- 真正待补证的是 actor 环境与依赖可用性、包导入来源、测试收集是否成功，而不是题目缺少预期根因。单凭静态导出不能确认 CPU/内存/临时目录配额、预装环境或可写权限已满足。

**4. issue、harness 操作指令与环境声明分开记录**

| 类别 | 公开内容 | 本次审查中的处理 |
|---|---|---|
| issue 需求 | user_prompt.txt:3–65；public_bundle.json:1 的 problem_statement | 修复 precision 无效，保留上述兼容契约。报告者系统信息是原问题背景，不是当前容器证明。 |
| harness 操作指令 | public_bundle.json:1 的 public_hints：探索源码、只改 NON-TEST 源文件、禁止改测试、运行窄测试、完成后简短回复 | 原指令仍应记录，审查未授权忽略。若本次求解适用，当前公开线索没有显示必须修改测试才能修复；验证可使用已有测试和 CLI 临时输入。若不适用，可以增加针对 CLI 传递的回归测试，但缺少新增测试不应被误作源码修复不可表达。是否应用到本次真实求解仍是共享输入问题。 |
| 旧机制解释 | public_hints 声称测试修改会全部恢复且永不计分 | environment_brief.md:18–24 已明确：这不能代表当前机制；当前取消按测试文件名统一排除，仍可能恢复具体官方文件。本公开角色未查具体文件清单，不推断哪些编辑最终会保留，也不据旧解释判定本题无效。 |
| 待验环境事实 | public_bundle.json:1 声称 /testbed、预激活 conda testbed、python/pip/测试工具指向该环境；另列镜像及 digest | 这些字段提供定位信息，未证明本次 actor 实际激活或依赖兼容。environment_brief.md:3–12 明示静态导出和未验状态。 |
| 共享输入可见性 | environment_brief.md:3–4、23–24；public_bundle.json:1 | user_prompt.txt 是静态渲染，没有还原实际模型请求。public_hints 未出现在该渲染中，不等于实际求解者不可读取；bundle 会写入公开容器路径。是否进入 CLI system message、实际工具与 shell 配置均未验证。 |

**5. 开发需求表**

下表及后续代码块中的所有命令均为“建议，未执行”。命令面向之后的真实 actor /testbed 环境，不表示应在本静态 base 导出里执行。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小命令及预计结果 |
|---|---|---|---|---|
| Python 与 checkout 导入 | base/setup.py:49–93、147–159；base/dvc/__main__.py:1–7；.github/workflows/tests.yaml:45–46 | environment_brief.md:8–12 仅描述拟用 actor 与待验解释器；public_hints 声称 conda 已激活 | Python 实际版本、依赖版本与导入位置未核验；setup 的 >=3.6 不足以保证任意新版本能跑老测试 | 建议，未执行：python -c "import sys, dvc; from dvc.command.metrics import _show_metrics; print(sys.executable, sys.version); print(dvc.__file__)"。预期导入成功且来源是 /testbed 的当前源码；失败先定位环境，不算已重现 precision bug。 |
| 格式化与 YAML 解析依赖 | base/setup.py:65–67、81–82；base/dvc/utils/flatten.py:1–4；base/dvc/utils/serialize/_yaml.py:23–31；base/dvc/utils/diff.py:88–100 | 未提供安装清单或实际 import 结果；禁止假定公网下载可用（environment_brief.md:10） | ruamel.yaml、flatten_dict、tabulate 及正常 DVC 导入链是否可用/兼容 | 建议，未执行：python -c "from ruamel.yaml import YAML; import flatten_dict, tabulate; print('imports ok')"。预期成功；这只是定点依赖探测，不能替代完整 CLI 导入。 |
| 最小输入资产与 CLI 复现 | user_prompt.txt:12–20；base/tests/func/metrics/test_show.py:108–122、171–176 | 理论上只有两行本地 YAML，workspace/home 可写是 profile 声明，不是本题实测 | 临时目录是否可写、显式 target 路径读取能否成功 | 建议，未执行：执行下方临时目录复现块。基线预计默认和 precision=8 都显示 1e-05、0.0；修复后 precision=8 应代表 0.00001483、0.00000001，而默认仍按五位舍入。 |
| 最窄公开精度测试 | base/tests/unit/command/test_metrics.py:133–154、303–333；base/setup.cfg:22–26；base/test_requirements.txt:4–9 | 没有 actor 身份的收集或测试结果 | pytest 6.2.3、相应插件与根 conftest 导入链未核验 | 建议，未执行：DVC_TEST=true python -m pytest -q tests/unit/command/test_metrics.py::test_metrics_show_precision tests/unit/command/test_metrics.py::test_metrics_diff_precision。基线预计已通过；它们验证旧 helper 契约，不能独立检出 CLI bug。 |
| 命令级公开回归检查 | base/tests/unit/command/test_metrics.py:12–46、103–130、224–372 | 环境说明仅允许/建议窄测试 | fixture 所需临时目录、DVC 初始化及全部收集依赖待验 | 建议，未执行：DVC_TEST=true python -m pytest -q tests/unit/command/test_metrics.py。修复前后原则上均应通过；新行为仍需 CLI 复现比较。 |
| 本地 metrics 读取/仓库集成 | base/tests/func/metrics/test_show.py；base/tests/dir_helpers.py:92–112、294–320、324–348；base/tests/func/conftest.py:7–28 | 2 CPU/4 GiB 等仅为默认 profile 声明（environment_brief.md:9–12） | Git 可执行文件、Git 身份、可写 temp/cache、子进程和锁行为未实测 | 建议，未执行：git --version；DVC_TEST=true python -m pytest -q tests/func/metrics/test_show.py。本文件本地生成指标，部分测试创建 Git 分支/标签或执行小型复制脚本；预计无需训练数据或云账户。 |
| 测试收集时的附带依赖 | base/tests/conftest.py:6–7；base/tests/remotes/__init__.py:5–35；base/tests/remotes/s3.py:7；base/tests/remotes/webdav.py:7；base/tests/basic_env.py:7–13 | 没有声明这些包确实已安装 | 即使只跑本地测试，根 conftest 仍导入 remotes，moto、wsgidav 等缺失也会造成 collection error；关闭远端标记不等于避开顶层 import | 建议，未执行：DVC_TEST=true python -m pytest --collect-only -q tests/unit/command/test_metrics.py。预期成功列出测试；若在 import 处失败，需由环境准备补齐兼容预装包。 |
| 安装/构建与网络 | base/README.rst:138–156；base/setup.py:117–144；base/.github/workflows/tests.yaml:73–81 | environment_brief.md:10 不假定公网文档/依赖可达；解释器与系统包写权限待验 | CI 的完整安装包含所有远端及两个 Git 外部依赖，不能直接当作本题最小前提；没有离线 wheelhouse 或完整锁定传递依赖的证据 | 本题局部改动无独立编译需求。若仅缺 checkout 的可编辑关联且依赖已备齐：建议，未执行：python -m pip install --no-deps --no-build-isolation -e .。若缺依赖，需要预制兼容环境或已声明离线来源；不建议在受限 actor 中盲跑公网安装。 |

最小 CLI 复现（建议，未执行；在真实 actor 中创建临时输入，不修改仓库测试）：

~~~sh
audit_metrics_dir=$(mktemp -d)
cat > "$audit_metrics_dir/metrics.yaml" <<'YAML'
mae: 1.4832495253358502e-05
mse: 5.0172572763074186e-09
YAML
cd "$audit_metrics_dir"
DVC_TEST=true PYTHONPATH=/testbed python -m dvc metrics show metrics.yaml
DVC_TEST=true PYTHONPATH=/testbed python -m dvc metrics show metrics.yaml --precision 8
DVC_TEST=true PYTHONPATH=/testbed python -m dvc metrics show metrics.yaml --precision 8 --show-md
DVC_TEST=true PYTHONPATH=/testbed python -m dvc metrics show metrics.yaml --precision 8 --show-json
~~~

预计默认仍是 1e-05、0.0；precision=8 的普通及 Markdown 表格应显示等于 1.483e-05、1e-08 的舍入后数值；JSON 继续包含原始读取的数值。这里没有把对齐空格或科学计数法拼写作为尚未执行的精确断言。DVC_TEST 的本地测试用途可见 base/tests/conftest.py:9–12。直接从当前 checkout 的模块入口运行，是为了验证实际改动的源码，仍需核对真实导入来源。

功能测试涉及 Git 提交时需要可用的测试身份；旧 CI 明确配置过身份（base/.github/workflows/tests.yaml:82–85），但本包不能证明 actor 已配置。仅对本次命令设置临时 Git author/committer 环境变量即可作为后续验证方案，无需把全局用户配置改成旧 CI 身份。

base/tests/__main__.py:17–20 默认增加并行、覆盖率和详细报告。对这两个窄模块，直接运行上述 pytest 命令更贴合最小资源验证；不需要据旧 CI 的全仓 --all、-n=4 推导出 Docker、云凭据、所有远端服务或全仓测试是本题前提。是否存在隐藏验收不属于本公开角色要求提供的开发输入。

**6. 阅读范围与限制**

完整打开：

- 角色卡 public_reader.md；user_prompt.txt；public_bundle.json；environment_brief.md。
- base/dvc/command/metrics.py；base/dvc/repo/metrics/show.py；base/dvc/utils/diff.py；base/dvc/utils/flatten.py；base/dvc/utils/serialize/_yaml.py；base/dvc/command/repro.py；base/dvc/__main__.py；base/dvc/version.py。
- base/tests/unit/command/test_metrics.py；base/tests/unit/test_metrics.py；base/tests/func/metrics/test_show.py；base/tests/conftest.py；base/tests/func/conftest.py；base/tests/remotes/__init__.py；base/tests/__main__.py。
- base/README.rst；base/CONTRIBUTING.md；base/setup.py；base/setup.cfg；base/pyproject.toml；base/test_requirements.txt；base/.github/workflows/tests.yaml。

部分打开：base/dvc/command/base.py:1–57；base/dvc/command/experiments.py:520–545；base/dvc/cli.py:1–135；base/tests/dir_helpers.py:48–116、290–380；base/tests/remotes/s3.py:1–22；base/tests/remotes/webdav.py:1–20；base/tests/basic_env.py:1–100；base/dvc/fs/gdrive.py:1–60。

此外使用 rg 做文件名/符号检索；部分命中只读了命中行，未全文审查。包括 base/tests/remotes 下的 base、azure、gdrive、gs、hdfs、http、local、oss、ssh、webhdfs 等模块的 import/fixture 行，以及 base/dvc/dagascii.py、istextfile.py、progress.py、ui/__init__.py、utils/__init__.py、stage/monitor.py、parsing/context.py 的相关符号命中。检索发现 base/dvc/compare.py 和 base/tests/func/metrics/conftest.py 不存在；未将缺失的猜测路径当作证据。其余文件名枚举不代表打开了内容。

未查：私有材料、标准答案、未来 Git 对象、公开祖先历史、外部文档正文、tabulate/ruamel.yaml 的实际安装源码与版本、真实容器及 actor 资源/权限/依赖、实际模型消息与工具配置、任何运行结果。没有因本地能读取导出就声称运行环境可用。此次未接触本题私有材料；这种范围控制只是协作约定，不是文件权限隔离或预训练无污染证明。

关键未知集中在三个方面：实际 actor 的导入/测试条件是否成立；public_hints 的真实注入与禁止改测试指令适用范围；题面是否有意扩展到顶层标量和科学计数法尾数精度。前两项应通过共享输入及运行验证补证；第三项已有仓库语义足够支持当前小数位修复，无需先猜额外产品设计。
