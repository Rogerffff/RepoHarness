# getmoto__moto-6185：旧发现差分

独立初稿 SHA256：`1b6b19f493abc83312c30a05ad804d622e2d55b608655c09af637d7617d34239`。协调者核验的文件 mtime：2026-09-20T21:33:26.463037Z（SGT 2026-09-21 05:33:26）；稿内21:32是撰写标时，封存原件不改。历史开放时间：2026-09-20T21:33:44.951990Z / SGT 05:33:44。

获准后仅读 `runs/swegym_quality_batch03_20260921_v1/history/getmoto__moto-6185/refs.json` 指定的唯一旧记录：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-6185.json`。未追它的repo_level_findings、旧mat、master、他题或旧聚合。下文路径约定沿初稿。

| 旧主张 | 本轮判定 | 新的决定性证据与处理 |
| --- | --- | --- |
| 初态会把普通属性名S当类型标签；新增测试黑盒且保留负例 | 确认 | base table.py:487–503；完整test.patch；N:588–607、700表明旧负例完成，新增合法put失败；G:654通过。 |
| 主键S字典负例属于私有材料、公开无法知道 | 推翻 | P/base中917–940已存在且公开导出；public_read先于gold已读到。公开要求可从旧测试补足，不属于隐藏的新标准。 |
| 只有主键S字典才应报错 | 推翻该规范概括 | 题面只要求区分普通名称与类型；base注释493–503并无“仅主键”限制。gold的条件是实现选择，不能反推规格。 |
| 原例NULL未评分；非键S字典负例缺失 | 确认并扩展 | F2P成功项只用顶层字符串，既无NULL也无深层map。新增独立发现：表HASH名M时合法深层S仍被gold拒绝。 |
| gold达成目标；与master一致所以瑕疵不算本题缺陷 | 推翻结论；master事实未核 | table_key_attrs的245–259与gold递归条件给出M主键反例。是否与未读master一致不影响公开要求。非键S字典校验被跳过后，DynamoType.size→bytesize(dict)预计内部AttributeError，不能简写成宽松接受。 |
| _validate_item_types是所有put_item/update_item的必经路径 | 部分推翻 | 本轮追加读backend models/__init__.py:377–474：update_item仅在item is None时调用table.put_item(data)，且data为键；已有item的更新走UpdateExpressionValidator/Executor或update_with_attribute_updates。Put、batch Put、transaction Put共享链仍确认。不能用所有update必经为由泛化回归范围。 |
| 离线make init rc2，环境待修 | 对所引最新grader条件已过时 | E/image.json离线wheel增层；G:424–584/N对应段两次editable安装完成；两角色安装rc0且完整测试。不是COPY即安装。正式actor、目标机镜像及wheel重建资产仍待验。 |
| 两个参数节点合并，F2P无参数化所以reward不受影响 | 身份合并确认；reward结论收窄 | G:643–644、N:741–742确为两节点，冻结parser split()[1]和冻结P2P只有一个...[set键。本次两个均pass，所以无已观测错分；不能推广所有候选。 |
| 与5620/5960同文件即同族相关性高 | 未核实，不用于分组 | 未获跨题commit/补丁/需求证据；不读被提及他题，不以共文件建立派生关系。 |
| 公开hints为维护者解释修法 | 对当前公开输入过时 | P/public_bundle的public_hints是工程/harness通用指令，user_prompt没有旧记录所述维护者提示；实际模型消息仍未知。 |
| ready_for_probe | 不沿用 | 本轮统一needs_review/static_review；gold深层漏修待CPU、actor待验。旧17分钟不是本轮成本。 |

封存后对本人初稿作一项证据强度限定：初稿第4节“混合pass/fail时存在遮蔽风险”只可保留为一般条件性解析疑问。追加核读N:718–754可见此-rA摘要将PASSED列在FAILED之前；同键的失败若如此排列将后写，不能仅凭字典last-write机制推出真实mixed状态会被遮成pass。本轮最终记录仅报告**两节点身份合并、35解析键对应36执行节点**，不声称已证reward漏洞，不把parser修订列为最高优先。此限定不改变gold漏修主发现、静态处置或初稿哈希。

本轮新增未被旧记录捕获的主发现是M主键/深层S合法反例；未执行。唯一优先下一步仍是初稿I1的base/gold/上下文正确实现对照。独立reviewer未读取或回填；本记录不代替其结论。



## 封存后单位限定（2026-09-20 UTC）

协调者复核指出初稿曾将原件峰值数值标为MiB。原运行产物只提供 `mem_peak_mb` 字段，本轮未核实其单位定义，也未作MB/MiB换算。初稿继续保持封存；最终引用应只保留原字段名及原数值，不据此宣称已确认的MiB或推导资源结论。该限定只修正审查文档表述，不修改运行原件、资源配方或评分。
