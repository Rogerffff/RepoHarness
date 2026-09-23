# conan-io__conan-15422：独立初判

2026-09-21。第一阶段，只读本题原件及指定既有日志；未读公开读者、主审、旧调查或其它题结论。没有运行项目代码、测试、安装、Docker、SSH 或模型，也没有修改原件。本文是静态复核及既有运行证据复读，不是独立复现。

## 初步判断

本题可以保留为 **development_diagnostic 静态探针候选，仍为 needs_review，须补实际 actor 验证**。公开目标与唯一 F2P 的主方向一致，base 确实缺少生成字段，gold 的修改路径合理，尚未发现材料错配、明确误拒合理实现或 gold 的确定性业务回归。主要限度是评分只验证一个显式值，不能把 reward=1 等同于默认并行度、所有生成器和真实 CMake 执行均正确。

## 引用约定与暴露范围

- `PUBLIC` = `runs/swegym_quality_batch01_20260921_v2/public/conan-io__conan-15422`；`B` = `PUBLIC/base`。
- `PRIVATE` = `runs/swegym_quality_batch01_20260921_v2/private/conan-io__conan-15422`。
- `L` = `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w02-1/ledger.jsonl`。
- `N`、`G` 分别是同一 worker 的 `eval_logs/evallog_replay-f216-baseline01-w_434a958a.eval.log`、`evallog_replay-f216-baseline01-w_e40da522.eval.log`。
- 上述相对路径均以 `${REPO_ROOT}` 为根。

已读角色卡、actor_environment_card、record_template、quality_review_protocol；本题 user_prompt、public_bundle、base_identity、environment_brief；test.patch 全文、grading 的全部 F2P/P2P ID、gold.patch/validation、run_refs/source_refs/environment_record；下述源码及测试。environment_record 只当引用元数据，其所指 scope_reconciliation 总结未打开，运行结论以 L/N/G 原件为依据。日志重点复读初态、候选差异、恢复/应用测试、安装及测试结果段；未逐行分析 `git show` 所打印的无关 base 提交差异。

八方面均已检查到下文声明的范围。跨题血缘、实际 actor、完整镜像可见文件/历史、全仓测试及真实模型能力未验证。

## 公开目标与源码依据

`PUBLIC/user_prompt.txt` 要求 Conan 生成的 `CMakePresets.json` 在 `buildPresets` 中设置 `jobs`，使安装后的 `cmake --build --target all --preset conan-relwithdebinfo` 能并行构建。`16` 是示例，题面没有要求硬编码 16，也没有逐字规定配置键或默认 CPU 算法。

这些选择可从公开 base 合理收敛：`B/conans/model/conf.py:55` 已公开描述 `tools.build:jobs` 为 Ninja/Make/VS 的默认并行度，默认 max CPUs；`B/conan/tools/build/cpu.py:8-28` 的 `build_jobs` 文档与实现约定显式配置优先，否则 `_cpu_count()`，返回整数；`B/conan/tools/cmake/cmake.py:11-23` 已将此配置用于 CMake 构建。要求新 preset 尊重已有并行配置有公开依据，不是只能从 gold 得知的隐藏 API。

开发入口明确：`CMakeToolchain.generate()` 在 `B/conan/tools/cmake/toolchain/toolchain.py:231-232` 调用 `write_cmake_presets()`；`B/conan/tools/cmake/presets.py:54-68,86-103` 的首次创建、多配置追加/更新分别通向 `_build_preset_fields()`；base 的该函数（190-192）仅返回 name/configurePreset/configuration，没有 jobs。`_test_preset_fields()` 是另一路，不能将 build 的字段要求无条件扩展为 CTest 需求。

## 需求—断言双向核对

| 公开需求或合理旧行为 | 依据 | 验收断言及覆盖 | 证据 / 限度 |
| --- | --- | --- | --- |
| 生成 build preset 的 jobs | 题面 JSON 示例；presets.py:190-192 | 唯一 F2P `test_presets_njobs`：空 conanfile.txt，经真实 Conan install 生成 JSON，再读首个 build preset，断言 jobs == 42 | 主需求有覆盖；不是比较日志文本，也不是只 mock 内部函数 |
| 尊重显式并行配置 | conf.py:55；cpu.py:8-28；cmake.py:17-19 | F2P 传 `-c tools.build:jobs=42` | 只覆盖 42；未覆盖题面示例 16、其它整数、profile/global.conf 输入 |
| 未指定 jobs 时采用既有默认并行度 | conf.py:55；cpu.py:10-20 | P2P 多次不传配置，但不检查 jobs 值 | 缺少值断言；“只在显式配置时输出 jobs”可能获相同评分，不能据评分判默认行为完整 |
| 单配置重写，多配置追加/替换仍正确 | presets.py:54-83,86-103 | P2P `test_cmake_presets_singleconfig`、`test_cmake_presets_multiconfig` 断言 preset 个数、配置名和关联；多配置覆盖 Release/Debug/RelWithDebInfo/MinSizeRel 及重复 Debug | 保护既有结构；未验证新建、追加、重复更新时各项 jobs，尤其更新并行值 |
| 用户 preset、命名、路径和环境等已有结构不被破坏 | presets.py:176-199,232-330 | P2P shared_preset、custom_location、binary_dir、ninja_msvc、layout、avoid_overwrite 等 | 相关字段有保护；没有全字典快照强制“必须与 gold 一样实现” |
| 最终文件能被 CMake 消费并实现并行构建 | 题面命令；公开功能测试 `test_cmake_presets_with_conanfile_txt`（functional/toolchains/cmake/test_cmake_toolchain.py:953-997） | 评分运行的 integration 文件不启动 cmake，不验证并行过程；上述功能测试不在参考 P2P | 生成文件是合理直接测点，但真实工具接受性与并行效果未由本次评分证明 |

