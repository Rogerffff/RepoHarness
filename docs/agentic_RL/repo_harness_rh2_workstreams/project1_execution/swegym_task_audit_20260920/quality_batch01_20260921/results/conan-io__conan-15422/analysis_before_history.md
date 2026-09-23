# conan-io__conan-15422：历史读取前分析

2026-09-21；私有主审。此稿在任何本题旧调查/history 引用读取前保存。仅静态读指定原件、以标准库核 JSON/哈希；未运行 Conan、pytest、CMake、安装、容器或模型。已读本题 `public_read.md`，不曾读 reviewer 文件。下文源码路径相对 `PUBLIC/base/`；`ROOT=${REPO_ROOT}`，`PUBLIC=ROOT/runs/swegym_quality_batch01_20260921_v2/public/conan-io__conan-15422`，`PRIVATE` 同根的 `private/conan-io__conan-15422`。

**暂定处置：needs_review / static_review，可作为范围明确的开发诊断候选；不是 ready_for_probe。** Linux 普通正整数安装路径有真实失败/修复证据；没有发现绑定 gold 内部实现的误拒约束。但只有一个显式值断言，默认并行度、多配置新增条目的 jobs、实际 CMake 消费和生成器兼容性未得到功能验收。对 gold 无条件向所有生成器添加 jobs 的兼容风险只作静态疑点，不据此宣判 gold 错误或题目拒绝。

## 1. 材料、初始问题与公开规格

- public/grading 的 base 均为 `f08b9924712cf0c2f27b93cbb5206d56d0d824d8`；`base_identity.json` 记录 tree `c6db74a43d17809b8abb51050c6be72c58461ff0`、1002 个条目、字节验证通过、无 Git 元数据。未重新导出 Git tree；这是物化记录，并非 actor 容器证明。
- 已用只读标准库比较 source_refs 指向的 S2 public/grading/validation JSONL 第 38 行与本包，三者均相等；`test.patch == grading.test_patch`、`gold.patch == validation.golden_patch`。gold SHA256 为 `1bcbaa52ea35d4893b8eb55e921f082ce73d7948e355f5a4d8657f4b1b620e66`。
- 题面要求生成 `buildPresets[*].jobs`，使 `conan install` 后的外部 `cmake --build ... --preset ...` 能并行；示例 16 是值例，不是常数要求。报告环境 Ubuntu 23.10/Conan 2.0.14/CMake 3.27.4；实际 base 运行日志包版本 2.1.0-dev。不能把报告环境与精确 base 版本混称。
- 公开仓库 `conan/tools/build/cpu.py:8–28` 已定义 `build_jobs`：尊重 `tools.build:jobs`，缺省使用 cgroup/CPU 检测；`conan/tools/build/__init__.py:8` 已导出 helper。题面未指定调用这个内部/公开 helper 的代码形状，但既有配置契约支持沿用值来源。
- 初态调用链为 `CMakeToolchain.generate()` (`toolchain/toolchain.py:187–232`) → `write_cmake_presets()` → `_CMakePresets.generate()` → 首次 `_contents()` 或已有多配置分支 → `_build_preset_fields()` (`presets.py:15–19,54–68,85–104,189–192`)。两条路径的 build 字典均无 jobs。源码缺口与下述 noop 的 KeyError 相符。
- public_hints 包含“仅改非测试源码”“不改测试”和“测试修改永不计分”的旧机制措辞；静态 `user_prompt.txt` 未包含 hints，实际 CC 消息及 hints 注入待核。共同环境卡说明当前不按测试文件名一概排除；本题原始评分日志只证明指定官方文件被恢复。不能据静态 prompt 缺少 hints 就认定 actor 看不到它。

## 2. 新测试的完整展开和双向映射

F2P 唯一 ID：`conans/test/integration/toolchains/cmake/test_cmaketoolchain.py::test_presets_njobs`。test patch 只在文件末新增八行，不改普通源码。

其完整过程：`TestClient()` 创建临时 current/cache 目录及默认 profile；`save({"conanfile.txt": ""})` 写空 recipe；`run('install . -g CMakeToolchain -c tools.build:jobs=42')` 通过真实 Conan CLI/API 执行安装/生成；从 current folder 读 JSON；断言第一个 build preset 的 `jobs == 42`。没有针对 jobs 的 Mock。`TestClient.run` 的 requests/getpass/IO 替代用于隔离外部交互，不直接伪造预设结果 (`conans/test/utils/tools.py:374–434,492–569,606–616`)。命令异常会由测试工具报错，不能靠跳过生成直接到断言。

