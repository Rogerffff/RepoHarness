# pandas-dev__pandas-48106：独立复核

2026-09-21，B2 pandas reviewer，第二阶段。**建议保留受限静态候选：`state=needs_review`、`scope=static_review`、`intended_use=development_diagnostic`。** 同意主审对公开契约与修复后 grader 对照的基本判断；补充确认剩余两组 tz 节点身份合并。现有材料没有证明这两组导致错误 reward，也没有理由因一般覆盖未穷尽直接拒题。不是正式训练、评测或 actor 开发批准。

`ROOT=${REPO_ROOT}`；下文相对路径以 ROOT 为根。`I=runs/swegym_quality_batch02_20260921_v2`，`B=I/public/pandas-dev__pandas-48106/base`，`P=I/private/pandas-dev__pandas-48106`，`R=runs/env_recipe_repair_20260919/pandas_meta_v3`，`T=R/tasks/pandas-dev__pandas-48106`。第一阶段初判 SHA256 `fd89b2c4db4163a03e99d4d8cba2377422bd0352e4046e6f09d8ff132e47ed8a` 保持不变。三份初判统一封存后才读本题五份主审/公开产物、history/refs 和其唯一精确旧记录。仅静态文件、JSON、文本分析；没有项目导入、测试、安装、容器、网络、模型或 source/test/gold/reward 修改。

## 公开要求、断言及合理实现

核心期望明确：字符串 categorical Series 在新标签追加数值 0，保留原值且结果为 object，不能仅消除 TypeError。第一阶段已独立核 base `8b72297c8799725e98cb2c6aee664325b752194f`、`indexing.py:2082–2131 → maybe_promote`、CategoricalDtype 的 type 及 concat 路径，并逐项读 test.patch、全部 16 F2P 与 helper。主审的 4 方法/16 节点/30 次结果比较计数相符。

| 新测试组 | 全部关键观察量 | 公开依据及判断 |
| --- | --- | --- |
| 类别外 0，1 节点 | 完整 Series 等于 a,b,c,0，object dtype 和原标签保留 | 直接来自题面。 |
| 已有类别 a，1 节点 | 追加后的 Series 仍为 categorical，原类别和值保留 | 题面未单列，但最小承载 dtype、同类别 concat 和已有赋值规则提供合理依据。 |
| nullable 数值类别，10 节点 | UInt8/16/32/64、Int8/16/32/64、Float32/64：先扩容 NaN 比较，再对已有标签写 NaN 比较，保留相应 categories dtype | fixture 实际是 10 种，不是旧记录的 12。比较不止“不抛异常”。 |
| np.nan/pd.NA/None/pd.NaT，4 节点 | 扩容结果与原位设置结果比较，再与直接构造的 categorical 期望比较 | 第二层期望避免两条路径同错仍过。该相邻契约可从 categorical 缺失值规则与 dtype 保留路径推知。 |

同意主审撤回旧记录“只有 1/16 可从公开材料推出、其余方向冲突”的确定性结论。题面括号说明原例扩大时转 object，不能脱离例子扩成一律丢弃 categorical dtype；公开 `maybe_promote`、`categorical.py:1556–1592`、`categorical.rst:764–790,808–812`、已有 set-into 行为确实提供约束。仍保留推知边界：题面没有逐字承诺所有 EA/NA 组合，旧 base 的扩容行为也并非这些新增测试都已通过。不能为了迁就旧解释把实际 15 个 F2P 改称 P2P，或按 gold 分支直接补写一整套隐藏规则。

合理非 gold 实现可在缺失标签的 indexing 构造路径处理 categorical，结果正确即可；新断言没有 helper 名、调用顺序或精确内部异常文案要求。一律转 object 的自然部分修复能过主例，却会被其余类别保留检查拒绝；一律增新类别而保留 category 则违反原例。当前未找到有具体公开依据、语义完整却必被这些结果断言拒绝的替代解。Gold 仅添加 CategoricalDtype 限域分支，原调用者的 EA 分派和非类别路径没有被全局放宽；未见已证 gold 回归，不把全部 ordered/空类别/数值组合未测当成硬门。

## 原始执行、冻结参考与剩余身份合并

第一阶段已核 `T/{gold,noop}/ledger.jsonl` 各第 1 行及精确原日志。第二阶段重读原始 tz 摘要、Period 绑定审计和当前解析代码。`G=T/gold/eval_logs/evallog_replay-er19-pandas_meta__1160016c.eval.log`；`N=T/noop/eval_logs/evallog_replay-er19-pandas_meta__67b00d26.eval.log`。

