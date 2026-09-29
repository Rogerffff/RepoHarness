# Moto 5406 / 6114 跨包结果复核（两题正式结果与最终卡均已核）

2026-09-29。独立审查者：Pydantic 题负责人。先读公开题面、base 相关源码与公开命令，再读 actor/private/noop 原件，最后对照题主两份 result_partial.md。本次只本地读文件与校验文本/JSON/hash，未执行项目或远端命令。既有协作上下文可见，不称无上下文盲审。**两题 noop 均为正常目标失败的 reward 0，正式三方均0/1/1。5406恒East2破坏East1，6114首对象候选查B返回A，两个真实违例都被正式reward1接受，均为S1/T2b误奖。** 本稿先完成原件验收，再窄对照两题最终result.md/json，均一致。首轮partial范围在下文保留，后续正式补核分段说明，不倒签首轮已知状态。

## getmoto__moto-5406 — actor/private/noop 已验；正式三方已续核

公开要求是客户端选择 East2 时表 ARN 应反映 East2。题面示例本身混用了创建表名与末尾 `test_table`；本轮命令统一实际表名，只定位地区错误，没有把表名拼写问题当产品要求。base 的 `Table.__init__` 接收 region，`_generate_arn` 第569行却固定 East1；已有 `test_create_table_standard` 明确要求 East1 客户端返回 East1。因此 East1 保持正确有直接公开源码/旧测试依据，不由 gold 推导。最小复现省略 Stream/SSE/TableClass，不能声称完整原例组合通过。

原镜像 manifest `727caa5dba157d41b1e839a5044106f0ad7ea1fe824c9a5f562e2f74113339d6`，实际 image `808c60d962cb94330e499404720a0813fa400a2e86464aabdb47fcaa05aad5f6`，base `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`，本轮没有派生层。actor 的4个 Bash tool_use/tool_result ID 一一配对，CC 2.1.205、UID 54321、`/testbed`、testbed Python 3.12.4、boto3/botocore 1.35.9、pytest 8.3.2；源码从 checkout 导入，prelaunch/activation 正常，初末 git status 0行。East2 rc1 精确失败在 ARN 相等断言：Create/Describe 都错误返回 East1；East1 rc0、旧 East1 测试 1 passed/5 warnings。两地区的另一地区列表均空，故不是隔离失败。actor 容器/network/relay/stub 清理无残留，agent 进程0。

私有三变体是独立 root 容器：base 的 East2 失败、East1及旧测试通过；gold 三项均通过；恒 East2 修复 East2，但 East1 新断言与旧 `test_create_table_standard` 都在地区字段失败。9个行为命令均执行，没有首项失败跳过余项。审查者由公开 base 逐 hunk 重建两补丁，完整源码 SHA 与实际 prep 输出一致：base `87a558769bc0786464aeaca26fc29217c718971f447d6ddfc4ced9a3977d4f23`；gold `2fd7febd19be90e561f79b324508cc934b05922fc32c8daab7f5097d25234b5c`；恒 East2 `4bd4d6450546ba4a497c938023bea94b7bd81c774e089c0a0db690c461c66253`。准备/check/apply/hash步骤均0，三容器 rm/query 均0且 remaining 空。该段是首轮私有行为核验；正式 export 已在下段补齐。

noop 原日志逐ID核对冻结的1个 F2P、26个 P2P：`test_create_table` 在 East2 ARN断言失败，26 P2P 全通过，无缺席、skip或额外测试。完整 pytest 为1 failed/26 passed/151 warnings，reward0成立。实际候选 kind=noop，投影 included_paths=[]；原 `make init` 完成 rc0，安装8.014秒，测试6.030秒且完整结束标记；setup293.409秒。runner摘要前后一致，候选容器已移除，manager_close 无打开容器、租用供应或清理失败。日志 SHA `a301e150e5cd62acbebe972f1d3032968f3a425055142cef7ca23c970422d8d8` 已本地重算匹配账本。ledger `image_id_actual=null` 保持此事实：原镜像依据 digest/pull/actor身份链，不把空字段说成 grader config ID 已直录。