公开 Linux 默认 profile 为 gcc/Release (`conans/test/conftest.py:199–207`)，工具链默认生成器选择落在 Unix Makefiles (`toolchain.py:234–270`)；conftest_user 可覆盖 profile (`conftest.py:235–239`)，实际镜像该文件未单独读取。因此“Unix Makefiles”是源码默认路径推断，日志没有打印本 F2P 的生成 JSON。测试不调用 CMake，不启动编译器，不测真实并发或速度。

| 公开要求/合理旧行为 | 公开依据 | 对应测试与关键断言 | 覆盖判断 / 证据 |
| --- | --- | --- | --- |
| 安装生成的 build preset 带 jobs，显式配置应传递 | 题面前后 JSON；`cpu.py:8–28` | 唯一 F2P：空 recipe、jobs=42、`buildPresets[0]["jobs"] == 42` | 覆盖一个正整数、一次安装、默认生成器；noop KeyError，gold pass。既不是 helper 身份测试，也不要求字典键顺序。 |
| 未配置时使用 Conan 的可用 CPU 默认值 | `cpu.py:11–20,31–54`；现有 CMake helper 使用 build_jobs | F2P 显式设置 42；相关 P2P 不断言 jobs | 缺失。只在显式配置时写字段的部分实现可满足已见断言，却留下通常 install 的原缺口。是否实际全套得分需另做 CPU 反例。 |
| 其它合法正整数应原值传递 | 同配置契约；示例 16 | 仅 42；公开 `cpu_count_test.py::TestNJobs::test_cpu_count_override` 测 helper 值 5，但不属本题 P2P | 部分。固定 42 在静态断言层无法区分；这不是已实测成功的攻击。`==42` 也未显式检查 JSON 数字的 Python 类型。 |
| 保持名称、configurePreset、单配置覆盖和多配置追加/同名替换 | `presets.py:54–83,176–229` | P2P `test_cmake_presets_singleconfig`、`test_cmake_presets_multiconfig`：数量、configuration、名称/引用；跨多次安装 | 旧结构行为有保护；多配置每次新增条目的 jobs 仍不测。只在 `_contents()` 首次分支添加字段可能漏后续配置。 |
| 保持自定义布局、路径、用户预设包含关系与不覆盖用户文件 | `presets.py:47–53,232–330` | P2P `test_cmake_presets_binary_dir_available`、`test_cmake_presets_shared_preset[...]`、`test_user_presets_custom_location[...]`、`test_recipe_build_folders_vars`、`test_avoid_ovewrite_user_cmakepresets` | 相关结构/路径/错误行为有覆盖；没有实际外部 CMake 读取 jobs。 |
| Ninja/MSVC 的 architecture/toolset 仍正确 | `presets.py:126–143` | 四个 `test_presets_ninja_msvc[arch-arch_toolset]` P2P；断言 configurePresets 的值和 external strategy | 覆盖生成的元数据；不执行 Windows 构建，不证明 jobs 与 MSBuild/NMake 的兼容性。 |
| 对不同 generator 保持合理的并行策略 | `cmake.py:11–23` 对 Makefiles/Ninja 加 -j、排除 NMake；`blocks.py:237–252` 对 Visual/MSVC 使用 /MP | 新 F2P 没指定 generator；上述 P2P 不消费 jobs | 未唯一规定。命令行旧策略是兼容线索，不等同新的 preset 规范；不能仅凭差异宣告 gold 错或要求所有合理解无条件加字段。 |
| jobs 字段在题面 CMake 构建命令中实际生效 | 题面命令与性能目标 | 无新增构建执行/并行观测 | 缺失。当前验收证明 JSON 字段传递，不证明实际后端启动数或加速倍数。 |

反向检查：唯一新增强制要求 `jobs` 的键名、层级来自题面；42 来自测试自身输入并沿用已有配置，不是题面隐藏魔数规范。未见精确文案、私有 helper 名或 Mock 调用形状约束。P2P 保留旧接口行为有公开来源，不因条目数多就推断并行语义受保护。

## 3. 合理替代解、部分解与 gold

**非 gold 的合理路线：**在生成流程上游求 `build_jobs`，向首次与多配置插入的 build preset 都传值，保持 testPresets 不变；或提取并行策略 helper 后在 build preset 生成时应用。验收仅观察 JSON，不要求新增导入位置、局部变量名或特定函数修改。按已有 CMake 策略对 Makefiles/Ninja（含 Ninja Multi-Config）处理并对 NMake/Visual 做兼容判断，也是公开仓库支持的调查方向；是否应扩至全部生成器，应以对应时期规范/可执行兼容测试裁决，不能用 gold 本身当规格。