| 集合或解释层 | 已证事实 |
| --- | --- |
| 实际执行 | `pytest -rA --tb=long pandas/tests/indexing/test_loc.py`，1045 collected；gold 1044 passed/1 xfailed；noop 1028 passed/16 failed/1 xfailed。 |
| 冻结参考 | 16 F2P + 1020 P2P，共 1036 个来源参考；与 1045 执行项不同。 |
| 显式绑定 | 输入 `R/reference_bindings_v1.json` 的本题对象仅含 3 个 Period 别名，共 7 个完整 node；两 run 的 recipe/reference_bindings.json 与实际 reference 审计对应。不是完整 node 映射，也不是增加 7 个独立评分项。 |
| 同一日志 original/revised 解析 | `.reference.json` 的 original 均少 3 P2P，gold RESOLVED_NO；revised 均 missing0/P2P1020，gold RESOLVED_FULL、noop 仍 RESOLVED_NO。original parsed=1037、revised parsed=1040 也都不是执行数或冻结参考数。不是两次重新执行。 |
| 历史最终评分 | 两 run 实际消费绑定后 noop F2P 0/16、gold 16/16；P2P 均 1020/1020，reward 0/1。旧“这题必然恒零”的结论对现有配方已过时。 |

当前 `reference_bindings.py:14–31,46–66` 要求绑定组所有成员有状态，再按优先级聚合；在合并修正前删除冻结 alias 的旧解析结果，成员缺席不能退回该 alias 的旧末值。两份 raw_node_states 的 7 个成员和原日志均为 PASSED，支持修复真实消费，不能仅凭 wrapper 名称或 bindings=true 推断成功。

主审历史后新增的两组 tz 合并属实，且**没有**列入上述 3 组 bindings：

| 冻结别名前缀 | 完整成员及原始证据 | 对照正文 |
| --- | --- | --- |
| `TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1,` | 同一负一小时时区，`var`/`idxer1` 共 2 例；G:5133–5134，N:6112–6113，全 PASSED | 新补读 `B/pandas/tests/indexing/test_loc.py:1430–1440`，保护浮点 DataFrame 的标量/列表列选择赋值。 |
| `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1,` | DataFrame/Series × None/指定末尾时刻，共 4 例；G:5691–5694，N:6654–6657，全 PASSED | 新补读 `test_loc.py:2239–2273`，分别比较普通切片和 loc 切片。 |

`conftest.py:444–449,1198–1238` 明确给出 DataFrame/Series 与 repr 含空白的时区 fixture；结合当前 `swegym_parsers.py:44–55` 的 split/后写覆盖，足以证实身份合并。它不等于已经发生错误计分。特别是 N:6966–6984 的真实摘要先 PASSED，再 XFAIL，最后列 16 个 FAILED；测试先失败后通过，并不能推出最后有效摘要也是 PASSED。主审对旧“只保留最后执行那条”的修正正确。

这些 tz 成员本次全部通过，保留历史 0/1。若以后只替换原 PASSED 位置制造一个 FAILED 文本再证明被后续 PASSED 覆盖，那仅是人为行序下的 parser 结果，不能代表真实 pytest 摘要和真实候选假阳性。同样，某成员无状态时 alias 仍可能存在是静态观察不足；是否对应允许的完整执行及实际错误分数还需区分 manager 的全局故障处理。

## 环境原件和当前接线

同意主审材料分层。输入为 `R/recipes/pandas-dev__pandas-48106.json` 和 `R/reference_bindings_v1.json` 的 own entry；`T/{gold,noop}/recipe/recipe.json`、before/after 脚本、reference_bindings.json、`.reference.json` 是每 run 的审计输出，不能相互替代，也不能把审计文件自身 hash 当输入 recipe_sha256。

本 reviewer 第一阶段已读 image.json/build.log/assets/preflight、10 个固定兼容 wheel 清单及两 run 的安装正文。COPY-only 派生镜像不等于安装：这里额外有 wheel 安装、源码 editable 构建、`build_ext`、pandas 安装成功和 pip check 成功的日志支持 revised_install 被消费。gold/noop 约 708.967/708.235 秒是历史 grader 安装时间，不是 actor 或模型固定成本。根用户 preflight 也不是开发会话。

