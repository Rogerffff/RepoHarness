# 第3类 → 第2类交接清单（11 题，09-30 续接后追加）

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
| SWE pydantic-8567 | R-c v4 `7014f5fc…`（熔断收口，31 次诊断评分符合停止条件） | `upstream261`、`c3_reorder`（独立核实，范围差异见下） | v4 待 Codex 确认（熔断规则）；B03 不断言的取舍；正对照范围差异随交接保留 |
| SWE dask-8801 | v5 `59293680…`（v4＋B2 修正＋词表调整；41 次诊断评分与复核预期一致） | gold | **须处理**：`rv_enum_types`（`1.5` 实例）、原因判定的设计、`wr_null_raises`、`wr_perm_fatal`（v5 下仍为 1）；R-f 新公开读者验收 |
| SWE dask-7305 | R-b/R-c v2 `6e96caa7…`（27 次诊断评分符合预期） | `gold_full`（主）、`exact_full`、`higher_full`（独立核实，限公开大整数范围） | `npartitions="auto"` 路径三份正对照都丢 1 行（范围外，须登记处置）；v2 聚焦复核由第2类承接 |

**09-30 续接后追加**（Codex 复核时列为“继续完成诊断”，之后完成作者诊断与独立复核）：

| 题目 | 采用版本 | 可信正对照 | 重要余项（修好后才能按用途验收） |
| --- | --- | --- | --- |
| SWE moto-6185 | R-c v3 `fc65a527…332d`（v2s 路线＋复核 B2、B3 实例；只有私有模拟） | `ctx`（主）、`parity`（独立核实）；gold 失败按 D4 留档 | 第2类落地后做一次正式诊断评分，与复核 v3 列逐格一致即完成；登记项见条目 |
| SWE pydantic-8316 | R-c v3 `b248daa2…81e0`（复核草案；34 格诊断评分与复核预期逐格一致） | gold；`keep_digit`、`upstream_main`（两种数字读法） | 数字边界登记为 gold 的范围外行为变化（新旧都接受，不属 P5）；T3 阈值余量只登记 |
| R2E pillow__a682ceaf | R-c v2 编辑块 `21581578…`（复核草案，隐藏测试 `3573f459…`，93 键不变；只有私有模拟） | gold；`alt_typeerror`、`r_kwtuple` 等合理实现 | 第2类在 R2E 正式评分链上跑一轮，与复核 h4 列一致即完成；`pytest.warns` 保留 |

**09-30 用户决定后转入**：

| 题目 | 采用版本 | 可信正对照 | 重要余项（修好后才能按用途验收） |
| --- | --- | --- | --- |
| SWE dask-9378 | 用户选 B：路线不限的 mask 测试（规格见条目；补丁由第2类起草） | gold；`toplevel_only`（只修顶层，经 B 规格应为 1） | 按规格起草并验收；题面不改，R-f 草案作废 |
| R2E coveragepy__f5eb5f21 | 用户选 A：R-b v3（复核者 `test_1_rb3h.py`＋`expected_rc3.json`，8 键） | gold、A1；C1（上游 5.1 写法）在 R-b v3 下应为 1 | 第2类正式评分逐键与复核“R-b v3”一列一致即完成 |

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

- **公开目标**：Annotated 中的 serializer 无论在 `PlainValidator` 前后、与它相隔几个元数据都生效（Python 与 JSON 输出，可复用于 `TypeAdapter`）；PV 取代它左侧的全部验证与约束；PV 两侧都有 serializer 时外层生效（base 行为）；保留“普通类＋`PlainValidator`”接管 pydantic 无 schema 类型的公开能力。
- **采用版本**：[`revised_test_v4.patch`](../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v4.patch)（`7014f5fc…`），即 v3 聚焦复核的 `t_v4`（逐字节相同）。
  - v3 聚焦复核发现 3 项阻断（B1 左侧约束被挪到 PV 外层；B2 serializer 与 PV 之间夹元数据；B3 两侧 serializer 时改用内侧）。B1 与首轮阻断 `rv_pv_first` 属同一状态边界，连续两轮新阻断，按协作协议 §5 熔断；
  - 按熔断规则，v4 交 Codex 确认，不再开新一轮 Claude 复核。
