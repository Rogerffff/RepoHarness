# 第3类 → 第2类交接清单（11 题）

2026-09-30 / Claude（云端，第3类负责人）。依据：各题 `tasks/<id>/result.md` 与归档证据，以及 Codex 09-30 独立复核（[总报告](../category3_cloud_review_20260930/README.md)、[接续反馈](../category3_cloud_review_20260930/claude_feedback.md)）。

## 这份清单是什么

- **转第2类的含义**：公开目标已足够明确，已证问题有可执行的修法与验收办法，可以开始落实修复。
- **不含义**：修订已验收、正式材料已落地、可以进普通探针或训练。本清单没有任何题转第1类，也不授予训练资格。
- **接收方**：第2类线程（按本目录 README 的分工，由本地 Codex 负责）。正式接收时请在第2类记录中写明接收人与接收的题目版本；只改类别标签不算交接完成。
- **第2类要完成的共同事项**：
  1. 按所列版本正式落地修订材料；
  2. 在正式评分身份下复验所列的正确与错误候选；
  3. 核对真实 actor 开发条件；
  4. 处理每题“重要余项”，修好后再按用途验收。
- **D6 现状**：已验收的首片只有 `append_mypy_p2p`。下文需要的“测试补丁替换”“参考分组调整”“`statement_replace`”都是已获总体授权、尚未实现的后续实施项。本页所有修订版分数都是 `--materials` 诊断评分或私有模拟，不等于正式 actor 已消费修订版。
- **证据层级**：“正式”指 `replay_grade.py` 正式评分链（UID 54322、deny_all）；“诊断”指同一链路加 `--materials` 的修订版诊断评分；“私有”指 root 或 nobody 一次性容器中的私有对照或私有模拟评分。

## 总表

| 题目 | 采用版本 | 可信正对照 | 重要余项（修好后才能按用途验收） |
| --- | --- | --- | --- |
| SWE conan-14177 | R-c/R-b v2 `ee614041…2d8c` | `pubcand`（独立核实） | 参考分组：`test_single_patch_description` 在 base 已通过，改列 P2P；`output_verbose`、仅关键字参数两处边界由 Codex 定 |
| SWE moto-7584 | R-b/R-c v3 `58875207…4fd3` | `stmt`（独立核实）、`stmt_arnmsg` | 生命周期与协议正例须保留；`aws_verified` 标记处理 |
| SWE pydantic-9066 | R-c v1 `73d97a37…` | `fallback`（独立核实）、`upstream271` | 回归检查所属参考组（宜独立成 P2P）；固定等效派生镜像的 wheel 清单 |
| SWE dvc-9395 | R-b/R-c v4 `2f6ac1be…` | `c3_frozenfix`（独立核实）；`up351_port` **不能**无条件作第二正对照 | **4 组已证缺陷须补验收**：冻结 stage 必需输出、dry 无副作用、无需下载时的无 remote 与 HTTP run-cache 恢复、`--no-run-cache` 等回归；compat-wheels 正式复验 |
| R2E pillow__3a61c9e9 | R-c v2 隐藏测试 `78631c73…`＋74 键期望 | C1（主）、U11（独立核实） | 固定正式 C1 的实际字节；准入卡改 gold／A1u 期望 |
| R2E coveragepy__016af5f6 | R-c v2 隐藏测试 `ccdd7d89…`＋窄 R-f 题面 | 6 个合理实现（跳过 4、转换 2） | 修订题面须由新公开读者验收；不得追加告警、报告或其它异常约束 |
| R2E coveragepy__5dbbe143 | 用户 09-29 选定 A：修订题面 `b2a7f5fb…`＋隐藏测试沿用 v5 | gold、CE3 | 标明自建题面版本；同步旧题卡与看板；原 CE 与重建 CE 分开复验 |
| SWE conan-13403 | R-e/R-b/R-c v4 `2f55ba31…`（熔断收口） | gold；13 个合理实现 | v4 待 Codex 确认（熔断规则）；GNU 工具链端到端与 actor 未验 |
| SWE pydantic-8567 | R-c v3 `4600867b…` | `upstream261`、`c3_reorder`（独立核实，范围差异见下） | 聚焦复核结论待并入；`c3_serpass`、`rv_ser_to_end` 两个边缘项须给处置 |
| SWE dask-8801 | v5（v4＋B2 修正＋词表调整，正式诊断评分进行中） | gold | **须处理**：`rv_enum_types`（`1.5` 实例）、原因判定的设计、`wr_null_raises`、`wr_perm_fatal`；R-f 新公开读者验收 |
| SWE dask-7305 | R-b/R-c v2 `6e96caa7…`（正式诊断评分进行中） | `gold_full`（主）、`exact_full`、`higher_full`（独立核实，限公开大整数范围） | `npartitions="auto"` 路径三份正对照都丢 1 行（范围外，须登记处置）；v2 聚焦复核由第2类承接 |