当前 `replay_with_install_recipe.py` 从 `--code-root` 下的 src 和 scripts 加载，精确核 original_install 后替换两个脚本，再消费 own bindings；当前调用该入口时 code-root 应是 **ROOT/rh2**。重新只提取旧 plan 的本题对象，真实历史路径为 `/work/env_recipe_repair_20260919/resources_v1/code/rh2`。该旧字节快照没有经本地同一性认证；不能由路径名、版本标签或当前源码推定当时每个 parser/manager 字节都一致。历史消费由 run 审计和日志证明，当前机制判断由当前文件证明。

实际安装/测试身份为 grader/54322、派生镜像、deny_all；正式 actor 是 public image/54321，不能自动继承 wheel 修复、可写 conda 前缀、构建目录权限或已激活解释器。`apply_user=agent` 仅证明应用提交。正式开发前仍要核实际 shell/PATH、checkout 导入、已有扩展与 Python 修改生效；若现成扩展可用，本题 Python 修复不需无条件再作约 12 分钟全编译。核心内存 Series 用例不需外部服务或数据。

官方恢复精确限于 `pandas/tests/indexing/test_loc.py`；当前 `test_globs=()`，cast/indexing 源码修复可提交，`additional_exclusions=[]`。普通完整 pytest rc1 不自动 reward0，冻结参考与全局故障分层处理；共享 stdout 状态伪造风险尚无本题攻击运行，也不因历史建议只过滤参考 ID 就称已修好。

## 阅读边界、历史判断和用途

实际阅读分三层：第一阶段已读全部 16 F2P、相关旧 categorical/扩容/Period P2P 正文、fixture、helper 和共享调用者，具体行段保留在 reviewer_initial；第二阶段新增上表两项 tz 正文/fixtures、上述摘要/审计、主审五份成品和精确旧记录。**没有把主审自报的 23 方法/74 P2P 数量移作本 reviewer 的阅读数量**，也没有读完全部 1020 P2P 或全仓。主审的其它额外旧测试阅读不是本 reviewer 的执行证据。

旧记录仅为 `env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-48106.json`。另按本题引用只取 `s2/raw/swe_gym_lite_full_f70b1a29.jsonl:166`：hints 确有 first bad commit、PR47342 和 maybe_promote 最小例，但当前 public_hints 是 harness 操作说明，没有那些 raw hints。肇因定位线索不自动等于未来 gold 泄漏；未跟进网络链接。旧“安装必联网”“15 节点都不可推知”“移除 3 P2P 才能评分”均不能继续作为当前结论。

第一阶段一次完整读取授权 environment_record，确已看见环境 summary/checks/observations、原运行结果和 history 中三个环境批次/analysis 路径/roles 索引，不能缩写成只看到键名。该有限暴露已报告，未追质量历史指针；决定性环境事实重新核到 own 原件。第二阶段才获准读旧质量正文。不从另一位主审的阅读偏差推断本题新主审受相同暴露。

本 reviewer 在三题原件范围内已确认 53958/56849 base 的 cast.py:626–631/634–639 含本题分类分支，是跨版本答案暴露关系；三题目标不同，不据同仓归成重复题。该结论补充主审未查关系的范围，不能反推其已知。已经暴露 gold/隐藏测试/历史与跨版本源码的本上下文不得交给盲解 solver；真实镜像/Git 可见资产及真实模型表现仍未知。

## 唯一优先下一步

**采纳主审历史后调整：优先做固定 grader 的两组 tz 别名聚合诊断，替换我初判“先做 actor 启用”的优先顺序。** 固定运行器、pytest 版本、原冻结参考和当前 3 组绑定，在其实际解析/绑定/故障判断入口比较完整成员状态与 alias 结果；使用经该版本确认的完整 `-rA` 摘要顺序，重点观察混合通过/失败、非通过状态及成员缺席。记录身份集合、有效摘要位置、全局会话状态和正常评分，不能只改某行位置后冒称真实候选错分。

这是已定位的评分身份问题，信息量高于此时泛化重测 actor。若只有合并而无错误评分，不把它升级为题目不可用；若诊断证明某类不完整/非通过成员被错误接受，再决定版本化 all-members 接线修复及相应复证，不能立即删参考或改 reward。诊断输入实验也不等同于已观察到生产候选假阳性。正式 actor 核验仍在启用前单独完成，不把这两项机械列成当前双重必测。

本轮未执行该 CPU 建议，没有新容器成本或模型 token/费用，相关成本仍 unknown/null。独立复核保留静态候选，不批准正式准入，也不承诺未执行的实验会得到哪种分数。