test.patch 只有上述一个新增测试、一个显式 `assert`，没有改 helper 或普通生产源码。`TestClient.run` 通过 `Cli(ConanAPI).run` 执行命令，默认要求成功（tools.py:508-537,540-565,590-604）；`save/load` 确实写读临时工作目录（399-434,606-614）。因此 F2P 还隐式要求 install 成功、JSON 可解析、buildPresets 非空及 jobs 键存在。

全部 40 个参考 P2P 均位于该 integration 文件，已经通读该文件全部测试体。除上述直接相关 preset 测试，也核了交叉编译、flags、Android、变量类型、编译器/链接脚本、test_package 和缺文件错误测试；它们主要保护原有生成内容。未把这 40 项当作 40 项并行语义验证。

## 漏测、误拒与 gold

**有具体漏测限度，但没有把未执行候选宣称为获分证据。** 对输出恒定 `jobs=42` 的错误实现，唯一新断言无法区分它与正确的配置映射；已有 P2P 不断言 jobs。只修新建单配置分支、漏掉多配置更新，也是可区分的静态错误候选。默认无配置路径、不同 jobs 值、多配置配置值刷新应是最有价值的后续补充。`==42` 本身也不严格检查 JSON 数值类型（例如浮点 42.0 的 Python 比较）；其真实 CMake 接受性未在本轮执行，不能仅据此宣布已有确定坏解。

**未发现明确误拒。** 新测试约束的是题面指定的可观察 JSON 字段和已有 conf，未规定 helper 名、调用次数或内部实现。合理替代实现可在完整生成流程的相应分支注入从既有并行配置得到的值，只要新建与更新行为一致；不必逐字复制 gold。仅通过环境变量开启并行而从不生成 jobs，不满足题面明确要求，不构成误拒反例。

**gold 静态上覆盖主要路径。** PRIVATE/gold.patch 只给 `_build_preset_fields()` 添加 `build_jobs(conanfile)` 与 `ret["jobs"]`；同一函数被首次生成、多配置追加/替换共用；不会给 configure/test preset 添加字段。既有 CPU helper 已处理 cgroup/CPU fallback，且 gold 保留原配置名称、关联与合并规则。额外导入没有引入新第三方依赖。未发现混入其它需求或需要未交付文件。

仍未验证 jobs 的特殊值及各平台实际工具行为。base 的 CMake helper 对 Make/Ninja、NMake、Visual Studio 原本有不同并行参数处理（cmake.py:18-23；相关单元测试 `test_cmake_cmd_line_args.py:22-45`），而 gold 给所有 build preset 写入 jobs。不能把 Linux 的文件生成通过外推成所有平台的真实构建已验证；这目前是覆盖边界，没有足够证据定为 gold 回归。

## 材料与既有运行证据

public/base_identity、grading、L 的 base 均为 `f08b9924712cf0c2f27b93cbb5206d56d0d824d8`；base_identity 记录 tree `c6db74a43d17809b8abb51050c6be72c58461ff0`、1002 个跟踪条目、无导出的 .git。N:135-139 的 clean 状态与 `git show` 对应此 base；G:692-713 的候选差异对应本题 gold。题面报告 Conan 2.0.14，评分工作区为 2.1.0-dev；本题要修的字段在指定 base 仍缺失，所以版本标注差异本身不构成错配。

本地只读哈希检查：N=`24800e3c13ca9842c442d6e21457a70fec4992477951dbcd908637352147fe0e`、G=`a0aa7082c33b1b3e99c7b1287a7767575d8ccd5c2e498c2f5fa8cdf6f3a3c089`，均与 run_refs、L 一致；gold.patch=`1bcbaa52ea35d4893b8eb55e921f082ce73d7948e355f5a4d8657f4b1b620e66`，与 validation 及 L 第 2 行一致。

