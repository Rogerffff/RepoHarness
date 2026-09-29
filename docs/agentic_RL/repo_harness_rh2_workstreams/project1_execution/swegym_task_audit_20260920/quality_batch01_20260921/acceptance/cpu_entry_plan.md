# 三题 actor CPU 开发条件：薄诊断入口实施单

2026-09-21，静态调用链核对；**尚未实现或执行**。依据 [当前计划](../README.md)、[环境卡](../actor_environment_card.md)、[审查回应](../review_response_20260921.md)。Conan15422、Dask8597、Pydantic8511 仅为三种环境形式的设计样例，不预判质量通过；成熟单题可先做，不等三题或十二题齐备。

## 1. 实现一个什么入口

新增一份实验目录内的薄 Python 编排（文件名/CLI 待实现者定，不存在现成 actor CPU CLI），消费当前 manifest 指向的 **v2** 公开包、镜像身份、环境 recipe 和逐题公开命令。只运行准备、确定性开发操作、补丁导出与可选 RH2 重放，不调用模型、Ray 或 learner。公开容器不挂私有材料；recipe 由 host 读取，只写入必要安装命令与公开依赖。

**复用真实 helper，按 generate 的顺序编排；不伪装成调用过完整 generate。** 下列源码路径均相对仓库根，行号为本次快照：

| 阶段 | 现成函数与执行顺序 | 薄编排补充 |
| --- | --- | --- |
| 输入 | `adapters/slime/prepared_task_face.py:342 rollout_spec_from_view` 取公开 prompt/base/workdir；`:387 PreparedTaskFace.load` 读冻结身份。 | Conan 取原镜像；派生题在诊断配置明确覆盖实际 image ID、`image_local_build=True`、原父镜像和 recipe 摘要，不改 public bundle 或正式 loader。 |
| profile / 网络 | `sandbox_profile.py:665 rollout_profile_from_env`；`:914 start_egress_relay`、`:785 create_attempt_network`、`:826 connect_relay_to_network`、`:467 docker_run_args`。 | 宿主启动仅本次使用的本地无模型 HTTP fixture，relay 指向其可达地址/端口；采用真实 isolated internal 网络，不能把 `network=none` 的 replay 容器称正式 rollout 网络验证。fixture 未准备好则先只设计/构建，不删掉 prelaunch 检查凑通过。 |
| 物化 / 初始化 | 遵循 `generate.py:4592 _materialize_rollout_sandbox`：核实际容器镜像 → `envpack/materialize.py:60 build_probe_script` / `:153 evaluate_probe` → `sandbox_profile.py:1802 run_git_sanitize` → `:1790 run_trusted_init(rollout_trusted_init_script(profile))` → 原未跟踪清单 → public bundle / BASH_ENV → `:1736 run_rollout_prelaunch_check`。 | 原镜像用 `evaluate_image_digest` 核 RepoDigest；本地派生额外比对容器 `.Image` 与冻结 image ID（不能拿原镜像 digest 顶替）。host 保存完整 inspect/初始化/预检证据。诊断配方准备后再记一次 HEAD、Git差异、包版本与文件可见面。 |
| 基线 / 运行 / 导出 | `generate.py:3767 _prepare_workspace` 中的 `generate_baseline_manifest`；`slime/agent/harness/common.py:122 run_agent` → `slime/agent/sandbox.py:80 exec_and_wait` → `adapters/slime/docker_sandbox.py:94 DockerSandbox.exec`；导出复用 `export_frozen_patch`、`classify_frozen_patch`、`build_trusted_scoring_projection`（现成组合见 `replay_grade.py:293 _candidate_stage`）。 | 配方准备与基线操作显式分阶段。环境准备产物不能混入候选；先存原始初态，再存准备后基线及差异。每轮 fresh 容器，有限超时；调用方 `finally` 负责容器→attempt 网络→本次 relay/fixture 的精确清理与落账。 |

上表 `adapters/`、`envpack/` 前缀为 `rh2/src/repoharness2/`，`slime/` 前缀为 `rh2/src/`。不要直接借 `_candidate_stage` 代替 actor：它以 agent 应用补丁，但安装在后续 grader，且不包含相同网络、sanitize、公开 bundle 和 harness 启动过程。

## 2. 先验原路径，再验明确的诊断配方

`run_agent` 固定 `user="agent"`；`exec_and_wait:109` 的 launcher 先 `cd workdir`、`export HOME=/home/agent`，经 `setsid bash` 启动；`DockerSandbox.exec:111` 最外层也是 `bash -c`。首轮确定性脚本必须走这些函数，不能用 root、`su -` 或手工 login shell 替代。

**环境注入尚有接缝：**`generate.py:2867` 只在 `HarnessLaunchSpec` 记录 `BASH_ENV=/root/.rh2_bash_env`；`:2893` 实际 driver 参数没有 `env_injections`。`bringup.py:496` 合并训练守卫，实际额外 env 由 `slime/agent/harness/claude_code.py:60 launch_and_wait` 读取 `SLIME_AGENT_CC_EXTRA_ENVS`；profile 又隐藏 `/root`。所以先记录原启动环境，既不预判失效，也不暗中补 `source activate`。确需 PATH/可读 BASH_ENV 时，作为独立诊断版本显式注入、保存前后对照；这不是已修正式链。

每轮保留：UID/GID、HOME/cwd、`/proc/$$/exe`、Bash版本、PATH、BASH_ENV值及可读性、`command -v python/pip/pytest`、`sys.executable/version/path`、模块 `__file__`、包版本、实际 image ID/profile、退出码/完整输出。只采这些字段，不导出全部环境或鉴权值。

