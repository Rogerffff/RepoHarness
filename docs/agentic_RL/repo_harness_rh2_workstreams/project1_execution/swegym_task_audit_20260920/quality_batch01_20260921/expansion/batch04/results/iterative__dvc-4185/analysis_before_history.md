# iterative__dvc-4185：history 解封前私有主审

2026-09-21。结论范围：静态阅读＋复核既有真实 RH2 原件；本轮未运行项目、测试、安装或新反例。暂定 `needs_review / static_review`，仅 `development_diagnostic`。主要疑点是 **gold 和参考测试只处理题面第二个症状；第一个“未变参数仍被 commit 提示已变”有明确未修调用链**。在 CPU 定点对照前不把参考满分解释为题意已完成，也不自动判废本题。

路径约定：权威 ROOT=`${REPO_ROOT}`；P=`runs/swegym_quality_batch04_20260921_v1/public/iterative__dvc-4185`；V=同批 `private/iterative__dvc-4185`；E=`runs/env_recipe_repair_20260919/dvc_install_v1c`；B=本文件目录。下列路径均相对 ROOT，`base/...` 相对 P，L 是文件行号。

## 材料身份与公开目标

公开 base 为 `0899b277c02082ffc24bb732e8a7cf3ef4333948`，tree=`faa685976839d33d073296f5561daf8284cf2e40`；P/base_identity.json 记录 422 个跟踪文件、无 gitlinks/LFS 未物化项，导出校验为真。这是导出身份记录，未复验实际 actor HEAD。公开镜像 digest=`sha256:c5cf0dfbf7d14f04f84618ccf6a1234efe18e46d156a57719478e48029155af7`。V/grading.json 与 validation.json 的 base/补丁一致；本题 gold SHA256=`e7e7e3a57a260031662358552a139407eac46a7bc133fdb30a4881dfb097289d`，既有 gold ledger 同值。

B/public_read.md 已读，计算 SHA256=`12ba0ac7e72c588d84a7e3297aa51128d2fca65434da7df8d755173bd9eebc80`，与封存值一致，未回写。其 R1–R8 的公开推导与本次源码核对相符。题面末尾明确列出两件事：未变的 `get_base_dv` 被 commit 提示依赖变化；`eval.filter_limitup: false` 反复被 status 标 new（P/user_prompt.txt:L107-L109）。原业务脚本、数据和 dvc.lock 没有交付，但可用本地两阶段小例验证通用语义；不要求 WSL/9p、GPU、业务数据或云凭据。

`public_hints` 的“禁止改测试”是可见操作指令，是否进入真实 system/tool 消息尚未核验；“所有测试修改都会恢复”只是旧机制说明，本题实际恢复范围见后文。`user_prompt.txt` 是静态渲染，未见真实 solver 的 rendered messages（check 3 unknown）。题意本身（check 23）可定位且包含两个目标，不能把消息未捕获与规格不明混成一项。

## 需求—断言双向映射

完整 F2P 前缀为 `tests/unit/dependency/test_params.py::test_params_with_false_values`。七项都使用真实临时参数文件、真实 Repo/ParamsDependency，无 Mock：`tmp_dir` 改 cwd 并 `Repo.init(no_scm=True)`（base/tests/dir_helpers.py:L250-L276、L90-L108），`load_yaml` 经 PyYAML SafeLoader（base/dvc/utils/yaml.py:L8-L25），`fill_values` 后在 `dvc.state` 内断言 `dep.status()=={}`。`status` 再从实际参数文件读取所跟踪键（base/dvc/dependency/param.py:L56-L103）。

