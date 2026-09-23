# getmoto__moto-5752 — reviewer_initial

日期：2026-09-21。独立 reviewer 第一阶段；未读取公开读者、主审或旧质量结论。三题初判全保存后等待协调者整包封存；未创建 review.md。

## 初判

建议 `needs_review / static_review`，用途 `development_diagnostic`。公开顺序问题在 base 中明确成立，gold 的总体修复路线合理，历史 RH2 原基线 noop=0/gold=1。保留一个具体范围争议：同一新增 F2P 在验证两种 Equals 顺序之后，还强制修复标签 BeginsWith 的既有行为；仅消除早退、完整实现公开 Equals 原例的自然修复会被后两条断言拒绝（静态预测）。公开验证器已经允许 BeginsWith，是支持这些断言的重要反证，因此尚不把它定为无依据隐藏要求或坏题。

路径缩写：`P=ROOT/runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-5752`，`Q=…/private/getmoto__moto-5752`，`L=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w04-1`；`ROOT=${REPO_ROOT}`。以下 base 路径在 P/base。

## 公开目标、初态与每项修改

base `b2300f1eae1323e3e8bc45f97e530ce129dff12e`，tree `af5bc183f2d8898aca1282badb9e2dc1554d552f`。S2 source_refs 精确 public/grading/validation 第 73 行身份对应。公开原例两个 String 参数 a/b，均有 hello=world，x 各为 a/b；两个 Equals 过滤器的两种顺序均应只返回 b。_match_filters docstring 明说 matches all filters；models.py:1608–1613 遇到第一个匹配标签就 return True，跳过后续过滤器，是直接原因。

| 要求 / 改动 | 公开依据 | 对应断言 / 正文 | 判断 |
| --- | --- | --- | --- |
| x=b 在前，hello=world 在后 | user_prompt 第一调用 | 新 F2P test_describe_parameters__multiple_tags 第一个 length_of(1) | 覆盖公开例；base 该顺序原本成功 |
| hello=world 在前，x=b 在后 | user_prompt 第二调用；_match_filters:1578–1645 | 同 F2P 第二个 length_of(1) | 核心回归；历史 noop 在 tests/test_ssm/test_ssm_boto3.py:1062 此处返回2 |
| tag:hello BeginsWith w 返回2 | base models.py:1462–1468 对非 Path 允许 Equals/BeginsWith；题面未要求前缀修复 | 同 F2P 第三个 length_of(2) | 是额外行为要求；与公开已接受选项一致，但并非顺序问题的直接复现 |
| tag:x BeginsWith a 返回1 | 同上；原标签分支忽略 option，只做值相等 | 同 F2P 第四个 length_of(1) | 该例 a==a，对“startswith 真的生效”的区分力弱；上一 w/world 断言才区分等值与前缀 |
| 结果身份应为 b / 满足所有筛选 | 公开解释不接受错配标签；_match_filters docstring | 新测试只验长度，不验名称 | 覆盖有限；未据此强造错误实现或自动判坏题 |
| get_parameters_by_path 的原功能 | test.patch 七处去掉创建参数时的 Description | P2P test_get_parameters_by_path 正文已读，路径、递归、类型/KeyId/Label、分页、非法键断言都未改 | 设置清理，没有删掉目标过滤断言；该输出本来不靠 Description 判定 |

test.patch 全文、新增四项断言与修改过的 P2P 全文均已读。F2P 是一个聚合节点，不是四个独立参考项。冻结 P2P 共79；真正精读相关正文为 test_ssm_boto3.py:1–236、554–1090：删除/路径访问；describe 基础、分页、旧 Filters Name/Type/KeyId；ParameterFilters KeyId/Name/Path（含默认 Equals/OneLevel、BeginsWith、Contains、Recursive）、两类参数互斥、14组非法筛选、3组非法路径、返回属性、单标签筛选与标签 CRUD 错误。其余版本历史/命令等 P2P 仅核冻结 ID 和历史结果，不冒称全部79正文逐读。imports/mock_ssm/sure 等本文件依赖已核，无外部 fixture。

## 合理替代、自然部分实现与 gold

自然的顺序修复可在 tag 分支先求“本过滤器是否有匹配 tag”；不匹配 return False，匹配则 continue 到下个 filter，最终统一 return True。这与 gold 的“将 tag 值归一为列表，统一比较”不同，亦能保留标签缺失为 False、多个 tag 和非 tag 条件都必须满足、Values 内任一值匹配。若仍按 base 的精确相等处理标签 option，则公开两种 Equals 顺序和相关既有回归可成立，但隐藏 w/world 前缀断言静态预计失败。应区分“满足窄的顺序请求”与“补齐公开代码已允许的前缀接口”；仅跑 CPU 不能替人决定范围，但可确定原评分如何对待它。

gold 让标签值成为 list，用 any 检查任一 value 命中，过滤器间继续合取；BeginsWith 同样逐 tag/value 比较。Name、KeyId、Type 的字符串路径保留；Label 分支在之前 continue，Path 的 OneLevel/Recursive 原逻辑保留；Contains 只对公开验证器允许的 Name 有意义。调用者 describe_parameters:1291–1330 和 get_parameters_by_path:1513–1535 都已读，responses.py:223–274 的参数/分页调用已读。未发现 gold 对这些已读旧行为的具体破坏。未穷举所有混合筛选、多值组合、分页组合；一般未覆盖边界不作为否定理由。

