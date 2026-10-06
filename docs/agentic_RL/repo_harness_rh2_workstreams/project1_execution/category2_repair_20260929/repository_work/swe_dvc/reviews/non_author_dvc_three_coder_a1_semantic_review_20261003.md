# DVC4166／6954／9395：Coder 首臂非作者候选与轨迹窄核

2026-10-03。仅本机离线标准库读取。审查者已读过本批私有材料、CPU 控制与公开 actor 结论，也读了本次作者审计，**不是 fresh 公开读者验收**。未运行候选、pytest、CPU、Docker、SSH、模型、评分或资源操作；未改材料、原件、作者报告、共享看板或发布登记。

## 当前结论

| 题目／原作业 | 当前官方结果读回 | 独立候选语义结论 | 尚不能声称 |
| --- | --- | --- | --- |
| 4166／gpu1003-dvc4166-coder-a1 | reward 0；66 实际节点＝3 F 失败、60 P 通过、3 额外通过；install 0／test 1 | 有效错修。拆分连续同标志 regex 分组没有解决目录尾斜杠及父目录剪枝，三个行为 AssertionError 与源码一致 | 公开 29 项通过不表示目标修好；不因此改材料迁就候选 |
| 6954／gpu1003-dvc6954-coder-a1 | reward 1；26 实际节点＝3 F、12 P、11 额外均通过；install／test 0 | 冻结合法负数行为修复成立；修前解析遗漏、修后真实 CLI 成功有原件；非数字一元表达式与弱自测边界保留 | 不等于完整 Python 表达式语义、全功能回归或训练资格 |
| 9395／gpu1003-dvc9395-coder-a1 | reward null／not_graded；解题完成后 relay rm 超时，入口 exit 1；grader 未实例化 | 源码足以确定修法未完成：缺失检查先抛异常，新增恢复不可达，checkout 没有远程 pull | 源码错修判断不等于正式模型 0；没有本臂 41 节点、安装／测试／projection／hygiene 结果 |

本报告支持封存三条 **Coder 单臂候选／七维轨迹判断**。它读回已有 4166／6954 评分，**不是一次新的执行验收，也不是 completed 的非作者 GPU／评分全链验收报告**。9395 原 FP 正式评分仍待恢复；三题 Qwen 首臂仍 pending，成对请求不 ACK／returned，不清 active_request_id。未发现需要修改冻结题面、断言或材料的新阻断；单次每题不能授予稳定性、双模型排名、训练或留出资格。

## 范围、版本及重建方法

本次直接读取三份原 FrozenPatch、严格 base64 解码后的业务与相关诊断脚本、业务 baseline tar 成员、公开 solver_prompt、完整 CC 工具序列及结果、原评分 report／projection／完整 eval log／diagnostics／status，以及 9395 失败和清理恢复记录。完整字节封存清单核查由题主负责；本核未机械重核全部 653／600／605 文件或代码树，也不重审旧 CPU 矩阵／actor／题义。历史材料与评分分区适用边界复用既有非作者报告，当前结论再与本次原件独立对照。

日志重建以完整行上的 pytest 状态与节点为准，保留含空白 ID；失败行仅去掉 pytest 的 ` - Asse...` 解释尾巴，不改节点主体。以当前 diagnostics 声明的参考集合做集合对照，结果来自原日志，未采用作者节点摘要代替。4166 的 66、6954 的 26 是实际执行分母；参考分母分别 63、15，不把额外项算成奖励参考。原 source 参考及有效节点绑定的语义沿用已核冻结版本，不改全局 parser。

作者当前全文为 4166 v1、6954 v2、9395 v1；三者 SHA 在末表。6954 v1 的一处表达式引用误写已被指出，作者保留旧 SHA 并新增 v2，仅更正引用，未改变候选、日志或评分。全文差异核确认 v2 与原轨迹一致，其余两题核心事实无新增矛盾。

## 4166：逐维核查

