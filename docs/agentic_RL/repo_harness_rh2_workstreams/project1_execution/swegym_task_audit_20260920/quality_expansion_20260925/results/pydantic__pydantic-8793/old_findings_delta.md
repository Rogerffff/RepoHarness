# pydantic__pydantic-8793 — 旧发现对照

root 已明确释放本题 history/refs.json；封存前稿 SHA256 为 c12547018acb4df0b9c271c2ebc4a3da40648037ad9e37c2c0ce8020a591f793，本阶段只读核对，未修改。唯一新增历史内容为 refs.sources[0]：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8793.json，SHA256=9d3f323be6432aa01c1a44e21e14d110669efc0890929b69581c2c5e4a2085f4，与授权值一致。该JSON内指向其他summary、R2/R3/R4、轨迹和其他题的链接未跟随。未读reviewer/根结果，未执行项目。

本文 S=当前静态源码/断言证据，H19=前稿已核本题09-19修订配方真实RH2原件，O16=本次获准旧记录的主张；O16 引述其他实验不等于此次读到其日志。

| O16旧主张 | 处理 | 决定性证据及当前表述 |
|---|---|---|
| 单FieldInfo捷径绕过Ellipsis归一化，base有缺陷 | 确认 | fields.py:174–193,371–419,513–519；H19三个F2P逐项FAIL→PASS。版本与patch/hash绑定已在前稿核对。 |
| BaseModel类体写法是题面未直述的自然扩展 | 确认并补公开依据 | docs/concepts/models.md:1041–1066 明确动静模型等价，:1320–1345定义必填；不靠gold反推要求。 |
| check3输入完整/pass | 收窄 | P/user_prompt内容完整只支持计划公开规格。实际system/user消息、hints交付和工具呈现仍unknown；规格充分性归23，不能用文本长度证明3。 |
| test_patch仅测试文件、gold仅fields.py、exclusions为空 | 确认 | Q两patch全文及H19投影/恢复；file_rules.additional_exclusions=[]。H19只证明自身交付，不证明任意actor输出路径。 |
| 与所列其他修复不同，check5全pass | 部分确认/其余未核 | 本包9066已允许base中含8793的字段修复与三测试，目标/gold不同但有版本依赖。O16提及5706/6043等未获跨题阅读，不沿其引用复核，也不据此宣布所有划分无重叠。 |
| install rc=2、安装需要网络，checks6/11 issue | 原条件未核；当前适用性过时 | O16引用的stage1日志未获本轮扩读。H19的pydantic-install-v1已改为editable pip+testing/testing-extra并使用PIP_NO_INDEX本地wheelhouse；本题noop/gold install RC均0、network=deny_all。只否定“这两次修订H19仍被安装阻断”，不否定早期曾失败，也不证明A环境。 |
| dirty_equals镜像预装，资产无碍 | 收窄 | H19环境及测试收集执行可支持该grader对应依赖；当前actor的解释器/插件/位置/权限未捕获。不能由gold全绿推导A全部资产合格。 |
| 某CC轨迹出现pytest/dirty_equals/typing_extensions缺失 | 未核原轨迹 | 仅见O16摘要，不把它当此次捕获的真实actor事实；保留check10/33 unknown。H19 grader不同用户与激活入口，不能替该轨迹翻案。 |
| 任何若干替代补丁都能过三F2P，check24 pass | 收窄 | 断言未强制gold内部实现，替代方向合理；O16没有在授权记录中给逐候选实测。前稿未执行替代解，当前不能保证所有合理实现无误拒。 |
| 无直接.default断言，因此只改is_required必过367且是错误修复 | 确认局部缺口，纠正推论强度 | 新增只断言schema/is_required、实际selector不含test_annotated/test_create_model，支持缺少目标运行时/边界覆盖。未复核O16的全文件零命中统计，不把其全绿预测升级为运行事实。补读main.py:200–226发现model_construct也是先检查not field.is_required()，_generate_schema:1074–1078同样受此门控，因此“仍必把Ellipsis流入model_construct/默认schema”不能直接成立。fields.py:558–582的repr确会显示非Undefined default，但是否构成必须拒绝某实现，需要与公开可观察行为对应，不能仅因内部状态不同于gold定错。 |
| check26=issue，只因未覆盖其他merge调用者 | 纠正分类 | 这是check25覆盖风险；没有展示gold使某合理旧行为base通过、gold失败的证据。check26仍unknown。 |
| _attributes_set仍Ellipsis证明gold不彻底 | 收窄/不采纳缺陷定性 | fields.py:180在原构造中本已保留显式传参，:412–417再合并时经__init__归一化；O16也承认当前无害。仅存Ellipsis不证gold错误或缺陷，不新增清空内部属性的评分要求。gold局部对应性有正证据，完整性仍未知。 |
| check29无泄露/pass | 收窄 | 旧leak扫描的原范围与实际actor材料未取得；A泄露unknown。审查者此次可见gold/hidden/O16另列usage，不能称solver无泄露。 |
| check31静态残余面/R4 | 未核 | 本轮H19有受保护测试与runner完整性局部证据，但R4未展开/未访问，不能宣告当前控制面安全或漏洞成立。 |
| ready_for_probe、20分钟成本 | 不沿用 | 本批是static_review/needs_review、development_diagnostic；O16成本非当前工具观测，当前token/费用/CPU时间为null。 |

对自己前稿的增量：维持原例/断言一致、覆盖有限、A未知的初判；新增main.py:200–226、fields.py:558–582的调用路径证据，进一步限制“只改is_required一定导致model_construct错误”的旧推论。前稿关于真实默认/工厂与单/多Field覆盖歧义保持未定；不把它升级成gold回归。没有证据需要修改封存前稿的结论。

唯一优先下一步保持：任务二按正式actor入口核对实际消息、初态/导入来源，并执行公开原例及缺值验证；Python3.8使用公开旧测试已有typing_extensions.Annotated。它直接改变A未知状态。旧记录要求“为了拒绝非gold内部状态而直接补default哨兵断言”不自动采纳；不执行也不修改评分。所有新运行/模型工作仍由任务二处理。
