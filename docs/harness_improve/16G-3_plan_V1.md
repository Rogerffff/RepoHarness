

**Stage 16G.3 执行计划草案**

阶段名称：

```text
Stage 16G.3：受控命令行诊断、内部项目测试路由和临时复现能力
```

阶段目标：

```text
让 RepoHarness 从“主要依赖静态读写和少量保守命令”的 harness，
升级为能支持 Claude Code / Codex 风格动态诊断闭环的训练环境。
```

核心闭环是：

```text
读代码 / 搜索
-> 运行公开诊断命令或定向测试
-> 查看 stdout / stderr / exit code
-> 使用 scratch Python 做临时复现
-> 修改代码
-> 再运行验证命令
-> 查看 diff
-> 结束轨迹，由最终 verifier 计算 reward
```

**一、总体设计方向**

Stage 16G.3 不再把 `run_project_test` 作为默认模型可见主工具。更推荐的设计是：

```text
模型可见工具：
  run_public_command(command: str, cwd=".", timeout_sec=60, purpose?)
  scratch_python(code: str, cwd=".", timeout_sec=30, purpose?)

模型不可见但内部必须实现：
  CommandStringV1Parser
  CommandClassifier
  ProjectTestRouter
  PublicCommandProfile
  PublicTestProfile
  TestTrustClassifier
  PublicExecutionSubstrate
```

也就是说，模型看到的是接近 Claude Code / Codex 的命令行形式：

```bash
python -m pytest tests/test_parser.py::test_empty_input -q
python -m compileall src
git status --short
rg "missing_timeout" src tests
```

但 RepoHarness 内部不能把它当作自由 Bash 执行，而是：

```text
command string
-> CommandStringV1Parser
-> normalized argv
-> command classifier
-> public command / project test / repo inspection / smoke / denied
-> isolated public execution snapshot
-> sanitized result + artifact + trust facts
```

**二、当前必须明确的待决策点**

这些地方现在不要让执行 agent 自己临场决定。

**决策 1：模型可见命令入口**

选项 A：`command_profile_id + structured args`

优点：最安全、实现简单、schema 清晰。  
缺点：最像私有 DSL，和 Claude Code / Codex 的命令行表面差距大。

选项 B：`argv: list[str]`

优点：比 profile 更接近命令行，执行安全，避免 shell。  
缺点：模型表面仍然不像真实命令行，训练分布和真实产品有差距。

选项 C：`command: str` + `CommandStringV1`

优点：最接近 Claude Code / Codex 的模型可见表面。  
缺点：需要实现受限 parser、classifier 和更多拒绝语义。

我的决定：采用选项 C，但只支持 `CommandStringV1`，不支持完整 Bash。底层执行仍然必须归一化成 `argv`，并且使用 `shell=False`。

**决策 2：`run_project_test` 是否暴露给模型**

选项 A：作为模型可见工具暴露。  
优点：实现简单、审计方便。  
缺点：训练出 harness 专用行为，和真实软件工程 agent 的工作方式不一致。

选项 B：不作为默认模型可见工具，只作为内部 API、acceptance probe 和可选 scaffold 工具。  
优点：模型学习真实命令行测试工作流，内部仍能审计测试语义。  
缺点：需要 `ProjectTestRouter` 从命令中识别测试行为。

我的决定：采用选项 B。

**决策 3：第一版是否允许 `tox` / `npm test`**

选项 A：条件允许，只要存在 `tox.ini` / `package.json`。  
风险：`tox` 和 `npm test` 背后可能执行任意 shell 字符串，等于绕过 `CommandStringV1`。

选项 B：第一版拒绝，留到 V1.1。  
优点：安全边界清晰，避免二级 shell 解析漏洞。  
缺点：覆盖面较窄。

选项 C：允许，但必须递归解析 `tox.ini` / `package.json scripts`，二级命令也走同一套 classifier。  
优点：覆盖面更大。  
缺点：实现复杂度明显上升。

我的建议：第一版采用选项 B。`tox`、`npm test`、`make test` 标记为 `planned_not_enabled` 或 `manifest_derived_deferred`。等 `CommandStringV1`、Docker 隔离和测试信任分类稳定后再扩展。

**决策 4：是否先做数据集命令形态统计**

选项 A：直接按直觉 allowlist 实现。  
风险：上线后大量合理命令被拒绝，误判为模型能力差或 harness 工具差。

