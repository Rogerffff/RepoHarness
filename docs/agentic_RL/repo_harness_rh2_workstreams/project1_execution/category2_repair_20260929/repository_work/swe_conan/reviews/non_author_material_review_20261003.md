# Conan 四题非作者材料窄核

2026-10-03。审查者未参与本包生成。**未发现阻断当前四题材料准备的具体问题；可进入已登记的 CPU 与正式接线验收。** 本次是静态、非作者、非 fresh 核查，没有新节点运行、新 reward、正式 actor 资格或训练准入结论。13403/14177 只核交接身份与支持缺口，不重审云端实验。

范围为当前准备入口、11594/12397/13230/15422 的修订单和有效测试，以及必要公开 base/fixture/helper/候选；只检查公开依据、合理实现的接受范围、参考保留和正式保护/消费需求，不启动全题审查或新增机械候选上限。

## 四题结论

| 题目 | 本次静态核验 | 尚待确认 |
| --- | --- | --- |
| 11594 | 保留原六个 generator case；新测试通过真实 CTest 写 Release marker，未写 marker 或执行错误配置都会失败。原截断 Ninja 来源参考仍对应两个完整成员，要求 ALL。 | Ninja 恢复、CTest 实际执行、新文件的受信缺席/创建/保护、完整绑定正式消费及 0/1/0。 |
| 12397 | Apple 两 cpp 键按完整 INI 键读取；Linux native clang/libc++ 直接覆盖公开原场景。已有 P2P 未变；objcpp-only 和 Apple-only 静态反例分别对准错键与系统限域遗漏。 | actor 配置生成、真实节点收集、gold 和两个反例实际结果。 |
| 13230 | 原 Android 断言保留；新增 Macos build/Linux host 的无 SDK 与 SDK 哨兵两个节点，核公开 cflags 和最终导出 CFLAGS。 | 新节点运行、正式 0/1/0 和新机必要身份。 |
| 15422 | 默认 jobs 在生成器同一进程取公开 helper；显式 2/7 和 Ninja Multi-Config 的 Release2→Debug7→Debug3 保持配置对应关系。 | 实际收集、原候选的新评分、CMake3.23.5 真实消费兼容诊断。 |

### 11594：验实际执行，保留原参考分组

公开题面直接是 `cmake.test()` 在 Ninja Multi-Config 上调用错误测试目标；原日志同时明确请求 Release。新 recipe 调用公开 CMake configure/test，`project(... NONE)` 不引入编译器要求；CTest 的脚本必须看到 `$<CONFIG>` 为 Release 才写 marker，最后从 TestClient 隔离目录读 marker。因此检查不只依赖命令文本、返回码或“配置成功”，也允许不同内部修法只要实际执行请求的测试。

公开 base 中该测试文件确实不存在；原补丁本身创建原六例文件。有效补丁保留这六例的函数 AST 原样，仅新增真实执行函数。修订单没有伪造 base SHA，`base_test_file_exists=false` 与 null 摘要正确表示缺席。正式维护者需显式承载“原文件缺席”的受信状态，在评分恢复时创建有效官方文件并保护它，不能借别题文件充当基线。

[绑定文件](../tasks/conan-io__conan-11594/reference_bindings.json)对应原 `test_run_tests[Ninja` 的两个完整成员为 `Ninja Makefiles-test`、`Ninja Multi-Config-test`；不把它们改算两个来源参考。原 F2P 一项保留，新增 marker 一项，结果为 **2 F2P + 4 P2P**。正式登记必须固定该绑定文件的实际字节/版本并核运行消费；JSON 存在不等于 ALL 聚合已接入，任一完整成员非通过或缺席不能由另一成员通过覆盖。

证据：[修订单](../tasks/conan-io__conan-11594/revision_plan.json)、[有效补丁](../tasks/conan-io__conan-11594/effective_test.patch)。Ninja1.10.2.4/CMake3.22.1 是准备入口引用的原配方边界；本轮未验新机资产，也未下载 wheel。

### 12397：完整 cpp 键与 Linux 原场景

公开题面明确 Ubuntu22.04、Clang14/libc++ 的链接错误，说明 compiler 已有 stdlib 参数而 `cpp_link_args` 缺失；Linux native 新节点是直接公开场景，不是凭 gold 扩展一个隐含平台规范。host/build 同 profile 固定为 Linux，加载 native 文件；测试只生成配置，不需要安装 clang/libc++、链接软件或启动 Meson。

Apple 原场景保留自定义 SDK、arch、min-version 的相邻行为。新 helper 使用 `[built-in options]` 的完整键，安全读取列表、字符串常量、常量引用及列表拼接；因此引号、列表分组和现有 `+ deps_cpp_link_args` 不被锁死，`objcpp_link_args` 的后缀不能冒充 `cpp_link_args`。对所核公开模板与自然列表/常量表达路线，未见要求 gold 的内部调用位置或固定 flag 次序；Apple 两 cpp 键要求 libc++ 且保留原自定义 flag 内容。

`objcpp_only.patch` 只给 objcpp 链接追加参数，Apple 的 cpp 链接完整键应拒绝；`apple_only.patch` 仅在 Apple 系统追加，Linux native 应拒绝。两份反例独立通过静态 `git apply --check`，但其实际结果未验证。未扩大为“解析器覆盖所有 Meson 表达式”的声明；若 CPU/真实候选出现公开有效但 helper 不支持的具体输出，应按证据复核接受范围。

原两个 P2P 的完整函数 AST 与原补丁应用后的版本相等，未因本轮放宽或改写；只修改 Apple F2P 的 cpp 两键检查并加一项 Linux F2P，结果 **2 F2P + 2 P2P**。