1. **根因与修法。** baseline `dvc/ignore.py:32–43` 的 groupby 仅合并连续相同 ignore 标志，保持输入顺序；`:68–73` 已逐组匹配并由后匹配更新布尔结果。同标志组 OR 匹配与逐规则匹配在此具有相同最终布尔结果。原 FP 只是 list(map)、每条 regex 单独编译及说明注释，未改 `matches()`、目录类型、父目录遍历或尾斜杠表示。`/*` 加 `!/scripts/` 中目录名 `scripts` 不匹配 `^scripts/.*$`，仍被剪枝；平面子文件匹配不能证明目录已恢复。也不能将 issue 中所有写法强行视为同义。正确计为错修，而非公开规格缺陷。
2. **定位与纠偏。** 轨迹早期读到 ignore 实现及公开测试，却以错误 mock 调试空 ignore_spec。行 533 明确显示 `.readlines()` 为 MagicMock、regex 列表为空，最终脚本 `simple_debug.py` 仍设置 `.read.return_value`。后续曾将规则排序，行 756 完整单元结果 2 fail／13 pass；撤销排序后原单元恢复。行 966 才形成最终逐条匹配，恢复旧保序而未触及目录根因。定位文件正确，因果判断未成立。
3. **工具。** 1055 行轨迹，89 个真实工具：Read 12、Bash 45、Write 22、Edit 10。相关输入／结果均已按顺序核。目录 Read、错误 mock、漏建嵌套目录、空／陈旧 Edit、排序引入失败是实际工具问题，不能归为依赖或服务失败。大量近似脚本使错误 mock 与手工 regex 输出互相矛盾。原 FP 为 23 项：1 业务文件加 22 根目录诊断脚本；正式 projection 完整保留 23 项。末段 git diff 的 setup.py Moto 变化已经在 baseline 中，FP 没有该文件，不能算模型修改；最后空 Edit 也未撤销它。
4. **并行。** 所有工具批次至多一个工具；没有有效并行。初始实现／公开测试读取可批量，重复 regex 示例可合并；Edit→回归→回滚有依赖，真实 DVC 状态测试不应无隔离并发。主要浪费是错误调试对象与重复，不能用更多并发掩盖。
5. **自测与陈述。** 基线公开单元 15、功能 14，最终同 29 项通过；中途两个单元失败已纠偏，重复运行不增加覆盖分母。真实 WorkingTree 脚本主要传入空 dirs 与含斜杠平面文件，行 994／998 仍显示 `*`+`!scripts` 对子文件保持原行为，行 1003／1007 工作写法通过，但未覆盖父目录遍历。没有有效目标回归断言。最终“逐条处理才确保最后规则生效”与 baseline 不符，成功主张应拒绝。
6. **效率与观察。** attempt solve 293.626 秒；CC result duration 289.825、API duration 251.907 秒，90 turns；累计 input 3,046,377／output 28,003 是 CC usage 元数据，含重复上下文，不是上下文峰值。89 次工具和 22 个新增脚本对应大量重复。grading report total 277.491、test 7.405 秒，candidate 安装 3.132、测试 3.675、pytest 1.16 秒范围不同；不能相减推断精确思考／工具时间。无速度或模型能力因果排名。
7. **结束与评分。** CC result 第 1055 行 success、end_turn／completed，harness 0。现有 actor 清理 true；manager created 1／removed 1，open／supply／failures 均空。UID54322 wheel prerequisite verified，install 0，实际 test 1；三个失败栈都是业务 AssertionError，没有导入／收集错误造成 0。`env_qualification` absent，resource_facts null 保留，不能授予环境或训练资格。

正式三 F 原件：

| 完整节点 | 原栈行为 |
| --- | --- |
| tests/func/test_ignore.py::test_ignore_file_in_parent_path[data_struct2-pattern_list2-result_set2] | `subdir/`＋`!should_ignore` 应剪枝，却返回 `dir/subdir/should_ignore`；测试行 208 |
| tests/func/test_ignore.py::test_directory_rule_prunes_directory | `blocked/` 规则后 `tree.isdir("blocked")` 仍 True；行 243 |
| tests/func/test_ignore.py::test_negated_directory_rule_recovers_non_example | `/*`＋`!/kept/` 后 `tree.isdir("kept")` 仍 False；行 258 |

