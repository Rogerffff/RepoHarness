# pydantic__pydantic-5706 — 历史主张复核

2026-09-21。协调者核实前稿并登记SHA256/保存时间后，才读取本题history/refs.json及其中明确列出的两份记录。封存分析未改字节。路径缩写沿前稿。

H16=`R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-5706.json`；H20=`R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-5706.json`。收到追加范围授权后，仅沿报告明确引用读取本题旧候选和轨迹：`C=R/runs/env_probe_20260909_codex_backup/ledger/logs_cc/pydantic__pydantic-5706/candidate.diff`，`S=同目录/stream.jsonl`；H16引用的final_sync同路径副本只做字节校验，两者相等。未读catalog、verification汇总、跨题材料或未明确定位的独立实验文件。轨迹工具调用/输出及相邻文本构成本轮新增答案暴露，不作为新模型实验。

候选SHA256=`92a9d03601cc8b13094e0002af19b4592c0b4dd3fcd785b55c461ec09d04a20b`；轨迹SHA256=`1ef68bcc9debc0c438b91613981eba429d58f1470063c98be144962402d5f1fd`。前稿SHA256仍为`5060a772bede4fd9ac8d342019409796bd2fffcc1e5ff1697cc6ad5880d8dea9`。

| 旧主张 | 处置 | 新证据与适用边界 |
|---|---|---|
| H16：题面充分、唯一要求schema和JSON均成功 | 推翻此唯一性；确认H20纠正 | 当前prompt明确称schema失败看似正确并提出JSON也应拒绝；F2P却选成功。支持方案可使条件前提消失，故不是形式矛盾，但窄拒绝方向未被明确排除。公开阅读与本轮私有前稿在看历史前都记录了方向歧义。 |
| H16/H20：两Sequence F2P确实捕获初态问题 | 确认，收窄运行归因 | 当前原始noop日志4061、4139均在model_json_schema调用失败；第二条尚未触发JSON验证。gold日志4093-4096支持完整新增用例通过。不能称noop已执行并复现第二段JSON错误。 |
| H20：旧collections.abc.Sequence→list候选有局部Sequence回归 | 候选与轨迹原件确认，限旧局部环境 | C:2387-2398只在生产代码新增该映射；S:6871记录改动，6904-6905记录公开Sequence测试6 failed/10 passed/635 deselected，8165明确range拒绝、tuple/deque变list。C还含pdm.lock/pyproject和测试变化，不能把整个候选叫source-only。S:12069、12093之后才改成功容器/生成器测试，晚于上述失败。前稿L1改_sequence_schema且allow_any_iter=True，不是同一补丁；历史只能支持相近失误机制。 |
| H20：旧候选官方满分、隔离source-only对照base/gold各16 passed | 仍为报告转述，原件未核 | H20仅给cc_candidate_grading.jsonl:19,44文件名及verification.json#historical_runs.L3_5706摘要；未明确定位到获准独立原始对照文件，本轮未扩搜。旧独立swegym_probe不是09-19 RH2，不能将RESOLVED_FULL或16/16升级成当前评分/受控对照事实。 |
| H16 check24：该不同路径候选通过证明合理替代解可接受 | 推翻“合理解实证”的推论，确认H20限定 | 接受不同实现只证明无该路径锁定；历史自己报告它破坏Python旧行为，不能当正确替代解。前稿提出的无重复metadata回调分流方案仍只是静态合理路线，未运行。 |
| 273 P2P足够覆盖Sequence回归 | 不成立；确认旧覆盖缺口 | 当前grading全参考只在test_json_schema.py，base该文件没有Sequence；公开test_types:1876-1891、2010-2144明确保护Python容器和输入边界。原始执行也只运行JSON Schema模块，未查的行为不能补pass。 |
| H16：直接把generator/sequence_str等全部加入硬P2P | 暂不照单采用，确认H20的争议保留 | generator文档116-118与基线测试相反；虽前稿选择维护明确旧实现，不宜静默将此冲突升级成新验收标准。edge字符串测试<3.9跳过；当前Python3.8引用也未执行该模块。优先取无此冲突的range/tuple/deque。test_types中的Sequence负例主要是is_instance_of与元素解析，sequence_str来自edge用例，不能混写。 |
| H16：Any/裸Sequence改动必然属scope creep | 不支持必然性；记录分派差别 | gold对同一抽象做合理泛化不自动越界，亦不能成为隐藏新增要求。更精确地说裸typing.Sequence可先由_std_types_schema:557-600的map处理，而参数化Sequence[Any]的origin为collections.abc.Sequence、走另一分派；不应把二者都称为gold所改“裸Any分支”。 |
| H16：_generate_schema与generate_schema差别只是缓存/递归语义疑点 | 保留风险、以本轮具体路径替换模糊归因 | 前稿G2追到prepare/core/json hooks在公开入口194-234、312-328，gold回调用私有入口会绕过这些步骤。自定义items的JSON导出仍为静态推断，非原int例回归，尚无CPU事实。 |
| 旧安装rc2、必须联网是当前阻塞 | 在现引grader条件下过时 | 已核本题09-19原始ledger/log/recipe、哈希，deny_all中两角色安装rc0，gold测试rc0；不是跳过安装，实际editable安装项目并消费测试依赖。不可沿用“改成no-op安装”的旧建议。 |
| 旧actor PATH错、缺core/pytest；当前actor也坏 | 部分旧原件确认；当前未知 | S:6896-6897确实由/opt/miniconda3/bin/python报No module named pytest；相邻输出记录临时pip安装后再跑。其它旧core/PATH主张未逐项追证。当前grader导入/权限与正式actor工具shell不同，不能证明actor已修或仍坏。维持actor验证需求。 |
| 镜像pdm.lock/pyproject脏状态必须全部清除 | 确认存在，动作不沿用 | 当前noop日志132-138和3502-3512证实环境差异；ledger gold投影仅_generate_schema.py、noop无投影。未核当前提取逻辑的全平台范围，不能要求清理所有预存环境改动或新增排除；本题业务提交路径已可交付。 |
| H16：无泄漏、同文件其它题关系、控制面漏洞 | 未核实/不扩大结论 | 本轮没看实际镜像答案资产、跨题源文件、旧联网轨迹或控制面攻击。已知源码可读和测试恢复文件范围，不等于这些完整结论。 |