首批中 **dask-9378 暂不交第2类**：`da.ma` 新 API 是否为唯一目标仍需选择，见[题页](tasks/dask__dask-9378/result.md)。

## 逐题交接

### SWE conan-14177

- **公开目标**：`apply_conandata_patches(conanfile, verbose=False)`；`verbose=True` 时逐个记录实际应用的补丁；缺省与 `verbose=False` 的输出不变；补丁真实应用。
- **采用版本**：[`revised_test_v2.patch`](../../../../../rh2/experiments/category3_cloud_20260929/conan14177/revised_test_v2.patch)（`ee614041…2d8c`），父版本 v1 `51c9bd79…`。
- **诊断评分（v2）**：`pubcand`、`probe_post`、`probe_abspath`、`probe_merged`、`probe_header` 为 1；noop、gold、`gold_log_only`、`always_log`、`never_log`、`print_only`、`output_verbose`、`probe_basename`、`probe_kwonly`、`probe_logonly_v` 为 0。
- **重要余项**：
  - `test_single_patch_description` 在 base 就通过，v2 撤回原 test_patch 对它的修改；正式落地时把它从 F2P 移到 P2P（需要 D6 的参考分组调整）。
  - `output_verbose`（用 `ConanOutput.verbose()`，默认等级下不可见）与 `probe_kwonly`（仅关键字参数）两处边界判 0，依据写在题页 §4，请 Codex 在落地前确认。
- **正式落地前置**：D6 测试补丁替换与参考分组调整。

### SWE moto-7584

- **公开目标**：题面生命周期（有效 application 端点订阅成功 → 删除端点 → 再订阅报 `InvalidParameter`）、从未存在的端点同样报错；非 application 协议照常订阅。
- **采用版本**：[`revised_test_v3.patch`](../../../../../rh2/experiments/category3_cloud_20260929/moto7584/revised_test_v3.patch)（`58875207…4fd3`）。
- **诊断评分（v3）**：`stmt`、`stmt_arnmsg` 为 1；noop、gold（D4 记录失败）、`gold_order_stmtmsg`、`reject_all_application`、`reject_all_arnmsg`、`wrong_code`、`all_protocols`、`deleted_set`、`arn_form` 为 0。
- **重要余项**：
  - 修订后的 F2P 仍带 `@pytest.mark.aws_verified`，新增断言没有在 AWS 上验证过：去掉标记，或把新增部分拆到无标记测试；
  - 可选：正文检查收紧为正则；补一条“有效端点重复订阅返回同一 ARN”。
- **正式落地前置**：D6 测试补丁替换；install_wave1 派生镜像（云端等效重建，三个 wheel 摘要已核）。

### SWE pydantic-9066

- **公开目标**：IPv4 等默认值的 schema 输出正确，且不破坏标准库 dataclass 默认实例的 schema 生成（base 已支持）。
- **采用版本**：[`revised_test_v1.patch`](../../../../../rh2/experiments/category3_cloud_20260929/pydantic9066/revised_test_v1.patch)（`73d97a37…`）。
- **诊断评分（v1）**：`fallback`、`upstream271` 为 1；noop、gold（D4）、`gold_catch_user_error` 为 0。
- **重要余项**：
  - dataclass 回归检查目前嵌在 F2P 里；它在 base 上本来就成立，不应称为新目标。宜独立成 P2P，需要 D6 支持新增参考；
  - 修订测试注释里的 “documented BaseModel + stdlib dataclass usage” 改为不声称有文档；
  - 正对照范围：两条路线都通过，但不代表在所有 API 组合上等价；
  - 派生镜像为云端等效重建，入库时固定 wheel 清单并登记来源。

### SWE dvc-9395