| 公开要求或合理旧行为 | 依据 | 对应验收与关键断言 | 覆盖与证据 |
| --- | --- | --- | --- |
| 已记录的 false 不应反复 new | 题面 false 与 new；base/param.py:L43-L77 | F2P `[false]`、`[no]`、`[off]`：三种 YAML 1.1 布尔假表示，装载后空状态 | 核心局部路径覆盖；既有 noop 三项均报 `param: new`，gold 均通过。未直接走 CLI、StageLoader 或嵌套 `eval.filter_limitup`。 |
| 显式 null 与键缺失不同 | 已有 PARAMS 包含 None；read_params/save_info 按键存在性 | F2P `[]`（param_value 是空文本）、`[null]` | 两者生成 `param: ` / `param: null`，都为 null；**空文本项不是带引号的空字符串**。只测有键且未变，未测 lock 缺键。 |
| 空容器是合法已记录参数值 | PARAM_SCHEMA、read_params 按键取值 | F2P `[[]]`、`[{}]` | 覆盖空 list/dict，均只断言空状态。七项合计为四类假值语义；数值 0、带引号空字符串未覆盖。 |
| 未变的普通参数 commit 不应提示变化 | 题面第 1 点；repo/commit.py:L39-L48 | F2P/P2P 无参数 commit；执行的两文件也无这一断言 | **缺失**；gold 仅改 fill_values，不改 commit 调用链，详见 I1。 |
| 保存、加载 lock、repro/cache 恢复后保持所选假值 | 题面 commit/repro 后仍 new；stage/loader.py:L25-L45、cache.py:L150-L157 | `test_run_params_default` 的类型断言是 test.patch:L9 唯一功能测试新增断言；原断言检查真值嵌套参数及 lock | 局部/部分；该测试实际执行通过，但不在 22 P2P 参考中。F2P 直接调用 fill_values，不覆盖假值持久化整链。 |
| 真改值/删键/新增未记录键仍应 modified/deleted/new；未跟踪字段不影响参数状态 | param.py:L63-L75；公开 repro 参数变更测试 | 七 F2P 只有“不变→空”方向；11 个参数 P2P 无 status 变更断言 | **缺失**；公开 `test_repro_multiple_params` 的 42→43 行为不在执行两文件或参考内（base/tests/func/test_repro_multistage.py:L473-L527）。 |
| 默认/自定义文件、参数合并、值记录/导出、嵌套读取、错误路径保持 | base/tests/unit/dependency/test_params.py:L16-L109 | P2P 参数 11 项，见下一表 | 相关旧 API 有保护；不能推成 status/commit 的变更语义已保护。 |
| 普通文件依赖/输出变更、缓存与 force 提交行为保持 | base/tests/func/test_commit.py:L19-L97；test_status.py:L70-L114 | 两文件执行包含普通 run/输出回归，参考中只有非法名与缺 cmd；commit/status 文件未执行 | 部分/缺失；若合理修复碰共享 Stage 路径，须定点补查这些公开回归。 |

22 个 P2P 已逐一读其测试体与相关 helper，按同体参数化分组如下；没有把“同文件中的其余测试”偷算成计分参考。

| P2P 测试 ID（前缀） | 个数 | 最终断言及公开依据 |
| --- | ---: | --- |
| `tests/unit/dependency/test_params.py::test_loads_params` | 1 | 三个 ParamsDependency；默认/两个自定义路径、合并后的 params、初始空 info。对应 loads_params/_merge_params 现有接口。 |
| 同文件 `test_params_error[params0]`、`[params1]` | 2 | `[3]`、自定义文件的非列表值抛 ValueError；对应依赖格式限制。 |
| 同文件 `test_loadd_from` | 1 | PARAMS 映射（含 None）恢复为 ParamsDependency，params/info 保持。 |
| 同文件 `test_dumpd_with_info`、`test_dumpd_without_info` | 2 | dumpd 分别输出参数值映射或参数名列表。test.patch 将字面默认文件改成已有常量，无新增私有规格。 |
| 同文件 `test_read_params_nonexistent_file`、`test_read_params_unsupported_format`、`test_read_params_nested` | 3 | 缺文件返回 `{}`、非法 YAML 抛 BadParamFileError、点分键得到列表。 |
| 同文件 `test_save_info_missing_config`、`test_save_info_missing_param` | 2 | 缺文件/缺选定键抛 MissingParamsError；没有检查 status 的 deleted/new 分类。 |
| `tests/func/test_run_multistage.py::test_run_with_invalid_stage_name` 的 `[@:] [#] [$] [:] [/] [\\] [.] [;] [,]` | 9 | run_copy(name=非法名) 抛 InvalidStageName；run_copy 生成 copy.py 并调用 dvc.run（dir_helpers.py:L292-L307）。与本修复间接相关的原有输入校验。 |
| 同文件 `test_run_without_cmd[kwargs0]`、`[kwargs1]` | 2 | 单/多阶段未给 cmd 抛 InvalidArgumentError，文案 `command is not specified`。这是旧测试/已有异常约定，并非本题新增文案要求。 |

反向看七 F2P：空状态对应“已记录且值相等”，假值类别可从公开参数数据模型合理推出；没有要求与 gold 相同的行、调用顺序或额外 Mock。`fill_values` 是既有公开源码方法，测试直接调用它有接口依据，但“任何只修 StageLoader 的端到端方案都该通过”不能静态保证。没有已证实的合理解误拒（check 24 unknown），不能填全体合法路线 pass。

