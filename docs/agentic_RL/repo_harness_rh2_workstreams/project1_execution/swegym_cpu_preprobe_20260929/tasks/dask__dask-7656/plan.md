# Dask7656：本夜 CPU 接续

2026-09-29。静态审查及独立复核沿用 quality_expansion_20260925/results/dask__dask-7656；未重新盲审，未在本机执行历史项目。

## 已交付输入

- `runs/swegym_cpu_preprobe_20260929/task_inputs/dask__dask-7656/public_commands.json` 可直接给 devcheck.py；命令只来自题面与 base 公开测试。原例和增强例在未修 base 预期非零，但必须看到缺失 primary_key 的目标异常，环境/收集失败不能算复现。公开旧测试应通过。
- 同目录 `private_semantic_spec.template.json`、`gold.patch`、`opaque_dataclass.patch` 仅供私有控制。root 填本批镜像并把 files 路径解析到远端，分别在全新容器跑 base/gold/opaque；prep 失败即无效。
- opaque 在 gold 修改位置把 dataclass 当不透明对象，违反公开旧测试要求的嵌套 Delayed 求值。它预期原例成功而 default_nested 失败；需把 source-only candidate.diff 经正式 replay_grade 评分，预期 0，确认目标测试执行、完整输出及清理。私有语义退出码不替代正式评分。

## 最小判据与剩余项

base 原例 AttributeError；gold 原例输出 Hack works、增强例 ENTRY_DEFAULT_NESTED_PASS；opaque 增强例不能通过。先校准真实 actor 身份、初态、导入、逐命令 RC/墙钟/收尾，再核本批 noop=0/gold=1 和 opaque 正式分数、全部参考键及额外失败。历史 compat_v2b 的 noop/gold 差异已有核验，只适用于旧版本。

已存在 init=False/post_init 状态仍是扩展边界：旧 gold 必过 oracle 已撤回，不凭 gold 行为扩大题意。公开 Fix 提示需在用途保留，本题不能解释为纯独立定位能力。当前用途尚 conditional；CPU/模型资格均未提前签发。

## 版本与依据

base `07d5ad0ab1bc8903554b37453f02cc8024460f2a`；实际字段分支 dask/delayed.py:110、公开测试 test_delayed_with_dataclass:99 / test_traverse_false:280 / test_to_task_dask:44 已核。历史 compat_v2b: Python3.9.19、pandas1.3.5、SETUPTOOLS_USE_DISTUTILS=stdlib；恢复输入见 env_recipe_repair_20260919/compat_v2b/recipes/dask__dask-7656.json，actor 与 grader 是否实际一致须本批记录。

## 可执行构建计划（2026-09-29 补齐）

本题 task_inputs 内：`grader_build_plan.json` 由 `rh2/experiments/base_probe_20260922/build_derived.py --plan PLAN --out-dir OUT --tag-suffix 20260929` 消费；`actor_build_plan.json` 由 `rh2/experiments/task2_swegym_dev_20260925/build_actor.py PLAN --out-dir OUT` 消费；`grader_install_recipe.json` 已复制/生成。三个题合并计划放 Dask7656 的 `three_task_grader_build_plan.json`、`three_task_actor_build_plan.json`。全部使用 immutable source manifest、具体 pins 与逐 wheel SHA；构建还未执行。

Dask7656 历史批次名 compat_v2b 映射 builder 的 `style=compat_v1`，因为实际 Dockerfile 同为 COPY 到 `/opt/rh2/compat-wheels/`；这不表示改用 6626 的 pytest 配方。grader 只存 pandas wheel，评分候选安装段 export SETUPTOOLS_USE_DISTUTILS=stdlib、离线 pandas1.3.5 后原 editable 安装。actor 直接装 pandas1.3.5，并用 `etc/conda/activate.d/rh2-dask-distutils.sh` 设置 stdlib；正式 BASH_ENV 调用 source activate testbed 会读钩子，须用另存 `public_environment_check.json` 实测。只装依赖和环境钩子，不改 /testbed。语义控制若绕过 conda 激活、只改 PATH，必须显式 export SETUPTOOLS_USE_DISTUTILS=stdlib。

Dask6626 grader COPY pytest7.4.4 wheel，原安装 recipe 中才 pin；actor 在构建时装好 pytest7.4.4。mypy15139 grader 用 install_wave1 的九 wheel 与 PIP_NO_INDEX/PIP_FIND_LINKS，原 test-requirements + editable 命令不改；identity recipe 只是让可选 wrapper 有具体文件可用，也可直接正式 replay_grade。actor 预装同九依赖，不带私有测试或 gold。build_actor 不保留离线 wheel：足够当前已装依赖的公开开发验证，不宣称覆盖任意新增依赖的离线供应。

## 已登记完整返回类型缺口的决定性候选

另交 `wrong_result_type.patch`：过滤缺失字段，但在原 dataclass 重建位置固定返回 types.SimpleNamespace。该候选只利用 gold 修改位置替换对象类型，未改测试；字段/嵌套值可求值，但 dataclass 类与方法语义丢失。公开 delayed 行为及现有重建 typ 的语义要求传入原类对象，已有公开增强命令中的 isinstance(entry, Entry) 会拒绝它。此候选直接回答既有审查登记的“最终只查 a、没有检查完整对象类型”缺口，预期比 opaque 更可能被正式参考漏判。先语义确认错误，再正式评分；若得1就是 S1/T2b，不能因 opaque 得0而核销它。这里的预期尚未运行。私有 spec 已加变体，并显式 export SETUPTOOLS_USE_DISTUTILS=stdlib（semantic_control 只设 PATH，不读 conda hook）。