- **公开目标**：`dvc repro --pull` 拉取“all missing files”“whatever is missing and necessary for this repro”；数据源包含 `dvc add` 与 `dvc import`；用户修改过的数据保留修改。
- **采用版本**：[`revised_test_v4.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dvc9395/revised_test_v4.patch)（`2f6ac1be…`）。
- **私有模拟（v4，16 个候选）**：`c3_frozenfix`、`up351_port`、`c3_missing_only` 为 1，其余 13 个（含 gold 与 6 个吞错候选）为 0。**第三项是已证漏判，不是可接受结果。**
- **主正对照**：`c3_frozenfix`（`94d44848…`），主体由前一复核者核实，冻结条件由复核者写、主审用独立场景核实；198 项公开测试结果与 base 相同。
- **重要余项（Codex 09-30 复核，均须处理，不能以熔断、“少见”或“主正对照能过”核销）**：
  1. **冻结 stage 的必需输出**：`c3_missing_only` 不恢复下游必需的冻结 stage 输出，v4 仍给 1。修法：把现成的 C1／C2 场景改为窄行为验收——冻结 stage 的缓存与工作区输出都删掉，下游 repro 所需数据要从 remote 恢复，且不执行冻结命令；预期 `c3_missing_only` 为 0、`c3_frozenfix` 为 1。目录“部分删除算缺失还是修改”仍属 P5 歧义，不直接补断言。
  2. **dry 无副作用**：`up351_port` 在 `--pull --dry` 下下载或写回（B1／B1b／B1c 场景），v4 仍给 1。修法：沿现成场景比对 workspace、对象 cache、runs 目录前后状态，且不执行 stage 命令。未处理前，`up351_port` 不能作满足最终验收的第二正对照。
  3. **无需下载时的无 remote 行为，以及 HTTP 上已有的 run-cache 恢复**（B2／B2b、B4b 场景）：base 成功、gold 式实现失败。沿固定场景确认所用公开能力与失败归因，再纳入行为断言并写明候选预期；确实需要下载却无 remote 时，不能把应有的错误改成成功。
  4. **其它已记录回归**：`--no-run-cache` 仍下载 runs、已存在的无 hash 输出被误删、依赖已变且旧输出不可得时阻断可重算路径（B5／B6／B9）。逐项处理，或给出基于公开行为的边界理由。
- **正式落地前置**：D6 测试补丁替换；09-19 dvc_tail_v1 的 compat-wheels（云端没有重建，本题只有私有模拟，须在本地正式复验）。

### R2E pillow__3a61c9e9

- **公开目标**：RGBA 调色板经恒等映射后保持不变；整数透明索引随映射移动（公开 `Tests/test_image.py:612`）。
- **采用版本**：R-c v2，[`hidden_test_1_revised_v2.py`](../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/hidden_test_1_revised_v2.py)（`78631c73…`）与 74 键期望 `expected_output_revised_v1.json`，接在材料 v5 之后。
- **私有模拟（v2）**：C1、U11、G_del、G_cim、HYB、G_gif 为 1；base、gold、A1u 与 W1–W5 为 0；首轮漏过的 G_small 为 0。
- **重要余项**：
  - 保存 v4→v1→v2 的版本链与 74 键期望；
  - 正式复验 noop、gold、A1u、W1–W5、C1、U11、G_small、HYB、G_gif；
  - 正式评分过的原 C1 补丁与本页重建版未逐字核对，固定实际使用的字节与摘要；
  - 准入卡的 gold／A1u 期望要改，不能沿用 v4 的训练资格；
  - 元组背景路径（N2–N4）登记为 T3，理由是文档未规定。
- **正式落地前置**：R2E `hidden_test_text_replace`＋`expected_file_replace`；R2E 派生镜像。

### R2E coveragepy__016af5f6

- **公开目标**：不可编码的文件名不导致崩溃，同时保留同一次测量中正常文件的覆盖数据。
- **采用版本**：R-c v2 [`hidden_test_1_revised_v2.py`](../../../../../rh2/experiments/category3_cloud_20260929/cov016/hidden_test_1_revised_v2.py)（`ccdd7d89…`）＋窄 R-f [`revised_statement_v1.txt`](../../../../../rh2/experiments/category3_cloud_20260929/cov016/revised_statement_v1.txt)（只补 import、把原 exec 移进测量区间、改正注释）。
- **私有模拟（v2）**：6 个合理实现（跳过 4 种、转换 2 种）为 1；noop 与 7 个错误候选为 0。
- **重要余项**：
  - 修订题面须由未看隐藏测试与 gold 的新公开读者验收；
  - 不得以 “gracefully” 为由追加告警、`report()` 成功或吞掉所有异常等约束；
  - `source=` 未执行文件、直接 CoverageData API、不可编码 context 不在题目要求内。
- **正式落地前置**：R2E `hidden_test_text_replace`＋`statement_text_replace`。

### R2E coveragepy__5dbbe143

- **公开目标**：按用户 09-29 的 A 决定——同一 slug 即使 message 不同也只显示第一条，不同 slug 各显示一次。这是**自建题面版本**，不是原题唯一读法。
- **采用版本**：修订题面 [`revised_statement_A.txt`](../../../../../rh2/experiments/category3_cloud_20260929/cov5dbbe/revised_statement_A.txt)（`b2a7f5fb…`）＋隐藏测试沿用现行材料 v5；新公开读者已验收（`tasks/coveragepy__5dbbe…/public_read_revised_A.md`）。
- **私有模拟**：gold、CE3 为 1；CE1、CE4、noop 为 0。CE 系列是重建补丁。
- **重要余项**：
  - `statement_text_replace` 落地，固定新题面摘要；
  - 同步本地题卡与看板上的 on_hold 状态与用途；
  - 正式复验 gold、noop 与**原** CE1／CE3／CE4，与重建版分开记录；
  - 保留边界：once 之后的非 once、`slug=None`、跨实例都没有新增判据。

### SWE conan-13403

- **公开目标**：`autoreconf` 可指定执行目录，语义同 `configure` 的 `build_script_folder`；缺省仍用 source 目录；`args` 照常生效；目录切换是临时的；命令失败照常报错。
- **采用版本**：[`revised_test_v4.patch`](../../../../../rh2/experiments/category3_cloud_20260929/conan13403/revised_test_v4.patch)（`2f55ba31…`），即 v3 聚焦复核的 `v3_fix_plus`。
  - v3 聚焦复核发现 2 项新阻断，一项由 v3 自身的修改引入，触发协作协议的修复循环熔断；
  - v4 按复核者的根因分析重写失败检查，只检查行为：有异常、失败命令只在所选目录执行一次、调用者目录恢复；
  - 按熔断规则，v4 交 Codex 确认，不再开新一轮 Claude 复核。
- **诊断评分（v4，41 次）**：
  - gold 与 13 个合理实现为 1；
  - noop 与 25 个错误或边界候选为 0，每个 0 都停在针对它的断言上；
  - `w3_code_unrelated` 为 1：拿到失败码后抛出无关的 `TypeError`，构建仍被中断。它满足“命令失败时照常报错”，测试按设计不锁文案，判为可接受边界；
  - 结果与聚焦复核写明的停止条件逐项一致。证据在 `tasks/conan-io__conan-13403/evidence/rerun_0930/formal_revised_v4/`。
- **重要余项**：
  - Codex 确认 v4；
  - 真实 GNU 工具链端到端（镜像里没有 autoreconf）与 actor 条件未验；
  - gold 的位置参数回归维持 S2（仓内没有位置调用），修订版不锁参数顺序。

### SWE pydantic-8567

- **公开目标**：Annotated 中的 serializer 无论在 `PlainValidator` 前后都生效（Python 与 JSON 输出，可复用于 `TypeAdapter`）；保留“普通类＋`PlainValidator`”接管 pydantic 无 schema 类型的公开能力。
- **采用版本**：[`revised_test_v3.patch`](../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v3.patch)（`4600867b…`）。
- **诊断评分（v3，17 次）**：
  - `upstream261`、`c3_reorder`、`rv_condwrap` 为 1；
  - noop、gold（只在未知类型处失败，D4）、9 个作者错误候选与 `rv_pv_first` 为 0；
  - `c3_serpass`、`rv_ser_to_end` 为 1。
- **重要余项**：
  - **两个边缘候选须给处置**：`c3_serpass` 在 A08（serializer 与 PV 之间夹验证器）上漏修；`rv_ser_to_end` 只在 PV 两侧都有 serializer 时让内侧生效。首轮复核给过覆盖 A08 的可选断言（`AfterValidator` 放在 serializer 与 validator 之间）。云端的 v3 聚焦复核正在判断它们是否违反公开要求，结论出来后补入本条；
  - 正对照的范围差异必须随交接保留：`upstream261` 在 B06、B07、B08 上与 base 不同；`c3_reorder` 在 A16、A17 上不修；
  - 固定等效派生镜像的 wheel 清单；actor 条件未验。

### SWE dask-8801

- **公开目标**：顶层不是映射的配置文件，以及 YAML 语法错误的配置文件，都要在读取处报错，报错点名出问题的文件并说明原因；包括新进程 `import dask`（P5 第一分支，R-f 补明）；空文件与全注释文件照常加载；读不到的条目照常跳过。
- **采用版本**：v5 = v4 ＋ 聚焦复核 B2 的修法 ＋ 原因词表调整。v5 正式诊断评分正在进行，结果出来后补入本条。
  - v4：[`revised_test_v4.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v4.patch)（`91baa55d…`），正式诊断评分 23 次符合预期；
  - v5：[`revised_test_v5.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v5.patch)（`59293680…`）。
- **重要余项（Codex 09-30 与 v4 聚焦复核）**：
  1. **类型子集漏判**：`rv_enum_types` 只拒 list、str、int，v4／v5 下仍为 1；顶层 `1.5` 的文件直接作配置时，导入报 `AttributeError` 且不点名文件。修法：在非映射实例里加一个 `1.5`，预期它为 0，不必穷举全部 YAML 类型。
  2. **原因判定的设计**：v4 按 `dict/mapping/key/类型名` 词表判断；v5 放宽为 `dict/map/key/object/类型名`，放行了两个已知合理措辞。但这仍是词表，“expected an object／got a sequence” 一类合理说明仍会被拒。修法：先写明最低诊断行为（点名文件、确实失败、语法错误时解析器原因可见、已知错误仍被拒），再设计不依赖特定英文同义词的验收；用一个代表性的合理措辞检查修法。v5 只是缓解，不能写成“误拒已消除”。
  3. **显式 `null`／只含 `---` 的文件**：`wr_null_raises` 对它们报错，v4 下为 1。base 把它们当作空配置加载，与“空文件、全注释文件合法”同属一类公开行为。修法：在“加载结果为空”的检查里加一个显式 `null` 文件。
  4. **权限错误改成致命**：`wr_perm_fatal` 让不可读文件导致失败、其它 `OSError` 照常跳过，v4 下为 1。它违反公开测试 `test_collect_yaml_permission_errors`。可选修法：在非 root 的正式评分身份下加一个 `chmod 000` 文件实例；root 私有对照中这类检查不起作用，要写明身份依赖。
  5. **身份表述**：root 下完整 pytest 是 2 失败 43 通过，失败的是不在参考名单内的两项原权限测试。写作“按参考名单一致”，不写“root 全套通过”。
  6. **R-f 新公开读者验收**；复核建议把措辞改为 “the contents of a Dask configuration file cannot be used …”，避免把“读不到”理解为应报错。
- **正式落地前置**：D6 测试补丁替换＋`statement_replace`。

### SWE dask-7305

- **公开目标**：大整数输入下，`partition_quantiles` 返回精确的最小值与最大值，dtype 保持输入 dtype；`set_index` 把每行放进自己的 divisions 区间。不限单分区、不限 2**63 以下；有符号大整数也在内。
- **采用版本**：R-b/R-c v2 [`revised_test_v2.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask7305/revised_test_v2.patch)（`6e96caa7…`），即独立复核的两行补充（300 行相邻大 uint64、3 进 5 出分区；全负大 int64）。v1（`d3f78c2c…`）不能当作充分验收。v2 正式诊断评分正在进行，结果出来后补入本条。
- **正对照（D4，独立复核核实）**：`gold_full`（主）、`exact_full`、`higher_full`。核实范围是公开要求的 numpy 大整数；扩展 dtype 与 `npartitions="auto"` 路径不在核实范围内。
- **已证错误候选**：
  - 原测试：`nearest_via_float`（正式）与 `rv_interp_pin_noclip`、`rv_swallow_int64`、`rv_k_le4`（私有模拟）得 1。合理实现被误拒：作者的 `exact_full`、`higher_full`（正式），以及复核者 4 个中的 3 个（私有模拟）；
  - v1：`rv_pin_noclip`、`rv_interp_pin_noclip`、`rv_maxonly_threshold` 为 1，另有构造性较强的 `rv_k_le4`；
  - v2 草案下全部为 0（私有模拟）。
- **重要余项**：
  - `npartitions="auto"` 路径上，gold 与三份正对照都丢 1 行。它不在题面示例的调用方式内，但属于同一“行进自己的区间”要求：由第2类判断是否纳入，或写明边界理由；
  - v2 的聚焦复核由第2类承接（Codex 建议）；
  - base 上“丢行”只发生在默认 disk shuffle，`shuffle="tasks"` 时行不丢但落在区间外。题页 §1 要补这一句。
- **正式落地前置**：D6 测试补丁替换。
