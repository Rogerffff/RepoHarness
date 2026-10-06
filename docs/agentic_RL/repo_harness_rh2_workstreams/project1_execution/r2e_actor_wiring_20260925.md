# R2E 正式 actor 接入：派生镜像、`.venv` 与提示措辞（E09 + D4=B）

2026-09-25 / Claude（B 线，R2E）。用户 09-25 批准由本线程今晚实现、交 A 审。对应 [A→B 接线交接 §5](base_probe_chain_fixes_20260923/b_wiring_handoff_20260924.md) 的 E09，以及 [R2E 接线](r2e_grading_wiring_20260920.md) 当时留到流水线阶段的 D4=B（正式 actor 使用本地派生镜像）。同批还收了 [Codex 批次三复核](r2e_t0_batch3_review_20260924/README.md) 的 F1（orange3 修订与环境绑定）。**状态：已实施；单测、不建网络的真实核对、以及 8 题经真实 Claude Code 启动链（桩端点）的开发命令核对都已通过；经 Qwen adapter 的链路未验证；待 A 审。**

## 1. 为什么要改

- **镜像**：`rollout_spec_from_view` 取 `public.image`。R2E 的 `public.image` 是来源镜像：`/r2e_tests`（隐藏测试）对所有用户可读，git 的 main 分支上有修复提交（以 pandas `294cbc8d` 为例，`git show 294cbc8d` 就是答案）。派生镜像此前只在回放评分里消费。E09 交接没有写这一项。
- **解释器**：`RolloutTaskSpec.expected_interpreter_prefix` 默认 conda，R2E 的 `.venv` 会被启动前激活核查拒绝。
- **提示**：R2E 公开面沿用 SWE-Gym 的 `PUBLIC_SYSTEM_HINTS`，写着 conda 环境、pip 可用、"评分会重置测试文件"，三处对 R2E 都不成立。正式链不把它注入系统提示，但它随 public bundle 写进容器的 `/rh2/public_task_bundle.json`。
- **orange3 绑定（Codex F1）**：`r2e-mr-020` 只在 SciPy 1.5.4 的 `+env_v2` 镜像上成立，旧 `r2e_derive_v1` 覆盖条目仍能通过互检，重算 gold 是 11/13、reward 0。

## 2. 改了什么

| 文件（写入者） | 改动 |
| --- | --- |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py`（B） | R2E 题的 `RolloutTaskSpec`：`image` = 覆盖条目的派生镜像 image ID（不可重指），`image_local_build=True`，`env_activation_script` = `R2E_VENV_ACTIVATION`（`VIRTUAL_ENV` 与 `PATH` 指向 `/testbed/.venv`，与镜像 ENV 一致，不设 `PYTHONPATH`），`expected_interpreter_prefix` = `/testbed/.venv`。R2E 题缺覆盖条目 = 构造任务面即拒，不回退来源镜像；非 R2E 题给覆盖条目也拒。`grading_spec` 对 R2E 同样切到派生镜像 ID（`image_local_build_id` 同值）。新增 `overlay_binding_mismatch`（回放与正式 actor 共用的互检）与 `load_overlays_input`（覆盖表路径与摘要成对，缺一即拒） |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py`（B） | `_overlay_static_mismatch` 改为调用共用互检，行为不变，另加修订所需的环境步骤 |
| `rh2/src/repoharness2/envpack/environment_overlay.py`（B） | `REVISION_ENV_REQUIREMENTS = {"r2e-mr-020": "+env_v2"}` 与 `env_requirement_mismatch`；模块说明里"正式 actor 不在本片"改为已实现 |
| `rh2/scripts/build_r2e_derived.py`（B） | 本题修订要求的环境步骤缺失时，构建在动 Docker 之前失败，不写 facts，也不进 `overlays.jsonl` |
| `rh2/src/repoharness2/envpack/ingest_r2e_subset.py`（B） | R2E 公开面用 `R2E_PUBLIC_HINTS`；重新生成产物，提交记录 pin `adbd27a1…` → `781363b0…`，只变 48 题的 `public_hints` 与 `public_bundle_digest`；旧产物归档 `s2_r2e/ingest_history/material_v3_conda_hints_20260925/` |
| 测试（B） | `tests/adapters/test_r2e_actor_task_face.py` 7 例；`tests/envpack/test_build_r2e_derived_env.py` 加构建反例；`tests/envpack/test_ingest_r2e_subset.py` 加提示措辞；`tests/adapters_miles/test_r2e_group_transport.py`（B 09-23 补的 R2E 组级运输）两例给合成 R2E 题补覆盖条目（经环境变量），并在本测试内把激活探针对 `/testbed/.venv` 前缀的应答包一层——共用替身 `sandbox_test_support.ProfileFakeState` 不论声明什么前缀都答 conda，同一批里 SWE 与 R2E 成员共用一个替身，没有改共用替身 |

**没有改 A 的文件**：`bringup.py` 不显式传覆盖表（A 今晚在改它），`PreparedTaskFace.load` 在调用方未传时读 `RH2_IMAGE_OVERLAYS_PATH` / `RH2_IMAGE_OVERLAYS_SHA256`；`generate.py` 不需要改（激活核查只比 `sys.executable` 的前缀；`image_local_build` 本来就豁免 registry digest 比对，rollout 只做 `image inspect` 与 `run`，不 pull）。

## 3. 已验证