59 个 bound_source P 加 1 个 added P 全通过；3 个额外通过是 `test_dvcignore_in_out_dir`、`test_match_nested`、`test_ignore_external`。所有 63 参考在完整日志均有精确状态，无 missing、skip、额外失败或无法归属参考。

## 6954：逐维核查

1. **根因与修法。** 原 `_get_ast_value` 不接受 UnaryOp，外层忽略 ValueError，合法负数赋值丢失。新增 USub 递归读 operand 后取负，容器分支已有对 scalar helper 的调用，修复冻结负整数／浮点及容器中的负值；UAdd 是额外支持，不能推导任意嵌套容器或完整表达式求值。静态上 `+"x"` 会直接返回字符串；USub 对字符串／None 可抛 TypeError，外层只吞 ValueError／AttributeError。该范围限制不是已运行评分失败，不新增本轮评分要求。
2. **定位与纠偏。** 两次 Read 不存在的 serialize.py 后，通过 loader 接线找到 `_py.py`。行 129／133 修前 parser 仅留下正数；行 142 的有效业务 Edit 后，行 155／159 同脚本输出全部负整数／负浮点。没有业务回滚；行 370／374 重复旧字符串 Edit 失败，没有第二次业务修改。根因及因果方向正确。
3. **工具。** 418 行、36 个工具：Bash 21、Read 7、Write 6、Edit 2；Write 六次对应五个新增脚本，其中 test_negative_params 重写一次。不存在文件 Read 两次、表达式误断言失败、重复 Edit 为四次工具错误。完整 FP／projection 共 6 项，不只是业务文件；hygiene clean 不表示无脚本残留。
4. **并行。** 每批一个工具，没有观察到工具并发。修前复现→Edit→修后复现有必需依赖；独立源码读取可批量，parser 示例可合并。临时 CLI 建仓库／写 lock 有状态，应隔离；重复同类集成不等于新增覆盖。
5. **自测与陈述。** 行 199／203 和 357／361 是两个真实临时 Git/DVC 仓库，以 PYTHONPATH=/testbed 执行 `dvc repro`，rc0、真实 cat 阶段及 lock 生成日志可见，不能降格成只有 mock。但脚本仅判 rc，没有读回 lock 内负值、改变负参数再 repro 或核输出内容。comprehensive 十组主要打印比较。负值脚本第一项有真断言；第二项原写 `expr = 1 + 2` 和 `div = 10 / 2` 的 raises(ValueError)，首轮在加法处失败（轨迹 269、278／282）。行 291 改为 try／打印／捕获也放过，300／304 空 dict 后称 All tests passed，缺少空 dict 断言。正式 SUM／CONSTRUCTOR P 通过属于另一证据范围。公开实际 CLI parse 1、dependency 20、params show 11；新增脚本 pytest 2；`-k serialize` 的两项是 YAML，不能当 Python 表达式回归。最终负数修复有证据，全部功能保持／完全解决表述过宽。
6. **效率与观察。** solve 60.305 秒；CC duration 56.212、API duration 45.406，37 turns，input 433,841／output 5,946 是 CC 元数据。重复 find、同类 CLI 与无效 Edit 可减少。grading total 223.892、report test 5.990，candidate install 3.674／test 1.679，pytest 0.87 秒不能混为同一计时。该单臂不能用来排名模型定位或推理速度。
7. **结束与评分。** result 第 418 行 success、end_turn／completed，harness 0；actor cleanup true，grader manager created 1／removed 1、opens／failures 空。UID54322 prerequisite verified，install／test 0；完整 eval 26 PASSED、无跳过／收集错误。resource_facts null、env_qualification absent 保留。

