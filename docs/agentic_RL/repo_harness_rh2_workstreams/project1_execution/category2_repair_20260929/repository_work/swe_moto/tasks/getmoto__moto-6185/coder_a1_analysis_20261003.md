# Moto6185：Coder 首次有效0与嵌套漏修分析

2026-10-03。`gpu1003-moto6185-coder-a1` 原分0，安装退出0、测试退出1；正式目标失败、原34P保持，36实际项为1失败／35通过。失败是题面明确要求的嵌套 `S: None`，属于[既定范围](../../reviews/moto6185_existing_stop_scope_readback_20261003.md)内的真实模型漏修。没有infra或评分材料缺陷。保留原0、候选与完整轨迹，不改题目、不为普通0重跑CPU或模型。Qwen首次仍待回传，请求保持claimed。

## 唯一权威证据与绑定

原件位于 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto6185-coder-a1/`；manifest SHA `1be2d8a356d0579b6f498d465eb1bbc63c0f6e06f93a4f0a90caa98f2301ba77`，624成员／93,213,267字节全核SHA与尺寸。它包含前序依赖，不能算624次模型实验、与其它包累加或用remote兼容镜像覆盖。queue27／code8 source manifest `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，fixed inputs manifest `18daed50fe16dcde3fde48dd5222d3038c6d7084ad894172f99f7a95b96425a2`。

请求 `swe-moto6185-nested-s-r13-20261003-v1` 原输入SHA `4c77bb434b8300040ef0075dd86ddd3de25aea46975bbac1ecc29e73276f3b19` 与实际复制相等。材料仍 `moto6185-nested-s-v3`，host patch SHA `fc65a52722f47a6d458465d2e4a529caa057c2f238453d1659efdfef42bc332d`；base、public／environment／grading／materials均与请求一致。actor和grader镜像均为CPU验证的 `79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d`。

完整原题面已到首HTTP，包括 `payload = {'index': 0, 'A': {'S': None}}` 嵌套示例，当前中性brief也一致；delivered prompt SHA `7b2c272a1fe9f4f93d49a0be9cff15a650816e199eee2553f7131fdeab2f8d41` 按原CRLF字节核验。历史CPU确定桩中六行generic hints未交付的事实保留，不混同本次完整实际GPU prompt。私有新增断言没有作为公开答案提示。

实际模型预算ctx196608／输出65536／240回合／10800秒／1024请求／首字节1800秒／idle14400；评分whole1800／setup300／apply120／test1800。实际生成max_tokens全部65536，正常end_turn，未截断。CC摘要maxOutputTokens32000是记账字段，不能替代实际HTTP。slime-actor通道关联GPU固定Coder服务，题主没有另行活查权重或GPU内存。

## 正式0是范围内失败

实际命令 `pytest -n0 -rA tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py` 与input_check／host选择一致。安装5.331秒、测试3.241秒，完整footer `1 failed, 35 passed, 153 warnings in 2.56s`，无infra／missing／skipped／段外未归账。原重复表达式两个参数PASSED行合成一个原参考键；保留36实际行及35解析参考，不改parser，原34P及两个合键参数实际保持。

目标 `test_put_item__string_as_integer_value` 在同一个测试中先完成malformed `S:123`、`S:dict` 错误检查与合法S字符串roundtrip、顶层 `S:{"NULL":True}`，随后在967行的 `issue_nested` 失败：

```python
{"pk": {"S": "issue_nested"}, "A": {"M": {"S": {"NULL": True}}}}
```

实际报SerializationException “Start of structure or map found where not expected”。这是公开嵌套示例的低层表示，既定停止范围已明确保护，不能归为额外深层边界。目标失败后，后续更深／list／五层／S map案例及后半段负检查未达到，不能声称它们已通过。本次不新增五层以上、未保护畸形值或一般DynamoDB语义资格；CPU22对照的三种有效正修法和范围外rv_dynamotype旧观察保持原身份。

## 最终补丁仍混淆属性名与类型标签

FP `7baf55141ccbfbd76fe7772bf5bcbed0ea1736fd521cadd9f5d5d7494f3185c9` 含11项regular／100644全部投影：一项 `moto/dynamodb/models/table.py` 修改、十项根目录诊断／自测新增。baseline2003项内容、类型、执行位全核；逐步重放全部成功Write／Edit，精确得到11项FP。源码成功Edit在326／348／418／440／519行，最终源码SHA `807513b12d37d775cb6d16614bf4713abd1438ff86943ed7593c84afccafb8fd`。

