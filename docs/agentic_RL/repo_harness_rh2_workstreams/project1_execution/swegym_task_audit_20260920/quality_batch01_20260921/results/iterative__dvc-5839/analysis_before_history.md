# iterative__dvc-5839：history 前静态分析

本稿在历史调查开放前封存，不回写。主审：investigate_dvc。日期：2026-09-21。这里只做静态源码、原始日志与元数据核对；没有运行 DVC、安装、Docker、SSH、模型或候选补丁。

## 引用范围与材料身份

- R = ${REPO_ROOT}。
- P = R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-5839；Q = 对应 private/iterative__dvc-5839；下文源码相对 P/base。
- O = R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/iterative__dvc-5839。
- T = R/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-5839。
- GL = T/gold/eval_logs/evallog_replay-er19-dv1-iterativ_0842b89c.eval.log；NL = T/noop/eval_logs/evallog_replay-er19-dv1-iterativ_5507cf1b.eval.log。账本均为 T/{gold,noop}/ledger.jsonl:1。

P/base_identity.json、public_bundle 与 Q/grading 的 base 同为 daf07451f8e8f3e76a791c696b0ea175e8ed3ac1，tree=128a483541be19fec2b303ba64c4baa6c6f0f758。元数据称 540 个跟踪条目、无 gitlink/LFS 指针/.git；本轮没有逐 blob 重建 tree。精确读取 source_refs 指定的 s2/ingest/public_bundles_v0.jsonl、grading_bundles_v2_v0.jsonl、validation_bundles_v0.jsonl 各第 142 行，与本题三份 JSON 内容相等；test.patch、gold.patch 与各自 JSON 字符串相等。gold sha256=15078fc2c73469c535ed73bfdce45674205d0b77922f4dd082580e8be569ddde。两份日志与 run_refs 的 SHA256、两角色共十个 recipe 文件与 environment_record 的 SHA256 均相符。源码导出身份、评分派生镜像身份和实际 actor 身份分别记录，不合并。

已读 O/public_read.md。已暴露 Q 全部私有测试、gold、grading、validation、source_refs、run_refs、environment_record；后者含 verified_environment_pair 标签、环境检查汇总及 history/analysis 引用，属于非盲暴露，但未跟随这些历史/分析链接。已读角色卡、八方面协议、环境卡、模板及协议明确引用的 40 项清单、记录定义。没有读取 manifest、主计划、method_adjustments、其他题结果、旧质量报告。工具曾枚举本题路径，不代表逐文件阅读；大输出被截断的部分不作全文已读证明。

## 1. 公开需求和初态

题面 user_prompt:8、12–41 要求 metrics show 的 --precision 生效，给出两个科学计数法浮点数。题面对普通小数位与科学记法尾数精度提出两种设想，但公开 CLI 帮助 dvc/command/metrics.py:250–258 明示“小数点后 n 位、默认 5”；旧 test_metrics_show_precision:303–333 已固定默认、4、7 位行为。因而沿既有普通小数位语义修正足以满足本题，不能据 issue 的偏好擅自要求新 CLI 或有效数字语义。题面 :30 的 0.001e-09 与 :35 的 0.00000001 不等值，前者是例文数值笔误，不宜当精确 oracle。

公开源码中 parse_args → CmdMetricsShow.run → repo.metrics.show → _show_metrics 是完整入口。run:92–98 漏传 self.args.precision，而 _show_metrics:32–38 已有 None→5 和 round(float,n)。静态因果与 NL:832–860 的真实失败一致：预期 precision=8，实际只调用 _show_metrics({},False,True,True,True)。NL:130–136 显示 HEAD=base、工作区干净；其 :189 后无候选差异。初态问题不是安装或收集失败。但题面两个 YAML 值的真实 CLI 输出尚无本轮执行证明。

真实模型请求未捕获；P/user_prompt 是当前静态渲染，public_hints 是否进入 system message 未核实。NON-TEST 修改限制若实际应用，本题仍有合法 source 修法；“所有测试改动都恢复”只是旧解释，不能概括当前机制。