15 参考来自原绑定负整数 F＋新增 `test_parse_negative_float_and_containers`、`test_negative_python_params_lock_and_repro` 两 F，以及 valid_types 的 dict/set/str/list/bool/float/int/class/none/tuple 和 invalid_types 的 sum/constructor 共 12 P；逐项在当前完整节点行均 PASSED。11 额外项正是公开 `tests/func/params/test_show.py` 的原 11 功能实例，也均通过，无 missing、skip 或额外失败。baseline 中新私有 test_python.py 不存在，公开 params show 不含新增负数 lock/repro；模型自测未读取新增私测。

## 9395：逐维核查（未评分）

1. **根因与修法。** 模型识别普通数据源没有 run-cache pull，但原 FP 在 Stage.run 的 `_check_missing_outputs()` 后才调用新增 helper。baseline stage/utils.py:140–143 遇 `not out.exists` 立即抛 MissingDataSource；目标缺失场景到不了 helper。Output.exists 是 property，不能误报漏括号。helper 调用 Output.checkout(allow_missing=True)，baseline output.py:884–929 仅取 `self.cache` 对象并 checkout，缺失可返回 None；没有新增 cloud.pull。因此先检查／后恢复及把本地 checkout 误当远程 fetch 是两个独立明确缺陷。保持 dry 条件并不能证明目标恢复成立。
2. **定位与纠偏。** 轨迹 185／189 读到 run-cache cloud.pull，264／268 明确读到 missing 即抛；303 仍把调用插在检查后，329 加 helper，507 仅扩大 CheckoutError 吞错。定位到正确模块，却忽略已读控制流。无真实 remote→push→删源／cache→repro --pull 的前后实验。
3. **工具。** 558 行、44 工具：Bash 22、Read 17、Edit 3、Write 2。两个猜测节点在 422／426、479／483 exit4、0 collected，不是能力测试失败或通过。435／442 广泛功能测试转后台；558 最后任务通知为 stopped。492／498 multistage pytest 经 head -20，17 collected、可见前11 PASSED，随后 BrokenPipeError／teardown warning，工具未标错不能证明 pytest rc0。原 FP 三项：业务 stage 文件加两个根目录弱脚本；没有正式 projection 可读。
4. **并行。** 一次后台后继续其他工具，形成重叠，但未回收完整结果，不能计有效并行验证。实现读取可批量，依赖／缓存状态测试需隔离。约120秒等待只是可观察边界，不能由 solve−API 精确归因为某个工具内部时间。
5. **自测与陈述。** reproduce 单元3及 command单元2真实通过；不覆盖 remote 恢复。临时 DVC init 仅初始化，没有 repro --pull 实验。两个 mock 脚本捕获所有 stage.run 异常，只断言 hasattr，不核 checkout／cloud.pull 或恢复内容；对 utils 函数的 patch 也未保证替换 Stage 导入绑定。comprehensive 正常阶段明确打印失败仍 rc0，缺失阶段以方法存在宣告成功。最终“checkout会fetch”“所有缺失已恢复”“全部功能保持”均与源码或证据不符。没有有效既有目录回归。
6. **效率与观察。** solve 215.507 秒；CC duration 206.557、API 56.380，45 turns，input 779,757／output 6,657 元数据。等后台后不回收结果、guess节点和head截断降低验证效率。原轮次无 grader，不能填写 grader install／setup／test 成本或峰值；绑定900秒预算不代表已使用或成功保护。有限资源采样不证明全程无 OOM、完整峰值或最低配置。
7. **结束与边界。** CC success/end_turn/completed 在第555行，而第558行是后台任务 stopped，不能用最后一行替代 solver 结束。harness0、FP已封存；随后 relay rm>60秒、cleanup false、entry1，评分前停发，failure.json 明确“求解清理未确认”。原失败保留。10:27:17／18 UTC 两次恢复观测均无本作业容器／网络；MainPID0、ExecMainStatus1／failed。恢复记录不执行候选，也未产生分数；grader未实例化、无grading结果。后续仅同原FP补分，不能重新求解覆盖本臂。