- **诊断评分（v4，31 次，与复核停止条件逐项一致）**：
  - `upstream261`、`c3_reorder`、`rv_condwrap` 与复核者 5 个合理实现（含上游 2.10 写法的回移 `ok_up210`）为 1；
  - noop、gold（只在未知类型处失败，D4）与 22 个已知错误候选为 0，reward 与失败行号全部吻合；P2P 158/158（`rv_before_sem_rebuilt` 除外，它本来就弄坏一项 P2P）。
- **重要余项**：
  - Codex 确认 v4；
  - 正对照的范围差异必须随交接保留：`upstream261` 在 B06、B07、B08、N3 上与 base 不同（B06、N3 是它自身的已知回归，不能当参考）；`c3_reorder` 在 A16、A17 上不修；`ok_wrapshim` 不作正对照；
  - B03（生成不了 schema 的类型、serializer 放在 PV 前）不断言，理由见题页 §5：`upstream261` 在此与 base 相同，断言会把“在注解层修”定为唯一路线；若协调者仍要求覆盖，正对照只能保留 `c3_reorder`；
  - 固定等效派生镜像的 wheel 清单；actor 条件未验。

### SWE dask-8801

- **公开目标**：顶层不是映射的配置文件，以及 YAML 语法错误的配置文件，都要在读取处报错，报错点名出问题的文件并说明原因；包括新进程 `import dask`（P5 第一分支，R-f 补明）；空文件与全注释文件照常加载；读不到的条目照常跳过。
- **采用版本**：v5 = v4 ＋ 聚焦复核 B2 的修法 ＋ 原因词表调整，即复核者私有验证过的 v4rvb（逐字相同）。
  - v4：[`revised_test_v4.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v4.patch)（`91baa55d…`），正式诊断评分 23 次符合当时预期；
  - v5：[`revised_test_v5.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v5.patch)（`59293680…`）。