## 2. 所有新增/修改断言与 fixture/helper

Q/test.patch 只改 tests/unit/command/test_metrics.py 的 test_metrics_show，F2P 恰为该一个 ID。没有新增 fixture 或其它测试文件。

| 位置 | 输入、调用、最终断言 | 对应公开依据/限度 |
| --- | --- | --- |
| patch:8–9；base test:103–116 | parse_args 的 metrics show、-R、三个 all-*、target1/2，新增 --precision 8；断言 func 为 CmdMetricsShow | 公开 CLI 的已有 flags 与精度选项 |
| patch:16 | repo.metrics.show.show 被 mock 为 {}；原 m 改名 m1 | 不读取 YAML、文件、真实 metrics 数据或科学计数法 |
| patch:17–21 | _show_metrics 被 spec=_show_metrics 的 mock 替换，返回空字符串 | helper 本体完全不执行；spec 容许按签名归一化的位置/关键字调用。gold 使用位置参数且已通过，不把 pytest 失败消息中的 kwargs diff 误解成只接受关键字 |
| patch:23 | cmd.run()==0 | 成功命令退出；没有检验打印内容 |
| patch:25–33 与 base:123–130 | m1 仅调用一次，repo、两个 target、recursive、三个 all-* 完全匹配 | 保护读取参数传递，precision 不该改底层数据读取接口 |
| patch:34–41 | m2 仅调用一次，输入 {}，markdown=False，三个 all-*=True，precision=8 | 唯一新增核心 oracle；验证某内部调用处携带 8，没有直接验证用户输出或任意 n |

dvc fixture 实际链为 tests/conftest.py:6 导入 dir_helpers；dir_helpers.py:294–308 用 tmp_dir/make_tmp_dir 构建 DVC repo 并切 cwd。make_tmp_dir:264–289 缓存本地模板，TmpDir.init:92–112 在没有 scm fixture 时调用 Repo.init(no_scm=True)。该 F2P 不要求云远端或 Git 历史。CmdBase:34–46 从当前目录开 Repo(uninitialized=True)、保存 args，updater 在测试环境下被 DVC_TEST 抑制。mocker 来自 pytest-mock，版本由 test_requirements:7 固定 3.5.1，原始 GL/NL plugin 表亦确认。

根 conftest 的 autouse reset_loglevel、enable_ui、_close_pools 已读；还会顶层导入 remotes。tests/remotes/__init__.py 导入 s3/webdav 等，s3:7 导入 moto，webdav:7 导入 WsgiDAVApp；即便本题不启动服务，收集仍依赖这些包。未逐层审计第三方 fixture 实现。没有 unit 或 unit/command 子目录 conftest 文件。

## 3. 双向需求—断言映射与 P2P

完整打开 base tests/unit/command/test_metrics.py 的 22 个函数，含全部 21 个参考 P2P。以下“保护”指来源参考中有该断言；“执行”另由第 5 节原始日志支持。