本题当前没有正式41节点或F／P统计，CPU控制的c3或任何他臂不能填入。该候选语义错修已确定，但 reward 仍 null，是当前评分核收未完成项。

## 作者全文差异与非阻断纠正

**唯一需纠正的作者原文字事实：6954 v1 §5 将自测原表达式写成 `sum(...)`。** 原轨迹269行是 `expr = 1 + 2` 与 `div = 10 / 2`；282行首轮失败在加法检查处。工具编号不同口径不混用，以JSONL原行号与tool_use_id定位。已先通知作者；v1保持SHA，当前v2只修正文首版本说明及该段引用，解释正式SUM参考另属评分证据。该纠正已解决，不改变真实负数修复／reward1、不要求重跑。4166及9395冻结作者v1核心结论与本核原件一致。

所有脚本残留、弱测试、过强最终陈述均按实际保留，不删FP，不把hygiene clean当只有业务改动，也不把这些习惯问题混成已判定冻结材料缺陷。当前没有授权范围内的材料／断言修复必要项。

## operational 指针与证据限制

对补充 owner operational JSON 及三个作业前实际capture做限定指针对照：capture时间早于各solve；共同engine/adapter ID、只读 `/model` mount、argv、HTTP model_path=/model、BF16、TP1、context196608、max-running1与声明一致；adapter output65536、idle-drop14400均有argv／配置。capture五个文件pins逐项实读SHA匹配；download_manifest实际files数组25项与model_file_sizes 25项名称／大小相同，其中16个.safetensors分片。**25是模型文件数，不能称25权重分片。** 未重复读取全部权重做SHA，也无GPU内存已加载权重证明。历史download_manifest头部files_count=28不替代其当前25项实际数组；该元数据边界不被扩写成运行错误。

原input config-only=true、runtime_request_and_sglang_readback_verified=false原样保留；独立live capture是另一个证据，不能回写原input。该窄核核指针一致性，不重复完整模型执行／服务审查，不将模型名称或result model字段单独当checkpoint证明。各题gateway加总时延、全部请求／SSE及有限资源样本总量以作者读回／执行receipt的范围披露，未在本报告重新逐请求作独立全链验收；候选／轨迹语义结论直接来自原件。

各profile的2CPU／4GiB／PID512与8GiB可写层配置不是全程实际资源或配额强制证明。4166／6954报告峰值为对应grader测量，resource_facts仍null，不证明全程无OOM／PID峰值；9395无grader峰值。未重审共享consumer、R20支持policy或旧actor事实；不操作资源，不自动普通重复，不作训练适用决定。

## 必要SHA索引

下列为本核实际读到的文件字节SHA256；canonical digest另外列明，不混用JSON文件SHA。路径简写：`S{id}=runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dvc{id}-coder-a1`，`J{id}=S{id}/queue_v27/results/gpu1003-dvc{id}-coder-a1`；`P`为本报告所在swe_dvc包根。