- **诊断评分（v5，41 次，与聚焦复核预期逐项一致）**：
  - gold、作者 6 个与复核者 7 个合理实现为 1（含原被词表误拒的 `ok_object_value`、`ok_map_settings`）；灰区 `gr_attr_wrap` 为 1；
  - noop、2 个另一政策候选、12 个作者／首轮复核错误候选、聚焦复核者 7 个错误候选（含 B2 的 `wr_zip_misalign`、`wr_zip_misalign_orempty`、`wr_all_files`）为 0；`gr_basename_only`、`gr_csafe_loader` 为 0；
  - **`wr_null_raises`、`wr_perm_fatal` 仍为 1**，列入下面必须修的项。
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
- **采用版本**：R-b/R-c v2 [`revised_test_v2.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask7305/revised_test_v2.patch)（`6e96caa7…`），即独立复核的两行补充（300 行相邻大 uint64、3 进 5 出分区；全负大 int64）。v1（`d3f78c2c…`）不能当作充分验收。
- **诊断评分（v2，27 次）**：`gold_full`、`exact_full`、`higher_full` 与复核者 4 个合理实现为 1；noop、gold（`issue_1to3`，D4）、作者 10 个错误或不完整候选与复核者 8 个错误候选为 0；v1 放过的 `rv_pin_noclip`、`rv_interp_pin_noclip`、`rv_k_le4` 停在相邻值一行，`rv_maxonly_threshold` 停在全负 int64 一行。
- **正对照（D4，独立复核核实）**：`gold_full`（主）、`exact_full`、`higher_full`。核实范围是公开要求的 numpy 大整数；扩展 dtype 与 `npartitions="auto"` 路径不在核实范围内。
- **已证错误候选**：
  - 原测试：`nearest_via_float`（正式）与 `rv_interp_pin_noclip`、`rv_swallow_int64`、`rv_k_le4`（私有模拟）得 1。合理实现被误拒：作者的 `exact_full`、`higher_full`（正式），以及复核者 4 个中的 3 个（私有模拟）；
  - v1：`rv_pin_noclip`、`rv_interp_pin_noclip`、`rv_maxonly_threshold` 为 1，另有构造性较强的 `rv_k_le4`；
  - v2 下全部为 0（正式诊断评分，09-30）。
- **重要余项**：
  - `npartitions="auto"` 路径上，gold 与三份正对照都丢 1 行。它不在题面示例的调用方式内，但属于同一“行进自己的区间”要求：由第2类判断是否纳入，或写明边界理由；
  - v2 的聚焦复核由第2类承接（Codex 建议）；
  - base 上“丢行”只发生在默认 disk shuffle，`shuffle="tasks"` 时行不丢但落在区间外（题页 §2 已补）。
- **正式落地前置**：D6 测试补丁替换。

### SWE moto-6185（09-30 追加）

- **公开目标**：`put_item` 的条目中任何位置（顶层、任意深度的嵌套 map、list 内的 map）名为 `S` 的属性都能写入并等值读回，对表的主键名没有限制；名为 `S` 的属性不影响其它属性的类型校验；关闭 SDK 参数校验时，服务端对所有属性照旧拒绝 `S` 值为 int 或 map（base 公开旧行为，`test_put_item_wrong_datatype` 同类断言）。
- **采用版本**：[`revised_test_v3.patch`](../../../../../rh2/experiments/category3_cloud_20260929/moto6185/revised_test_v3.patch)（`fc65a527…332d`），由独立复核起草；材料 [`materials_revised_v3.json`](../../../../../rh2/experiments/category3_cloud_20260929/moto6185/materials_revised_v3.json)（版本 `c3-moto6185-nested-s-v3`）已备好。父版本 v2s（`4122cced…`，正式诊断评分 14 次）、v2（`7bbae287…`，正式诊断评分 14 次）留档。
- **证据层级**：v3 只有复核者的私有模拟（22 个版本，root；gold、`ctx`、`parity` 另以 UID 54322 复跑 F2P）。v3 相对 v2s 只加数据行；此前原材料、v2、v2s 的 42 格私有模拟与正式评分逐格一致。
- **v3 私有模拟**：`ctx`、`parity`、`ctx_list`、`rv_dynamotype` 为 1；noop、gold（主键名 `M` 一例）、作者 9 个与复核者 7 个错误候选为 0，各停在预期断言。
- **已证错误候选**：
  - 原测试放过：`top_only`、`siblings`、`depth2`、`list_as_names`、`swallow`、`skip_s_subtree`、`rootkey`（正式），以及复核者的 7 个（私有）；
  - v2 放过 gold 两处缺口、`rootkey`、`rv_shape_key` 等；v2s 放过 `rv_depth4`、`rv_tagparent`。
- **重要余项**：
  - D6 落地后做一次正式诊断评分（候选清单与预期见题页 §5 v3 小节），逐格一致即完成，不再聚焦复核；不一致只定位那一格；
  - 只登记、不再阻断：深于五层嵌套的阈值写法；除 `S` 以外“属性名恰为类型标签”的畸形组合；base 本来就不校验的输入；服务器模式的 HTTP 状态码；真实 AWS 的确切文案；
  - actor 条件、真实 AWS 行为未验；上游到 5.2.3 与 gold 写法相同（只作佐证）。
- **正式落地前置**：D6 测试补丁替换；install_wave1 派生镜像（云端等效重建，三个 wheel 摘要已核）。

### SWE pydantic-8316（09-30 追加）

- **公开目标**：`to_snake` 在缩写与后接单词之间断开，不限缩写长度、个数、位置、串长，串中含非 ASCII 字母（不在断开边界上）时同样适用；保留 17 个旧参数的大小写、数字、下划线行为与末尾缩写的拆分（`parseURL → parse_url`）。
- **采用版本**：[`revised_test_v3.patch`](../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/revised_test_v3.patch)（`b248daa2…81e0`），由独立复核起草，v2 的 7 条断言原样保留、追加 4 条；材料 [`materials_revised_v3.json`](../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/materials_revised_v3.json)（版本 `c3-pyd8316-acronym-position-v3`）。父版本 v2（`f0b7b090…`，诊断评分 22 次）留档。
- **诊断评分（v3，34 次，与复核预期逐格一致）**：gold、作者 5 个与复核者 4 个合理实现为 1；noop、作者 15 个与复核者 8 个错误候选为 0。v2 放过的 7 个（`acr_max5`、`w_acr_max8`、`w_count2`、`w_window8`、`w_len_cap`、`w_mid_underscore`、`w_skip_nonascii`）停在 v3 新增的断言上。
- **重要余项**：
  - 数字边界（gold 让 `A1 → a1`、`fieldV2` 的 alias 变为 `field_v2`）：不断言、不属 P5，登记为“gold 的范围外行为变化，新旧数字行为都接受”；探针与事后审计中两种都不算错，也不算额外的语义正确；
  - 只登记、不再阻断：缩写长度上限 ≥ 13、个数上限 ≥ 3、起点窗口 ≥ 20、串长上限 ≥ 30；单字母词、两个缩写相连、复数缩写、非 ASCII 字母处在断开边界、kebab-case；
  - 复验时建议把复核者的 12 个候选一并纳入（`rv_tokens`、`rv_scan_gold` 能同时检查两类未规定行为没有被误拒）；
  - 固定等效派生镜像的 wheel 清单；actor 条件未验；Codex 复核。
- **正式落地前置**：D6 测试补丁替换；pydantic_v1 派生镜像（云端等效重建）。

### R2E pillow__a682ceaf（09-30 追加）

- **公开目标**：`info["transparency"]` 是元组、分配不到调色板项时，保存 GIF 不抛异常且不带透明度（任何这类图与颜色，含 `save_all=True`）；元组能用时仍保留透明度（与之前保存过什么图无关）；保存不改被保存的图的 `info`；保存时发出 UserWarning（base 行为与公开测试 `test_trns_RGB`、`test_rgb_transparency` 支持，不限文案）。
- **采用版本**：复核者合并草案 v2，编辑块 [`revision_draft_review_v2.json`](../../../../../rh2/experiments/category3_cloud_20260929/pillow_a682/review/materials/revision_draft_review_v2.json)（`21581578…`），修订后测试文件 `hidden_test_1_review_v2.py`（`3573f459…`）；期望映射不变（`a465b6c9…`，93 键）。父版本为作者 v1（`ff7a439c…` → `7f247bf4…`）。
- **证据层级**：R2E 在云端没有正式评分链，全部是私有模拟（运行评分包 `run_tests.sh`，逐键对照期望映射；上游口径与 RH2 生产口径 164 格逐格一致；关键候选以 UID 54322 复跑）。
- **v2 私有模拟**：gold、作者 4 个与复核者 3 个合理实现为 1；上游 10.1.0、10.4.0、11.3.0 通过；noop、作者 13 个与复核者 5 个错误候选、`q_prestrip` 为 0。
- **已证错误候选**：原测试放过作者 7 个触发反例（`w_literal`、`w_count256`、`w_notin_image`、`w_drop_full`、`w_drop_big`、`w_mutate`、`w_convert_mutate`）与复核者的 4 个；作者 v1 放过复核者的 `w_mutate_kept`、`w_nosaveall`、`w_order_cache`。
- **重要余项**：
  - 第2类在 R2E 正式评分链上跑一轮，与复核 review.md §3.2 表的 h4 列一致即完成，不再需要聚焦复核；最少跑 gold、`alt_typeerror`、`r_kwtuple`（期望 1）与 noop、作者 7 个触发反例、`w_mutate_kept`、`w_nosaveall`、`w_order_cache`、`w_filter_leak`、`q_prestrip`（期望 0）；
  - `pytest.warns` 保留；有意去掉警告的写法得 0，写进题卡的训练价值备注；
  - 只登记、不再阻断：只在多于 256 色的图上改调用者 `info`；只在示例以外的路径去掉警告；关键字元组、`getdata`、RGB 整数透明度、RGBA 或 P 图带元组；GIF 版本号；其它解码器；
  - X1（同仓 6 道 R2E pillow 题的修复都在本题工作树的祖先里）、E3（来源镜像 `.git` 含修复提交对象，派生镜像已清理）；
  - Codex 复核修订条目。
- **正式落地前置**：R2E 材料修订一条（`hidden_test_text_replace`），出新 pins、重建派生镜像。

### SWE dask-9378（09-30 用户选 B 后转入）

- **公开目标**：`ones_like`、`zeros_like`、`empty_like` 在 masked dask 数组上按 numpy 的方式逐元素保留 mask。题面用顶层 `da.ones_like` 展示问题，新增 `dask.array.ma.*_like` 只是题面建议的路线，不是唯一要求（用户 09-30 选 B）。
- **采用版本（规格，补丁由第2类起草）**：在 R-c v1（[`revised_test_v1.patch`](../../../../../rh2/experiments/category3_cloud_20260929/dask9378/revised_test_v1.patch)，`67393733…`）的 `test_like_funcs` 上改为：`da.ma` 下若有该函数，它必须逐元素保留 mask（`getmaskarray` 比较；ones／zeros 另保留原 `assert_eq`）；没有时，顶层 `da.<name>` 必须逐元素保留 mask。测试编号不变；题面不改。
- **预期**：noop 0；gold 1；`toplevel_only` 1；`ma_mask_none`、`ma_mask_invert`、`invert_values7` 0；复核者自写的非 gold 正确实现 1。候选补丁在实验目录 `dask9378/`。
- **重要余项**：起草补丁并按预期私有与正式复验；R-f 草案作废；Codex 复核。
- **正式落地前置**：D6 测试补丁替换。

### R2E coveragepy__f5eb5f21（09-30 用户选 A 后转入）

- **公开目标**：开启分支覆盖时，JSON 报告的 `totals` 带 `covered_branches`、`missing_branches`，按被报告的文件汇总（多文件累加、零分支时为 0、`--include` 子集只算被报告的文件）；行模式不出现分支键、不另加其它新键；每文件 `summary` 可以带这两个计数，但必须成对且为本文件自己的值（用户 09-30 选 A）。
- **采用版本**：R-b v3，复核者的 `rh2/experiments/category3_cloud_20260929/cov_f5eb/review/materials/test_1_rb3h.py`（`fd4d6ac9…`）与 `expected_rc3.json`（`e150a338…`，8 键）；落地时可直接用复核者文件，或在作者 `_build_materials.py` 的 v2 条目上做逐字等价的改动。
- **证据层级**：全部为私有模拟（R2E 在云端没有正式评分链）。
- **R-b v3 私有模拟**：gold、A1、C1、`rv_sym_xml` 与复核者 3 个合理实现为 1；noop 与全部 19 个错误候选为 0（NB 只错 K4；`wr_alldata_proj`、LF 只错 K3；C3 只错 K2）。
- **重要余项**：第2类登记修订、出新 pins、重建派生镜像后正式评分，逐键与复核 review.md §4 表“复核 R-b v3”一列一致即完成，不再做聚焦复核；R2E 线准入卡改写（多文件、零分支改为已覆盖；LF、FC、NB、`wr_alldata_proj` 登记为负对照）；Codex 复核修订条目。
