# Dask6626：本夜 CPU 接续

2026-09-29。复用既有 quality_expansion_20260925 的静态审查和独立复核，未在本机运行历史项目。

公开 `public_commands.json` 从两条题面 set_index 原例和实际 base 测试生成。issue_two_paths 先打印两条 metadata/compute 且核 compute 与 pandas；metadata_assert 再明确拒绝类别不一致，base 预期目标断言失败。公开测试在未注入隐藏测试的 base 应通过。

私有 `private_semantic_spec.template.json` 对 base/gold/fixed_object_empty；固定 object 空 Index 候选在 gold 修改位置硬编码类别 dtype，违反公开 dataframe metadata 保留 dtype 不变量（docs/source/dataframe-design.rst）及同一空类别要求的 int64 实例。必须先实测该违反，再正式评分；得 1 则为 S1/T2b/T2c，不能拿公开原例成功替代覆盖判断。gold 和此候选需正式导出、重建、投影、全部参考及额外测试状态/清理。

## 环境恢复与旧 runner 差异

compat_v1 原件目录：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/`；`image.json`/`build.log`/`assets_manifest.json` 可恢复构建输入。公开镜像 `xingyaoww/sweb.eval.x86_64.dask_s_dask-6626@sha256:a182a6a7383561f7b7a078585259c6314e60504235b4d86cf00f4fd15ef69503`，Dockerfile 仅 ARG BASE_IMAGE / FROM / COPY wheels/ /opt/rh2/compat-wheels/。wheel `pytest-7.4.4-py3-none-any.whl` 325287 bytes，sha256 `b090cdf5ed60bf4c45261be03239c2c1c22df034fbffe691abe93cd80cea01d8`。运行安装配方：`docs/.../env_recipe_repair_20260919/compat_v1/recipes/dask__dask-6626.json`，先离线 pytest7.4.4，再原 editable --no-deps 安装。旧 base ID fd456e2b… / 派生 ID 9776743c… 不代表新后端必然得到相同 ID。

两侧旧 diagnostics 的 runner pre `0f3527775c70cece62a1cb6aebd15f554bceee5d03e6f54575b5af67d5068f43`，post `a7b7f1e4d9d840b38dcc19daa1f46d09c0cb3e558d41c91f1c5e08dcfcb509cc`。gold 原日志433–443明确卸载 pytest8.3.2、安装7.4.4；摘要覆盖 pytest/_pytest/pluggy 包路径与文件内容（排除 pycache/pyc）。这解释变化机制，**不能证明全部变化只有 pin**：旧日志未保存逐文件清单，旧完整性 unknown 保持。

本批需在 source/compat_v1 初态、pin 后、editable 后分别保留逐文件 SHA/总摘要及包版本；对比 pin 是否完全重现旧 pre/post，逐文件解释 pytest/_pytest 变化且 pluggy 不变。可在派生构建阶段预装 pin 后固定 actor/grader，相应配方及摘要是新版本，另取资格。新证据不能倒签旧完整性。

## 尚未完成

真实 actor 路径、两条用户流程、私有非示例对照、正式 noop/gold/退化分数、本批完整性/资源/清理、冷恢复、独立复核。空 CategoricalIndex 邻接问题不自动扩为本题必修要求，保持旧边界；当前用途 conditional，未签发训练/模型资格。

## 可执行构建计划（2026-09-29 补齐）

本题 task_inputs 内：`grader_build_plan.json` 由 `rh2/experiments/base_probe_20260922/build_derived.py --plan PLAN --out-dir OUT --tag-suffix 20260929` 消费；`actor_build_plan.json` 由 `rh2/experiments/task2_swegym_dev_20260925/build_actor.py PLAN --out-dir OUT` 消费；`grader_install_recipe.json` 已复制/生成。三个题合并计划放 Dask7656 的 `three_task_grader_build_plan.json`、`three_task_actor_build_plan.json`。全部使用 immutable source manifest、具体 pins 与逐 wheel SHA；构建还未执行。

Dask7656 历史批次名 compat_v2b 映射 builder 的 `style=compat_v1`，因为实际 Dockerfile 同为 COPY 到 `/opt/rh2/compat-wheels/`；这不表示改用 6626 的 pytest 配方。grader 只存 pandas wheel，评分候选安装段 export SETUPTOOLS_USE_DISTUTILS=stdlib、离线 pandas1.3.5 后原 editable 安装。actor 直接装 pandas1.3.5，并用 `etc/conda/activate.d/rh2-dask-distutils.sh` 设置 stdlib；正式 BASH_ENV 调用 source activate testbed 会读钩子，须用另存 `public_environment_check.json` 实测。只装依赖和环境钩子，不改 /testbed。语义控制若绕过 conda 激活、只改 PATH，必须显式 export SETUPTOOLS_USE_DISTUTILS=stdlib。

Dask6626 grader COPY pytest7.4.4 wheel，原安装 recipe 中才 pin；actor 在构建时装好 pytest7.4.4。mypy15139 grader 用 install_wave1 的九 wheel 与 PIP_NO_INDEX/PIP_FIND_LINKS，原 test-requirements + editable 命令不改；identity recipe 只是让可选 wrapper 有具体文件可用，也可直接正式 replay_grade。actor 预装同九依赖，不带私有测试或 gold。build_actor 不保留离线 wheel：足够当前已装依赖的公开开发验证，不宣称覆盖任意新增依赖的离线供应。

## 接续作业入口（待独立复核、未运行）

新实验 `rh2/experiments/swegym_cpu_preprobe_20260929/dask_mypy_followups.py --task <ID>` 供root派发。只消费 code_v1、inputs_v1、prepared/v1、gold/v1 和 tools_v1/private_behavior.py；Dask6626端口18094，mypy15139端口18095。顺序为原actor→已有依赖派生→actor复验→私有行为→正式noop/gold/既有错误候选。错误候选共两类：6626 fixed_object_empty、15139 unconditional_lowercase，不为凑数新增候选。所有结果仍需读取目标输出和完整评分证据。

6626另在COPY-only grader镜像执行runner_before→pin_pytest→runner_after_pin→editable→runner_after_editable，输出完整逐文件清单和runner_file_comparison.json。比较同时列新旧摘要是否相同、pin期间具体文件变化、editable期间变化；这是真实重建证据，不倒签历史缺失的文件清单。各采集/安装命令非零则停止归因。脚本只经AST及实际输入/冻结vendor安装串静态核对，未在本机或远端执行。

### 接续编排停止条件修订（2026-09-29）

交叉窄审指出，原脚本会把部分 timeout 当成预期非零，且私有 helper 的整体 rc=0 不保证子命令完成。`dask_mypy_followups.py` 已修订：actor 排除未执行/超时/截断，修复后逐命令核目标输出；私有逐变体运行单个 matrix，导入/收集/超时或目标输出缺失即停止本题，原始命令输出保留。mypy 原例不预断 gold 是否修好，只要求两条 reveal 和 CLI 收口；输出仍待题级归因。正式 noop/gold 及 install/test/reference 收口做最少核查，不将 Dask 有意 pytest 降级判为意外 runner 改动。

修订脚本 SHA256：`38c81608aa1b1307c119329f931565feccbc2375ceca1115a77d8d696cb53b82`。只完成 AST 及生成 Python 体语法检查，未运行远端或项目；待窄复核及 root 回传证据。
