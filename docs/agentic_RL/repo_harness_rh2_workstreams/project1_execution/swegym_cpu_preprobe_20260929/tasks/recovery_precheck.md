# MONAI / Conan / Moto 五题恢复性预检

依据日期：2026-09-29。仅核本包已交付输入、selection 所引历史配方和资产记录；未下载、拉镜像、执行项目或操作队列。本地 `task_inputs` 与待同步原件 `remote/inputs_v1` 五题逐文件一致；这不证明远端当前文件或运行结果。

**未发现已证明会导致当前脚本失败的资产漏项。** 两个派生镜像的增量 wheel 都有精确文件名、大小及历史 SHA256；公开来源为 `https://pypi.org/simple`，脚本在远端按固定版本下载，核完整 hash 后才构建。**未归档逐文件下载直链**（例如 files.pythonhosted URL），因此不能称为直链齐备；当前网络、索引和镜像 registry 可达性均未验证。

| 题目 | 恢复所需增量与核对结果 | 剩余条件 |
| --- | --- | --- |
| MONAI2446 | `nibabel==4.0.2`，3,345,004 bytes；[wheel 清单](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-2446/wheel_manifest.json) 与 [compat_v1 原清单](../../../../../../runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/assets_manifest.json) 一致。固定源镜像 digest；原 testbed Python 3.8.20。当前 Dockerfile 将同一 wheel 预装入 testbed；评分仍用已交付历史 recipe。 | 冷构建未验。原安装流程的其余依赖沿用源镜像既有环境；该增量清单不宣称能离线重建整个 Python 环境。 |
| MONAI5932 | 原镜像、原安装配方，无新增 wheel/派生构建。 | 历史准备删除 MetricsReloaded URL 的初态差异见 recovery.json，不能称为 pristine；源镜像恢复与正式运行待验。 |
| Conan11594 | 原镜像；参考绑定为 wrapper 所需顶层 `tasks` 映射，已交付。无新增 wheel。 | **实际 CMake/Ninja 是否存在、版本和 Multi-Config 支持未知**，详见下文。 |
| Moto5406 | 原 baseline01、原 `make init`，无派生镜像或新增 wheel。 | 不套用 install_wave1；源镜像恢复与正式运行待验。 |
| Moto6114 | `setuptools==72.1.0`（2,337,965 bytes）、`wheel==0.43.0`（65,775）、`packaging==24.1`（53,985）；[wheel 清单](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/getmoto__moto-6114/wheel_manifest.json) 与 [历史 aggregate 清单](../../../../../../runs/env_recipe_repair_20260919/install_wave1/assets_manifest.json)、[本题 image.json](../../../../../../runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/image.json) 一致。COPY-only + `PIP_NO_INDEX=1` / `PIP_FIND_LINKS`，原 `make init` 不变。 | 冷构建未验。旧下载指定 Python 3.9，本次用源镜像 testbed Python 3.12.4 下载；三者均为历史 `py3-none-any` wheel，并以相同 hash 验收。 |

Conan 的 [本题 inventory](../../../../../../runs/env_recipe_repair_20260919/inventory/records/conan-io__conan-11594.json) 只有 Python/files/packages/git_head 等记录，未记录 CMake/Ninja 系统可执行文件；包表无二者，不能据此断言系统二进制不存在。源码 conftest 的工具路径配置和历史 mock 评分也不能证明工具已经安装。公开 `toolchain` 命令实际执行 `cmake --version && ninja --version && cmake --help`，随后 `real_cmake` 验 Release CTest 真执行。若工具缺失或不支持，则本题停止归因；recovery.json 中 `cmake==3.23.3` / `ninja==1.10.2.4` 仅是未验证建议，没有 wheel hash，也未接入自动修复。未引用 Conan15422 环境结论。

本检查范围是五题镜像恢复的增量输入，不是全依赖离线供应链证明、冷恢复成功证明或 actor 能力验收。未改输入、调度脚本或生产代码；队列由 root 控制。