| 要求/合理旧行为 | 公开依据 | 测试与决定性断言 | 覆盖程度 |
| --- | --- | --- | --- |
| CLI 指定 n 应影响普通/Markdown 表格 | prompt:8、17；metrics.py:250–258 | F2P test_metrics_show 仅验证 helper 收到 8 | 部分：空数据、无真实输出、无另一个 n/默认 CLI |
| n 为小数位、默认 5 | metrics.py:11、32–38、254–255 | P2P test_metrics_show_precision:303–333，默认/4/7 的具体表格；diff_precision:133–154 默认/10 | helper 层有强保护，未覆盖 CLI 任意精度 |
| 原题两科学记法小数的输出 | prompt:14–15、35 | F2P 无数据；上述 P2P 使用约 1–3 的普通小数 | 缺失端到端原例；不能用 22 passed 代证 |
| 读取 flags/targets 保持 | metrics.py:79–85 | F2P 的 m1 参数断言 | 覆盖选定组合 |
| 表格零值、非 dict、修订列、多路径/分支、不同键缺失值 | metrics.py:40–69 | P2P show_with_valid_falsey_values、no_revision、non_dict_values、multiple_revision、one_revision_multiple_paths、different_metrics_header:224–300 | 覆盖其具体输入；标量仅整数 1，无标量自定义精度 |
| 默认普通及 Markdown 布局 | utils/diff.py:88–107 | P2P show_default:336–350、show_md:354–372 | 覆盖 helper 默认；没有 CLI --show-md 与 n 组合 |
| JSON 保持原始数值，precision 只管表格 | metrics.py:87–90；repo/metrics/show.py:48–59、81–91 | 参考 P2P 的 show_json_diff 实际是 _show_diff 的嵌套键表格；test_metrics_diff 的 --show-json 路径 mock 为空 | metrics show JSON 精度兼容没有参考行为断言；源码分支可解释 gold 不影响它 |
| diff 旧显示行为 | metrics.py:108–138、157–162 | P2P show_json_diff/raw_diff、diff_no_diff/no_changes/new_metric/deleted_metric、diff_sorted、diff_markdown_empty/markdown/no_path:49–100、157–220 | 具体字符串、缺失值、排序、Markdown 已保护；本题 gold 未改该路径 |
| 默认 helper 调用者保持 | repro.py:22–24；experiments.py:538–541 | 参考集中无相应命令端到端测试 | 已读调用点；gold 只改 show 命令，不改 helper 签名/默认 |

额外公开回归实际读过 tests/func/metrics/test_show.py:1–228：本地 YAML 标量/字典、多个 metrics、分支/标签、缺缓存、未登记 target、无 DVC/Git repo、recursive、零值、损坏/不存在/重叠输出。它们验证底层读取，均不在本题参考集，也不在本次 GL/NL 执行命令。所用本地 TmpDir/gen、run_copy_metrics 链没有全部展开；不把这批“已读”当作已验证或已执行。已读 repo/metrics/show.py、serialize/_yaml.py、flatten.py、utils/diff.py，确认 YAML 值先解析为数字，再由显示 helper 舍入；未读第三方 tabulate/ruamel 的安装实现。

关键测试约束反查：CLI flags、现存 helper 参数与默认舍入有公开依据；“必须在 run 中恰好调用 _show_metrics 一次且显式携带 precision=8”是内部调用方式，并非用户可见契约。不同于 gold 的合理路线是以关键字 precision=self.args.precision 调用（spec 接受）；更大重构可由独立格式化适配层生成相同输出并保持原 helper 对旧调用者兼容，但隐藏 mock 可能拒绝。这里只记录实现耦合的静态风险，不声称已证误拒，也不把任何内部 mock 自动判为无效。

## 4. gold 完整性、缺口与可区分控制

gold 只为 CmdMetricsShow 的既有 _show_metrics 调用增加 self.args.precision（Q/gold.patch:8）；不改 default、helper、读取层、JSON、diff、依赖、资产或其它需求。argparse 未提供值时为 None，helper 恢复 5；0 不会被 truthiness 替换；负数沿既有 round 行为。Markdown 共用调用可获得精度。静态上原例按 8 位应表示 1.483e-05、1e-08；默认依旧 1e-05、0.0。顶层浮点 metric 仍在 helper:54–57 直接 str()，属于已有边界且题面为字典，本轮不擅自扩张成 gold 必修目标。没有发现 gold 所需依赖漏交或无关改动；这不是所有输入均正确的证明。

具体漏测疑点：保持 helper 原状，仅在 run 中硬编码第六参数为 8，则 F2P 的空字典调用形状仍匹配，21 个 P2P 又主要直接调用 helper，预计评分仍全过，但 CLI 默认、--precision 4/7 等会错误地用 8。这是有公开依据的部分实现，不是借修改测试或伪造日志蒙混。尚未执行，因此写“可能漏判”，不写“已构成真实 RH2 反例”。

