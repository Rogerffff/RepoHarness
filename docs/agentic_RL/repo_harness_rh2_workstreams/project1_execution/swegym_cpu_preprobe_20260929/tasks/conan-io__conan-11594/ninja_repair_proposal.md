# Conan11594：只补 Ninja 的修订建议

2026-09-29，待执行方案；不改旧 inputs、CMake、源码或公开命令，未写 runner，未下载/执行远端。本题 `mixed-v1` 在原 actor 后停止，不能计目标复现或正式评分。

**版本依据来自本题公开 base：Ninja 1.10.2。** [conans/test/conftest.py 第 83–87 行](../../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-11594/base/conans/test/conftest.py) 配置 `ninja.default="1.10.2"`，同版本 Windows 路径为 `C:/Tools/ninja/1.10.2`。这证明仓库已有版本选择，既不证明 Linux 安装存在，也不是 Ninja 最低版本声明。本题公开源码/材料未找到更明确的最低版本约束；没有引用 Conan15422。

[真实 toolchain 输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/mixed-v1/actor_original/captures/toolchain.out) 显示 CMake 3.22.1 可用、`ninja: command not found`。[real_cmake 输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/mixed-v1/actor_original/captures/real_cmake.out) 已成功生成 Conan toolchain，CMake 识别 `Ninja Multi-Config` 后因缺构建程序、`CMAKE_MAKE_PROGRAM` 未设而停止 configure；尚未执行 `cmake.test()` 或到达目标 `RUN_TESTS` 错误。因此保留 CMake 3.22.1 有直接运行依据，题面作者的 CMake 3.23.1 不应自动变成本批升级要求。旧 4 个公开测试通过也不能替代真实 Ninja 工具链。

最小安装选择：取得 **Ninja 上游 1.10.2 的 Linux x86_64 二进制**，放入现有 actor/grader PATH 可见且只读的路径。若 root 检查发现源镜像已有未入 PATH 的同版本可执行文件，先确认版本/来源，再评估仅暴露该文件是否足够；不要先安装第二套工具。

若确实不存在，优先考虑原 testbed Python 3.10 可安装的 `ninja==1.10.2.4` Linux wheel，仅下载这一包、`--only-binary=:all: --no-deps`，离线装入 testbed，保持 PATH 和公开命令不变。**1.10.2.4 是 Python 分发候选 pin，不是已证实的二进制版本**；此前 recovery.json 中只有建议，没有本题成功或 hash 证据。恢复前由 root 核 PyPI 元数据/公开来源，固定完整 wheel 文件名、URL、bytes、SHA256，并核分发到上游版本的对应关系。没有这些资产证据就不把该 pin 标为可执行定案；不改成无 pin 的 `pip install ninja`，不同时安装 CMake，也不复制其它题的恢复结论。

仅需的镜像读取检查是 `command -v` / `type -a ninja`、明确位置（如 `/usr/bin/ninja`、testbed bin）的存在性、系统包记录以及现有 CMake 路径/版本。无需全盘搜索或运行目标项目。后续派生镜像应只有 Ninja 相关增量，记录原层保留、CMake 路径与版本不变、`ninja --version` 实际输出。若它报告带打包后缀的版本，应原样保留，不能改写为纯上游版本。

验收应使用原封不动的公开命令：toolchain 全链通过；base real_cmake 必须越过 configure，真正到达本题 `RUN_TESTS` target 错误；gold 才应跑到 Release CTest marker，退化按自身行为判断。随后仍需原冻结评分与本题 reference bindings 的完整验收。所有原 actor 失败证据、四个旧测试结果和清理记录保留；修订使用新输入/产物版本，不覆盖在途或历史原件。