**有区分力的部分解：**只读显式 `tools.build:jobs`，未配置时省略字段。它保留 F2P=42 和所有既有结构，却不修默认安装；比纯硬编码更接近自然的不完整实现。最小 CPU 对照建议：原官方评分加上公开最小 recipe，分别设置 2、7 和不设值，默认值与该进程 `build_jobs` 对照；确认“官方通过但默认缺失”才登记实际漏收。另可用 Ninja Multi-Config 的 Release→Debug→Debug 三次安装检查追加/替换值，区分只改首次生成的实现。均未执行。

gold 只新增一条已有 helper 导入和给公共 build 字段函数赋值，依赖已在 base 中、没有未交付新包；两条生成分支均调用该函数，静态看覆盖首次、单配置重建、多配置追加/替换，且不改变 testPresets。无无关文件改动。它对 `None/0/负数` 和任何 generator 均无条件写入 `build_jobs` 的返回值：公开代码支持正常整数与 CPU 默认来源，但未提供足够 preset schema/后端行为证据来证明所有边界有效。Visual/MSVC 还已有 /MP，新增 preset jobs 可能改变并行层次；仅记兼容待核，不宣称 OOM 或坏题。

## 4. 真实运行原件与评分边界

运行根 `RUN=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w02-1`；本次对两日志 SHA256 均复算并与 PRIVATE/run_refs 一致。ledger 第 1、2 行分别是 noop/gold，来自 baseline 原镜像，没有 derived recipe。

| 角色 | 决定性原件 | 事实及限制 |
| --- | --- | --- |
| noop | `RUN/eval_logs/evallog_replay-f216-baseline01-w_434a958a.eval.log:130–139,686–728,863–940,983–994`；ledger:1 | HEAD=精确 base、初始 clean；官方文件恢复并 test patch clean apply；三个 requirements 安装步骤均已有依赖，无安装错误，最终 install rc=0；pytest 指定整文件 44 collected、40 passed/1 failed/3 skipped；目标 `KeyError: jobs`，test rc=1。F2P 0/1，P2P 0 fail/40。 |
| gold | `RUN/eval_logs/evallog_replay-f216-baseline01-w_e40da522.eval.log:687–725,889–950,957–1008`；ledger:2 | 投影只纳入 `conan/tools/cmake/presets.py`，gold digest 与 validation 相同；install rc=0；41 passed/3 skipped，目标明确 PASS，test rc=0；F2P 1/1、P2P 0 fail/40、reward=1。 |

两 ledger 的 reference_missing/reference_skipped 均空；三个 pytest skip 是非参考的 Apple 两例和 Windows path normalization。parser 的 `num_parsed_tests=42` 不是 collected=44 或执行通过数，不能代替逐条测试执行证据；本题 41 个参考项由日志 PASS/FAIL 与 ledger 共同支持。

条件：Linux/Python 3.10.14/pytest 6.2.5，rh2grader/54322，2 CPU/4 GiB、deny_all，解释器前缀可写；日志 PYTHONPATH 为 /testbed，ledger import path 指向 `/testbed/conans/__init__.py`。env_qualification 为 absent，image_id_actual 为 null，记录使用 digest 与 public 一致。这里只证明所记录评分条件；没有 actor 身份实际 shell、image inspect、资源稳定性复验或完整用户交互。

