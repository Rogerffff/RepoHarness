# iterative__dvc-5839 独立复核初判（封存）

2026-09-21。角色：独立 reviewer；本文件在阅读本包任一其他角色结论之前写成，落盘后不改。第一阶段顺序：5839 → 9395 → 3620。本次只静态读文件和校验元数据，没有执行 DVC、pytest、安装、Docker、SSH 或模型。下列新 CPU 方案全部未执行。

路径约定：`R=${REPO_ROOT}`；`P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-5839`；`Q=同材料根/private/iterative__dvc-5839`；源码行号相对 `P/base`；`E=R/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-5839`。引用的相对路径均以这四个明确根解析。

## 初判与建议用途

公开目标是让 `dvc metrics show --precision n` 实际控制输出。题面曾疑问科学计数法的精度语义，但公开 CLI 帮助 `dvc/command/metrics.py:250–258` 和已有 `_show_metrics`/`_show_diff` 测试都明确按小数点后 n 位取整；不能把偏好“尾数 n 位”升级成必须实现的隐藏需求。

base 的 `CmdMetricsShow.run:92–98` 没有传 precision，helper `:32–37` 因而回退 5 位。gold 只补传该参数，保留默认、JSON 路径与其他调用者；对题面字典型 YAML 的主路径是直接、合理修复。原始 noop 运行也恰在缺失 precision 的调用断言失败，而非安装或收集失败。

静态建议：可作为范围明确的参数传递开发诊断候选，但仍为 `static_review / needs_review`，不能按 reward=1 宣布完整需求已满足或 actor 已就绪。主要质量限制是新增 F2P 只对空结果 Mock 检查 `precision=8`，没有 CLI 实际数值断言；固定传 8 的错误补丁也有静态可通过路径。另有合法标量浮点 metrics 分支仍绕过 rounding（base 已有，gold 未处理），需要区分“题面原例修复”与“所有 metric 类型都遵循参数”的更宽承诺。先做下述窄 CPU 对照，再决定是否把本题用于超出参数传递能力的评估。

## 暴露、材料身份与实际阅读

- 已读共用 reviewer 角色卡、actor_environment_card、record_template、quality_review_protocol；没有沿协议中的主计划/旧调查链接阅读。
- 已读 P 的 user_prompt、public_bundle、base_identity、environment_brief；Q 的 test.patch、gold.patch、grading、validation、run_refs、source_refs、environment_record。后者暴露环境修复汇总、gold/noop reward 与 history/analysis 路径名；只把它当索引，没有打开其 analysis/history 目标。未读 public_read、analysis_before_history、old_findings_delta、card、screening_record、任何 review、质量 history、manifest、主计划、method_adjustments 或其他角色结论。
- base_identity 声明 commit `daf07451f8e8f3e76a791c696b0ea175e8ed3ac1`、tree `128a483541be19fec2b303ba64c4baa6c6f0f758`、540 tracked entries、无 .git。公开/私有 base 一致；本次没有重建整个 Git tree 来独立核其身份。
- 标准库文件校验：Q/test.patch 与 grading.test_patch 完全相等；gold.patch 与 validation.golden_patch 相等且 SHA-256 为 `15078fc2c73469c535ed73bfdce45674205d0b77922f4dd082580e8be569ddde`；两份指定 eval.log 的 SHA-256 均与 run_refs 相符。
- 完整读 `dvc/command/metrics.py`、`tests/unit/command/test_metrics.py` 的 22 个测试、`dvc/repo/metrics/show.py`、`tests/conftest.py`；读 `dvc/utils/diff.py:88–120`、flatten.py、`tests/dir_helpers.py:1–120,210–326`、`dvc/command/repro.py:1–90`、`dvc/command/experiments.py:508–543`、YAML loader `:1–39`、setup.py 的依赖/extras、setup.cfg、CONTRIBUTING.md。抽查 `tests/func/metrics/test_show.py:1–42,99–125,158–209`；其他功能测试仅检索 test 名，不称逐条读完。
- 原运行读 E 两个 ledger.jsonl 第 1 行及指定日志中的官方测试恢复、安装结束、测试命令、错误栈与全部测试终态；并读 E/gold/recipe/recipe.json。没有把重读日志称为独立重跑。

## 需求—断言与反向来源

