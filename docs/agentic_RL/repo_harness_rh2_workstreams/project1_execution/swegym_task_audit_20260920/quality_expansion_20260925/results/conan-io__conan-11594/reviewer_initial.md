# conan-io__conan-11594 独立初判

本稿为 fresh reviewer 独立初判，尚未接触本包任何 public_read、主审稿、history、旧质量报告、根汇总或其它包。只读指定 P/V 和 run_refs/environment_record 精确引用的本题原运行材料；使用文件文本、JSON、hash，未执行/导入项目、测试、安装、网络或容器。共享工作区按允许路径管理，不宣称 OS 隔离。本稿写完封存后不修改，等待明确 cross_review release。

记号：ROOT=/Users/roger/Desktop/claude-code-verl-stage0h；P=ROOT/runs/swegym_quality_expansion_20260925/public/本题；V=同级 private/本题。下列源码路径相对 P/base，原运行路径相对 ROOT。八方面是阅读导航，不另造准入门。

## 1. 身份与初态

公开 base 为 4ed1bee0fb81b2826208e8c1c824c99fb6d69be8（1.51.0-dev）；题面报告 1.49.0，属于报告环境和修复基线的差异，不能由此认定错配。V/grading、validation 的内嵌 patch 与独立 test.patch/gold.patch 字节相同；原 gold 工件 hash=e49265e4fd430f627dd2293f1f79b3b6c30b30d36c8a6a066c992f4d4b48abfa，与本题一致。stage HEAD 相同、git_apply；projection 只纳入 conan/tools/cmake/cmake.py。

P/base_identity 是精确 Git blobs 静态导出，无 .git；actual_actor_worktree、实际消息仍 unknown。历史 noop 日志 135–139 行为 grader 准备阶段普通 git status clean 和基线 git show；gold 的 status 为补丁后的 cmake.py 修改。它们不是本轮 actor 准备后 porcelain 采集；git show 中的 Path accessor 差分是基线提交展示，不是残留未提交修改。

## 2. 公开要求与断言双向映射

题面要求：Ninja Multi-Config 下 cmake.test() 经 conan build . 能使用存在的 test target，避免 RUN_TESTS。没要求改变所有构建命令、多配置属性或覆写调用者显式 target。

令 T=conans/test/unittests/tools/cmake/test_cmake_test.py::test_run_tests。完整新增文件45行已读；六参数共用唯一断言：平台对应的 --target 文本必须出现在 ConanFileMock.command。

| 公开要求/既有行为 | 测试/断言反向归属 | 覆盖结论 |
| --- | --- | --- |
| Ninja Multi-Config 的默认 test target | T[Ninja Multi-Config-test]，target='test' | 覆盖命令选择；不执行 Ninja/CTest |
| 其它单配置生成器继续使用 test | T[NMake Makefiles-test]、T[Unix Makefiles-test]，P2P；T[Ninja Makefiles-test] 与 F2P 合组 | 合理回归约束；Ninja Makefiles 是测试字符串，不证明真实 CMake 接受该 generator |
| Visual Studio/Xcode 保留 RUN_TESTS | T[Visual Studio 14 2015-RUN_TESTS]、T[Xcode-RUN_TESTS]，P2P | 覆盖目标文本 |
| 保留 Multi-Config 的 --config Release 等行为 | 无新增断言 | 缺失，不能以六绿证明配置正确 |
| 保留显式 target、skip_test、cli_args/build_tool_args | 隐藏文件无断言；公开 integration/toolchains/cmake/test_cmake.py::test_configure_args 仅覆盖参数透传 | P2P 选择器未包含该旧测试 |
| 真实 conan build→cmake.test→Ninja 执行成功 | 无 | 核心端到端效果未验 |

