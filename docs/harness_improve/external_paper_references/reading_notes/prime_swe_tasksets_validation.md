# Prime SWE tasksets：评分、验证与清洗产物精读

**结论摘要。** Prime 的价值不是另外合成了一份统一 SWE 数据，而是将不同来源的任务封装成可消费的 taskset，同时发布部分经过验证和筛选的数据。本次沿 **R2E-Gym、SWE-rebench V2、ScaleSWE** 三条路径，读到任务加载、镜像选择、求解期可见信息、评分函数、验证 CLI 和清洗脚本。三者的 reward 并不相同；`Verified` 也不是统一的重复可靠性保证。当前 verifiers 的 `--only-setup` **只检查 setup，不执行 no-op 评分**；三条 taskset 的常规评分仍使用求解时的沙箱，捕获 patch 不等于干净容器重放。数据卡和当前实现还存在数量、安装路径与行为差异。因此，这些产物适合成为 B 线的可复用候选与对照，但不能仅凭名称替代本项目的评分、可见性和基座学习性验证。以下明确分开七月发布主张、固定提交代码、数据卡、离线检查与项目建议。

导航：[来源与覆盖](#sources) · [三条执行／评分路径](#paths) · [验证实际语义](#validation) · [清洗产物与版本](#datasets) · [边界与离线检查](#checks) · [B 线可采取的下一步](#project)

<a id="sources"></a>
## 1. 来源、版本与阅读范围

阅读日期 **2026-09-08**。这是一个**版本化环境／数据源码专题**，不是一篇新 RL 算法综述。主文章完整阅读；实现以三条任务路径为主，不声称通读 Prime 全平台、所有 taskset、所有语言 parser 或原作者的整套研究代码。

### 1.1 固定来源

| 标记 | 来源及本次身份 | 核验范围 |
| --- | --- | --- |
| B | Daniel Auras、Prime Intellect Team，[*Scaling Agentic RL: 365,000+ Environments for SWE, Terminal, and Search*][B]，2026-07-22 | 网页全部主体、任务列表、验证、训练及局限；网页正文取得，未制作本地网页/PDF镜像 |
| C | `PrimeIntellect-ai/prime-envs@c4d04dfe212c153a587ea4ce072ae6753e74d6e9` | SWE 总说明；三包 README、三个完整 taskset；Scale scorer；SWE-rebench 测试与 parser 头部；根许可 |
| V | `PrimeIntellect-ai/verifiers@27bbd216df0af719a43705866b2cf6139bcc95de` | 完整 model-free validate CLI／配置、patch capture helper；rollout 初始化与 close 的相关范围 |
| U | `R2E-Gym/R2E-Gym@0d94c4eb9431cd195c55a7ea3abd54006c9a1735` | `src/r2egym/agenthub/runtime/docker.py` 中执行、日志解析分派、`_calculate_reward_r2e`；不是完整原论文复读 |
| H-R | [`PrimeIntellect/R2E-Gym-Subset-Verified`][HR] | 数据卡全部正文与文件入口；未下载全量 parquet 或逐题排除记录 |
| H-W | [`PrimeIntellect/SWE-rebench-V2-Filtered-Verified`][HW] | 数据卡全部主体、内嵌清洗／发布脚本、附带原始数据卡；未读全量逐题验证日志 |
| H-S | [`PrimeIntellect/Scale-SWE-Verified`][HS] | 数据卡全部主体、内嵌清洗／发布脚本、附带原始数据卡；未读全量逐题验证日志 |
| P | `Rogerffff/RepoHarness@miles-migration` 的 `d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5` | [B 补读请求](../../../agentic_RL/repo_harness_rh2_workstreams/project1_execution/b_external_reading_requests_20260908.md)、本库模板与本文目标路径查重；未重审 rh2 实现 |

**版本限制。** C、V、U 固定到实际 Git commit。HF 数据卡按本次取得页面记录，**三套 HF 数据没有全部获得并核定 dataset revision**，没有独立统计其 parquet 行数；网页抓取缓存与库内 README 也可能有更新时间差。因此下文数量均带来源身份，不伪称是冻结数据后的自行实测。正式训练仍需固定真实下载的数据 revision、镜像 digest 与执行依赖。

**资料边界。** `prime-data` 的官方入口本次 GitHub API 返回 404，无法确定是访问权限还是公开状态原因；不能写成“作者没有代码”。卡片虽展示两份生成脚本，本次未取得它们引用的全部 sidecar 文件、`swe_cards` 辅助包与完整验证运行。部分 HF 原始文件请求失败，也不能用卡片说明冒充逐题审计。

### 1.2 主文章覆盖与本专题展开位置

| 原文章节 | 本次处理 | 后续展开 |
| --- | --- | --- |
| 引言、任务总览 | 完整读；标题规模与合格任务数量分开 | §2 |
| One contract, three domains | 完整读；用当前代码检查边界 | §3–4 |
| Validated re-uploads | 完整读；回数据卡、脚本与 CLI 核对 | §5–6 |
| Software Engineering Tasks | 全部条目读；三条选定路径深入 | §3–6 |
| Terminal Tasks | 全部条目读；只作为完整范围记录，不扩展 terminal 源码审计 | §2 |
| Search Tasks | 全部条目读，保留固定检索与 BYO search 的区别；不审各 judge | §2 |
| Training | 完整读；没有由框架默认值补 loss 或模型收益 | §2、§8 |
| What's next、引用与尾部 | 完整读；未来隔离评分、替代解局限与当前实现分开 | §4、§8–9 |

网页没有技术附录。顶部任务可视化的可解析文本已检查，但没有据动画数字独立计算总数。各任务的第三方论文链接是导航，不能因此声称逐篇已精读。H-W/H-S 内嵌原始作者结果只用于区分资产谱系，不归为 Prime 清洗的训练消融。

### 1.3 实际代码范围

下文首次引用均给完整路径与符号。C 仓库中完整读取：

- [`environments/swe/r2e_gym/r2e_gym/taskset.py`][CR]；
- [`environments/swe/swerebench_v2/swerebench_v2/taskset.py`][CW]；
- [`environments/swe/scaleswe/scaleswe/taskset.py`][CS] 与 [`score.py`][CS-score]；
- [`environments/swe/swerebench_v2/tests/test_swerebench_v2.py`][CW-test]。

SWE-rebench 的约 3.6K 行 parser **不是全部逐函数审计**：读取了来源说明、状态枚举和 pytest 头部，再追 taskset 中 parser 选择与调用。其余语言 parser 的完整正确性为未检查项。

V 仓库完整读取 [`verifiers/v1/cli/validate.py`][V-validate]、[`configs/cli/validate.py`][V-vconfig]、[`utils/git.py`][V-git]；[`rollout.py`][V-rollout] 检查到创建 trace、runtime policy、结束／失败及 finalize→score→stop 路径，没有把整套 agent/session/trainer 纳入本专题。

## 2. 作者主张与能确认的贡献层次

七月文章将 23 个 SWE、terminal、search taskset 放到共同接口下，报告约 365K 任务及约 135K 托管镜像，并提供 GLM-4.5-Air/ScaleSWE 的训练配置线索（6 个 H200 节点、2 天）。这些不是全部任务逐条验证通过、全部开源环境独立可运行或清洗方法的受控模型消融。[B：引言、One contract、Training][B]

完整范围还包含 Terminal-Lego、TMax、Terminal-Bench 2、OpenThoughts-TBLite，以及 WideSeek、PaperSearchQA、OpenSeeker、DeepDive、S1-DeepResearch、REDSearcher、BrowseComp 和 BrowseComp-Plus。最后一项自带固定语料检索，是一般 BYO-search 组织的例外。文章结尾承认同沙箱评分和正确替代解误判的局限。[B：Terminal、Search、What's next][B]

**本篇可独立确认的重心是代码与数据资产，而不是新训练算法。** C 的 SWE 总表把数据、镜像可用性、验证和 `prime-data` PR 分列，且仍有 `—`、未覆盖镜像等状态。该表支持“多来源有统一接入”，不支持“所有来源有相同质量保证”。当前表还包含 `deep_swe` 等新增项，不能拿它倒推七月 23 项清单。[C：`environments/swe/README.md`，Tasksets][C-overview]

这里的 taskset 行是一道任务，镜像是一种执行资产，rollout 是一次尝试，Verified 是发布者的处理标签。它们均不等于训练 token、有效梯度组、成功轨迹或最终训练消费量。实际 trainer 的 GRPO、OPD、mask、staleness 由另一个已派出的 Prime 算法专题负责，本稿不擅自补全。

<a id="paths"></a>
## 3. 三条任务路径：统一生命周期，不统一评分含义

### 3.1 从数据到 reward 的实际时序

在本次三条 taskset 与 V 的正常 rollout 组合中，路径是：

```text
HF row → TaskData（含参考评分材料，但正常 prompt 只取题面）
       → runtime.start / setup
       → harness 运行，agent 修改工作区
       → task.finalize 捕获 agent diff
       → task.score / harness.score（仍持有原 runtime）
       → trace 记录结果 → runtime.stop
```

V 的 `Rollout.close()` 先停止 harness session／交互服务，再在未失败且已打开的情况下执行 task finalize、可选工件收集，然后并发调用 task/harness score。预先失败的 run 跳过评分；正常 stop 的部分轨迹仍可以评分。异常被记录为失败 trace，不能把未得到分数与得到 0 分混为一谈。该层不决定最终 learner 是否保留数据。[V：`verifiers/v1/rollout.py::close/fail/abort`][V-rollout]

**三条任务没有将捕获的 patch 投入第二个干净容器评分。** `solved()` 收到的仍是原 runtime。C 的总说明中另有 `deep_swe` 独立 verifier 容器路径，但不属于这里三条，不能把其隔离性质推广给 R2E、Scale 或 SWE-rebench。[C：三份 `solved`；总说明 Grading-material visibility][C-overview]

### 3.2 Loader 与运行前提对照

F2P（FAIL_TO_PASS）是原本失败、修复后应通过的测试；P2P（PASS_TO_PASS）是原本通过且不应回退的测试。下面的 reward 指各 task 的 `solved` 项，不是任意附加 harness 奖励组合后的最终总分。

| 字段 | R2E-Gym | SWE-rebench V2 | ScaleSWE |
| --- | --- | --- | --- |
| 默认数据 | R2E-Gym-Subset-Verified | SWE-rebench-V2-Filtered-Verified | Scale-SWE-Verified |
| 默认 split | `train` | `train` | `train` |
| 任务名称 | `commit_hash`，缺失退回序号名 | `instance_id`，缺失退回序号名 | 必需 `instance_id` |
| 模型题面 | `problem_statement` | `problem_statement` | `problem_statement` |
| 镜像字段 | `docker_image` | `image_name` | `image_url` |
| 工作目录 | `/testbed` | `/<repo 最后部分>` | row `workdir` |
| 基础版本 | setup 后 `resolve_head()` 保存在 host | row `base_commit` | `parent_commit`，否则 `base_commit` |
| setup | venv 链接、清理 pycache、搬走隐藏测试 | 尝试安装 ripgrep；不自行 reset 到 base | 执行 row `pre_commands`，失败抛异常 |
| 评分依据 | 完整预期测试状态映射 | F2P+P2P 目标 ID | F2P+P2P 目标 ID |
| 额外 loader 过滤 | 可选 `filter_fn` | 可选 `filter_fn` | `filter_fn` 加默认镜像可用性过滤 |

三个 loader 都调用 `load_dataset(name, split=...)`，**没有 dataset revision 配置**；`filter_fn` 是本地操作者提供的 Python 表达式，限制 builtins 不应被视为对恶意表达式的安全沙箱。`idx` 还会随过滤／行序变化，不能用它替代数据来源与 instance 身份。[C：三份 `Config`、`Taskset.load`][CR] [CW][CW] [CS][CS]

三者都设置 `TaskResources(cpu=4, memory=4, disk=10)`。这里记录的是 taskset 声明，不是测得的资源需求、硬性可解上限或本项目预算。runtime 如何解释单位、覆盖配置和实际容量，需随选定部署确认。

**schema 可以装有参考答案，不等于答案已交给模型。** 这三条 loader 明确以 `problem_statement` 建立 prompt；R2E 数据预览中的另一个 `prompt` 字段包含题面生成指令，并未被当前 loader 用作 solver 输入。SWE-rebench 的 `PR_description`、`interface` 也没有被当前 loader 自动追加。上层 harness 若自行序列化整个 TaskData，仍须另审，不能由本层保证所有消费者都不泄漏。[C：三份 `load`][CR] [CW][CW] [CS][CS]

### 3.3 R2E-Gym：匹配“预期状态”，不是所有测试变成 PASSED

`R2EGymTask.setup()` 将 `/r2e_tests` 压缩，读回 host 临时文件，再从沙箱删除原目录与临时压缩包。task 对象可以被同组多次尝试共享，因此 host 字典按 `id(runtime)` 保存测试归档与 pre-agent SHA。`solved()` 将归档恢复到 `/testbed/r2e_tests`，运行 `/bin/bash run_tests.sh 2>&1`，只将 stdout 交给 `calculate_reward`。[C：`environments/swe/r2e_gym/r2e_gym/taskset.py`，`setup/_stage_tests/_restore_tests/solved`][CR]

`parse_log_pytest` 从 `short test summary info` 后的内容提取 PASSED、FAILED、ERROR，按 `::` 后的部分形成名字；路径部分被去掉。`calculate_reward` 去除部分 ANSI 和 ` - ` 后缀，比较字典大小，并检查每个**非空**实际键的状态是否与 `expected_output_json` 相同。[C：`parse_log_pytest/calculate_reward`][CR]

因此正常非空唯一键条件下，它近似于：

```text
reward = 1  ⇔  本次解析的测试状态映射 == 数据记录的预期状态映射
```

它允许某项预期状态本来就是 FAILED。若数据预期 FAILED 而实际变 PASSED，精确匹配反而失败。这不是 Prime 独自发明的规则：本次读取的 U `DockerRuntime._calculate_reward_r2e()` 使用同样的长度、键、状态比较结构；U 的其他 SWE-bench／SWE-smith reward 是另外的分支，不能混用。[U：`src/r2egym/agenthub/runtime/docker.py::_calculate_reward_r2e/_calculate_reward`][U-r2e]

**边界。** 当前 Prime `solved` 没有单独依据测试命令的 exit code 判分；缺 summary 且 expected 非空通常为 0，非法 expected JSON 会抛异常。若 expected 本身为空且解析也空，函数会返回 1；空键还被跳过。§7 的离线输入已确认这些行为，但没有检查全量数据是否实际含此类行。[C：`calculate_reward`][CR]

Gold 从 `parsed_commit_content` 重建 unified diff，默认只取 Python 且排除 test 文件／目录。空 gold 或 `git apply --whitespace=fix` 失败均抛异常；`validate` 在应用 gold 后运行同一个 `solved` 并检查结果等于 1。这里的 gold 由代码选择规则决定，不能泛化成任意仓库原始提交的完整变更。[C：`extract_gold_patch/apply_gold_patch/validate`][CR]

**生命周期细节。** `_restore_tests` 会 pop host 归档并在 finally 删除本地文件，是一次性消费；同一 runtime 上再次调用 solved 会缺归档。这要求重复 gold/no-op 检查使用独立 setup/runtime，不应在同一个已评分工作区反复调用。正常恢复失败会抛异常。若 rollout 在评分前取消，所读路径没有 task 专有归档清理钩子；是否造成长期临时文件残留属于待完整运行验证项，不是本轮已复现的泄漏。

R2E README 概述“测试 harness 隐藏”，但实际搬走的明确对象是 `/r2e_tests`。`run_tests.sh` 仍在工作区被调用；V 的 `snapshot_untracked` 注释还将它列为 R2E 镜像自带未跟踪文件。不能将目录移动描述成所有评分控制面都已经消失。[C：`_stage_tests/solved`][CR]；[V：`utils/git.py::snapshot_untracked`][V-git]

### 3.4 SWE-rebench V2：保留 task 指定测试与 parser，但容错会折叠错误原因

setup 不应用 test patch，只尝试安装 `rg`；该安装命令的结果未显式检查。评分时，`run_tests()` 解析 `install_config.test_cmd`（字符串或列表），要求非空 `test_patch`；恢复 patch 涉及的路径到 base，再应用测试补丁。这恢复的是**补丁触及的路径**，不是所有测试和评分相关配置。[C：`environments/swe/swerebench_v2/swerebench_v2/taskset.py::setup/run_tests/restore_test_files`][CW]

补丁策略先用 `git apply --3way --recount ...`，再尝试 `patch --fuzz=5`。测试补丁仍不能应用，返回空输出，最终 reward 0；恢复命令失败则抛异常。没有发现跨两种补丁策略显式恢复干净快照的代码，因此不能把“某次 fallback 成功”自动等同于严格应用原始 diff。[C：`run_patch_commands/try_apply_patch`][CW]

`build_eval_script` 顺次执行测试命令，每条追加 `|| FAIL=1`，最后退出 `FAIL`。外层仅当脚本 exit code >1 才抛异常；内部命令的多种非零退出通常已被折叠成 1。§7 实际用本地 bash 运行了 `(exit 7)` 的包装，确认外层得到 1。不能据此外层判断推断“1 一定是正常测试断言失败”。[C：`build_eval_script/run_tests`][CW]

`calculate_reward` 用 `install_config.log_parser` 从 `NAME_TO_PARSER` 或模块属性取 parser。未知 parser、parser 抛异常、空输出、空状态图都返回 0。日志边界标记存在时裁剪，不要求一定存在。最终：

```text
E = normalize(FAIL_TO_PASS + PASS_TO_PASS)
reward = 1  ⇔  E 非空，而且 E 中每个 ID 的状态都是 PASSED
```

未知／额外测试的失败不会独立否决；只要 P2P 非空，函数也不要求 F2P 单独非空。名称规范化会去除某些耗时后缀；碰撞与 parser 的状态覆盖规则需要结合真实语言日志再检查。[C：`normalize_test_name/is_resolved/calculate_reward`][CW]

Vendored parser 头部称来自 SWE-rebench-V2 的 `lib/agent/log_parsers.py @ main (2026-04)`，内联 `TestStatus`。这个来源注释没有原作者 commit SHA；**固定 Prime 文件不等于已经证明与当前或某次原作者 parser 字节一致**。本轮只核头部与 pytest 示例，不宣称验证全部语言支持。[C：`log_parsers.py`][CW-parsers]

包内 `test_swerebench_v2_test_patch_visibility` 使用 FakeRuntime 检查 setup 不写测试 patch、评分才恢复并应用。这是有价值的顺序单测，但不是实际容器防作弊测试、全部 parser 测试或原评分器等价性测试；本轮读取但没有运行该需安装依赖的原测试。[C：`tests/test_swerebench_v2.py`][CW-test]

### 3.5 ScaleSWE：显式 JUnit ID 匹配，仍须核对补丁和执行状态

setup 执行数据行 `pre_commands`，失败抛异常。评分先合并 F2P/P2P，空目标直接 0；恢复已识别的测试路径和 `conftest.py`，并删除 base 中不存在的新增测试。扫描包含 tracked 与 untracked 文件，这一点由其 README 的 2026-07-17 变更解释。[C：`environments/swe/scaleswe/scaleswe/taskset.py::setup/solved`、`RESTORE`；README Changelog][CS] [CS-readme][CS-readme]

恢复不是整仓库 reset：普通源文件改动保留。与此同时，大量 restore 命令包含 `|| true`，调用者也不检查整体返回值；未匹配的配置、插件、Python 环境等并未被证明恢复。路径规则定义了实际保护范围，不是“所有可能影响评分的文件”。

若存在 `f2p_patch`，`_apply_patch` 依次尝试严格 git apply、忽略空白、GNU patch fuzz5、git apply --reject。**gold 路径要求返回 True，正常 solved 对测试 patch 的返回布尔值不做检查**，然后继续评分；有 `f2p_script` 时写入 `test_fail_to_pass.py`。这是实现的 best-effort 行为，不能替换成 README 的绝对“held-out tests 已成功恢复并应用”。[C：`_apply_patch/apply_gold_patch/solved`][CS]

之后 host 写入 scorer 源文件和目标 ID JSON。`score.py::main()` 在项目 Python 中调用 pytest，指定 `-vv`、JUnit XML、清空 addopts 和固定 rootdir，再解析 XML。`all_passed`：

- 为 pytest node ID、JUnit classname/name、路径及空白生成几种匹配形式；
- `skipped` 不计作已找到，`failure/error` 计失败；
- 至少匹配到一个目标，全部 expected ID 找到且其匹配状态为 passed，才算 1；
- 未列为 expected 的 testcase 不参与结果；同一目标被多个 testcase 命中时，后一次状态覆盖前一次。

以上来自 [C：`environments/swe/scaleswe/scaleswe/score.py::normalize/all_passed/main`][CS-score]。这比读最后一行 pytest summary 更细，但也不是全部 XML 测试都必须通过。

**执行边界。** `pytest.main()` 的返回值未使用，固定 XML 文件运行前未显式删除；外层 `solved()` 从 stdout 中取最后一个 `<score>…</score>` 数字，没有单独检查执行返回码或把值限于 [0,1]。本轮用 mock pytest 和旧的 passing XML 做了控制流重放，得到 1；这证明该路径在这些输入下可能接受旧报告，**没有证明任何真实任务已经遭遇或利用它**。[C：`score.py::main`、`taskset.py::solved`][CS-score] [CS][CS]

### 3.6 一张不能省略的失败语义表

| 情况 | R2E-Gym | SWE-rebench V2 | ScaleSWE |
| --- | --- | --- | --- |
| 预期目标为空 | expected={}且 parse={}可得 1 | expected 为空为 0 | expected 为空为 0 |
| 测试日志／报告缺失 | 通常通过 map 不匹配为 0 | 空 output/map 为 0 | XML 不可读或无 score 为 0 |
| parser 不认识／抛错 | 非法 JSON 可抛错；parser 部分模式空图 | 未找到 parser 或 parser 抛错均为 0 | XML 解析错误为 0；运行导入失败可能无 score |
| host 测试归档缺失 | 抛异常 | 不适用 | 不适用 |
| gold patch 应用失败 | 抛异常 | 抛异常 | 抛异常 |
| 测试 patch 应用失败 | 不走此机制 | 空输出→0 | 返回 False 被 ignored，继续评分 |
| 已知 expected 测试失败 | 是否失败取决于 expected 状态 | 0 | 0 |
| 额外、非 expected 测试失败 | 多出映射可能导致 0 | 不独立否决 | 不独立否决 |

表是固定代码行为，不是建议 B 统一复制。尤其 **reward=0 并不唯一表示模型没有解决问题**：它可能混入映射、数据、测试包装或运行异常。区别这些原因，应依赖事实日志和实际发生阶段，而不是反过来由分数猜原因。[C：三条 reward 路径][CR] [CW][CW] [CS][CS]

## 4. 求解期可见性、网络与 patch：三条不同的保证

### 4.1 隐藏材料是重要改变，但不等于评分隔离

R2E 将测试目录从求解容器移走，是对原作者公开运行时可见信息的有意改变。SWE-rebench 当前在 reward 阶段才应用测试补丁，与旧 composable port 的 setup 即应用不同；Scale 的参考测试同样在评分时引入。这些改变即使保持 task ID，也改变了求解器可取得的反馈。[C：SWE 总说明 Grading-material visibility，三包 README][C-overview]

所以应分别记录：**普通仓库测试、当前任务的新增隐藏测试、评分脚本／参考状态、原始 Git 历史**。隐藏新增测试并不要求删掉所有正常开发测试；反过来，删掉某个 hidden 目录也不证明其他评分控制面安全。

当前三条 reward 都运行在 agent 使用过的 runtime：恢复文件可以减少直接篡改，无法由静态代码证明环境变量、解释器、插件、残留进程、依赖或日志都未受影响。这是结构上的未覆盖范围，不是本轮发现具体逃逸利用。

### 4.2 2026-09 的网络改动必须与验证时期区分

C 的实际提交为 2026-09-08 合入的 #798。说明称 #795 恢复了训练 taskset 的 solver 网络访问，随后为七个 SWE 训练来源附加 fair-use system prompt；评测 taskset 不在这项改动范围内。README 将相应变更记为 09-03/09-04，本稿保留 changelog 日期与合入日期的不同身份。[C：提交 `c4d04df` 说明；三条 `SOLVER_SYSTEM_PROMPT`][C-head]

提示允许一般文档/API背景查询，禁止取得本题参考修复、上游解答及跨 ref 的 Git 信息。**这是行为约束，不是 taskset 中新加的网络过滤器。** 移除空 allow-list 也不保证所有 runtime 最终都全网开放，仍取决于运行配置与 harness。相同 PR 对 SWE-smith 当前分支历史的已知解答暴露保留了未解决项；这里只记录作者承认的范围，不声称复现它。[C：`c4d04df`][C-head]

由此，七月数据验证标签不自动包括九月 solver prompt／网络策略的完整新条件。B 若比较 Prime 原生运行与 rh2，应把网络和可见信息作为条件，而不只匹配问题文本。

### 4.3 Patch capture 是观察证据，不是自动的权威交付工件

V 的 [`verifiers/v1/utils/git.py::capture_patch`][V-git] 在 scoring 改测试前执行 `git add -A` 和对 host 保存 base 的 staged binary diff，再 unstage。host 随机临时文件名减少并发交叉读与可预测路径问题。base 缺失时退回 HEAD，会遗漏 agent 自己已 commit 的变化；R2E 以 setup 时 SHA 缓解，另两条依赖数据 base。

输出超过 **2,000,000 bytes** 截断并标 `patch_truncated`。Git 返回非零但容器仍能执行 `true` 时记 `patch_error`，允许后续流程；容器无响应／运输异常则抛错。三条 taskset 未把这个字符串用于实际 reward，因此不能照 helper 注释将所有 capture 失败解释为“本次按 no-op 评分”。当前同沙箱仍可能基于修改后的工作区得分。[V：`capture_patch`；C：三条 finalize/solved][V-git]

helper 还提供 `snapshot_untracked` 和 `ignore`，避免将镜像初始就有的未跟踪文件当作 agent 新增。**本次三条 finalize 均未传 ignore 列表。** 把这些 trace patch 将来用到干净容器时，需要检查原镜像已带文件、截断、base、二进制和评分后修复等问题；不能因为 `trace.info['patch']` 存在就认为可准确重放。[V：`snapshot_untracked/capture_patch`][V-git]

<a id="validation"></a>
## 5. 当前 `validate` 实际验证什么

这是本轮最直接影响 B 的版本发现：**当前 `--only-setup` 不是 no-op scoring。** 七月文章写的是两侧 gold/no-op；固定 V 代码的含义如下。[B：Validated re-uploads][B]；[V：CLI与配置][V-validate]

| 模式 | 实际执行 | 没有执行什么 |
| --- | --- | --- |
| `--only-gold` | 新 runtime → setup → `task.validate(runtime)` → stop | 不运行学习模型；不自动增加另一轮 no-op |
| `--only-setup` | 新 runtime → setup → 返回 True → stop | **不调用 solved／task.score，不检查未修改代码是否得分** |
| 默认 `all` | 同一 task 上依次执行 gold 和 setup，两次建立独立 runtime，再汇总 | 第二次仍不是 no-op reward；不是两轮 gold稳定性检验 |

CLI 不执行正式 agent 的 harness provisioning／交互过程，甚至与正常 rollout 的 runtime prepare hooks 也不完全相同；这里验证的首先是 task check 路径。对本稿三条 task，`validate` 都是 apply_gold_patch 后运行自身 solved。这个路径可以证明“所用 gold 在这次执行中得到 1”，不能单凭当前 CLI 证明原状态得 0。历史清洗使用 SolveEnv／其它运行的记录，不能因今天 CLI 的差异就判定历史验证没有做。[V：`verifiers/v1/cli/validate.py::_run_check/_run_all`][V-validate]

### 5.1 状态、重试和分母

CLI 把结果记录为 `valid / invalid / unchecked / error / timeout`。`unchecked` 表示 task 没给可判定的 gold check；error/timeout 不是普通 invalid。保存 task 内容键、模式、位置、时间、错误、配置、结果 JSONL、summary 和日志。[V：`_classify/_row/run_validate`][V-validate]

`--resume` 按 task 内容 hash 与 mode 保留 final 记录，**valid、invalid、unchecked 都是终态**；只有缺失、error、timeout 会再运行。它不是自动对所有 gold 得 0 的题再试十次。重复测量与“补齐失败执行”是不同实验，不能把 resume 后的结果当成固定次数独立重复。

`summary.valid_rate` 的分母是 `total - unchecked`，不是仅 valid+invalid；只要存在 checked 项，未完成和异常可能仍在分母内。阅读 dashboard 数字时应同时保留各原因计数。`load_results` 还会重写保留的终态行，旧 error/timeout 尝试不一定继续留在同一 results 文件中；做可靠性分析需另行保留尝试历史。[V：`summarize/load_results`][V-validate]

### 5.2 时间和资源不是一项总 timeout

配置默认 Prime runtime、最大并发 128；setup timeout 和 validate hook timeout 分开，默认值可以为 None，setup 还可继承 task 配置。`runtime.start()`、`stop()` 在这些 hook 的 `wait_for` 之外，不能把单一 `timeout.total` 解释成完整 start-to-stop 限制；runtime 自身仍可能有别的时限。本轮未核全部后端。[V：`configs/cli/validate.py`、`_run_check`][V-vconfig]

setup/runtime 的错误被记录；teardown 错误仅 warning，不会自动把已判 valid 改为 invalid。gold/setup 两次检查不运行普通 rollout finalize，这点对 R2E 的 host 临时文件生命周期也值得本地验证。[V：`_run_check`][V-validate]

### 5.3 B 的 no-op 应怎样理解

概念上需要在**另一份原始环境**中：执行相同 setup，不应用 gold，不调用会应用 gold 的 validate，直接执行实际 reward 路径并保存测试事实。它不能用 setup 成功代替，也不应以解析失败／容器未启动冒充“no-op 正确失败”。

这里是测试设计，不是未经运行验证的完整 CLI 配方。`debug` 可用于诊断运行命令，但本轮没有跟完其源码，不能保证随手一条 debug 命令等同最终 reward/no-op 路径。优先沿 B 已有评分入口编写明确的 gold/no-op 配对检查，或在固定 V 上增加薄测试驱动。

<a id="datasets"></a>
## 6. 清洗产物：同一个 Verified 名称，三种不同证据

以下卡片均按 2026-09-08 本次可取得页面记录，不是本轮全量重新验证。

| 数据 | 卡片报告来源量→保留量 | 产物与主要规则 | 重要限制 |
| --- | --- | --- | --- |
| R2E-Gym-Subset-Verified | 4,578→4,522；另 56 dropped | 一轮全量 gold，失败项再重试；保留原行 | 重试至少一次成功的 flaky 行仍可保留 |
| SWE-rebench-V2-Filtered-Verified | 32,079→6,272 | metadata/题面/语言/镜像筛选、gold、复验、no-edit与后续审计 | 包含任务选择和平台限制，不是纯完整性过滤 |
| Scale-SWE-Verified | 20,181→17,202 | 排除镜像与三类 instance 原因 | 所示脚本是排除集的补集，不是逐个 kept 行的正验证白名单 |

来源：[H-R Changes/Splits][HR]、[H-W Changes/Generation][HW]、[H-S Changes/Generation][HS]。

### 6.1 R2E：通过性验证，不是“十次全部成功”认证

数据卡报告全量首轮并发 200，再对失败项做 10 次 fresh-sandbox 重试；0/10 的进入 dropped，至少一次通过的留在 train。56 个排除项中 39 个来自 aiohttp/tornado；原因还包括 expected 状态漂移。原行与 schema 不改，排除信息声明位于 `metadata/filtered_drops.json`。[H-R：Changes vs upstream][HR]

本轮未取得逐行重试日志或排除 JSON，故这些为发布者报告，不能验证每题实际尝试次数、所有失败归因或现在复跑的稳定性。尤其不能把 `10×-retry gold validation` 改写为 `10/10`，也不能据这张卡断言该版本已经逐题完成 no-op 和合法替代解检查。

### 6.2 SWE-rebench：质量筛选、运行可用性与评分验证共同形成子集

H-W 提供完整内嵌脚本，标题 `swe-rebench-v2-filtered-verified.py`，代码头仍为 `swe-rebench-v2-clean.py`。以下按实际谓词解释，而不只复述“clean”。[H-W：Generation][HW]

**第一层：上游 LLM metadata。** `difficulty` 必须是 easy/medium/hard；`code == 'A'`；`intent_completeness == 'complete'`；检测的问题标志全 false；`confidence >= 0.95`；`external_urls` 为空。这里的 confidence 是 judge 对分类的确信程度，不是目标模型成功率或统计验证置信水平。这个 difficulty 条件首先删除未标注行，并不单独偏向中等难度。

**第二层：文本与来源选择。** 正则匹配 `#1234`、`gh-1234`、PR/issue 引用和 `/issues/`、`/pull/` 等模式后，**删除整行**，不是将原题中的引用擦掉再保留。仅含无关编号的文本也可能被这种宽规则命中；是否实际误排及频率未核。已有题面中的所有外链都可能被删除规则排除，即使缺失内容并非必要，这属于偏保守的数据选择，不是已证明污染。

**第三层：运行能力。** 丢弃 Julia、C++、Clojure，并使用手工镜像 blocklist。脚本注释记录 29 个 C#/Go 镜像经过三次 Prime 转换仍失败；另排除 `statamic/cms`，理由是其部分题以不相关 JS suite 判分。前者带平台条件，后者是评分区分性问题，不能归为同一种“原始坏题”。

**第四层：正验证与排除补充。** `_VALIDATION_PASSING` 收集验证记录里 `reward == 1.0` 的 instance_id；`_passes_filter` 要求存在于这份集合，再排除 flaky、no-edit 和后续 always-fail 审计名单。形成 passing set 的文件是 hard+medium 与 easy 两个分批结果的并集；出现一次正结果即可进入集合，二轮规则再单独扣除，并非代码要求所有历史记录都为 1。

第二轮排除标准也不一致：hard/medium 只保留 `test_failed`／`gold_apply_failed` 原因作为失败名单；easy 则包含 sandbox_error、timeout、None 等所有不通过原因，另有显式 hang 项。这是一项实际分布选择，不能从名称推出统一的 flakiness 阈值。[H-W：Generation 的 flaky 注释与集合构造][HW]

**第五层：运行后反查。** 卡片说明，某些任务在 GLM-5.2 的独立 16-rollout 组中反复全零后，被重新执行两次 gold，最后排除 2 个确定不可解与 1 个 flaky 项。这里是 **模型失败触发排查，再由 gold 复验决定排除**；不是按 0/16 直接定义任务无资格。

**产物改变。** `image_name` 从原 registry 路径改写成 `prime/primeintellect/...`。保留 raw problem statement 与 PR metadata，不因有清洗就变成独立新题。可用代码行数、语言、仓库及难度分布的变化均应单独统计；本轮未下载全量数据，不能报告相应分布。

### 6.3 Scale：公布排除原因，不等于展示了每个保留项的完整证据

H-S 报告排除 2,979 行：892 镜像原因、2,061 `gold_patch_failure`、15 `noop_pass`、11 `stable_infra_failure`；另保留 299 个 `noop_valid_failure` 记录作为诊断，不用于过滤。四项数字相加为 2,979，20,181−2,979=17,202；这是对报告数字的算术核对，不是全量 unique ID 审计。[H-S：Changes vs upstream][HS]

内嵌 `scale-swe.py` 从两个 sidecar 加载记录：

```text
scale-swe-exclude-images.json
scale-swe-validation.jsonl
```

校验类别和 instance_id 类型，建立 gold failure、no-op pass、stable infra failure 的集合；`noop_valid_failure` 只保留作证据。最终条件为：

```text
row.image_url 不在 excluded_images
并且 row.instance_id 不在三类 excluded_instances 的并集
```

脚本会检查排除的镜像和 ID 是否存在于所加载上游数据，然后过滤、发布；**没有像 SWE-rebench 那样检查 kept 行必须存在于正验证白名单。** 因此，脚本可复现“按这些排除记录得到了哪些行”，但在本次未取得完整日志的条件下，不能独立证明每个保留任务都跑过相同数量的 gold/no-op。[H-S：Generation `_passes_filter/prepare_data`][HS]

299 条 no-op 正确失败记录也不能被解释为“全库只测过299题”，因为卡片没有完整给出所有执行日志的覆盖关系。`stable_infra_failure` 据脚本注释是降低并发后仍失败的 sandbox-side 问题；它不是证明任务在任何 runtime 都不可运行。

Schema 和行内容报告为不变，`image_url` 仍可为 `aweaiteam/scaleswe:...`，与 SWE-rebench 显式改写镜像地址不同。当前 C loader 又做一次镜像过滤：可枚举 Docker Hub 标签时删除缺失项；不可枚举、带其它 registry 主机名等情况保留。因此**卡片的17,202行与某一次实际 yield 的任务数还可能不同**。[H-S][HS]；[C：`_docker_hub_tags/_available_images/ScaleSWETaskset.load`][CS]

### 6.4 数量、名称与版本不能无声合并

| 差异 | 已观察来源 | 应怎样解释 |
| --- | --- | --- |
| SWE-rebench 6,275 与 6,272 | C 包 README仍写6,275；H-W现写6,272并说明后续3题排除 | 有3题后续审计的来源解释，但本轮未通过两个数据 revision 做独立逐ID diff |
| SWE-rebench 20／17／16 languages | C 家族表为20；H-W叙述为17；网页 viewer 的 language聚合显示16 values | 原始覆盖、文字说明和实际视图口径不同；不选一个数假装已验证当前全量 |
| `_v1` 安装路径与当前无后缀目录 | 七月文章和 HF 使用旧包路径；C 是 `r2e_gym/scaleswe/swerebench_v2` | 获取代码时按固定 C 树；不要照旧命令后再猜报错原因 |
| Verified 总行数 | R2E HF页面末尾总数4,578含train+dropped；train为4,522 | 总文件行与训练split分开 |
| 过滤后的 easy 子集 | H-W关联的easy产物属于子集 | 不与父集拼接当作额外独立任务；难度标签不代替目标模型画像 |

这里记录冲突而不替作者修文档。没有全量下载和 revision，不能声称做完了数据去重、语言分布、仓库数或训练／评测污染审计。

### 6.5 复现清洗，需要规则之外的东西

H-W/H-S 展示的脚本都以 `load_dataset(UPSTREAM_REPO, split=...)` 读取上游，未见 dataset revision 参数；上传数据、生成 card、上传 sidecar 也是分步操作。重新运行同一脚本不自动得到历史同一产物。

H-W 引用的附件包括：

```text
swe-rebench-v2-exclude-images.json
swe-rebench-v2-validation.jsonl
swe-rebench-v2-flaky-instances.json
swe-rebench-v2-no-edit-pass-exclusions.jsonl
swe-rebench-v2-rl-alwaysfail-exclusions.json
```

本轮能读取其使用方式与注释，但未完整取得内容。H-S 两个 sidecar、H-R 的 `metadata/filtered_drops.json` 亦如此。`prime-data` PR 号提供谱系线索，**不是本次已经核对过的执行证据**。[C：家族README的Prime-data PRs][C-overview]；[H-W/H-S Generation][HW] [HS][HS]

<a id="checks"></a>
## 7. 本轮执行的低成本语义检查

在本地 Python 3.13.5 和 bash 中执行了 **26 项断言**：从固定 C/V 代码摘录函数，或在保持相关控制流的情况下用依赖替身运行。没有安装完整 Prime 环境，没有 Docker、GPU、模型调用或真实数据行执行。完整输入、观察值和可重跑脚本保存在 [作者自查记录](reviews/prime_swe_tasksets_self_check_20260908.md)。

| 检查组 | 例子与结果 | 可以说明什么／不能说明什么 |
| --- | --- | --- |
| R2E（7项） | expected FAILED +实际FAILED→1；expectedFAILED+实际PASSED→0；expected空+无summary→1；两个文件相同测试名后条覆盖 | 确认精确状态与规范化边界；不证明实际数据有空expected或冲突 |
| SWE-rebench（7项） | 空目标false；缺失目标false；额外失败可忽略；只有P2P可通过；耗时后缀归一；测试命令exit7包装后exit1且仍输出END | 确认目标集及包装语义；不是全部语言parser审计 |
| Scale（9项） | 正常、skip、失败、缺失、坏XML；额外失败忽略；同目标重复结果顺序改变判定；mock pytest不覆盖旧XML时可读旧成功报告 | 静态风险得到合成输入重放；不证明真实pytest在这些镜像中发生了此异常 |
| validate（3项） | setup调用序列是start→setup→stop，valid=True；gold多一次validate | 核实当前控制流确实没有no-op reward，不需要猜CLI命名 |

**通过断言不等于通过安全或环境资格检查。** 测试的 expected 是“代码在这些输入下会怎样”，其中有些结果正是需要留意的边界。额外未列入目标的失败被忽略可能是合理任务合同；若本项目需要更强回归约束，应明确增加目标，而不是擅自将原评分器改成全日志全通过。

测试记录器初稿曾保存可变调用列表的引用，随后另一检查修改了它；本次发现后改为 deep copy，并重跑全部断言及序列化结果一致性检查。该修正是**本轮测试脚本的自查**，不是上游问题。

## 8. 开放资产、成本与证据强度

### 8.1 实际可复用的部分

| 资产 | 已核到什么 | 仍未证明什么 |
| --- | --- | --- |
| 三条 taskset 及 scorer | 固定C代码、字段、reward、setup/finalize；R2E包版本0.1.4/Python>=3.11/verifiers>=0.3.1 | lower-bound依赖不是完整可复现lock；其余package版本未逐一核定 |
| 数据卡和发布脚本 | 三份卡片；两份完整内嵌清洗脚本；R2E排除方法说明 | 全量HF revision、所有sidecar内容、逐题日志与发布流水线重跑 |
| 镜像 | row中原始Docker refs或Prime命名；README给镜像可用性 | 当前账号可拉取、转换成功、架构／digest、磁盘与网络成本 |
| model-free工具 | 当前validate完整逻辑、配置、结果与resume | 当前CLI包含no-op检查；真实三数据集全部运行正常 |
| 上游评分兼容 | R2E reward主体已与原作者函数核对；SWRparser来源注释 | 所有语言／日志等价；Scale与原作者所有测试环境等价 |
| 项目集成 | B请求与当前文档基线 | 这些代码已被rh2采用或已通过目标机器资格验证 |

C 的 README 描述镜像 registry 和平台自动构建／缓存；R2E与Scale已删除旧 `use_prime_registry` 映射参数。SWE-rebench row却显式改写为Prime地址。**provider能解释的镜像名称，不应被自动当作本地 `docker pull` 的标准OCI地址。** 自部署时先验证相同镜像资产或建立明确映射，不只改字符串。[C：三包README、loader][CR-readme] [CW-readme][CW-readme] [CS-readme][CS-readme]

### 8.2 成本与模型结果的缺项

本专题没有找到足以将清洗本身归因到模型增益的固定数据量、固定训练预算对照。数据存活率不是梯度效率，文章中的训练实例也不是三种taskset互比。未取得三份全流程环境构建、验证重试、API、CPU／内存／存储、镜像搬运或训练费用的可核算总表。

R2E重试增加成本，Scale镜像排除带平台特性，SWE-rebench的judge metadata由上游生产；不能把它们统一算成“免费model-free筛选”。虽然运行gold/no-op不需要学习模型，它们仍要执行环境与测试。稳定性、第一次成功成本、重试次数和总执行量应分开报告。

### 8.3 许可与使用范围

C根目录为Apache-2.0，并保留第三方代码说明；H-W、H-S数据卡标CC-BY-4.0。H-R明确未声明统一dataset license，来源仓库各有许可。这个记录不是法律意见；**任务封装代码的许可不替代数据行、源码仓库、镜像内依赖的使用条件**。正式发布训练资产或重分发镜像时还需按具体来源确认。[C LICENSE][C-license]；[H-R/H-W/H-S][HR] [HW][HW] [HS][HS]

### 8.4 知道什么，不知道什么

| 状态 | 具体内容 |
| --- | --- |
| 已从代码确认 | 三类reward、评分时序、当前setup非no-op、resume终态、patch捕获及异常分流 |
| 发布者报告，未自行重跑 | 数据保留数、各排除数量、重试统计、镜像可用性与原评分一致性声明 |
| 未披露到足够程度 | 全流程预算、清洗的模型消融、每个保留项统一验证次数／合法替代解覆盖 |
| 本次未取得 | prime-data完整仓库／PR内容、全部sidecar和全量parquet、三套HF固定revision |
| 本次未检查 | 每个语言parser、完整runtime网络强制机制、所有harness是否遵守prompt、全库重复与污染 |
| 需要真实试验 | dirty/fresh评分差异、数据中synthetic边界实际频率、目标基座可学习性、单节点资源成本 |

<a id="project"></a>
## 9. 对 B 线的建议：先缩短决策路径，不增加通用平台

项目映射日期 **2026-09-08**。本项目继续以 miles/SGLang/真实coding harness/rh2为基线；本文没有审当前rh2实现，因此下表是**设计层候选与验证次序**，不是已经实施的修复或批准的新训练规则。

### 9.1 优先复用什么

**第一，复用字段、原始命令与已存在的parser，不强行统一成单个pytest分数。** 三来源的raw schema应保留；在本项目转换时增加明确来源、revision和评分定义，而不是将R2E expectedmap改成“所有PASSED”后仍声称完全等价。

**第二，将现成Verified当候选起点，不重做所有生产工作，也不豁免验证。** R2E更容易先建立对照；SWE-rebench提供多样性但带语言/镜像/metadata选择；Scale有更多Python任务但需核JUnit与具体环境。哪一套更适合当前底座，需要本地事实，而非仅凭保留率排序。

**第三，先补真实no-op再谈任务资格。** 当前上游CLI的setup检查不能承担它。每题至少保存gold/no-op两份环境中的原始日志、目标ID、解析结果和判定；只看到两个bool不足以诊断parser失效或错误执行路径。

### 9.2 建议的薄结果表

不增加新的审批系统，只在B现有逐题记录中保留：

```text
source + dataset revision + source instance ID
repo/base commit + image reference/digest + scorer/parser commit
prompt字段与可见测试/网络策略
运行模式：gold / no-op / model patch / 合法替代解
attempt编号、资源、各阶段时间和重试原因
patch应用结果、测试目标ID、原始日志、解析状态
reward、是否可判定、异常阶段与异常类型
```

尝试失败、判定失败、任务排除是三个状态。不要用“曾通过一次”覆盖之前失败记录，也不要让一次API或sandbox错误直接变成普通负reward。另一方面，模型引起的真实代码失败不是环境无效，不能因为有ERROR字符串就无条件丢弃。

### 9.3 三个最小比较，比全量重新验证更早产生信息

| 比较 | 固定条件 | 期待回答的问题 |
| --- | --- | --- |
| 原作者／Prime／rh2评分事实对账 | 同题、同base、同补丁、相容资源与测试可见性 | 是parser/包装差异，还是任务本身失效？R2E先比较expectedmap，其余比较目标ID与状态 |
| 正确no-op、gold、少量合法替代解 | 独立环境、相同scorer、保存所有日志 | 能否区分未修复与正确修复；参考解通过是否掩盖替代解误杀？ |
| dirty与fresh候选评分 | 先确保候选工件完整、base正确、依赖约定相同 | 隔离的收益与限制来自哪里；不能使用2MB截断patch当完整候选 |

选题按评分机制和环境边界分层，不只随机抽“容易题”；规模是探索预算，不在此冻结某个题量。对SWE-rebench需要涵盖计划实际使用的parser，而不是承诺全部20语言。

### 9.4 A/B 的接口应传事实，不让两边分别猜测一次

B给出score及其依据、失败阶段、环境和工件身份；A决定它怎样参与group统计、哪个目标有信号、是否进入梯度。上游将未知parser计0、将某些gold失败列为invalid，是可以研究的实现选择，**不是自动继承给rh2的语义合同**。

尤其注意：一条同沙箱获得reward1的轨迹可能只有截断或缺失的capturepatch。若A要求可重放交付工件，B必须显式传递这个差异，不能让reward1盖过不完整工件；也不必因此否定所有仅用于运行日志的patch capture。

### 9.5 对“持续学习信号”的有限启示

SWE-rebench的always-fail再gold复验是一个有用的闭环实例：利用训练轨迹发现候选，再回到环境独立检查。它**不是已经证明有效的动态课程算法**。当前不应直接把0/8、0/16、低通过率写成任务无效，更不需要在首轮之前建立在线任务生成器。

一个实际可归属的工程增量，可以是恢复三种评分合同、核定误判与运行成本、使失败诊断不污染训练消费；是否带来更好学习，仍要通过目标底座和独立评测确认。本文不宣称已获得模型增益，也不要求每项语义保持修复都另训一个模型才能有价值。

## 10. 快速查阅与成品状态

| 问题 | 位置 |
| --- | --- |
| `Verified`是否同一质量标签？ | §6.1–6.3 |
| 为什么`--only-setup`不能做no-op？ | §5、作者自查中的三项调用序列 |
| 三类reward/解析失败怎样处理？ | §3.3–3.6 |
| 最新网络与提示词怎样影响数据含义？ | §4.2 |
| patch捕获能否用于fresh grading？ | §4.3、§9.3 |
| 清洗脚本与发布数据能否独立复现？ | §6.5、§8 |
| B现在可先验证什么？ | §9 |

复用已有资料入口与B请求提出的问题；本稿没有把旧综合调查作为一手证据。主要收紧的旧表述包括：`setup=no-op`、`Verified=重复稳定`、`统一taskset=统一评分`、`捕获patch=隔离评分`、以及将镜像/语言排除率当作原始坏题率。

**状态：专题精读、限定源码核查与26项离线检查完成；作者自查完成，待独立复查。** 没有独立子agent、没有完整安装依赖或运行沙箱、没有提交上游bug／PR。自查全文及脚本见 [检查记录](reviews/prime_swe_tasksets_self_check_20260908.md)。仅新增本稿与自己的检查记录，共享索引由汇总线程维护。

## 一手来源链接

[B]: https://www.primeintellect.ai/blog/scaling-agentic-rl
[HR]: https://huggingface.co/datasets/PrimeIntellect/R2E-Gym-Subset-Verified
[HW]: https://huggingface.co/datasets/PrimeIntellect/SWE-rebench-V2-Filtered-Verified
[HS]: https://huggingface.co/datasets/PrimeIntellect/Scale-SWE-Verified
[C-head]: https://github.com/PrimeIntellect-ai/prime-envs/commit/c4d04dfe212c153a587ea4ce072ae6753e74d6e9
[C-overview]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/README.md
[C-license]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/LICENSE
[CR]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/r2e_gym/r2e_gym/taskset.py
[CR-readme]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/r2e_gym/README.md
[CW]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/swerebench_v2/swerebench_v2/taskset.py
[CW-readme]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/swerebench_v2/README.md
[CW-parsers]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/swerebench_v2/swerebench_v2/log_parsers.py
[CW-test]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/swerebench_v2/tests/test_swerebench_v2.py
[CS]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/scaleswe/scaleswe/taskset.py
[CS-score]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/scaleswe/scaleswe/score.py
[CS-readme]: https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/scaleswe/README.md
[V-validate]: https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/cli/validate.py
[V-vconfig]: https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/configs/cli/validate.py
[V-git]: https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/utils/git.py
[V-rollout]: https://github.com/PrimeIntellect-ai/verifiers/blob/27bbd216df0af719a43705866b2cf6139bcc95de/verifiers/v1/rollout.py
[U-r2e]: https://github.com/R2E-Gym/R2E-Gym/blob/0d94c4eb9431cd195c55a7ea3abd54006c9a1735/src/r2egym/agenthub/runtime/docker.py