| 文件 | 实读SHA256 |
| --- | --- |
| `权威执行receipt` | `8ac94ba5e6df718d1c4f424c4e53025d5a42f42caf472f80cecc952e76af425f` |
| `tasks/iterative__dvc-4166/coder_a1_semantic_audit_v1.md` | `af340a29bf6e5c00817ee651e5dc723f0952ce5469cb237e9f9b17b81ffdbfb2` |
| `tasks/iterative__dvc-6954/coder_a1_semantic_audit_v2.md` | `7dc6452e69e72c8f50a2942894d0bec4fcb138befa6c8712ab8d28fbac306bee` |
| `tasks/iterative__dvc-9395/coder_a1_semantic_audit_v1.md` | `4ea483a455af6f66023deef3537ed4a99b5045c9a6697e07943199a0934ad85e` |
| `6954历史作者v1` | `e3103155b2238169141611bb9cbe340f1437293967e57e0fe0e3a9d3184e4302` |
| `补充operational owner读回` | `84fb2d8871578ca1e2559251110fc0b6aaaa1ce0201bb3e71fab824786513d29` |
| `J4166/solver_prompt.txt` | `f8e4a0203d4451e12190e55247960ca8b95dd005e3d5cf5b8e17c4de125c99fc` |
| `J4166/attempt/trajectory.jsonl` | `5b8161ceb039c9ff2766b55f0630936aeeb891751786cae49d6afe8abf7683ed` |
| `J4166/attempt/frozen/frozen_patch.json` | `71deed10c94bbb6a8e0ba3776600be964ea8456184fbdd863d6edf3a9ab8f258` |
| `J4166/attempt/frozen/baseline.tar` | `6ec884b34a24389e9a145f308ca7482762a819d787c1ae62f9bd157a0302a514` |
| `J4166/attempt/frozen/baseline_manifest.json` | `793c35ecb2b2dd28dbbded4976fc3f302343a5d7339c9facca5e467f6ce09929` |
| `S4166/closed_manifest` | `46bc255fa1d39b419dd1534b7e57caa1e72ee20ba7d21308a550ec95054cd403` |
| `P/tasks/iterative__dvc-4166/coder_a1_owner_evidence_readback_v1.json` | `646c856009b73ed3c344beb4e594b684fa44ea94d0757cb70b7b950b7e0f5bb8` |
| `S4166/diagnostics/.../capture_receipt.json` | `a339a78cb8d0ecbc1268a3aa1a587f0c1a39e7c7be0e97dced73541d326b1f92` |
| `J4166/grading/report.json` | `6c1346ad683730cbac6e4fea31dfbcd90b96c367ee1934c9d89dc1f599cde817` |
| `J4166/grading/projection.json` | `b17ea60a1b08406fecc53fde6dac7592b808a76e63375267a1e5fe05bfbf9713` |
| `J4166/grading/status.json` | `1fd0c59282ddae8dd87fbca0b4eb4ed54f4bbfb7645be1dfb3cdf842bdb776fd` |
| `J4166/grading/eval_logs/evallog_gpu1003-dvc4166-coder-a1_38f5eaf5.diagnostics.json` | `2e216beea54f37a7d23d56c212d7f0c6b898dbb2f1a6a7ecc7c58a412914baed` |
| `J4166/grading/eval_logs/evallog_gpu1003-dvc4166-coder-a1_38f5eaf5.eval.log` | `721576fcad7b1f19e0c2b4d9a6231913276d9e3b4d5e4b1162989d0f39b69ed5` |
| `J6954/solver_prompt.txt` | `5fdfe964e45d2c71264afc4c43542e1a778e173d75addd4039cbef861cf7fc98` |
| `J6954/attempt/trajectory.jsonl` | `bf059892ab2c62c566387b07a3ef0ab155c41132a5b1565fa03af14f4153ec70` |
| `J6954/attempt/frozen/frozen_patch.json` | `59bb5fcedab09aad10f04126d0d2b91963e0657883c33bc7c429865a0ca13f4b` |
| `J6954/attempt/frozen/baseline.tar` | `1427c0d3e9ee93acab8dc2283d2900b2875f610a0749ff0520031e0d8f099619` |
| `J6954/attempt/frozen/baseline_manifest.json` | `72a642433f73e15983fd0cd9089a1b7a42a4b5a94953f5a196c67312e2c73f94` |
| `S6954/closed_manifest` | `da13b8e61f549a9cb28c9e7b5a814d0ec63207ef02b64297b7c65e22b2edf833` |
| `P/tasks/iterative__dvc-6954/coder_a1_owner_evidence_readback_v1.json` | `523148553ef3c8a79577fbff0e86fe381768cf908ed5c9fdf3df150d3f54a4e0` |
| `S6954/diagnostics/.../capture_receipt.json` | `6a5691625732421195edf4d9503f22f68d374a48cf85b3585222a03061a1a771` |
| `J6954/grading/report.json` | `ec1d14701795b5af3734d8f00a31e67bb01675149436f423ae1573fbcb8ab8e6` |
| `J6954/grading/projection.json` | `4241a6c1ae3229f85fb567d05879d7462fd54d845865858d61029043a64c5ab0` |
| `J6954/grading/status.json` | `112aa2e91055bfed8e4186a157d0cb107d96022a6038eefe376b8da9d14189c7` |
| `J6954/grading/eval_logs/evallog_gpu1003-dvc6954-coder-a1_6c0253c6.diagnostics.json` | `9de5a9b670f20a140b900937ee8102d1bd04853e29470a1b7ee706c06b56ac9f` |
| `J6954/grading/eval_logs/evallog_gpu1003-dvc6954-coder-a1_6c0253c6.eval.log` | `607b14d43ef82a90082f9cfda7ec2300e6aeb1dd66f1517ac5c6f6087526df03` |
| `J9395/solver_prompt.txt` | `6aeed5c0b63922deb81519b033392a11ab4f2af0be1f24f954e66536bc41f3a4` |
| `J9395/attempt/trajectory.jsonl` | `3f7b11cae728a8057648ac92c5f4c83ac4baeef8913446a5389a9a6b783e3a00` |
| `J9395/attempt/frozen/frozen_patch.json` | `28766ba0af8a312357685ae9ce0206ce318a7d623354e35bf745add478fd9461` |
| `J9395/attempt/frozen/baseline.tar` | `6fb7167266118587a8fe0afbce99308f984d5acbca7f088cd4e7c1043d883a61` |
| `J9395/attempt/frozen/baseline_manifest.json` | `b41f4a530df5841ab7bc6f9c9f9344f4e3bc271649dc50f3345d5a444178d6d1` |
| `S9395/closed_manifest` | `dd3c2b3f578b86c54ea59a8654987dba41befd09028b9e0a7840b238a46b877d` |
| `P/tasks/iterative__dvc-9395/coder_a1_owner_evidence_readback_v1.json` | `6589a2b2d549b458d13ed8a945d62ba6eb32a3f8014d55e258369a74498cc3ce` |
| `S9395/diagnostics/.../capture_receipt.json` | `468973049487b255381388e471e62e5da40f739a044120d0713b429169a86102` |
| `J9395/failure.json` | `18b8cd84ec40427cd5742cce96576715c8f778da9326bf6563fc2c1fd47d5a26` |
| `S9395/q27_dvc9395_cleanup_recovery_v1/readback.json` | `c0c5ca097db66ccdcd255987584a346722c2a619ee771fdfbfc57e7a48499c6f` |

| 题目 | 原FP canonical digest | baseline canonical digest |
| --- | --- | --- |
| 4166 | `1f21d4efd80771070e0fb6135e9b48c736ff2b587218c3c5b2c4543a850076d7` | `sha256:16f108c365097d36390d40ff2b06c47fcf186b13c0e4cae2381ebfe6048ab6db` |
| 6954 | `2224b708089ede706f747dc1e9f487968a34b6f58536ebdbb4b9a2f4f40cae36` | `sha256:be0c03047652bd7c8ac13b696722f056a7b498ca5dd3c12fceba519a642c8625` |
| 9395 | `1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456` | `sha256:0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec` |

同一FP完整entries严格解码，未修改原JSON或条目；canonical与receipt／projection绑定一致。每题baseline业务源码只按本次改动路径和必要调用链读取，公开baseline与新增私测的隔离按具体成员核；不是全源码语义或全1479/950 release成员重审。

当前未验证范围：9395同原FP评分与之后清理、三题Qwen返回及双模型核收、单臂重复稳定性、完整执行独立报告、GPU内存权重／全程资源、正式训练捕获与reward训练消费、最终数据用途。当前只封存可观察的候选行为、轨迹习惯与已有评分读回，不以任何缺项自动补0或补通过。