- 单测：新增 9 例全过；envpack、回放与覆盖表相关套件 249 passed / 1 skipped（改提示前），改提示后 `test_ingest_r2e_subset.py` 37 passed。改完后第一次全量非 Docker 测试有 2 个失败，就是上面那两例 R2E 组级运输：合成 R2E 题没有覆盖条目，被新规则拒绝，属于本改动的预期后果，已按上表修正。
- **不建网络的真实核对**（A 线机器，`rh2/experiments/r2e_actor_20260925/activation_check.py`，证据 `runs/r2e_actor_20260925/activation_check.json`）：orange3 `9b5494e2`（Python 3.7.9，`+env_v2`）与 pandas `32dd55cb`（`+material_v2`）各一次。按正式代码构造任务面，用派生镜像 ID 起 `--network none` 容器，按正式函数跑可信初始化、写 `/rh2/bash_env`、以 agent 身份跑激活核查：两题都通过；同一容器改用 conda 前缀的反例被拒；R2E 预检（解释器可执行、隐藏测试不可读、HEAD 没有子提交）三项全过；容器已清理。

- **真实 Claude Code 启动链（桩端点）**（09-25 夜，同一台 A 线机器）：用任务二的共用入口 `devcheck.py`（A 线 `acceptance_startup_2` 的正式装配）加 R2E 一层 `rh2/experiments/r2e_actor_20260925/r2e_devcheck.py`，首批 8 道 R2E 题各跑一次：容器、relay、专用网络、git sanitize、可信初始化、激活文件、启动前与激活核查、`ClaudeCodeDriver.run` 全部走正式代码，CC 2.1.205 在 agent 身份下逐条执行命令清单；8 题的 R2E 预检三项全过，容器实际镜像等于覆盖表里的派生镜像 ID，`python` 落在 `/testbed/.venv`，激活文件对 agent 不可写，运行后无残留。逐题结果见 [R2E 首批开发命令核对](r2e_static_review_20260925/actor_devcheck.md)，证据 `runs/r2e_actor_20260925/devcheck/`。

## 3.1 Codex 09-25 复核后的修正（R1、O1）

- **R1：修订绑定批准的依赖内容，而不只是步骤名。** 原来 `REVISION_ENV_REQUIREMENTS` 只要求 `recipe_id` 里有 `+env_v2`，而 `env_v2.sh` 是通用安装脚本，给它一份 hypothesis 或别的 SciPy 版本的配方也能通过。现在每条要求带 `approved_recipe_sha256`：批准并用真实 grader 复验过的配方内容身份（`composite_recipe_digest`，覆盖 recipe 脚本、环境步骤脚本与逐个 wheel 的 sha256）。r2e-mr-020 登记的是 env_pins_v2 里 orange3 条目（scipy==1.5.4）按当前脚本算出的摘要，与批次三正式运行所用 derived7 镜像记录的 recipe_sha256 相同。构建（`build_one`，在动 Docker 之前）、回放与正式 actor 任务面（共用 `overlay_binding_mismatch`）三处都按它核对；错误在启动前暴露，不会变成 reward 0。
- **验证**：新增构建测试，hypothesis wheel、SciPy 1.7.3 两种错误配方都在 Docker 之前被拒，批准配方走到 Docker 边界；登记摘要与按当前脚本重算的结果一致，脚本或依赖一变这条测试就失败，提醒先复验再更新登记。任务面测试加了"步骤名对、摘要不对"的反例。在 A 线机器上用真实覆盖表核对：derived7（批准配方）构造通过，旧的 `r2e_derive_v1` 条目被拒。numpy `43e333e2` 没有这类修订，行为不变。Codex 列出的 5 份维护测试 68 passed（原 66 + 新增 2）；`tests/adapters`、`tests/envpack`、`tests/adapters_miles` 非 Docker 部分 1518 passed、347 skipped、0 failed。
- **O1**：`load_overlays_input` 改为解析核过摘要的同一份字节（新增 `parse_environment_overlays`），不再按路径重读；加了测试。

## 4. 未验证，与请 A 审查的点

1. **启动链**：经桩端点的真实 CC 链已跑（见 §3），经 Qwen adapter 的链路没有跑。A 的 `acceptance_startup_2.py` 本身调 `rollout_spec_from_view` 时仍不带覆盖条目，对 R2E 题会拒绝；本线程的 `r2e_devcheck.py` 是在外层把任务面换成正式 `PreparedTaskFace`（带覆盖表）后再调用它，没有改 A 的文件。正式探针若由 `bringup.py` 起任务面，覆盖表经环境变量或显式参数进入（见第 2 点）。
2. 覆盖表经环境变量进入 `PreparedTaskFace.load`，是否改成 `bringup.py` 显式传参，由 A 定。
3. 正式 actor 没有跑 R2E 预检（回放在候选阶段前以 agent 身份跑）。派生镜像身份由 ID 与覆盖表互检钉住，预检是第二道保险；建议加进 `generate.py` 的 R2E 启动前核对，属 A 的文件。
4. 提示措辞（`R2E_PUBLIC_HINTS`）按用户决定分来源，具体句子请 A / Codex 审；它不改评分。
5. 派生镜像只在构建机本地存在，正式 actor 所在主机要预先有这些镜像（rollout 不 pull）；分发方式属于流水线。
6. 摄入产物换了 `public_bundle_digest`，已有的 R2E prepared 产物需要重新准备（目前只有 B 线在 A 线机器上的 `replay_b*`）。

静态审查材料 v2 的 `public_bundle.json` 仍是旧提示（首批 8 题按 v2 审，提示差异不影响题意与评分判断）；之后的批次用重新生成的材料。