## 对前稿处置的改变

`needs_review/static_review`、`development_diagnostic`不变。方向澄清仍先于把模型失败解释为能力不足。G2只列扩展边界，不将其当本题必修原例失败或gold已证错误；独立reviewer未启动，reviewer结论为未知。

历史带来的实际调整在证据层次和唯一优先CPU设计：局部错误行为由静态预测提升为**旧轨迹工具输出确认**，但当前RH2漏判仍未实证。已核原候选混有元数据和测试改动，后续应在精确base `70e7e99ca1861ad71520cc8fcf1a2fb913abbc10` 上独立重建仅一行 `collections.abc.Sequence: list` 的生产补丁，不重放那些测试/元数据变化。让base、gold和此source-only候选消费同一pydantic-install-v1配方及其既有环境元数据，比较官方分数与**range成功、tuple/deque保持**。前稿L1仍是独立备用设计，不新增第二个并列优先实验。generator/错误文案因公开材料冲突留作次级诊断，不直接补进硬评分。

最小公开行为类定义（建议，未运行），Python3.8/core0.31.0、pydantic-install-v1；每断言独立记录，gold/base/候选同条件：

```python
from collections import deque
from typing import Sequence
from pydantic import BaseModel

class Model(BaseModel):
    values: Sequence[int]

assert Model(values=range(3)).values == [0, 1, 2]
assert Model(values=(1, 2, 3)).values == (1, 2, 3)
assert Model(values=deque([1, 2, 3])).values == deque([1, 2, 3])
```

冻结官方参考集保持原样观察，以上为附加诊断；只有确认真实得分与公开行为分离后，才讨论最小评分修订。公开支持/拒绝方向不能由CPU结果替代决定。本轮未执行实验或改题。
