# Pydantic 第八包静态收口

5662为有条件静态开发候选；6043、8316优先处理质量问题。三题仍needs_review/static_review、development_diagnostic、ready_for_probe=false。没有actor、训练或正式评测批准。

| 题目 | 关键判断 | 唯一优先后续 |
| --- | --- | --- |
| 5662 | ANY精确例和NotImplemented机制对应；模型分支保留，一般matcher覆盖不足 | actual actor公开ANY/一般matcher与dict/object护栏，同一开发验证 |
| 6043 | 递归排序仅验一层properties；新排序与旧字段保序的契约优先级未明确 | 先定properties及最终wrapper范围，再设计验收，无新CPU |
| 8316 | gold修缩写边界，同时删去大写→数字分隔；A1从a_1变a1可影响真实alias | 一个私有base/gold数字别名工作流对照，actor资格另采 |

5662已有dict不等P2P，不采纳L1“127项全是模型比较、递归委托即可满分”。pilot虽已纠正dict，也不能因此抹去一般matcher与m!=ANY缺口。完整gold模型类型/origin、字段与私有属性逻辑保持，26unknown、27unknown保留局部正证据。题面带方案是事实，训练价值/难度没有观测。

6043公开reader和主审指出docs/usage/models.md:964字段保序承诺，reviewer交叉后直接回读并承认初审漏项。root保留23/24契约冲突及条件性误拒风险，但将26 issue收窄为unknown：旧文档不能独自决定新排序任务是否授权行为改变。递归普通映射、保properties序是有公开依据的保守解释；全映射排序也是新题面可能意图，先澄清再验收。gold保列表位置合理，不能泛称不排list就少实现一半；prefixItems与默认数据列表语义应保持。两批量wrapper追加$defs/title/description产生固定非字典序，不等于不确定。旧properties-only fake满分只是获准历史记录转述，原实验未重读/执行。

8316主审与reviewer均独立发现[a-zA-Z]→[a-z]变化与alias调用链；root采纳reviewer26unknown，保留具体风险，未把静态行为改变升级为已证违规回归。旧17个to_snake参数数字前均小写，无法保护A1/API2；附带to_camel例误解可由公开原名/实际别名契约解释，不需要私有维护者hints，更不扩成任意输入key归一化。私有对照只需一个大写数字代表与HTTPResponse原例，结果不能认证独立actor。

历史install-v1三pair均安装RC0、test RC1→0；5662为141pass/1fail/26skip→142pass/26skip，6043为305pass/1fail/1xfail→306pass/1xfail，8316为158pass/1fail/14skip→159pass/14skip。各1 F2P；expected P2P分别127/303/143，全部原ID完成且无expected跳过。实际选定文件为test_main.py、test_json_schema.py、test_utils.py，均用pytest -rA --tb=short -vv -o console_output_style=classic --no-header；pytest-sugar摘要不可误套普通pytest计数。语义按风险读相关P2P，不将这些数目冒充全量语义审阅。

root核原recipe前后差异、recipe.json/image.json/build.log及noop/gold字节同一性：只见安装路线变为editable pip与candidate testing/testing-extra依赖，测试/selector未改。派生actual image ID分别b58abf…、faabec…、20d1a0…，完整摘要与base/manifest身份分列于record。角色还核原pyproject/pdm.lock初态差异；root未人工逐锁文件依赖审计，不能称干净actor。

六份主审card/record核交付SHA并归档后才改，清理5662/8316 checks2/20误带6043及5662的无关regex表述，保留所有封存初稿、delta与review。见[修订链](coordinator_revisions/pack08_pydantic/revision_log.json)、[输出检查](pack08_output_verification.json)、[来源检查](pack08_revision_provenance_verification.json)及[root阅读边界](reserve20_coordinator_read_notes.md)。五个审查角色均显式Astra/high/fork_turns=none，流程只证明请求配置和封存来源，不证明后端模型/OS隔离或无偏差。

[后续提案](pack08_followups.md)未执行或派发，任务二归Claude B。至此新增12/20、累计24/32完成；新增中期报告保持9题提交时点，不回写该快照。