## 调用路径、gold 与具体疑点

**初始 false 故障成立：**StageLoader.load_stage 先构造参数名列表，再 fill_from_lock→fill_values；旧代码的 `if value` 丢弃 false/null/空容器，self.info 无键；status 读到当前键后走 new。gold 把判断改成 `param in values`，仍仅装载所跟踪键，保留显式 null 与未记录键的区别。serialize.py:L92-L108 会保留已有映射中的假值；cache.restore 也调用同一个 fill_from_lock。由静态路径看 gold 可修复第二症状及其装载分支；原 noop 日志中七项都确实到达断言失败，不只是 parser 找不到 ID。

**I1：题面第一症状未覆盖，gold 有强静态未修证据。** `repo.commit` 调 `Stage.changed_entries`，后者对依赖直接调用 `changed_checksum`（base/dvc/stage/__init__.py:L397-L411）。ParamsDependency→LocalDependency→LocalOutput→BaseOutput 没有参数专用 changed_checksum；通用实现比较 `self.info.get('md5')` 与参数文件 MD5（base/dvc/output/base.py:L168-L195；LocalRemoteTree 的 PARAM_CHECKSUM=`md5` 在 remote/local.py:L44）。题面所选键 start/end/universe/benchmark 不含 md5，info 保存参数值而不是文件哈希，故存在正常文件时 None 仍不等于其哈希；gold 没改此链。与此同时 ParamsDependency.status 丢弃通用 modified 结果、自行按键比较，可返回 `{}`，正好解释题面“status 干净而 commit 提示已变”的差异。证据层次：强静态推断；本轮和已读 RH2 两文件均未重放这个 commit 行为。影响：gold 的 RH2=1 不能作为完成全部题意的标签。

**I2：单向状态测试可漏掉禁用真实变化检测的实现。** 可区分候选是仅把 ParamsDependency.status 恒返回 `{}`：静态看可满足全部七 F2P；22 P2P 检查读取/构造/导出/异常及无关 run 输入，没有 status 改值或删键断言。执行的其它 run 测试也没有针对参数变化的反向断言。该实现违反 param.py 的现有 deleted/new/modified 语义及公开 repro 参数变更行为。尚未执行候选，不声称真实 RH2 已接受；这是有具体代码和输入的漏测疑点，不是泛称可以硬编码。

**I3：覆盖范围不足的具体边界。** 七 F2P 未覆盖数值 0、真正空字符串、嵌套 false 的 StageLoader、缺 lock 键或参数文件删除。gold 的 membership 改动本身看不到这些边界的直接破坏；未做全仓证明。类型切换 false↔0 仍按原有 Python `!=` 比较，不把题面未给出的严格类型比较另立验收标准。

合理替代路线：fill_values 可用独立缺失哨兵或选定键映射投影更新 info，不必采用 gold 的 if 形状；同时在 Stage 的参数依赖变更判断中复用参数状态语义，普通文件继续走文件 checksum。若改为覆盖 ParamsDependency.changed_checksum，必须同步处理当前 status 对 `super().status()[str(self)]` 的索引假设，避免基类返回空字典时 KeyError。方法位置不是公开要求；需要满足两个症状、真变化检测和普通文件提交回归。没有实现或运行任何候选。

## 既有 RH2 与环境证据

已核本题 E/tasks/iterative__dvc-4185 下 gold/noop 两个 `ledger.jsonl:1`、driver.log 尾部、两份原 eval.log 的安装结果/pytest 启动/关键断言/摘要，并重算日志及 ledger SHA256，与 V/run_refs.json 一致。原件附件已暴露结果，**本审查独立于旧质量结论，但不是 result-blind**。