题面“与真实 AWS 相同”是原作者报告，未联网或进行 AWS 事实核验。

## 历史运行与开发条件

原始 run_refs 指向 L/ledger.jsonl 第7行 noop、第8行 gold；已精确读取，没有阅读该账本其它题行。对应日志为 `evallog_replay-f216-baseline01-w_0ec23aeb.eval.log` 和 `…_fb82c576.eval.log`。

| 条件 | 已核原件 / 适用范围 | 未证明部分与最小公开验证 |
| --- | --- | --- |
| 原始评分安装 | noop log:576 / gold:623 make init；873/920 成功安装 moto4.0.12.dev0；安装末rc0 | grader 54322 的 conda 前缀可写；不证明 agent54321 会收到同样解释器与权限 |
| 测试与评分 | noop log:886 起80项，1067–1072 1 failed/79 passed，唯一 F2P 第二次 Equals 的长度失败；gold:933、1001、1037–1041 80 passed/rc0 | 是历史真实 RH2，非本轮重跑；全部参考到场，F2P 0/1→1/1、P2P79/79、reward0→1 |
| 镜像身份 | public digest `2665296135d73d6ed10e225ac3942fcc9086811fdfa0ede89a8465a63716c134`；两行 derived_image_recipe=null、image_identity 对应该digest、actual image_id=null | 可称使用原基线绑定，无派生配方；不能捏造 Docker 实际 image ID。环境摘要不是 actor 验收 |
| 开发入口 | Makefile:17–19 为 setup.py develop + requirements-dev；公开复现只需 boto3、mock_ssm；requirements-tests 含 pytest/xdist/sure | 实际 actor shell 打印 sys.executable/moto.__file__ 后，在 mock_ssm 和明确 region 下执行公开 MWE；可窄跑公开 describe/路径筛选测试 |
| 资产与服务 | 参数和标签全部由本地 mock 创建。base_identity 唯一 gitlink 为 tests/terraformtests/terraform-provider-aws@f9a6db6…，.gitmodules 指向 Terraform provider | gitlink 不在上述源码/测试调用链，无证据本题需要它；静态未物化不是实际镜像缺资产。无需 live AWS、Terraform 或运行期下载 |
| 写入/交付 | 改 moto/ssm/models.py 足够，不必改测试/安装资产 | agent 工作区可写为代码事实；系统依赖改装权限待验。无需把共享环境未知升级为题不可用 |

ledger observation 为 /testbed/moto/__init__.py、4.0.12.dev；2CPU/4GiB/deny_all、UID54322，峰值约299–309MiB仅为历史 grader 观测。candidate.apply_user=agent/54321 只证明补丁应用。env_qualification=absent 不等于失败，亦不是正式准入。

## 当前投影、恢复、控制面

已读 ROOT/rh2 当前 prepared_task_face、trusted_projection、scoring、swegym_parsers 和 manager 的相关函数：test_files 从 test.patch 精确提取，`test_globs=()`。官方恢复/保护仅 `tests/test_ssm/test_ssm_boto3.py`；`moto/ssm/models.py` 在 gold ledger included_paths 中。未发现修复必须修改被恢复文件的冲突。setup/Makefile/其它测试 helper 并未因“测试目录”全部排除；不能把 public_hints 的泛化解释当真实投影规则。未构造通用安装或测试篡改攻击。

pytest parser 用摘要行的第2个空白分隔词作为节点键，解释了冻结若干带空格参数化 ID 的截短形状；对应历史 reference_missing=[]，没有本题漏配证据。scoring 只按 F2P/P2P 算结果，manager 另分全局失败；完整正常收尾的其它测试失败/rc1 不自动等于 reward0。

rollout_spec_from_view 正式使用 public image/digest；public_hints 公开可读但是否作为实际消息生效未知。默认 agent54321、受限网络和工作区可写，以及 /root/.rh2_bash_env 与隐藏 /root 的激活可达性，需真实 actor CPU 核验；不由原基线 grader 成功代填。

## 关系、暴露与唯一下一步

三道 Moto 私有审查共用上下文。5752 base 的 events/models.py:35、839、868 已包含5134的 sentinel 修法；7584 base 的 ssm/models.py:1872 起已包含本题 gold 的列表比较路线，后续又有变化。它们目标不同，属于版本答案包含关系，不直接判重复题；跨题 solver 可见范围须保留。未读其它题结论、history 目录、主审稿；其它两题授权 environment_record 原件中的批次 history 引用字段已经暴露，未跟读汇总。已见本题 gold、隐藏测试和原运行，不能担任本题公开盲读者。

唯一优先下一步：在冻结原基线 grader 条件做“只修过滤器早退、保留既有标签等值比较”的合理窄修复 CPU 对照，与 gold 同时记录公开两种 Equals 顺序、原 F2P 的各断言和 RH2 reward。预期窄修复通过原例但在 w/world 前缀断言失败；结果用于明确范围争议，公开验证器允许 BeginsWith 的反证必须一并保留，不能仅按失败宣布题坏。本轮未写或执行该候选；正式 actor 开发启用仍是独立待验条件。