唯一优先 CPU 对照建议（未执行）：固定 base、dvc-install-v1:iterative__dvc-5839、当前参考与独立 fresh 环境，比较 base / gold / 仅将命令层 precision 硬编码为 8 的单行候选。三者都做相同安装、官方 22 项评分，并用未 mock 的 CLI 从同一个本地 metrics.yaml 读取：
mae: 1.4832495253358502e-05
mse: 5.0172572763074186e-09
ordinary: 1.098765366365355
用默认、--precision 4、--precision 8，普通和 --show-md 输出，另跑 --show-json。控制输入文件字节、解释器和导入路径；读取输出按数值/公开布局判断，勿把题面 0.001e-09 笔误作为 oracle。gold 应分别保留默认5/指定4/指定8；硬编码候选应在默认/4 被行为检查识别，即使原参考放过。普通数确保默认/4 与8可区分，原科学样例确保没有漏掉题目核心。先留此一个实验，不并行扩大到全仓或强制第二补丁。

## 5. 原始运行证据及适用条件

本轮只读取 2026-09-19 已有真实 RH2 日志。两角色账本:1 均为 image sha256:9830786d461222987397d06799bb88a5e895c9af93cb94cfaec8bec30f5d7f3b、recipe dvc-install-v1:iterative__dvc-5839，user rh2grader/54322、deny_all、2 CPU/4GiB、PID512、shm64MiB、tmp1GiB，可写 conda 前缀。该镜像是本地派生镜像，不等于 P/public_bundle 指定的来源 image digest。candidate apply_user=agent/54321 只表示应用补丁的身份，不证明真实 actor shell 可运行测试。

| 证据层 | noop | gold |
| --- | --- | --- |
| 初态/候选/官方恢复 | NL:130–136、189–230：base 干净；恢复唯一测试文件并成功应用 test patch | GL:132–214：base 上仅 dvc/command/metrics.py 单行差异，恢复测试并成功应用；账本 projection included_paths 恰为该源码 |
| 安装 | NL:370–372、583–606：/opt/rh2/build-wheels，editable /testbed，RC0 | GL:387–389、600–623：同流程 RC0 |
| 实际命令与收集 | NL:613–623：pytest -rA tests/unit/command/test_metrics.py，22 items | GL:630–640：相同命令，22 items |
| 逐项与退出 | NL:797–860 的 F2P mock 断言失败；:875–895 21 P2P PASSED；:897、901 1 failed/21 passed，RC1 | GL:656–677 全 22 PASSED；:678、682 summary 与 RC0 |
| parser/参考核对 | 账本解析22、F2P0/1、P2P fail0/21、reward0，无 reference_missing/skipped | 解析22、F2P1/1、P2P fail0/21、reward1，同样无缺席 |
| 生效/清理 | 账本 import=/testbed/dvc/__init__.py、version2.0.18+daf074.mod、cleanup removed=true | 相同导入位置与清理；gold 差异与目标失败转通过相符 |

主审另用标准库对日志 PASSED/FAILED 行逐 ID 对账，参考 22 项全部出现。这里“22 已执行”的证据来自完整 pytest session、进度、失败栈、逐项 summary 和退出相互印证，不只依赖环境汇总标签或 parser 计数。安装依赖输出只定点/筛选读了关键行、版本、成功/失败标记，未逐包复核所有传递依赖；重复 conda 激活输出、完整 mock 栈部分未逐行读。无原题 CLI 重现、重复稳定性、真实 actor 或真实模型证据。

recipe.json:3–13 和 before/after scripts 显示维修将浮动升级/多次宽安装替换为 python -m pip install -e '.[all,tests]'，保留 install_rc；测试选择和官方补丁不改。source setup.py:131–144 确认 all/tests 是实际 extras。该配方已覆盖本次引用的 grader 安装问题，不能继续把旧默认安装障碍写成本次失败；actor 是否消费该配方仍未知。

## 6. 开发需求与交付边界