| 条件/结果 | 原件与适用范围 |
| --- | --- |
| 配方与镜像 | `E/recipes/iterative__dvc-4185.json` 先离线装 `networkx==2.3+rh2.1`，再 `pip install -e '.[all,tests]'`，保留安装退出码。image.json 的派生镜像为 `sha256:fff47cb990a42b0f174cf646d339681682c7538bf3caf6792ea5ceab216e5b96`；仅 COPY wheels 并设 PIP_NO_INDEX/FIND_LINKS。 |
| 真实执行命令 | gold 日志 `evallog_replay-er19-dv1-iterativ_24d09737.eval.log:L930-L938`、noop `..._92136cb3.eval.log:L913-L921`：Python 3.9.20 / pytest 7.4.4，`pytest -rA tests/func/test_run_multistage.py tests/unit/dependency/test_params.py`，收集 51 项。不是全仓测试。 |
| noop | 安装 RC=0（L903）；七假值项在 L944-L1184 均因 `{params.yaml:{param:new}} != {}` 失败；L2181 为 7 failed/42 passed/2 skipped，test RC=1。ledger F2P=0/7、P2P=22/22、reward=0。 |
| gold | 安装 RC=0（L920）；七 F2P PASSED 位于 L2007-L2013，L2016 为 49 passed/2 skipped，test RC=0（L2020）。ledger F2P=7/7、P2P=22/22、reward=1。 |
| reference binding | 仅读取 `E/reference_bindings_v1.json.tasks['iterative__dvc-4185']`。把一个非法名 P2P 的单反斜杠来源 ID 绑定到 pytest 的双反斜杠转义 nodeid；gold 原日志 L1980 的完整 node PASSED，recipe 下本题 reference audit 显示原 parser 缺该项、绑定后参考缺席=0。51 实测项与 52 parsed states 的差是保留原 node 再加 alias，不是执行了额外测试。 |
| grader 身份和资源 | 两 ledger：rh2grader/54322、2 CPU、4 GiB、64 MiB shm、1 GiB tmpfs、deny_all，解释器前缀可写；观察导入 `/testbed/dvc/__init__.py`、networkx=2.3+rh2.1。历史 mem_peak 为 gold 386.82 MiB/noop 482.152 MiB，仅此 grader 运行观测。 |
| 清理和执行边界 | 两 ledger cleanup.removed=true；各 driver.log 的 manager_close 无 open containers/cleanup failures；candidate apply_user=agent/54321 仅证明补丁应用身份，不是 solver 运行。ledger env_qualification=absent、resource_facts=null，不能冒称正式 actor 验收。 |

reference binding 实现已静态全文读 E/reference_bindings.py：只在 test output segment 匹配显式完整 nodeid，任成员缺席不补通过；原 F2P/P2P 分组保持。它没有修改测试或 gold，也没有补上 I1/I2 的语义覆盖。没有重新审计共享 parser 的所有可伪造输出攻击。

入口核对：E/replay_with_install_recipe.py 全文、run_dvc_install.py:L104-L117，确认本题追加 `--bindings`，配方替换 eval/candidate 安装行，转调用真实 frozen replay CLI。通过 tarfile.extractfile 只读 frozen_sources/dvc.tar.gz 内三个入口的有关行，成员 SHA256 与 inventory.common 记录一致：scripts/replay_grade.py=`611571...`；adapters/slime/replay_grade.py=`031046...`；prepared_task_face.py=`31ff514...`。派生镜像由 replay 显式 override；rollout_spec_from_view 仍使用 public image 和 render_user_prompt。没有解包、导入、执行这些脚本。

batch04/environment_replay_inventory.json 只选择 common 与本题 tasks entry。它记录原 summary 指向现不可达的历史 `/work` 路径、当前目标镜像未验、构建 context 缺失；若原派生镜像不可用，须准备真正 wheel/build payload，不能用 image/recipe 审计 JSON 代替。其缺口是未来重放准备工作，不推翻已核 09-19 运行。

## 开发条件、交付边界与八方面范围

| 开发需求 | 公开依据、现有证据 | actor 缺口/最小未来验证 |
| --- | --- | --- |
| Python、DVC 当前源码及 yaml/dpath/voluptuous/funcy/networkx | setup.py:L49-L82；参数与 Repo 导入路径。既有 grader 安装和源码来源已见。 | 真实 agent shell 的 PATH/激活、源码路径、networkx 配方消费未知。先打印 UID/cwd/python 路径与 `dvc.__file__`；不把 grader 导入成功记为 actor pass。 |
| pytest 收集依赖 | setup.py:L101-L134，tests/conftest.py 全局导入 remotes；即本地参数测试也依赖完整 fixture 导入链。 | agent 下先 collect-only 参数单文件，再跑公开已有参数单元测试；这是未来命令，未执行。无需为核心样例启动云端/GPU。 |
| 临时 Repo、锁/状态库、参数与本地输出、shell/Git | dir_helpers.py:L90-L108、L250-L305。核心样例 no-scm 可用本地小文件；run_copy 需要子进程。 | 验 workspace/home/tmp 可写、工具和子进程。Git/测试依赖可准备时固定；无证据需公网运行期服务。 |
| 依赖补齐与资产 | grader 使用离线 wheels；原业务数据缺失不妨碍通用最小例。 | 正式 actor 是否已含同兼容依赖未知；若缺包应准备固定离线资产，不能假定 actor 可写系统前缀或联网安装。无本题新编译/GPU需求证据。 |
| 合法交付 | 两条症状可用 dvc/ 普通源码修复；gold projection.included_paths 仅 `dvc/dependency/param.py`，ignored_paths 空。 | 不必写不可提交的系统文件。eval_script.after.sh 明确恢复 test_run_multistage.py 与 test_params.py 后应用官方 test.patch；这些测试改动不会成为该次验收输入。无证据扩大路径排除；additional_exclusions 应为空。 |

