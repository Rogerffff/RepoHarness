# getmoto__moto-6185

建议：**needs_review / static_review**；仅用于开发诊断。base `dc460a325839bc6797084a54afc297a2c9d87e63`。题面要求普通属性名S在顶层或深层均可写入，保留真正类型错误。

| 要求/旧行为 | 验收与证据 | 覆盖 |
| --- | --- | --- |
| 合法S写入并读回 | F2P新增顶层S字符串；noop在新增put失败，gold通过 | 顶层字符串覆盖；NULL和深层缺失 |
| 真正S整数/字典错误、嵌套N整数错误 | F2P前半两负例；P2P wrong_datatype | 公开旧测试有依据；S字典仅测主键 |
| map/NULL/返回旧值兼容 | 公开test_dynamodb.py相应测试 | 未在本题执行模块或冻结参考 |

**主要问题（静态推断，未跑反例）：**gold递归只记当前父键，并用表键名判断类型。HASH名为M、输入resource `{"M":"id","A":{"S":None}}` 时，合法嵌套S仍命中错误条件。另一个未保护的旧行为：非主键真正S类型给字典，gold跳过原SerializationException，后续预计在bytesize(dict)内部失败。详见[封存分析](analysis_before_history.md)。

原install_wave1日志确认离线wheel增层后真实make init完成；gold为36 passed、rc0、reward1，noop为1 failed/35 passed、rc1、reward0，冻结F2P1/P2P34。两个含空格参数节点合为一个解析键，故36执行节点对应35解析键；两次均pass，**未证错分或reward遮蔽**。实际摘要先PASSED后FAILED，不能仅按last-write推导漏洞。

八方面均有静态记录：题意/材料/初态已核；完整test.patch、唯一F2P和受影响P2P已展开；完整P2P清单≠全部测试体；可采用区分属性映射/类型值的非gold路线，未见内部写法强制；gold缺口如上；开发入口可定位，正式actor身份/工具/导入/镜像待验；官方只恢复精确测试文件，test_globs为空，额外排除为空；同包源码关系见下述协调收束。Terraform gitlink与所查Python路径无关。

历史“安装仍失败”“旧断言私有”“与master一致即可豁免”不沿用，见[历史差分](old_findings_delta.md)。正式actor、实际消息、完整SDK/全库回归、当前资产可用性与模型成本未查；主审已见gold/隐藏测试和唯一旧记录，不能充当新solver。独立复核已完成，见[复审](review.md)。

唯一优先下一步：在固定诊断环境只用base/gold，创建HASH名M/typeS并用正常resource API写入、等值读回 {"M":"id","A":{"S":None}}；保存实际异常/结果并另记原评分。上下文正确替代实现及非法S异常回归留作后续，不作为这项诊断前置。所有CPU和修订均未执行。


协调裁决（2026-09-20T22:11:49.417478+00:00）：暂不优先普通能力探针：gold对公开深层S要求有主键名M的具体漏修路径；非键非法S另有异常类别回归。二者为强静态证据，尚未CPU确认；不得称非法值成功落库。 同包源码关系已核：5960的scan复制/投影核心原样存在于6185 base；6185类型校验核心原样存在于6408 base，6408 scan另有返回值式演变。仅为公开源码包含/演变，不证明Git祖先、重复题或实际solver泄漏。