| 公开要求或合理回归 | 公开依据 | 测试和决定性断言 | 覆盖判断及证据层级 |
| --- | --- | --- | --- |
| 用户输入的 precision 到达展示步骤 | metrics.py:250–258；run:92–98 | 唯一 F2P `tests/unit/command/test_metrics.py::test_metrics_show`：新增 `--precision 8`；`CmdMetricsShow` 选择正确、run=0；repo show 的 targets/recursive/all flags 保留；Mock `_show_metrics({}, markdown=False, all_tags=True, all_branches=True, all_commits=True, precision=8)` 恰一次 | 覆盖这个调用点和值；没有实际 metrics、输出或多个 n。原 noop 恰在此调用断言失败 |
| 小数位默认 5，且用户指定任意支持的 n | metrics.py:32–37,250–258 | P2P `test_metrics_show_precision` 检查嵌套 float 在默认、4、7 位的完整字符串；`test_metrics_diff_precision` 检查默认/10 | helper 层充分可解释；缺 CLI 默认、0、3、10 与科学计数法原例的连通测试 |
| 原例两个小数数值经读取、CLI、格式化真正变化 | user_prompt 的 mae/mse YAML；repo/metrics/show.py:73–91；YAML loader | F2P repo 结果为 `{}`；P2P precision 用 1.x/2.x 字典，未用题面 YAML | 缺失端到端原例，不能从 Mock 通过推出已执行过科学计数法输出 |
| JSON 输出原始数据；Markdown 继续格式化 | metrics.py:87–100,228–239；diff 同类分支 | `test_metrics_show_md` 检查 helper Markdown 表格；`test_metrics_diff` 同时设置 show-json/show-md，核 repo 调用与 rc | show JSON 路径没有本题有效 payload 的输出断言；gold 不改该分支，静态未见新破坏 |
| scalar 浮点也属于合法 metrics | repo/metrics/show.py:48–50；func/test_show.py:17–22 接受 YAML `1.1`；helper:54–56 | P2P `test_metrics_show_with_non_dict_values` 仅 scalar int=1 | scalar float 无精度断言；helper 用 str(metric) 绕过 _round，gold 延续这一缺口。不是 gold 引入的回归 |
| falsey/nested、多 revision/path、不同列头保持 | helper:40–65；旧测试 | `test_metrics_show_with_valid_falsey_values`、`with_no_revision`、`with_multiple_revision`、`with_one_revision_multiple_paths`、`with_different_metrics_header`、`show_default` 的整表字符串 | 全部为评分 P2P，逐条已读；直接测试 helper，不保证 command 按不同 flags 的全部组合连通 |
| diff 的旧展示语义保持 | _show_diff；旧测试 | P2P `test_metrics_show_raw_diff`、`show_json_diff`、`diff_no_diff`、`diff_no_changes`、`diff_new_metric`、`diff_deleted_metric`、`diff_sorted`、`diff_markdown_empty`、`diff_markdown`、`diff_no_path` 及上列 diff/precision | 全部评分 P2P，逐条已读；共 21 个 P2P，没有把同文件测试数当额外覆盖 |

新测试没有引入 helper/fixture。`dvc` fixture 经 tests/conftest.py 导入 dir_helpers，在 tmp_path 下用 Repo.init(no_scm=True) 建本地仓库；mocker 来自 pytest-mock。`spec=_show_metrics` 使参数按函数签名匹配，因此 gold 用 positional 参数也可通过，不存在“只允许 keyword”误拒。测试还约束必须调用这个私有 helper、且恰一次；公开规格要求可见行为，并不要求内部调用结构。直接构造等价表格的重构理论上可能被拒，但未实现/运行替代解，不能报告已经证实的误拒。

## 八方面核对及剩余未知

1. **公开需求**：已核实际静态渲染题面、可见 hints、CLI 帮助和旧测试。小数位语义可由公开代码消解；Windows 路径只是用户原环境，目标修复无平台专属逻辑。实际 CC 消息、hints 是否进入 system 未验。
2. **材料与初始问题**：base/test/gold 身份及补丁字节一致；静态漏传参数和历史 noop 失败一致。未实际复现题面 YAML，不把格式说明中 `0.001e-09` 的明显数值疑点当正确输出约束。
3. **测试命中**：全部新增断言、1 个 F2P、21 个 P2P 已核；F2P 仅空 payload Mock。固定传 precision=8 会通过其调用断言，原有 helper P2P 无需变化；这是可执行候选的静态推断，未测 reward。
4. **合理解接受性**：同一 helper 的 positional/keyword 路线均被 spec 接受；内部 helper 调用约束有重构误拒风险，但目前没有实际替代解拒绝证据。保留不同于 gold 的实现空间，不把字符串 P2P 一律认定过严。
5. **回归/gold**：gold 仅改 CmdMetricsShow 调用；repro.py:24 和 experiments.py:541 仍调用 helper 默认精度，不受这一行修改影响。新增精度在 Markdown 同一分支适用，show-json 明确绕过。原例字典科学小数按 round(...,8) 可得到约 1.483e-05、1e-08（静态推断），不是按尾数 8 位。scalar float 未修的精度行为需独立定位；没有穷举所有数值/异常/平台。
6. **开发条件**：见下表。历史 grader 离线安装+22 测试成功不是 actor 环境成功；不要求模型联网或运行全仓 remote suites。
7. **交付/评分边界**：test.patch 只改 tests/unit/command/test_metrics.py；日志表明该文件从 base 恢复再应用官方 patch。gold 的 dvc/command/metrics.py 在 ledger projection.included_paths 中、ignored_paths=[]，可提交的普通源码修法不被该恢复覆盖。没有复审共享 parser/容器隔离代码、真实镜像答案资产；本静态包无 .git 不能证明镜像无泄漏。没有自行添加路径排除。
8. **题目关系/用途**：本题是现有 CLI 参数传递修复，公开代码给出可见 helper 和 diff 命令范例。本阶段尚未读后两题，不因同仓或题号推断问题派生；后续另题初判记录已暴露前题源码/gold。审查上下文已见隐藏测试/gold，仅用于 development_diagnostic，不能充当独立 solver，也不推测基座成功率/学习价值。