选项 B：实现前先对 SWE-bench Verified / Lite 或当前目标任务集做命令形态采样。  
优点：allowlist 有事实依据，能识别 Django、subdir、env、pytest 参数等真实需求。  
缺点：多一个准备阶段。

我的建议：采用选项 B。正式冻结 `CommandStringV1` allowlist 前，先做 empirical grounding。

**三、Stage 16G.3-0：命令形态经验统计**

这是新增的准备阶段，不改模型工具。

目标：

```text
统计目标任务集中真实公开测试、项目配置和常见诊断命令形态，
为 CommandStringV1 allowlist 和 env allowlist 提供依据。
```

需要统计：

```text
pytest / python -m pytest 占比
unittest 占比
Django manage.py test 占比
tox / nox 占比
npm / yarn / pnpm 占比
go test / cargo test / make test 占比
是否需要 cwd 切换到子目录
是否需要 PYTHONPATH / DJANGO_SETTINGS_MODULE / CI / NODE_ENV
是否常见 PYTEST_ADDOPTS / PYTHONHASHSEED / PYTHONDONTWRITEBYTECODE
是否存在 task-declared public test command
是否只有仓库配置，没有任务声明命令
```

产物：

```text
stage16g3_command_shape_inventory.json
stage16g3_command_shape_inventory.md
```

验收：

```text
正式 allowlist 中每一类 V1 支持命令都能追溯到统计依据；
不支持但高频出现的命令必须被标记为 V1.1 candidate，而不是静默忽略。
```

**四、Stage 16G.3A：共享公开执行底座**

目标：

```text
实现 run_public_command 和 scratch_python 共用的执行、隔离、输出、artifact 和审计底座。
```

这个阶段不应该先追求支持很多命令，而是先把执行边界做正确。

必须实现：

```text
1. disposable public execution snapshot
2. candidate patch 投影到 snapshot
3. Docker 或等价隔离后端执行
4. network_policy=deny / none，并且 fail closed
5. 不挂载 run_dir
6. 不挂载 runtime-private artifact
7. 不挂载 hidden verifier、gold patch、test patch
8. 执行后丢弃 snapshot side effects
9. 检查真实 episode workspace 没有被污染
10. stdout / stderr 截断和脱敏
11. sanitized artifact 和 raw runtime-private artifact 分层
12. 统一 permission denial envelope
```

每次执行至少记录：

```text
public_execution_snapshot_digest
candidate_patch_included
execution_side_effects_discarded
workspace_mutation_detected
post_run_workspace_digest_matches_pre_run
final_patch_pollution
network_policy
network_isolation_proven
run_directory_mounted
runtime_private_artifact_visible
host_path_visible
result_observation_valid
```

明确拒绝：

```text
local_process 作为正式 swe_public_core 执行后端
普通 workspace_adapter.run_command 直接跑模型可见 public command
真实 episode workspace 内直接执行测试或 scratch Python
raw artifact 直接暴露给模型
```

验收：

```text
public execution isolation probe
network fail-closed probe
artifact visibility probe
workspace pollution probe
candidate patch included probe
```

**五、Stage 16G.3B：`run_public_command` + CommandStringV1**

目标：

```text
提供模型可见的命令行诊断入口，但只支持受限简单命令。
```

推荐工具 schema：

```python
run_public_command(
    command: str,
    cwd: str = ".",
    timeout_sec: int = 60,
    purpose: str | None = None,
)
```

内部流程：

```text
1. command 长度检查
2. Unicode NFKC normalize
3. raw string shell metacharacter scan
4. shlex.split
5. token allowlist 校验
6. cwd workspace boundary 校验
7. command classifier
8. profile / router 匹配
9. public execution substrate 执行
10. 返回 sanitized result + structured facts
```

Parser 顺序必须固定为：

```text
长度上限
-> NFKC normalize
-> raw string metacharacter scan
-> shlex.split
-> token-level policy
-> command classifier
```

第一版建议长度上限：

```text
command <= 1024 字符
token 数量 <= 128
单个 token <= 256 字符
```

第一版允许命令，待经验统计后最终冻结：

```text
python -m pytest <selector> [safe pytest flags]
pytest <selector> [safe pytest flags]
python -m unittest <selector>
python -m compileall <workspace-relative-path>
git status --short
git diff --name-only
git diff --stat
git grep <pattern> [path]
rg <pattern> [path]
```