本题恢复文件只有 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`，日志明确从 base checkout 后应用 test patch。合法源码修复路径不会被此恢复覆盖，gold 投影 included 且 ignored 为空。未见 test patch 混入源码。`conftest_user.py` 可改变公开默认 profile，属于题目相关测试配置控制面；没有运行其篡改反例，也未完整重审平台隔离，因此不宣称抗评分控制面修改已证明。额外路径排除建议为空。

## 5. Actor 开发需求

| 必要操作/资产 | 公开依据 | 已有证据范围 | actor 缺口与最小验证（建议，未执行） |
| --- | --- | --- | --- |
| 查公开入口、导入工作区 Conan 和 TestClient | 上述调用链；requirements 三文件、pyproject；tools.py 的 CLI/API 导入 | grader 的依赖已满足且 import path 指向 /testbed | 以真实 agent shell 记录 UID/HOME/cwd、`command -v python`、sys.executable 与 Conan 来源，然后导入目标 helper/TestClient；不能由 grader 前缀可写代填 actor。 |
| 生成 JSON 的最小复现 | 空 recipe + CMakeToolchain 的公开安装用法；public_read C2 | 新 F2P 已执行生成，未调用 CMake | actor 临时 TestClient recipe，显式 jobs=2 与未配置两次生成；预期 base 缺字段、修复值匹配。使用临时文件，不改受恢复测试。 |
| 运行旧预设/配置测试 | integration 单/多配置测试及 cpu_count_test、cmd_line_args | 相关整文件 grader 已跑；其它两文件未在本次日志运行 | `python -m pytest -q ...test_cmaketoolchain.py -k 'test_cmake_presets_singleconfig or test_cmake_presets_multiconfig'` 加公开 helper 单测。检查 pytest 及依赖可用即可，无需系统 C++ 编译。 |
| 包/资产/服务与网络 | requirements；空 recipe 无 requires；TestClient 用本地 mock requester | 所读安装日志都为 already satisfied，评分 deny_all | 准备阶段若缺 Python 包，需预装/离线可用版本；解题与最小测试本身不需要公网、GPU、远端包仓库或账户。未核真实 actor 资产。 |
| 真正 cmake --build --preset 消费 | 题面 CMake 3.27.4；公开 functional 入口由 public_read 提供 | 本题 grader 不证明 CMake/Make/Ninja/编译器存在 | 若测真实并行需预配对应 CMake、构建后端及小 C/C++ 工程；跨 Windows 兼容另需相应后端。不是字段验证的必要依赖，也不能假定 actor 可联网安装。 |
| 可写与可提交位置 | 生成代码在 conan/tools/cmake/presets.py；TestClient 临时 cache/current folder | grader 能生成及安装；gold 源码路径被投影 | actor `/testbed`、home、tmp 的实际权限/配额待验；合法修复无须系统文件、隐藏文件或受恢复测试改动。 |

共享环境卡的默认 2 CPU 不能当成本题 build_jobs 的恒定期望；真实 cgroup/检测值需在同一 actor 进程核对。静态公开包不含 .git，也未捕获完整运行消息、环境提交、未跟踪资产及可见历史，不能宣称无答案泄漏或 Git 体验已验。

## 6. 八方面收口与未查范围

1. **公开需求：**题面/精确 bundle/S2 行及公开读者稿已核；generator/零负值规格、真实消息未核。
2. **材料与初态：**patch、S2、日志哈希一致；base 缺字段且 noop 在目标断言失败；未重新物化 tree/容器。
3. **测试语义：**新 F2P 全展开、helper/Mock 追到 CLI 与文件；默认/其它值/后续多配置 jobs/实际并行未测。
4. **合理解接受：**没有源码结构锁定证据；给出不同于 gold 的实现路线；所有合法解均接受未证明。
5. **回归/gold：**全文读 presets.py、cpu.py，追 toolchain generate/generator、CMake helper/ParallelBlock；直接相关 P2P 的预设数量、名称、配置、路径、toolset/architecture、覆盖保护已读。未逐个展开 40 P2P 中与并行字段无关的 cross-build、Android 等其它函数；其执行状态已核，不能冒称全部语义审完。公开 helper 单测读过，不是该 P2P。
6. **开发条件：**必要导入/配置/临时写入/网络/编译分开列；评分原镜像可运行、actor 待验。
7. **交付评分边界：**官方恢复目标、gold 实际投影、test patch 内容已核；实际镜像可见资产/祖先历史/完整评分控制面未重审。
8. **关系用途：**目前未读其它题，未建立跨题关系；题面给 JSON 目标但未给 helper 修法。用途仅 development_diagnostic。主审已暴露公开稿、隐藏测试、gold、评分日志，后续不得担任本题独立 solver。

实际定点阅读还包括：`test_cmaketoolchain.py:451–740,817–1071,1107–1172,1209–1216`；全部函数名/全部参考 ID；`test_cmake_presets_definitions.py`、`test_cmake_cmd_line_args.py`、`cpu_count_test.py` 全文；TestClient 与 default_profiles 范围见上文。较宽工具输出曾截断，关键引用已用定点读取补齐；未把未显示内容计为已读。未读任何旧 findings/history、主计划、manifest 或 reviewer 产物。

**唯一优先下一步：**在真实 actor 的指定配方中跑公开最小字段对照（显式 2/7、未配置、Ninja Multi-Config 追加/替换），记录解释器/包来源/权限，并将“只写显式配置”的部分实现作为 CPU 负对照与官方评分比较。该一步同时确定可开发性与最直接的功能覆盖缺口；跨生成器的外部构建兼容作为独立待核项保留，不能被这个 Linux 小实验代替。