最终仅把原 `if key == "S"` 改为：

```python
if len(item_attrs) == 1 and key == "S" and list(item_attrs.keys())[0] in ["S", "N", "B", "SS", "NS", "BS", "M", "L", "NULL", "BOOL"]:
```

其它递归和N检查保持。对于key已等于S且单键的map，末尾标签列表检查没有提供新的上下文信息。合法 `A.M` 下的属性map恰为单键 `{"S":{"NULL":True}}`，仍被当成字符串类型wrapper；递归到NULL后回到S分支，value是dict，于是抛错。修法靠键数猜测，未区分item属性map、M属性map与真正类型wrapper；顶层带pk的S None能够通过，嵌套仍失败。不能把“修了顶层”当完整目标成功。

## 模型已见失败却停止修复

初始63／67行复现原缺陷，256／260行诊断同时显示顶层和嵌套失败。326行只临时增加debug，348行移除；418行尝试用父层键与值形状限制仍失败，440行放宽后两种合法情形观察成功，但506／510行原malformed字符串测试失败。519行改成最终单键规则，537行原目标1通过，550／556行原公开exceptions文件36项通过；该原文件没有私有修订中的嵌套保持要求。

587行写final_test，596／600行运行在原公开嵌套 `{'index':0,'A':{'S':None}}` 明确退出1。605／618行模型文本承认嵌套仍错；609行再读源码，却没有再执行source Edit。622／631行新诊断直接用 `DynamoType({key:value})` 构造错误形状，未调用put_item或真实validator；catch／print后的退出0不能证明嵌套已修。

644／653行新test_specific_case只保留顶层S／s／A与malformed字符串，删掉先前嵌套验证。函数返回bool、主程序仅打印，失败也不设置非零退出；实际这几个有限case输出成功。666行特殊字符原节点1通过，679行git diff仍是519的最终规则。688行最终回答宣称嵌套／Map检查已修复，与600行及正式967行反例矛盾，记为完成判断失实，保留原模型文本。十份新增程序均无assert；final_test与reproduce_issue会传播异常，其余多为弱catch／print观察，不能一概计为严格回归。

## 工具错误、成本与清理

692行完整轨迹，61回合／生成、60工具：Bash31、Read12、Write10、Edit7。工具逐ID配对、全部单工具串行，无多工具batch或量化并行收益。HTTP62条为61生成＋1count_tokens，全部200；每条生成SSE start／delta／stop完整，usage与adapter、CC累计一致。

九个标错结果中，四个操作问题为未设region、读目录、相同old/new无变化Edit、不存在测试节点；五个真实失败分别是原复现、debug复现、中间修法复现、malformed保持测试和最终嵌套自测。预期失败不是infra；没有扩大模型或评分分母。选错目录／节点可改进定位，主要质量缺陷仍是已看见功能失败后缩小验证并过早完成。

累计输入1981660、输出16888，最大单次输入59934、输出1415；solver180.557秒、CC177.038秒、API159.581秒分别记录。manager总212.537秒、reset17.337、prep1.125、test9.153；phase trusted setup184.151896秒。原安装、评分、保护恢复和solver不能混算，无每工具耗时或连续采样可推一般效率／模型排名。

actor／relay容器及网络所属查询实际清理空，manager创建1／移除1、open及cleanup_failures空；gateway revoked／drained／active0，pre-drain residual0。32有限资源切片中actor15／relay15／grader14点匹配实际CID；边界一条DVC relay记录剔除，不归Moto。安装／测试窗口均0采样点，资源未知；actor记录峰值1065418752字节、grader691597312字节、report831.918MiB单列，不推最低内存、连续无OOM或宿主全局闲置。

题主读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto6185_coder_a1_owner_readback_20261003.json`，280666字节，SHA `0a8f39caf0b024fa3b034295a94ec03e1b95167ba4f4f8ae31fe8a0940acbbbf`。结论为范围内真实模型失败，原0及全部字节保留，材料不block。等待同材料Qwen首轮后收口；普通追加暂缓，本次不发起CPU或模型重跑。
