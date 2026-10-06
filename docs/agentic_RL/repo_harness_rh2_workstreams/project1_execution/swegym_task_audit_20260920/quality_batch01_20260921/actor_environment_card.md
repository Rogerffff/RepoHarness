# 09-21 解题环境卡：历史代码快照

2026-09-21 / 静态核对快照，**不是这 12 题实际 actor 容器的验收记录**。本页供协调者/私有 reviewer；公开角色只收材料包中的中性 `environment_brief.md`。本页仅保留当时事实，不充当新批次的环境配置或执行方案。所有源码路径均相对仓库根。

**2026-09-25 整理：**通用步骤已移至[开发条件共用验证流程](../../actor_development_validation.md)；Dask/Moto/DVC/Conan 的具体修复建议移至[本批任务二](../../environment_batch_20260925.md#22-任务二结果负责人待登记)。更新 Markdown 不会修改镜像或执行验证。新任务需制作本批实际环境卡；A 线后续修复以最新交接和实测为准。

| 项目 | 09-21 可确认的设置 / 证据 | 当时还不能声称什么 |
| --- | --- | --- |
| 输入与镜像 | `adapters/slime/prepared_task_face.py:rollout_spec_from_view` 使用 public bundle 的 image/digest、base、workdir 与 `render_user_prompt`；`generate.py:_materialize_rollout_sandbox` 核物化血缘，允许 HEAD=base 或来源环境提交的 parent=base。 | 12 题包是精确 base 源码；不包含真实镜像的环境提交、未跟踪资产和完整可见祖先历史。静态未知不能解释为这些线索在真实环境不存在。 |
| 修复配方 | 私有材料逐题引用 09-19 最终环境对照；50 道原基线范围单独引用原账本。 | 这些是评分/诊断条件证据。正式 face 仍取 public 镜像；没有“所有修复自动被 actor 消费”的证明。本批还未选择具体 actor 派生配方。 |
| 身份与可写路径 | `sandbox_profile.py:RolloutSandboxProfile` 固定 agent/54321；`rollout_trusted_init_script` 对 `/testbed`、`/home/agent` chown；`common.py:run_agent` 用 agent 启动。 | grader 的 rh2grader/54322 与解释器可写前缀不自动适用于 actor；能写工作区不等于能改系统包环境。 |
| 解释器/激活 | `materialize.py:BASH_ENV_*` 写入 `/root/.rh2_bash_env`，激活 conda testbed；`generate.py` 构造 env_injections；`claude_code.py` 的 launcher 支持 `SLIME_AGENT_CC_EXTRA_ENVS`。 | 文件落在 `/root`，而 rollout 的隐藏路径含 `/root`；需核实际 shell 是否收到并可读取激活设置。还需核 image ENV/PATH 或其它注入是否已提供环境，不能仅据此宣布已出错或已激活。 |
| 网络 | 正式 profile 每 attempt 独立 internal 网络，经 relay 通模型代理及显式内部服务。grader 为独立 profile/deny_all。 | 不默认 agent 能查公网文档、下载包/权重；也不把所有任务宣判必须断网可解。逐题分准备、解题、候选安装、测试执行。 |
| 资源 | rollout 当前默认 2 CPU、4 GiB、PID512、`/tmp`1 GiB、home256 MiB；可写层请求 8 GiB，强制配额默认关闭。可由 `RH2_SANDBOX_*` 配置。 | 这是代码默认，不是最终按题档位或实测保证。MONAI 等 grader 的高资源档不自动写入 rollout。rollout shm 实际值需 inspect，不能借 grader 的变量代填。 |
| CLI 与工具 | `bringup.py:ClaudeCodeDriver` 离线安装平台二进制，默认核 CC 2.1.205，可配置；vendored harness 经 `run_agent` 启动。public allowed_tools 为 bash/edit。 | allowed_tools 字段不证明所有 CLI 工具配置已一致；未验证本批真实工具命令、执行 shell、运行版本。 |
| 公开/私有可见性 | 正式准备写 public bundle，Git sanitize 清未来 refs/reflog/悬空对象；prelaunch 核身份/网络等。 | 当前静态包没有 `.git`，不是实际 Git 操作体验验收，也不是镜像资产无答案的证明；候选镜像需另核可见文件/包。 |
| 提示词 | `bundles.py:render_user_prompt` 渲染 issue；public_hints 留在 public bundle。`rollout_spec_from_view` 的 prompt 只调用前者。 | 本批 `user_prompt.txt` 是当前函数静态渲染值，非捕获的模型请求。未证明 public_hints 已成为 CC system prompt，也未记录工具/CC 自动附加消息。 |

上述源码前缀为 `rh2/src/repoharness2/`；`common.py` / `claude_code.py` 位于 `rh2/src/slime/agent/harness/`。源码身份记录在 `material_check.json`，行号可能随并行实现变化，复核按函数名查。对边界的已知审查范围见[chain_readiness.md](../chain_readiness.md)，不把旧“未修”快照当最新状态。

## 逐题必须补的开发需求表

现行模板与材料要求见[共用流程 §2](../../actor_development_validation.md#2-静态审查者交付什么)。

## 后续 CPU 负责人回填的最少事实

现行运行步骤与证据要求见[共用流程 §3–5](../../actor_development_validation.md#3-cpu-执行与修复五步)。grader 成功不证明 actor 可用。

## 2026-09-24 补充：开发条件缺口怎样修复和避免重复遗漏

本节旧入口保留。09-24 的执行建议于 09-25 分拆到[通用方法](../../actor_development_validation.md)与[本批具体修复安排](../../environment_batch_20260925.md#22-任务二结果负责人待登记)，尚不能视为新修复已完成。

历史背景保留：09-19 修复主要验证 grader；首轮前三题有专门开发检查，新增五题的准备主要核导入/pytest，后续求解又暴露路径问题。Dask 窄测试曾列入 CPU 方案，Moto 版本差异也曾记录后暂缓处理；既有未执行的检查，也有已知未修，不能统称静态审查没有发现。原依据见[首轮运行记录](../../base_model_probe_run_20260922.md)、`rh2/experiments/base_probe_20260922/dev_checks/`及[8 题处置卡入口](../../base_probe_analysis_20260922/README.md)。