八方面覆盖：①公开需求、提示分层和公开读稿已查，真实消息未知；②base/test/gold 身份及初态关键路径已查，未重放原业务；③全部 test.patch、7 F2P、22 P2P 与两执行文件全文已查，相关 fixture/helper 与状态路径已查；④合理替代路线及具体漏测候选已提出，合法替代解实跑未知；⑤读了 loader、serialize、cache、commit/status 及相关公开测试，发现 I1，未全仓证明回归；⑥grader 配方/原件已核，actor 开发条件待验；⑦两官方恢复文件和 gold 投影已核，未重审整个共享安全边界；⑧未读其他题，跨题关系/模型表现/学习价值未知。

泄漏与用途（check 29）：公开导出无 .git，只是材料包事实；真实 actor 祖先 refs、未跟踪文件、预装资产和答案可达性均未验。源码归档 CLI 文档含一个其他 task ID 的通用命令示例，只见标识，未打开该题任何材料。题面给出症状与配置，没有给此 gold 修法；本主审已见 gold、隐藏测试和既有运行答案，产物不得提供给 solver。清单 33–36 无真实模型运行证据，成本未观测项保持 null，不推断成功率或可训练价值。

## 唯一优先下一实验（尚未执行）

在准备好的本题固定环境中，对 **base 与 gold** 用同一公开本地两阶段样例做对照：params.yaml 含 `start: 20200101`、`eval.filter_limitup: false`；分别创建只跟踪 start 的 get_base_dv 和跟踪嵌套 false 的 eval，用简单命令生成小输出。重新打开 Repo 后记录 JSON status；在不改任何文件的情况下执行 get_base_dv 的不带 force commit，记录是否出现确认提示/StageCommitError，再记录 eval 的 status/repro。预期可区分：gold 消除 false 的 new，却仍触发 get_base_dv 参数变化提示。用真正改值、删键、改未跟踪字段作同一窄样例的控制，避免把“所有状态都为空”当正确修复。

这是先验证 I1 的 CPU 定点实验；若得到预期，再制定参数 commit 的规格一致回归断言，并用合理替代路线及 I2 恒空状态候选校准。新的候选/测试应是独立诊断版本，不改原题或原评分。执行人先核镜像/recipe、实际身份和源码来源；本文件没有授权或声称已执行。

## 实际阅读与暴露边界

本题公开 user_prompt/public_bundle/base_identity/environment_brief、封存 public_read；V/test.patch、gold.patch、grading.json、validation.json、environment_record.json、run_refs.json；上文列出的本题环境原件、common/本题 inventory、单题 bindings 均已读。environment_record 内附既有结果、issues 标签及名为 history 的环境批次路径列表，reference audit 附修正前后结果，因此明确不是结果盲审；**未沿这些路径打开旧质量调查或 history/refs**，未读 source_refs.json、旧报告、其他角色结论、root aggregates 或其他题条目。

源码全文阅读：param.py、dependency/base.py、dependency/local.py、stage/loader.py、repo/commit.py、tests/unit/dependency/test_params.py、tests/func/test_run_multistage.py、tests/func/test_commit.py、tests/conftest.py、tests/func/conftest.py、tests/remotes/__init__.py。其余是正文所列行段：output/base.py/输出本地类、stage/__init__.py/serialize.py/cache.py、repo/status.py、utils/yaml.py、dependency/__init__.py、setup.py、dir_helpers.py、loader/cache/repro/status 公开回归。环境 pip 重复依赖行和成功测试捕获日志未全逐行阅读，只定位实际安装/测试/断言/摘要证据，不宣称审完全量日志。曾猜测不存在的 dvc/tree/local.py，随后定位到 remote/local.py，不把猜错路径当资产问题。

未执行项目 import/pytest/build、网络、下载、安装、Docker/SSH/GPU/付费模型；未修改源码、原题、测试、评分、公开读稿；未提交或推送；未开子 agent。当前只写此 analysis_before_history.md，保存后等待协调者显式解封本题历史；card/record/delta 尚未生成。