**容器内命令草案，未执行；由上述 `run_agent` 执行：**

```bash
id; pwd; readlink /proc/$$/exe
printf 'HOME=%s\nPATH=%s\nBASH_ENV=%s\n' "$HOME" "$PATH" "${BASH_ENV-}"
command -v python; command -v pip; command -v pytest
python -c 'import sys; print(sys.executable, sys.version); print(sys.path)'
```

随后在 `/testbed`、`$HOME`、`/tmp` 各创建、读取、删除一个唯一探针文件；对实际需要的安装前缀也做权限/写入验证。现成 trusted init 只 chown `/testbed` 和 home，**不交出 conda 前缀**。需安装且无权限时，记录失败；下一版本明确选择准备期完成安装，或用户可写 venv/前缀并固定启动 PATH，不复制 grader/54322 的 chown 当 actor 默认。

## 3. 三题最小动作和候选生效证据

| 样例 | 配方与公开验证 | 判定边界 |
| --- | --- | --- |
| Conan15422 | 原镜像，无已知环境修复；import `conan`、`conans` 并记录源码路径。在独立临时项目以公开 base 的 `conan/tools/cmake/presets.py:15 write_cmake_presets` / `toolchain.py:187 CMakeToolchain.generate` 对应已有测试用法生成预设，保存 JSON。主审选定具体公开 fixture/窄测试后冻结命令。 | base 缺 jobs 是待实现功能，不是环境错误；最低验证只需能生成/读取预设，不额外要求下载包或真实并行编译。无 conf 与两个 jobs 值作为后续行为对照，不能编造当前已存在的 test ID。 |
| Dask8597 | `compat_v1` 镜像仅 COPY wheel；执行已存 recipe 的 `revised_install`，确认 `pytest==7.4.4` 与 editable 安装真的生效。按公开题面运行 `dask.array.from_array(numpy.zeros((3, 0)))[[0]]`，另跑 NumPy 对照。 | base 的目标 `OverflowError` 是预期复现；ImportError、权限或安装失败另记。recipe 原件：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-8597/gold/recipe/recipe.json`。 |
| Pydantic8511 | `pydantic_v1` 镜像 COPY wheels/设置离线 pip；复用 recipe 的 editable 安装与从当前 `pyproject.toml` 读取 testing/testing-extra 依赖的动作。原样跑公开 `user_prompt.txt` 中 stdlib/Pydantic `repr=False` 示例。 | base 输出仍含 `c=2` 是目标行为；记录 Python及 pydantic/core来源，不能把 grader Python3.8 外推为公开报告的3.11。recipe 位于同一 runs 根的 `pydantic_v1/tasks/pydantic__pydantic-8511/gold/recipe/recipe.json`。 |

**三题共用候选生效对照：**在 fresh 诊断副本中，以 agent 对将被导入的目标源码增加唯一、无业务效果的模块常量，按选定安装步骤执行，再由新 Python 进程导入目标模块，核常量与 `__file__`；从 `/testbed` 和临时工作目录各查一次，区分 cwd 偶然优先与 editable 安装生效。改动仅属标记清楚的诊断候选，不是模型解答。若需证明新增依赖被安装，单独用预置本地小 wheel 和候选元数据对照，不能仅用 pip 末码代替证据。

公开复现脚本放 home/tmp，不自动写入候选。导出后保存 frozen patch/基线/投影摘要；下一 fresh 容器经真实 replay 对账。Dask/Pyd 必须复用 `rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py` 的 **`--code-root <实际RH2根目录> --recipe … --audit-dir … -- run …`**，再传现成 `--candidate patch-dir:<目录> --derived-image <实际ID> --derived-image-recipe <说明>`；`--code-root` 必填，指向包含 `src/` 与 `scripts/replay_grade.py` 的目录。仅用原 `scripts/replay_grade.py --derived-image` 会漏诊断安装替换。不改来源测试或参考；若新镜像身份变化，旧资格账本不能冒充新资格。

## 4. 交付和范围

逐题交 `inputs.json`、原路径/诊断配方两组命令日志、包来源/标记对照、public reproduction、补丁投影与重放账本、资源及清理记录；失败区分目标 bug、环境准备、候选导入、协议与基础设施。**当前仍缺**：薄编排本体、可运行 CPU Docker 环境和镜像/wheels可用性、三题最终公开窄命令、actor安装策略，以及本批有效启动 env。

上述共享 launcher 验证并未运行 CC Bash 工具。GPU 前可加一个**无模型的固定 Anthropic tool-use fixture**：用 `bringup.py:372 ClaudeCodeDriver` 安装并运行真实 CC（平台包参数 `SLIME_AGENT_CC_PLATFORM_TARBALL`，默认核 `RH2_CLAUDE_CODE_VERSION=2.1.205`），fixture 只请求执行上述公开诊断脚本并收回工具结果。旧 `experiments/fa_bringup/claude_code_http_probe.py` 仅是文本/故障响应参考，须新增确定性 tool-use/tool-result 往返，不能称已有该套件。这样能查 CC 工具实际 shell/env，无权重或付费 API。若省略，明确把真实 CC 工具环境留到首次基座冒烟核实。

后续按本单执行并通过，才能证明所列配置下开发操作与重放可行；本单目前没有提供这项运行证明，也不证明模型解题能力、任务最终质量、正式 prepared loader 派生环境消费、训练 capture/receipt/组装配或 learner 正确性。本次仅静态读源码/公开材料并写本文件，未运行历史项目代码、Docker、SSH、模型或安装依赖。