证据：[公开题面](../../../../../../runs/swegym_quality_batch05_20260921_v1/public/getmoto__moto-5406/user_prompt.txt)；[actor](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/actor_original/attempt.json)；[私有原件](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/private_behavior/summary.json)；[noop账本](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_noop/ledger.jsonl)；[noop原日志](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_noop/eval_logs/evallog_replay-cpu29-getmoto-mot_b8d1b463.eval.log)。

### 5406 gold / 恒 East2 正式续核

03:59整批结束后，本次直接读取两份完整 eval.log、ledger、driver_close_checked、budget、candidate.patch、frozen_patch.json，再逐ID对照冻结参考。gold与恒East2均1/1 F2P、26/26 P2P通过，pytest均27 passed/151 warnings，测试rc0、reward1；无缺席、跳过、段外解析或额外测试。正式test_patch把创建用例的客户端及ARN断言改成East2；其它地区的已有操作通过不代表其ARN被验收。正式所选文件不包含已在私有对照中失败的公开 `test_create_table_standard`，所以这次漏判确有可定位的覆盖缺口。

两份候选补丁字节与私有输入完全相同；从 frozen 的 content_b64 解码完整源码，分别69070/69027字节，逐字等于公开base加对应补丁，SHA正是前述gold/恒East2源码SHA。每份只含 `moto/dynamodb/models/__init__.py`，base和runtime digest也匹配。退化账本kind为cc是评分候选入口标签，本轮是确定性补丁，不代表CC生成。由此把私有真实违例与正式reward1绑定到同一实际候选，不靠补丁名称或题主结论推断。

两次原 `make init` 正常完成并安装checkout editable包，安装rc0，安装/测试段起止标记齐全，无命令失败，runner摘要前后一致；candidate清理removed=true，manager_close创建/移除各1，无open/supply/cleanup失败。gold安装6.418秒、测试5.360秒、setup277.820秒；恒East2安装6.911秒、测试4.831秒、setup280.308秒。两次2CPU/4GiB，setup900/测试1800/whole1800条件一致；内存峰值795.359/795.750MiB，resource_facts仍null。原日志本地重算SHA分别`b79d78ea0a34a383880993bc26a9965a7e0ef087801bd0f75451b7e87f8fb080`、`795a35e7e9a1330e0116d4d6ebd36d6a28ecbcf4af41311f3832b8cfa3d1843b`，与ledger一致。root跨端SHA归档/冻结parser属于另一核验步骤，本段不代签。

结论：S1/T2b实测误奖，当前可用于错误奖励诊断；不能把原reward直接当正确修复率或准入训练。若另行决定受限能力比较，须实际交付公开输入、相同独立地区验收及完整预算，原reward与语义验收分列；现有私有East1后检不等于D6正式修复。最小公开有据的正式修订建议是保留East2目标并加入已有East1 ARN验收，配同三候选复验；本夜没有实施该D6改动。完整Stream/SSE/TableClass组合、真实模型输入与自主模型/GPU仍未由此解除。

[gold原日志](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_gold/eval_logs/evallog_replay-cpu29-getmoto-mot_547a733b.eval.log)；[gold完整导出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_gold/artifacts/swe_gym_lite--getmoto__moto-5406/a1-95f594d6/frozen_patch.json)；[gold清理](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_gold/driver_close_checked.json)；[degenerate原日志](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_degenerate/eval_logs/evallog_replay-cpu29-getmoto-mot_1b582627.eval.log)；[degenerate完整导出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_degenerate/artifacts/swe_gym_lite--getmoto__moto-5406/a1-95acaed8/frozen_patch.json)；[degenerate清理](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/grade_degenerate/driver_close_checked.json)。

## getmoto__moto-6114 — actor/private/noop 已验；正式三方已续核

题面一般要求按已存在集群的 ARN 或名称筛选并返回该集群。示例有 cluster-1/cluster-0 拼写混用；本轮创建 A、B，再用实际创建所得 B ARN 查询，避免该歧义。公开 base `describe_db_clusters` 第1951–1958行直接按名称字典查找并报不存在。比较 B 的 Identifier/ARN 有直接公开语义依据；仅长度1不充分，也没有额外要求跨账户或异常 ARN 的精确策略。