F2P 的原 ID 是截断的 T[Ninja，不是一个合法完整 pytest node；V/run_refs 指定 reference-bindings-v1 将其绑定到两个 Ninja 完整 node，必须全部通过。P2P 的 T[NMake、T[Unix、T[Visual 也截断，但本组各只有一个匹配 node；Xcode 完整。此运行不能脱离 binding 条件复述为通用来源 scorer 已修好。

## 3. 根因、helper 与调用者

完整读 conan/tools/cmake/cmake.py:1–159、utils.py:1–32、presets.py:1–161。CMake 初始化从 configure preset 读 generator；test:151–159 用 is_multi_configuration 判 RUN_TESTS；utils:4–7 把 Ninja Multi-Config 判多配置，因此基线必走错误分支。_build:101–129 使用同一多配置 helper 输出 --config，并经 args_to_string 组合 target 后调用 recipe.run。Mock.run（conans/test/utils/mocks.py:194–199）只记录 command，完全不执行 cmake。presets 写入和读取 generator 使新增测试确实抵达目标代码，而不是只检查独立常量。

读 toolchain/toolchain.py:118–234 的生成路径：标准 _get_generator 最终返回 Unix Makefiles 或具体其它字符串，generate 把 generator 写入 preset。读旧 conans/client/build/cmake.py:289–352，旧 API 也有同型 target 判断；题面未给 import 路径，存在接口定位歧义，gold/隐藏测试只修新 conan.tools.cmake.CMake。不能把旧 API 未修自动记成 gold 新增回归。

## 4. 替代实现、误拒与漏测

合理非 gold 路线是在 test() 明确识别 Ninja Multi-Config，或将目标映射独立为 helper，同时保留 is_multi_configuration 对构建/配置的含义。测试不强制 gold 的局部布尔表达式，接受这些路线。

测试对 POSIX shell 引号格式的子串检查偏紧：语义等价的 --target test 或不同正确引用风格可被拒；直接调用 ctest 的路线能执行测试，但是否保留 target/API/透传兼容性需另核，不能无条件列为正确解。漏测更明确：全局把 Ninja Multi-Config 判为单配置仍可满足该唯一 target 断言，却丢失 --config；这是有源码路径支持的错误实现通过风险（25），不是已经观察到的 candidate。仅写 command 字段的伪修复也会满足 Mock，但不满足公开实际执行目标；未全面审计控制面，31 保留 not_checked。

## 5. gold 与回归边界

gold 只在无显式 target 时添加 Ninja 排除，skip_test/显式 target/_build 未变；对标准字符串 generator 根因修复有充分静态支持，且保留多配置行为。没有已证实 gold 新增回归。新代码对 generator=None 的成员测试会 TypeError，而旧 utils/_cmake_cmd_line_args 对 None 有防御；但标准 toolchain 生成路径返回字符串，尚无自然公开 None 使用路径证据，因此只保留条件性风险，不将26记已证 issue。全仓、旧 API 修复、真实平台和用户自定义 preset 均未验。

## 6. 历史执行与评分条件

原账本：runs/env_recipe_repair_20260919/reference_v1/runs/conan-io__conan-11594-{noop,gold}/ledger.jsonl，各第1行；对应 eval_logs 文件由 V/run_refs 给出，noop 后缀 fea22e52，gold c6c7c2ef。两行 hash 与定位记录一致，两个日志文件 hash 已独立核对。读原 binding 两个 JSON（含 raw_node_states）。noop 日志559–633、gold578–608：命令均为 `pytest -n0 -rA conans/test/unittests/tools/cmake/test_cmake_test.py`；各收集6项，noop仅 Ninja Multi-Config失败，实际 command 含 RUN_TESTS（605–611），5过；gold6过。账本 F2P 0/1→1/1，P2P 0/4失败，parser记录5个参考身份；6个真实执行 node 与5参考分组不能混计。

日志显示 source miniconda activate，conda activate testbed，cd /testbed，PYTHONPATH=:/testbed；依次 `python -m pip install -r conans/requirements.txt`、requirements_server.txt、requirements_dev.txt。最后安装 rc=0，pytest-6.2.5/Python3.10.14/xdist3.5.0；账本导入 /testbed/conans/__init__.py，版本1.51.0-dev。grader 为 rh2grader/54322，deny_all，cpus=2.0，memory_bytes=4294967296；test seconds noop1.355/gold1.143；mem_peak_mb=76.875/67.91（原字段，不推断单位实现）。cleanup removed=true，runner_integrity_changed=false、reference_missing=[]。只证明这些历史命令下的测试差分。

image_ref 和预期 manifest digest 在公开包/账本一致；actual grader image ID=null。environment_record 的 source-image inventory ID 是另一次源镜像观测，不能替代本次实际 ID。scripts_digest=486a53c849689dab601b6bb76072825549ef734cfaa68e30e8b2667e8001c06b。只读归档身份元数据，未审归档 runner 内容；没有本轮环境修复或 actor 实测。

## 7. 公开开发需求与唯一优先下一步

| 需要操作/资产 | 公开依据 | 已有证据适用者 | 缺口与最小命令/预期 |
| --- | --- | --- | --- |
| Python、工作区导入、pytest、可写临时目录/cache/preset | README.rst:65–69,148–176；requirements；公开 Mock/参数集成测试 | 历史 grader 的安装与导入成功 | actor shell 的 UID/HOME/cwd/PATH/解释器/源码来源、准备后状态待采；`python -m pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmake.py` 应实际执行参数透传测试 |
| CMake 支持 Ninja Multi-Config、Ninja、无外部依赖的小项目 | 题面 CMake3.23.1及 conan build 原例；工具路径配置不能代替实物 | 当前仅 Mock，未证明 CMake/Ninja 可用 | 同一公开 recipe 使用 CMakeToolchain(generator='Ninja Multi-Config')，build 中 configure/test；CMakeLists 用 project(... NONE)、enable_testing、add_test 调用 cmake -E true；`conan install . -s build_type=Release` 后 `conan build .`；base应未知 RUN_TESTS，修复应执行测试成功且保留 --config Release |

优先下一步是任务二在真实 actor 条件做上述无编译器/无网络的公开 CLI 路径，核 CMake/Ninja版本和代码生效，并记录目标失败和合法修复的私有对照。不要仅为单元测试能跑而要求安装编译器，更不能把 README 的旧 cmake>=2.8 声明当作 Multi-Config 充分条件。未执行任何建议命令。

## 8. 阅读/暴露、40项与建议

已读：P 的题面、bundle/identity/brief；V 全部本题 patch、grading/validation，run_refs/environment_record 的定位/身份/条件字段；上述源码、Mock、参数透传旧测试、README安装测试段、requirements、pytest.ini、setup entry point；原账本选中行、日志中的 setup/status/diff/安装/完整测试输出、binding 原件、gold patch/projection/stage。conftest 工具声明只局部读；其余仓库、未来 Git、来源外网、原基线 runner内容、全仓回归、actor消息和实际初态未读/未验。部分长文件只按所列段落阅读，不声称全仓审计。

静态建议：可列 development_diagnostic 受限候选，state=needs_review，scope=static_review；优先补 actor 真实公开行为证据。19在本次绑定条件下有历史支持；23为轻度接口歧义；24为命令字符串误拒风险；25为配置/真实执行漏测；26 unknown（无已证新增回归）；3/10/33 unknown；5/14/29–31/35–39未作完整检查。18/20只能限本次6个node的历史差分。不得标 ready_for_probe、训练或正式评测合格；不新增路径排除。
