# getmoto__moto-5134：历史差异核对

协调者已封存无历史稿，SHA256 `88cf0906fe19f3877dbf314d961cc15b5465282a075cb781e3807977aae61fee`，本轮未回写。随后仅读本题I2/history/refs指向的 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_1/records/getmoto__moto-5134.json` 及其明确stage1本题目录内原件，没有打开其他题、reviewer或聚合。以下PUB/PRI/ENV/TASK及M/P/T缩写同初稿，路径相对权威ROOT。

| 旧主张 | 核对与本轮处置 |
| --- | --- |
| base把缺键和null折叠，gold修复；exists:false的null负例是合理对称要求 | **确认。** 公开M:830,857–861、旧P:23–45、test.patch:8,16和集成:29–95相符。当前两个F2P均过；旧stage1 empty:738–746也在null肯定断言失败，:929–935只收到字符串detail。反向null是从存在性及旧互补逻辑推出，非题面逐字要求；题面并没有专门给出缺键矩阵，缺键依据主要来自公开旧测试。 |
| gold=RESOLVED_FULL、install rc0，因此环境可用 | **确认安装及引用通过，补全被省略的完整失败。** stage1 gold:731–743实际editable安装成功；:867–880的2 F2P+12 P2P全部PASSED，与旧RESOLVED_FULL主张相容；但:881–888另有3个SQS失败，完整14 passed/3 failed、test rc1。empty完整12 passed/5 failed，同3个SQS失败外加2目标失败。不能把旧resolved写成完整测试成功，也不能把这3个非引用失败自动改成reward0。 |
| 题目不存在额外环境问题，唯一问题是截断ID | **过时且不完整。** 旧gold的3项SQS在create_queue取QueueUrl时KeyError（:772–816），旧日志依赖为boto3/botocore1.35.9、s3transfer0.10.2、urllib3 2.2.2。当前sqs_v1按4pins实际安装并打印query模型，gold17 passed、noop15 passed/2目标failed；初稿已验证revised_install被脚本及日志消费。旧失败与SDK协议不兼容解释相符，但旧日志没有模型metadata，本轮不伪称在旧环境实测过JSON协议。 |
| ID截断是当前题缺陷，应重写parser并造双JSON碰撞实验 | **确认截断，收窄为固定映射风险。** stage1原日志:877完整nodeid与status_map截断键对应；当前同样一个JSON参数及一个None参数，没有碰撞，17解析ID对14参考无missing。假想未来加第二个同前缀参数不能证明本题当前误判。无依据改冻结ID或oracle，也不把人造parser碰撞列为本题优先实验；若将来换parser，应配套版本化映射。 |
| 所有公开输入完整、无泄漏、ready_for_probe | **拒绝外推。** 静态题面自足，但实际模型消息、shell、Git对象/挂载/缓存、正式actor导入与权限未验；public镜像不同于本次派生grader。原hints仅致谢是旧记录主张，本轮未读取raw hints原件，不替它作实证背书。即便致谢属实，也不足以排除其他运行时泄漏。状态改为needs_review/static_review，静态候选不是ready_for_probe。 |
| 无二进制/LFS/子模块材料 | **修正子模块事实。** base_identity明确Terraform gitlink `tests/terraformtests/terraform-provider-aws@f34a786a6672e5629456a523e2b74cc4d368db45` 未物化。本题最小路径不依赖它；不能因此判任务材料失效，也不能声称仓库没有子模块或运行镜像一定缺它。 |
| “字符串哨兵”与存在标志都可接受 | **存在标志路线确认；字符串方案需限定。** 新测试不读UNDEFINED名字，不限制表示；但普通字符串若按值比较可与合法JSON值冲突，旧记录未给具体安全编码或运行候选，不能笼统把它当完整合法替代。初稿保留显式存在布尔/独立不可碰撞标记路线，无需新增候选实验。 |
| null+prefix/numeric可检验UNDEFINED是否泄漏；回归检查已pass | **更正因果及检查范围。** 显式null仍是None，UNDEFINED只由缺键产生；因此建议中的null本身不能触发缺失标记。base对缺失/None的prefix.startswith或不兼容numeric比较已有失败路径，不能把旧缺陷算gold新增回归。本轮读完全部12个P2P和额外3个SQS旧函数、4个Archive相关函数；Archive没有执行，完整Events与全仓未审。 |
| 本包其余18题不碰events，因此无重复派生；本题“最好” | **未核实且不沿用排序。** 本轮没有打开其他题或包级汇总。不共享源文件不足以证明无同源修复/留出重叠，静态质量比较性称号没有逐题独立证据。本题关系保留unknown。 |

历史精确原件为 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5134/{gold,empty}/offline/a1/{eval.sh,test_output.txt,status_map.json}`，另读gold/patch.diff。两eval.sh相同，明确原make init、恢复P/T、pytest两个整模块；gold patch.diff与当前PRI/gold.patch字节一致（SHA `739b971a40aebc9d3aa3f479a7802b5ee5f60edfa6b3b36586ebc48453f64411`）。逐ID元数据比较证实旧gold全部14引用通过、旧empty只2 F2P失败；3个非引用SQS两者同样失败，不是只读总分所得。旧日志root pip警告不能证明当前正式非root actor资格，旧17分钟亦不填本轮cost。

初稿主判断不变：本题需求—断言—gold基本一致，尚无具体误拒/误收反例；当前派生grader安装/协议/完整执行已核，正式public-image actor条件和真实暴露未知。唯一下一项仍是初稿§6的actor公开开发路径核验，不增加机械反例计划。未改test/gold/source/reward/recipe，additional_exclusions=[]，所有封存稿保持不变。