证据：[修订单](../tasks/conan-io__conan-12397/revision_plan.json)、[有效补丁](../tasks/conan-io__conan-12397/effective_test.patch)、[objcpp-only](../tasks/conan-io__conan-12397/objcpp_only.patch)、[Apple-only](../tasks/conan-io__conan-12397/apple_only.patch)。

### 13230：核最终 flags，不把 SDK 或 rc 当验收答案

公开 recipe 只声明 `os/arch`，故意 `raise Exception(tc.cflags)` 输出观察值。新的 MockSettings 与该最小声明一致：host Linux/x86_64、build Macos/armv8，没有 compiler/build_type/fPIC/额外 flags。公开 `architecture_flag` 在没有 compiler 时返回空字符串，其余相关默认值也不产生 flags，因此本场景期望空 cflags 有依据；不是把所有 Linux 配置一律约束为空。

新两例分别不给 SDK 和给不存在的路径哨兵。正确处理非 Apple host 时都不应需要 SDK。先断言公开 `toolchain.cflags == []`，再经现有 `vars() → environment().vars() → EnvVars.__getitem__` 检查导出 CFLAGS，`shlex.split` 不锁空白表示。MockConanFile 已提供 Conf、folders、options 等所需承载；`monkeypatch.delenv("CFLAGS")` 排除继承宿主值，并由 pytest 恢复，不污染后续测试。

原 Android F2P 的函数 AST 完整保留，原 34 P2P 数组逐项不变；新增两节点后 **3 F2P + 34 P2P**。不需要真实 SDK、交叉工具链或 GPU；公开故意 raise 的 rc1 是获取 flags 的观察路径，不能单独判环境失败或据此改 reward。

证据：[修订单](../tasks/conan-io__conan-13230/revision_plan.json)、[有效补丁](../tasks/conan-io__conan-13230/effective_test.patch)。新测试预计得分仍是未运行预期。

### 15422：同进程默认值与配置追加/替换

公开题面要求 Conan 生成 build preset 的 jobs，以便 install 后直接使用 CMake 并行构建。公开 `build_jobs` 明确优先取 `tools.build:jobs`，否则按现有 CPU/cgroup helper 求默认值。新默认节点在 recipe 的 generate 进程先输出该 helper 值，再生成 preset，避免把测试进程核数、固定数字或容器配额误作答案；只比较输出语义，不要求修复必须调用某个内部实现。

显式2/7排除只认原42的修复。多配置复用同一 TestClient，依次生成 Release2、Debug7、Debug3；每步比较 configuration→jobs 的完整映射，并要求数量等于预期配置数，核追加与同名替换而不锁列表顺序。公开 writer 的 `_insert_preset` 本就按同名替换/否则追加，新断言只要求该既有行为携带正确 jobs。没有新增 VS/Xcode/NMake 范围或固定 schema/最低版本数字断言。

原42节点和40 P2P 函数/数组保留；新增四个实际节点（含2/7参数化）后 **5 F2P + 40 P2P**。准备记录中的旧模型候选新得分都是预期；Qwen3.6 a2 仍为 null，需 CMake3.23.5 的真实消费结果，不把材料 JSON 可读等同于该 CMake 版本兼容。

证据：[修订单](../tasks/conan-io__conan-15422/revision_plan.json)、[有效补丁](../tasks/conan-io__conan-15422/effective_test.patch)。

## 两份云端补丁的交接支持缺口

本轮只独立核 13403 v4、14177 v2 的有效 patch 与各自所指云端 patch **字节相等**，并核所指 base/父 grading/public 摘要及分组迁移；未重读或重跑41/15份云端矩阵，不用本轮材料核对替代其原非作者根因意见。

- 13403 只替换测试，保持 **1 F2P + 0 P2P**；D6 正式替换、actor 和真实 GNU 开发路径仍待。不将记录器测试冒称系统 autoreconf 已执行。
- 14177 将 `test_single_patch_description` 从 F2P 移 P2P，得到 **2 F2P + 11 P2P**。迁移后与原13节点总集合相等，无丢失、重复或 F2P/P2P 重叠；正式分组必须与测试身份同步。替代正对照 pubcand 与旧 gold 的正式新结果、actor 条件仍待，本轮不重新裁定云端题义。

## 静态验证与边界

独立重算六题父 grading/public 的 canonical digest、原/有效 patch SHA、有效测试文件 SHA、存在 base 文件的 SHA，均与修订单一致。四份新补丁在临时隔离目录独立通过 `git apply --check --whitespace=error` 和静态应用，产物逐字等于本包 `effective_test.py`，并通过 AST 解析。与原补丁应用版本比较，11594/13230/15422 原方法全部保留；12397 仅修改上述 Apple 方法。四题候选矩阵中的非空文件摘要一致。新参数化完整 nodeid 尚需真实 pytest 收集；AST 能确认函数/装饰器，不能替代收集。

正式发布尚需四题追加共8新节点、六题受信测试替换/恢复/保护、11594缺席文件与绑定、14177分组迁移和同一材料身份贯穿。当前修订单明确不是生产 schema，`formal_registry_version=null`，这些已列待办不作为“材料准备已发布”的证据，也不因此要求先泛化重构。

停止条件：本次材料窄核结束；后续仅对正式接线差异、CPU原始结果矛盾或本次文件身份变化复核。不扩大模型预算、候选数量或启动全题角色链。没有训练资格变动。

本轮只读文件并做 stdlib JSON/hash/AST 和临时副本 git apply 静态操作；未执行准备生成器、Conan/pytest/项目模块、编译、安装、下载、SSH、容器或模型。唯一新增文件为本报告，排他创建避免覆盖并行改动。