| 操作/资产 | 公开依据 | 已知证据范围 | 当前缺口/建议最小验证（均未执行） |
| --- | --- | --- | --- |
| 定位与导入源码 | metrics.py:76–105；setup.py:49–93、147–159 | 已定位入口；grader 使用 /testbed/dvc | 实际 agent shell 打印 sys.executable、sys.version、dvc.__file__，确认当前 checkout 生效 |
| Python/格式化/YAML | setup.py 的 ruamel.yaml、flatten_dict、tabulate；test_requirements 的 pytest6.2.3/mock3.5.1 | grader Python3.9.19 与这些模块的测试链可用 | actor 先 import dvc.command.metrics，再 collect-only 窄测试；不要借 grader 前缀可写权代填 actor |
| 本地输入与临时目录 | prompt 的两行数值；func test_show 非登记 target/no_repo | 不需要训练模型、S3数据或用户资产；本地文件可合法生成 | actor 的临时目录/工作区写权限待验；用显式 target 跑原例默认/8 |
| fixture/工具 | dir_helpers；根 conftest 和 remotes 顶层 imports | DVC repo 本地创建，窄 F2P 不启动 Docker/远端 | 预装收集依赖不可少；无必要新服务；扩展分支功能测试才需 Git 身份等 |
| 安装/编译/网络 | setup.py 无本题新增依赖；recipe after:10–16 | grader 从固定 wheelhouse 离线安装完成；改动是 Python 参数转发，无新增编译步骤 | 准备阶段需固定历史依赖；解题/测试无业务联网要求；不假定 actor 可公网 pip install 或可写系统包 |
| 提交文件 | gold 只改 dvc/command/metrics.py；test patch 只改一个测试文件 | 账本该源文件被投影，GL/NL 恢复该测试文件 | 原 source 合法可交付；additional_exclusions=[]。未审其它实现的所有文件形态 |
| 最小公开验证 | 旧 helper precision test + 真实 CLI 原例 | helper P2P 已历史执行 | actor: DVC_TEST=true python -m pytest -q tests/unit/command/test_metrics.py；无私有 test patch 时其通过不检出 CLI 漏传，故仍要原例比较 |

未发现本题 test patch 混普通源码、必须改官方恢复文件、需要不可提交系统编辑或题目特有控制面规则。未做平台总安全审计；真实镜像 Git、缓存、可见 mount 与未来答案泄漏仍待 actor 验证。公开包没有 .git 不能代替真实 Git 清理验收。没有据同仓库/同文件建立题族；尚未开放后两题，不作跨题推论。

## 7. 八方面结论与暂定处置

1. 公开需求：已结合题面、帮助、旧测试澄清普通小数位；科学记法例文笔误保留，真实消息未知。
2. 材料/初态：S2行、精确base、补丁、日志/recipe hash相符；原始 no-op 失败位置对应漏传；本轮未执行 CLI 原例。
3. 测试目标：已逐条追全部变更与 1 F2P、读完21 P2P；命令层单值+空结果 mock 的覆盖有限。
4. 合理解接受：关键字转发是合理非gold形式；spec 与历史 gold 证明不拘位置/关键字；更大行为等价重构的内部耦合风险未实验。
5. 回归/gold：已读相关默认调用者、展示/读取边界；gold静态符合范围且历史参考全过；未证全部行为回归。
6. 开发条件：历史 grader 安装已修且证据完整；actor 配方、实际 shell、导入/可写与公开 CLI 未验。
7. 交付/评分边界：源码投影与单一官方测试恢复有原件；无新增排除；未做实际 actor 泄漏/控制面审计。
8. 关系/用途：无跨题关系结论；主审已见特权材料，仅 development_diagnostic，不能作未暴露 solver 输入。

暂定 disposition=needs_review，scope=static_review。语义/评分层保留“单值转发可能放过硬编码”的具体待验疑点；运行层另保留 actor 待验，不将二者混为坏题/环境失败。没有已确认 gold 缺陷或拒绝题目依据。唯一优先下一步为第4节固定输入的 base/gold/硬编码候选 CPU 对照；历史开放后另写 old_findings_delta，不回写本稿。

