# mypy15139：本夜 CPU 接续

2026-09-29。沿用 quality_batch01_20260921/expansion/batch03/results/python__mypy-15139 的审查/独立复核。base `16b936c15b074db858729ed218248ef623070e03`；未执行本机历史项目。

公开命令取自题面三行、公开 options.py 的版本/force 政策、check-classes.test 的 Type[Any] 赋值及实际旧 lowercase 测试。原例禁 config/第三方包、固定目标 Python3.10，不执行被检查代码。逐条保留 stdout/stderr/RC；CLI 中类型错误非零不当作环境失败，收集错误不能当成预期类型错误。核导入是否 /testbed 源码及 .so 遮蔽。

## 私有决定性对照

`private_semantic_spec.template.json` 在全新 base/gold/unconditional_lowercase 上跑同一公开 CLI 和回归；原例 base/gold 的 Type/type/reveal 实际结果决定是否兑现公开目标，不把官方单 case 通过当完整修复。固定小写补丁在 gold 修改位置取消选项/版本判断，违反公开 --force-uppercase-builtins 和旧版本政策；policy_force / policy_old 应看到 type[Any] 而正确兼容输出应 Type[Any]，公开 Type[Any] 测试应失败。这个负对照不是八条容器测试。

source-only 补丁需分别走本批正式 replay_grade。冻结参考只有 F2P1/P2P0，原官方单键名 `testTypeLowercaseSettingOff`；记录 base/gold/退化奖励、实际加载、完整目标输出、解析键和清理。若 gold 已得1而题面 reveal 仍 Type，与现代错误 type 混用，就是公开目标未完整覆盖；若退化得1且 force/旧版本失败，则另实证 S1/T2b。无需把新测试或参考解直接写入正式评分。

## 当前范围与剩余项

仍需真实 actor 开发事实、私有 CLI 对照、正式单键对照、关键回归、源码导入与环境/清理/独立复核。历史 install_wave1 只有 grader 的 noop0/gold1，不能替代本批 actor。单键遗漏已是具体静态疑点；本夜在实际输出前不写成运行事实。

若实测证明目标缺失，仍仅诊断，不纳入能力比较分母或训练；SWE 修订机制尚待设计/成本批准实施。题面允许统一别名或采用源码别名，builtins. 消歧边界仍保留，不能随意锁全部字符串相等。

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
