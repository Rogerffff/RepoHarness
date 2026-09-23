# getmoto__moto-5752：独立二阶段复核

**保留验收范围疑点，维持 `needs_review / static_review`，用途 `development_diagnostic`。** 可作为范围待定的静态候选；目前既不宣布“合法完整解已被误拒”，也不把仅修顺序的自然实现失败直接解释为求解能力不足。新增前缀断言有公开 API 线索，但确实要求修复另一项原有行为，不能用校验器允许该选项就省略 issue 范围判断。

三题独立初稿统一封存后才开放主审和历史。本人初稿 SHA256 为 `0b5b1cf65b3a20b0bafd68ab9409deb4945d68fafdf58007b284a934d8e21720`，保持不变。本稿读本题获准的五份主审产物及 history/refs 指向的 L1_moto_2 本题旧记录，再查其原 hints、public.json 和精确 stage1 运行原件。主判断与初稿和主审一致；新增一个需要明确的细节：raw hints 除字段拼写外还缺成功匹配后的 `continue`，不能只改拼写就当成预期能过公开原例的补丁。

ROOT 为 `.`；PUB/PRI 为 `runs/swegym_quality_batch02_20260921_v2/{public,private}/getmoto__moto-5752`；RUN 为 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w04-1`；S1 为 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5752`；MAT 为 `runs/env_overnight_20260916/L1_moto_2/mat/getmoto__moto-5752`。源码行号从 PUB/base 起算。

## 需求、断言和范围判断

公开要求是 describe_parameters 对同一组 ParameterFilters 的排列返回一致、且满足所有条件的结果；原例两项 Equals 标签只应返回 b。moto/ssm/models.py:1578–1580 的公开 helper 文档要求 matches all filters，但 :1608–1613 在第一个匹配标签立即 return True。这精确解释两种顺序结果不一致，两个时期的真实 no-op 日志也都停在反序返回2而非1。

| 验收内容 | 独立判断与证据 |
| --- | --- |
| F2P 前两次 x=b/hello=world 的顺序对照，均 length_of(1) | 直接对应 prompt:42–79。PRI/test.patch:64–87 没有查 Name，存在数量不能完整确认身份的普通覆盖限制；不能仅凭这个限制判坏。历史 no-op 第一项已过、第二项失败，不能称其执行了后两项。 |
| 单标签 hello/BeginsWith/w 期望2 | patch:89–94 修复旧 tag 分支忽略 Option 的行为，独立于多过滤器顺序。公开 models.py:1462–1468 明确放行非 Path 的 BeginsWith，普通字段匹配和旧测试展示前缀语义，故“完全没有公开依据”过强。另一方面，这个单标签缺陷在修复 AND 后仍存在，与题面给出的顺序缺陷可分离；把所有 API 已允许但旧实现不完整的情况都纳入本 issue 同样过强。 |
| 单标签 x/BeginsWith/a 期望1 | patch:95–99 的 a 同时是完整值，对正确实现了标签 Equals 且继续外层的窄修复而言，该条单独执行可过；它不具备 w/world 的前缀区分力。四断言在同一函数，第三项失败后第四项不会执行。 |
| by_path 的 Description 删除 | 精确 patch 是7处 fixture 参数删除，非旧记录的8处，原断言未变；models.py:225–240 的 response_object 不返回 Description。它确属额外清理，但无具体证据显示错配、误拒或新增业务要求。 |
| gold 的列表匹配、一般标量及 Label/Path | gold 从 tag 收集值列表，用 any 处理 Equals/BeginsWith，逐过滤器检查，不再提前成功；其它标量逻辑保留，Label 在列表分支前处理。静态满足公开原例，历史完整80项通过；未发现具体新增回归，也不把未读的其余服务归为已证实安全。 |
| 旧报告的 tag Contains 残余缺陷 | **当前 API 路径不可达。** models.py:1462–1468 仅给 Name 增加 Contains；describe_parameters 和 by_path 均先校验。旧拟议请求应先被 InvalidFilterOption 拒绝，不会进入 gold 的列表 Contains 分支返回0。旧“真实 AWS 应返回2”也未有本轮远程验证，不拿它裁决。 |

合理完整路线不止 gold：可在 tag 分支局部判断 Equals/BeginsWith，失败 False、成功继续外层，保留通用标量分支；测试不要求值列表、helper 名或特定代码布局。自然窄路线则只把当前标签等值匹配改为失败 False、成功 continue，修复所有 Equals 条件的 AND/顺序问题而保留旧 Option 处理。后者是否已完成本 issue 的全部合理要求仍是规范判断；只证明其会被 w/world 拒绝不足以判“过严”，而已经知道前缀选项存在也不足以证明这项独立修复当然必需。我的建议是保留这个可定位的范围差异，先确认具体拒绝原因；如将前缀作为固定验收范围，应明示该解释，避免把结果统称纯顺序修复能力。

第一阶段实际逐体读到 test_ssm_boto3.py:1–236、554–1090，覆盖全部相关 describe_parameters 与共享 get_parameters_by_path 的18个旧函数/33个冻结 P2P 引用，含参数化校验、分页、标签及旧 Filters；其余46个只核冻结引用和历史日志，不称已审全部79个测试体。全部新改断言、相关 fixture、responses 的校验与匹配调用顺序均读过。普通混合条件/结果身份等未覆盖边界没有被强造为第二个错误候选。