原 manifest `cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`，原 image `fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`，base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。原 actor 已全部符合预登记预期：identity0，查询 B ARN 抛 `DBClusterNotFoundFault` rc1，旧测试4 passed/31 deselected/21 warnings。派生 actor 结果相同。两侧各3个 Bash ID 配对，UID54321、Python3.12.4、boto3/botocore1.35.9、pytest8.3.2、CC2.1.205与 checkout 导入均核实；初末工作区干净、agent进程0、各层清理无残留。`all_match_expect` 既不表示 bug 修复，也不表示原 actor 依赖坏了。

派生 `aaf97ca9107336dc68a964386be07361bf363f3a4684998d3727d704c20cd5a0` 恢复历史 COPY-only 层：setuptools72.1.0、wheel0.43.0、packaging24.1 加 PIP_NO_INDEX/PIP_FIND_LINKS；Dockerfile无 RUN 安装，原 RootFS 完整作为前缀保留。下载/build完成，下载容器清理查询为空；同步未包含3个wheel，故本审查没有本地重算wheel字节，manifest与调度校验不包装成归档字节验收。派生层用途是正式离线构建资产恢复，未做原镜像正式安装对照，不能主张修复了本夜 actor 故障或量化收益。

private 在该派生 image 的独立 root 容器运行：base 在查询 B ARN时报正确目标缺陷；gold 返回1个B并通过；退化返回1个A，在第15行身份断言失败。数量断言已经通过，错误不是数量。审查者从公开base逐hunk重建，实际prep完整源码 SHA：base `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c`；gold `00e61d1980f71fb4b0f37fa8e517a1fd3778c8ac5d687e4847d27217c5bc1c5b`；退化 `a5e0c305e9981b61209a2fc3bc4e2c40944fade972a4ff28b5ed0fc54b81815e`，均相符。所有准备为0，三容器rm/query0、remaining空。

noop 使用实际派生 image ID（CLI及ledger均匹配），投影为空。逐ID从原日志找回1 F2P/34 P2P：`test_describe_db_cluster_after_creation` 对实际 cluster-id2 ARN 抛 DBClusterNotFoundFault，34 P2P通过，完整结果1 failed/34 passed/165 warnings，无额外或缺席/skip；reward0是有效负对照。原 `make init` 安装rc0，日志含editable构建完成，安装10.014秒、测试7.503秒、setup310.450秒，测试段完整结束。安装distribution记录4.1.0.dev0，而源码观察4.1.6.dev；两者原样保留，checkout导入路径为`/testbed/moto/__init__.py`，不混写为同一版本号。runner前后相同，候选与manager两层清理正常。完整日志SHA `2ddafa497a132fb21316c1c5c53444f23ef4ab83f6aa077d6ba539ff90447a23` 本地重算匹配。

证据：[公开题面](../../../../../../runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/user_prompt.txt)；[原actor](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/actor_original/attempt.json)；[派生actor](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/actor_revised/attempt.json)；[实际build](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/dependency_build/image.json)；[私有原件](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/private_behavior/summary.json)；[noop账本](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_noop/ledger.jsonl)；[noop原日志](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_noop/eval_logs/evallog_replay-cpu29-getmoto-mot_bf67a611.eval.log)。

### 6114 gold / 首对象正式续核

末条结束并同步后，直接读两份完整eval.log、ledger、driver_close_checked、budget、candidate.patch与frozen_patch。gold与退化均1/1 F2P、34/34 P2P通过，pytest35 passed/165 warnings，reward1/test rc0；35个参考逐ID全在原日志找到，无缺席、skip或额外失败。参考test_patch虽创建两集群并以第二个真实ARN查询，却只断言返回长度1，未断言Identifier/ARN。私有控制已明确退化返回数量1但对象A，故是对象身份覆盖不足导致的真实误奖，不是题面歧义或精确整对象比较拓题。

实际candidate.patch与各自输入字节相等，解码完整frozen源码分别161153/161120字节；由公开base逐hunk重建的结果与它们逐字一致，SHA为前述gold/退化SHA。单一修改路径`moto/rds/models.py`，materialized_head匹配base，runtime_image_digest为实际派生`aaf97ca9…`。与私有行为同候选、同派生环境可追溯。kind=cc仅候选评分入口，不声明模型产出。