第一版明确拒绝：

```text
bash -lc
sh -c
python -c
;
&&
||
|
>
>>
<
&
$()
反引号
heredoc
变量展开 $VAR
shell glob *
curl
wget
git clone
pip install
npm install
rm
mv
cp
chmod
chown
git log
git show
git reflog
git cat-file
git blame
```

需要特别写入 spec 的 edge case：

```text
pytest -k 'A and B'
  应允许，quoted string 内空格合法。

pytest -k 'A | B'
  第一版建议拒绝，因为 raw string 中出现 |，避免 quoted metacharacter 绕过策略。

pytest tests/x.py -v -v
  应允许，重复 safe flag 合法。

pytest tests/\u2024py
  应拒绝或 normalize 后拒绝，防 Unicode 同形路径攻击。

pytest $'tests/x.py'
  应拒绝，raw string 中出现 $。

空字符串
  拒绝。

超长字符串
  拒绝。
```

拒绝结果必须包含：

```text
reason_code
policy_version
safe_alternative_tool
safe_rewrite_example
retryable
```

例如：

```text
python -c 被拒绝：
  建议使用 scratch_python(code=...)

pytest a && pytest b 被拒绝：
  建议拆成两次 run_public_command

pytest ... | tee out.log 被拒绝：
  告知 stdout/stderr artifact 会自动保存
```

**六、Stage 16G.3C：内部 ProjectTestRouter 和测试信任分类**

目标：

```text
测试命令通过 run_public_command 进入，
内部识别为 project_test，
但 run_project_test 不作为默认模型可见工具。
```

内部识别：

```text
python -m pytest ...
pytest ...
python -m unittest ...
```

后续扩展候选：

```text
python manage.py test
tox
nox
npm test
go test
cargo test
make test
```

第一版可以只启用：

```text
pytest
python -m pytest
python -m unittest
```

其他标记为：

```text
planned_not_enabled
manifest_derived_deferred
```

测试信任分类至少包括：

```text
task_declared_public_test
repo_discovered_test
model_selected_existing_test
candidate_created_test
candidate_modified_public_test
```

工具结果中至少包含：

```text
semantic_command_kind="project_test"
test_runner
test_source_origin
public_test_observation_trusted
official_feedback_eligible
diagnostic_value
candidate_created_test
candidate_modified_public_test
ran_on_clean_public_test_snapshot
```

注意：不要使用容易误导的字段名，把一次 public test observation 的可信度和整条轨迹 policy-loss 资格混在一起。

不建议写成：

```text
result_valid_for_training=false
```

除非明确它只指“这个工具观察结果不能作为官方公开反馈”，不是指整条轨迹不能进入训练。

更清晰的字段是：

```text
public_test_observation_trusted=false
official_feedback_eligible=false
trajectory_policy_loss_eligibility_unchanged=true
```

公开测试被修改时的第一版策略，仍需决策：

选项 A：拒绝运行，提示恢复测试或改用 scratch_python。  
选项 B：允许运行，但标记为不可信诊断结果。  
选项 C：在 clean public test snapshot 上运行候选源码补丁，忽略候选 test 修改。

我的建议：

```text
第一版采用 B；
如果实现成本可控，再升级到 C。
```

原因是 B 不会错误地阻止模型新增或修改测试，但也不会把污染后的测试通过当成可信 public feedback。

**七、Stage 16G.3D：`scratch_python`**

目标：

```text
提供受控的临时 Python 复现能力，
替代 python -c、heredoc 和临时脚本命令。
```

推荐工具 schema：

```python
scratch_python(
    code: str,
    cwd: str = ".",
    timeout_sec: int = 30,
    purpose: str | None = None,
)
```

第一版边界：

```text
code 长度上限，例如 64 KiB
默认 timeout 30 秒
最大 timeout 120 秒
运行在 disposable public execution snapshot
必须能看到当前 candidate patch
不写回真实 episode workspace
无网络
不挂载 runtime-private
stdout/stderr 脱敏和截断
raw artifact 私有
```

需要决策：

是否限制 `subprocess`？

选项 A：第一版完全禁止 `subprocess`、`os.system`、`pty` 等明显 shell 逃逸。  
选项 B：允许，但依赖 Docker 无网络和 snapshot 隔离。  
选项 C：允许部分安全库，禁止 shell 执行类 API。