## 对 raw hints 和旧记录的具体纠正

MAT/hints.txt 确有源码行链接和近似修复讨论，片段使用 `parameter.tag`，实际字段为 `parameter.tags`。**还须注意成功命中后的控制流：**片段没有 `continue`；若只更正字段后直接替换 base 的 tag 分支，`what` 仍为 `hello` 或 `x`，会落入 models.py:1615–1624 的通用比较，拿标签键与 world/b/a 比较。原 Equals MWE 也会失败，不能据此得出“只因前缀而拒绝”的结论。这是静态推断，未执行讨论片段。

因此主审 old_findings_delta 中“修正字段并采用其控制流后，w/world 失败、a/a 可过”应理解为**另外加入匹配后继续外层循环的独立窄实现**，而非仅纠正 raw hints 的拼写。主审 analysis_before_history§3/§6 和本人初稿确实明确提出了 continue，所以实际优先实验方案无需改换，只需防止这处历史文字把不完整片段当可运行候选。旧报告“直接使用 hints 当合法解、两条前缀均失败”的实验建议不能原样采用。

MAT/public.json 的 public_hints 经直接字段读取为通用操作指令，没有该修复片段；当前包同样如此。这支持静态字段未嵌入原 hints，不证明实际模型消息、Git、挂载或缓存不存在答案。原 hints 只有在本轮门禁开放后由特权 reviewer 读取，不是 solver 轨迹。未访问其中外链。

## 两个时期的运行和 actor 边界

沿旧记录精确核 S1/gold/offline/a1 的 eval.sh 安装/恢复/测试入口、patch.diff，以及 gold test_output:864–877,890–901,992–1002、empty:826–831,913–934,1023–1033。旧 gold patch SHA256 为 `94e23bedb77a52fbef589882aec31531129cab051d1d6b49d1a28adcb9986a64`，与当前 PRI 相同。旧 gold install rc0、80 passed/test rc0；empty install rc0、第二个 Equals 断言失败、79 passed/test rc1。不是安装失败伪造了目标分差，旧 root pip 提示也不证明当前非 root actor 可运行。

当前 RUN 只读本题 ledger 第7行 noop、第8行 gold，并已在第一阶段亲读其原日志与本题 artifact：同一个公开 digest `2665296135d73d6ed10e225ac3942fcc9086811fdfa0ede89a8465a63716c134`，没有派生配方；安装完成、源导入 /testbed/moto/__init__.py，gold F2P1/1+P2P79/79/reward1，noop F2P0/1+P2P79/79/reward0。actual image_id=null 保留未知。UID54322、deny_all、2 CPU/4GiB 为历史 grader 条件；apply_user54321 不是开发会话。正式 actor 的 Python/PATH、源码导入和写入、离线依赖、消息可见性尚未验证，本轮没有新 CPU 或模型。

公开最小开发通过本地 mock_ssm、明确 region 和自建参数/标签完成，不需真实 AWS、数据下载或 Terraform。base_identity 的 terraform-provider-aws gitlink 未物化，但不在该路径；不能由导出缺口推断实际镜像缺资产。宽依赖安装在 grader 成功，也不等于 actor 有同样系统前缀写权限。

## 投影、关系、用途与唯一下一步

官方仅恢复 test.patch 的 `tests/test_ssm/test_ssm_boto3.py`；当前 `test_globs=()`，gold 的 models.py 已投影交付。public_hints 说“所有测试更改永不计分”不是当前精确机制。其它 helper/安装配置不能自动视为排除；未做篡改实验，额外排除保持空。冻结 parser 在空格处截短14个 filters0–13 ID 和一个 datatype ID，当前匹配无 missing，不把更换 parser 的假设风险当本题已经漏配；普通完成的非引用 rc1 与全局失败分开。

旧“与5502/5835同文件就成组”未获本轮指定原件支持，不采用，也未打开它们或 repo_level 汇总。本人已在指定三题公开 base 直接观察：5752 的 events/models.py:35,839,868 包含5134缺失标记修法，7584 的 ssm/models.py:1872 起包含本题列表匹配路线。主审关系 unknown 是其阅读范围限制，本稿补充这一真实版本包含关系；不直接归为重复或已证实污染，后续跨题 solver 暴露应保留。

**唯一优先下一步：**在冻结原基线 grader 条件下比较 base、gold 和独立的“等值匹配成功后 continue”窄候选，记录公开两顺序的返回 Name、相应 Equals 条件，以及未修改 F2P/全部原参考的结果和首个失败断言。静态预测窄候选修复公开顺序而被 w/world 拒绝；须验证原因及 P2P 是否保持，不能使用有拼写/落入通用分支错误的 raw hints 代替它。该组 CPU 只确认范围差异，不能独自判定不公；没有新增 Contains、作弊补丁或第二个优先实验。

独立初稿结论保持；历史纠正了 Contains、fixture计数、提示代码完整性和参数化 ID 的过度判断。正式 actor 核验仍是将来模型工作独立前提，无论范围如何裁定都不能称当前已正式准入。未改 source/test/gold/reward/recipe、封存稿或他人产物；本稿不提供模型 token/费用、重复稳定性或独立求解成功结论。