- L 第 1 行 / N:919-991：运行 `pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`，44 collected；F2P 在第 1224 行 `KeyError: 'jobs'`；40 passed、3 skipped、1 failed，测试 rc=1，F2P 0/1、P2P fail=0、reward=0。
- L 第 2 行 / G:945-1005：同一测试文件，41 passed、3 skipped，测试 rc=0，F2P 1/1、P2P fail=0、reward=1。3 项系统跳过不属于给定 40 项参考 P2P；账本 reference_missing/reference_skipped 均空。
- 两次均使用原镜像引用与相同预期 digest、没有 derived_image_recipe；L 记 grader 为 rh2grader/54322、deny_all、2 CPU/4 GiB，包来源 `/testbed/conans/__init__.py`。安装段依赖已满足、安装 rc=0。`image_id_actual=null`、`env_qualification=absent` 等字段不应被补写成新验收事实。

以上证据支持“原初态问题成立、该 gold 在既有评分条件下成功”，不证明本轮 actor 环境或任何其它候选结果。candidate.apply_user=agent/54321 只是候选应用身份，不能当作完整解题工具体验证据。

## 开发条件与交付/评分边界

| 需要的操作/资产 | 公开依据 | 已有证据及适用范围 | 当前缺口与最小验证 |
| --- | --- | --- | --- |
| 读写并导入当前工作区的 Python 实现 | README:90-114；工具链调用点；requirements*.txt | grader 日志导入 `/testbed`，安装所需 Python 包已满足 | actor 实际 shell 的 PATH、解释器、导入来源和权限未验；先记录 `id`、`pwd`、`command -v python`，以 Python 打印解释器及 conan/conans 文件路径 |
| 运行窄公开集成测试 | test/README:11-15 说明 integration 仅依赖 Python；TestClient 使用本地临时目录和内置 profile | grader 在 deny_all 条件下该文件通过既有 P2P | actor 下 `python -m pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py -k 'presets_singleconfig or presets_multiconfig'`；应通过且确实读候选代码 |
| 复核 jobs 配置与默认行为 | cpu.py:8-28；公开 issue 与旧 preset 测试 | 本题 F2P 的既有日志覆盖 42；默认并行度未断言 | 由后续获授权 CPU 负责人使用公开 TestClient/Conan CLI，在临时目录生成 conanfile.txt，分别不传配置、传 16 和其它整数，并检查每个目标 build preset；不需要隐藏测试 |
| 可写 cache、临时目录与生成文件 | tools.py:398-434；test_files.py:31-51 | grader 本地读写成功；纯生成不需远程包和编译器 | actor 实际 HOME/tmp 权限待验；本题不要求修改系统包或将临时生成物作为最终补丁 |
| 真正执行题面 cmake 命令（可选增强验证） | 公开功能测试:953-997；conftest 的 cmake 3.23 配置 | 当前评分没有执行 CMake；未核实际 actor 的 cmake/Ninja/Make/编译器版本 | 若要验证端到端，准备期固定所需工具及小型本地工程；不由此要求运行期公网或外部服务 |

本题的正常生产修复位于 `conan/tools/cmake/presets.py`，L 第 2 行显示该路径被投影纳入、无 ignored_paths。N:689-695 / G:715-721 显示恢复并应用官方补丁的文件仅是 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`，不覆盖该生产文件。test.patch 未夹带正常源代码，也没有发现必须改测试或不可提交环境文件才能修复的条件。

`public_hints` 的“conda 已激活”仍是待验声明；“测试修改永不计分”的广义解释不能替代实际文件恢复规则。本题合法生产修改不受该区别阻断。TestClient/conftest 确实能影响测试行为，但未进行共享防篡改机制重审，不能因可编辑 helper 就宣称已发现本题可利用的评分漏洞。

## 题目关系、用途与后续优先项

这是把既有并行度配置接入生成产物的功能补全题。题面直接给出目标 JSON 形状，属于公开规格提示；不等于提供实现答案。没有读其它题，故没有据实确认跨题重复或未来修复暴露关系。该静态包没有 .git，不足以证明真实镜像可见资产和历史无答案；这些共享可见性条件仍须在实际 actor 侧核对。本 reviewer 已见全部私有测试和 gold，不可充当未见答案的模型求解者。

优先下一步：在协调者统一实际 actor 入口下核实解释器/工作区导入和一个窄公开 preset 测试，同时以公开材料构造默认值、16/另一整数及多配置更新的生成检查。现阶段不因普通覆盖限度直接拒题，也不授予正式训练/评测准入；若后续要主张 reward 能表示完整修复，应对“显式配置才输出”或“仅新建分支添加 jobs”的候选分别核公开行为与 RH2 得分。此次没有执行这些候选。

第一阶段到此封存，等待协调者提供第二阶段 S2/S3 及旧结论变更材料。