两次`make init`均实际完成editable构建和安装，构建依赖阶段finished done，无install失败命令，install/test rc均0、所有起止标记齐全。安装distribution 4.1.0.dev0/checkout观察4.1.6.dev的区别同noop保留；日志未逐包展示隔离构建环境的实际pin，不能仅凭COPY层宣称已逐包观测。gold安装9.928秒、测试7.026秒、setup302.268秒；退化安装9.445秒、测试7.126秒、setup258.812秒。资源2CPU/4GiB、setup900/test1800/whole1800不变，内存峰值940.684/943.078MiB，resource_facts=null。runner前后相同；候选removed=true、manager创建/移除各1，无open/supply/cleanup失败。原日志本地SHA核对`335bf63a3b89e922d943ffdfc7d38a0c4de81202007d7a97fb170d4e38733e01`、`d70701a3d80f42055dbcff0037c67face55fd7878fd545d802b9e84ad4a7cedd`均匹配ledger。

结论：S1/T2b实测误奖；当前可用于奖励诊断，原reward不直接支持正确修复率或训练准入。最小公开有据的修订是已有两集群ARN用例同时断言返回对象的Identifier/ARN，复验同三候选；这仍是D6建议，未实施。受限能力比较需另行落实真实公开输入、同一身份验收与预算，分列raw reward和语义结果，不能把私有后检当正式修复。

[gold原日志](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_gold/eval_logs/evallog_replay-cpu29-getmoto-mot_c5a9f535.eval.log)；[gold完整导出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_gold/artifacts/swe_gym_lite--getmoto__moto-6114/a1-7ab15744/frozen_patch.json)；[gold清理](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_gold/driver_close_checked.json)；[degenerate原日志](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_degenerate/eval_logs/evallog_replay-cpu29-getmoto-mot_722b5ef8.eval.log)；[degenerate完整导出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_degenerate/artifacts/swe_gym_lite--getmoto__moto-6114/a1-37d5b73c/frozen_patch.json)；[degenerate清理](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/grade_degenerate/driver_close_checked.json)。

## 共同边界与接续

两题正式noop资源是2 CPU/4 GiB；budget审计明确只把准备预算300提升到900秒，测试预算1800、whole deadline1800不变。内存峰值分别809.312/969.551 MiB，`resource_facts=null`，不据此声明全程无OOM。actor 实际请求首条是 Devcheck 控制文本；本次验证公开命令/工具通路，不等于真实题面/public_hints交付或自主解题。私有root行为不替代公开UID权限验证，任何补充控制均未并入正式reward。

首轮最后读取两题 result_partial.md，与actor/private事实相符，无新增无证据主张。两题正式原件现均补齐。随后已读两题最终result.md/json：用途、S1结论、环境差异与剩余范围均一致；JSON各三行report/install/test逐项等于原ledger。6114最终正文对原actor正常、COPY-only恢复、元数据/源码版本差别、长度与身份断言、D6未实装均准确，未发现新增无证据主张。另窄核其正式日志确有每组两处离线links路径、两题noop frozen均为空，原grade log末尾cleanup与receipt一致。可以核销“独立复核/root对账接入”出稿待办，保留真实用途限制。

root冻结parser结果亦已读取：两题各3行，原日志SHA通过、test log完整、pretest_errors/参考外失败为空，与本审查逐ID结果相符；远端本地归档manifest分别91件/1,782,888字节、106件/2,309,115字节，verified=true、local_mismatches=[]，范围均排除wheel/image payload。该跨端检查由root执行，本审查读取结果，不重复远端操作。

[moto5406_final_v1.json](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/moto5406_final_v1.json)；[evidence_manifest_moto5406_v1.json](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_moto5406_v1.json)；[moto6114_final_v1.json](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/moto6114_final_v1.json)；[evidence_manifest_moto6114_v1.json](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_moto6114_v1.json)。

剩余：5406完整Stream/SSE/TableClass组合仍未知，D6未实装。完整pip check、模型真实输入与自主求解、模型/GPU/预算等不因本次CPU检查解除。

最终卡：[5406 result.md](../tasks/getmoto__moto-5406/result.md)；[6114 result.md](../tasks/getmoto__moto-6114/result.md)。
