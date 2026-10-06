# pack09 MONAI 静态审查

5932、6975均保留为有条件静态开发候选。两题公开目标和核心修复有源码及历史grader依据；当前actor消息、初态、工具、权限、依赖和资产仍未知，ready_for_probe=false。本包不新增私有CPU提案，两题各用一次明确的公开开发流程取得下一步证据。候选分类不表示评分完备或训练准入。

| 题目 | 决定性证据 | 处置与限制 |
| --- | --- | --- |
| 5932 | base按出现顺序对整串replace，短ID破坏长ID；新assertEqual 4直接验证公开同构算式。gold先长后短处理，依赖收集未改。 | 保留候选。反转出现顺序的坏修法可通过唯一F2P而在长在前失效；仅静态推断。缺失长ID+已有短ID的残留属于旧路径，未证gold新增回归。 |
| 6975 | Dataset省略lazy，helper默认False覆盖Compose实例True；gold改None恢复配置。四F2P仅核日志并丢弃ds[0]返回值。 | 保留候选但必须携带返回值漏测限制。正确执行后错误返回输入可逃过现有目标断言；未运行候选。公开内存Flipd流程可同时观察数据与执行模式，无需先扩大验收到所有Dataset。 |

6975的log_stats在公开题面及旧测试中已有依据，不能说日志完全无公开基础。精确文案可能过约束，但未证明合法方案实际误拒。新增空测试只构造数组，部分旧flags使用assertTrue(expected,actual)而非等值断言；这些削弱覆盖，不等于未执行或gold已回归。applied_operations是变换记录长度，不是实际resample调用次数。公共helper变化会影响其他调用者，但变换本身允许lazy，尚无消费契约反例。

两题均把check27的单状态从局部pass收为unknown，完整保留核心正证据，26维持unknown。5932主审/复核均完整读14 P2P语义；6975双方完整读59 P2P定义及参数。协调者读全部新增补丁、关键base链、角色技术正文及决定性记录字段，不冒认全P2P或底层resampling实现已由协调者读完。

| 历史原件 | no-op | gold | 身份边界 |
| --- | --- | --- | --- |
| 5932：pytest -rA tests/test_config_parser.py，15 collected | 1个目标SyntaxError，14pass，RC1 | 15pass，RC0 | base 3c8f6c6b94ba；Python3.8.20/pytest8.3.3，actual image ID=null |
| 6975：pytest -rA tests/test_compose.py tests/test_dataset.py，63 collected | 4个目标日志AssertionError，59pass，RC1 | 63pass，RC0 | base 392c5c1b860c；相同解释器版本，actual image ID=null |

各自安装最后命令RC0，expected无skip/xfail/缺项。历史初态存在删除MetricsReloaded依赖的diff；gold另含本题修订，旁边git show不是未提交差异。这些来自已授权ledger3/4、5/6及本题日志，不能替代当前actor或证明完全干净base。未新执行项目。

旧记录纠正：5932的TimedCall会spawn/Queue/执行函数并传播结果/异常，旧无多进程及helper只影响skip/timeout说法不准确。6975的Git导出缺图不证明镜像缺资产；Dataset局部传None是合理非gold方向，不能以gold范围扩大规格；1279/1432分别是ZipDataset/NPZDictItemDataset，reviewer在后稿也纠正初稿简称。旧真实模型满分、跨题关系与parser主张未沿链接复验，不继承资格。

两位单题公开阅读员、一个两题主审、一个两题独立复核均显式请求gpt-6-astra/high/fork_turns=none。六份初稿先封存，再明确释放历史/交叉；后端与OS隔离未独立认证。协调者仅改可变card/record，四份main原稿已归档。见[修订来源](coordinator_revisions/pack09_monai/revision_log.json)、[后续](pack09_followups.md)、[阅读边界](reserve20_coordinator_read_notes.md)。结构与来源校验只验证产物/封存链，不认证语义完整性或actor资格。