## 原始运行：事实、条件和限度

两条 `E/{gold,noop}/ledger.jsonl:1` 都为 2026-09-19 的历史真实 RH2 replay，derived recipe=`dvc-install-v1:iterative__dvc-5839`，实际 image `sha256:9830786d461222987397d06799bb88a5e895c9af93cb94cfaec8bec30f5d7f3b`，不等同公开 image manifest。profile 为 rh2grader/54322、deny_all、2 CPU、4 GiB、64 MiB shm、PID512，解释器前缀 /opt/miniconda3/envs/testbed 可写；candidate apply_user=agent/54321 不是 CC actor 运行证据。

- `E/gold/eval_logs/evallog_replay-er19-dv1-iterativ_0842b89c.eval.log:207–247` 显示恢复并应用官方测试；`:613–640` 显示 DVC 2.0.18+daf074.mod、安装 rc=0、运行 `pytest -rA tests/unit/command/test_metrics.py` 并收集 22 项；`:656–685` 全部 22 passed、rc=0。ledger reward=1，F2P=1/1，P2P fail=0/21，import path=/testbed/dvc/__init__.py，cleanup removed=true。
- `E/noop/eval_logs/evallog_replay-er19-dv1-iterativ_5507cf1b.eval.log:613–621` 同一测试文件/22 项；`:677–679,840–860` 缺失 precision 的实际调用；`:875–904` 21 passed、唯一 F2P failed、rc=1。ledger reward=0，安装 rc=0，无 reference missing，cleanup removed=true。
- recipe.json 把安装替换为 `python -m pip install -e '.[all,tests]'` 并报告包 metadata；备注只适用于 diagnostic spec，原 driver/projection/manager/tests。没有把这里的 full_test_exit_zero 解释为全仓测试通过，也没有把 environment_record 的 verified_environment_pair 作为题目语义质量结论。

## 开发需求与最小后续实验（均未执行）

| 必要操作/资产 | 公开依据 | 现有证据及范围 | 缺口 | 最小验证与预期 |
| --- | --- | --- | --- | --- |
| 定位 CLI/formatter，导入工作区 DVC | metrics.py 的 parser/run；setup.py:49–93；tests/conftest.py | 公开源码足够定位；grader import /testbed/dvc | actor 实际 PATH、Python、包来源未知 | actor shell 执行 `id; pwd; command -v python; python -c 'import sys,dvc; print(sys.executable,dvc.__file__)'`；应为 agent 工作区导入 |
| 运行本地 unit 测试和 YAML 读取 | pytest、pytest-mock、xdist worker_id fixture、ruamel.yaml、flatten_dict、tabulate | 历史 Python3.9.19/pytest6.2.3 可执行 22 项 | 公开镜像是否消费维修、actor prefix 可写及离线依赖未知 | 以受支持的统一 actor 入口运行公开 base 的 `python -m pytest -q tests/unit/command/test_metrics.py`；base 旧公开测试可过不代表修复 |
| 原例 YAML、非默认 precision | user_prompt；func/test_show.py 的 targets 路径 | 文件可本地生成，无外部资产/服务需要；CONTRIBUTING 仅外链但入口可从源码获知 | 实际 shell/导入/输出尚未验 | 在临时工作目录生成 mae/mse YAML，经 `dvc metrics show metrics.yaml` 与 `--precision 8`、`--precision 3` 对比；gold 应遵循 decimal rounding，JSON 原值保持 |
| 提交修复 | 普通源码 dvc/command/metrics.py | 历史 gold projection 接收并执行 | actor 可写/真实初态需统一验收 | 只需要仓库源码改动，无需提交依赖前缀、home 或生成 metrics 文件 |

**唯一优先质量实验**：在同一已确认身份/导入来源的 CPU 诊断入口，比较 base、gold 与“在调用处固定 precision=8”的最小错误补丁；同时记录原官方 22 项结果和公开 CLI 原例在默认/3/8 的输出。预期错误补丁可能官方 reward=1 却在默认/3 时不符合公开要求；执行前只能称候选。将 scalar YAML `1.098765366365355` 加为同轮独立观察，可确认 gold 对合法标量仍不应用 precision，不能据此声称题面字典原例未修。若以后强化测试，应加可见输出的多精度连通断言，并检验合理 formatter 重构是否可接受，不直接抄内部 Mock 规范进题面。

本文件至此封存。等待协调者在三题 initial 全部落盘后统一开放下一阶段材料；当前没有 review.md，也没有未执行实验的通过声明。