我的建议：第一版采用 A 或 C。否则 `scratch_python` 会绕过 `run_public_command` 的命令策略。

验收：

```text
scratch_python 能 import 当前 candidate patch 后的代码
scratch_python 产生的文件不会进入 final.patch
scratch_python 不能访问 runtime-private
scratch_python 不能联网
scratch_python raw artifact 不可被模型读取
```

**八、Stage 16G.3E：动态诊断闭环 probe**

目标：

```text
证明新工具不是孤立可用，而是真的支持 mini-SWE-agent / Claude Code / Codex 风格闭环。
```

至少设计一个小型任务 probe：

```text
1. 模型 read_file / rg 定位相关代码
2. run_public_command(command="python -m pytest tests/test_x.py::test_y -q") 观察失败
3. scratch_python(code="...") 做最小复现
4. apply_patch 修改源码
5. run_public_command(command="python -m pytest tests/test_x.py::test_y -q") 验证
6. run_public_command(command="git diff --name-only") 或 git_diff 查看补丁
7. final patch projection
8. verifier 最终计算 reward
```

验收要检查：

```text
工具结果进入 trajectory
TrainingView 能看到 sanitized observation
raw artifact 不进入模型上下文
candidate patch 被 snapshot 包含
执行副作用被丢弃
final.patch 不含 .pytest_cache / __pycache__ / scratch 文件
ProjectTestRouter 正确标记测试信任分类
```

**九、Stage 16G.3F：文档、inspector 和 acceptance map 更新**

目标：

```text
把工具能力、拒绝语义、信任分类和训练边界写进长期可复用文档。
```

需要更新：

```text
55-stage-16g-3-execution-plan.md 或新建正式执行计划
harness capability acceptance map
4-way tool comparison
TrainingView / inspector 文档
tool schema 文档
```

必须讲清楚：

```text
RepoHarness 没有开放完整 Bash；
模型可见表面接近命令行；
内部通过 CommandStringV1、router、Docker、snapshot 和 artifact 控制风险；
run_project_test 是内部概念，不是默认模型工具；
最终 reward 仍由 verifier 决定，中途 public command 只是诊断观察。
```

**十、非目标**

Stage 16G.3 第一版不做：

```text
完整 Bash
persistent shell
PTY
write_stdin
后台进程
server lifecycle
浏览器测试
完整 tox / npm / make 支持
依赖安装
网络访问
多命令 && / ||
管道和重定向
shell glob
python -c
任意脚本执行
local_process 正式训练暴露
```

这些可以后续进入：

```text
16G.3.5
16G.4
swe_public_extended
dependency setup policy
persistent diagnostic shell
```

**十一、第一版推荐冻结方案**

如果现在要先收敛一个我认为最合理的版本，我建议冻结为：

```text
1. 模型可见工具只有 run_public_command 和 scratch_python。

2. run_public_command 第一版使用 command: str，
   但只支持 CommandStringV1，不支持完整 Bash。

3. command string 必须归一化为 argv，
   最终执行使用 shell=False。

4. run_project_test 不进入 swe_public_core 默认模型工具面，
   只保留为内部 ProjectTestRouter / acceptance probe / optional scaffold。

5. 第一版启用 pytest、python -m pytest、python -m unittest、
   python -m compileall、git status、git diff、git grep、rg。

6. tox、npm test、make test、go test、cargo test 第一版不默认启用，
   除非后续 empirical grounding 和二级命令解析策略明确完成。

7. 所有动态执行必须经过 disposable public execution snapshot，
   并且只在 Docker 或等价隔离后端进入正式训练工具面。

8. public test 污染不直接决定整条轨迹 policy-loss 资格，
   只影响该次工具 observation 的可信度和 official feedback eligibility。

9. scratch_python 是受控复现工具，
   不是 python -c 或任意 shell 的替代入口。

10. 16G.3 实现前必须先完成 command shape inventory，
    用真实任务分布修正 V1 allowlist。
```

这版计划的核心思想是：

```text
不要训练一个只会使用评测 DSL 的模型；
也不要把完整 Bash 暴露给无人监督的 RL rollout；
而是让模型看到真实命令行表面，
让 RepoHarness 内部承担 parser、router、sandbox、artifact 和 trust classification。
```

