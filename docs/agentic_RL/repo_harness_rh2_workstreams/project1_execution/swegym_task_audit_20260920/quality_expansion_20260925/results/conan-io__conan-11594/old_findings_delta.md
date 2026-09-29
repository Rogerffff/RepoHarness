# 11594：旧结论逐项对照

协调者在三份初判SHA核定后明确release；旧记录简称A=env_overnight_20260916/L1_conan/records本题JSON，B=swegym_task_audit_20260920/conan_pilot/records本题JSON。

| 旧主张 | 判定 | 决定性证据与影响 |
|---|---|---|
| A1新增测试文件等于材料版本issue | 推翻此归类 | test.patch新建文件正常；base、gold、测试、stage HEAD一致。恢复边界归17，不能把不存在于base当错版 |
| A2/20 base确有错目标，gold有分差；B同一对照 | 确认，限运行条件 | 初判附录reference_v1账本各行1及日志：noop1fail/5pass，gold6pass；错在Ninja Multi-Config默认目标 |
| A4_17旧stage1裸checkout边界 | 旧原件未核；对本次已过时 | 原stage1脚本不在release范围；本题reference_v1 attest restored0、apply0、测试present1，gold生产文件投影存活，不能继续说当前恢复已坏；不因此保证所有候选安全 |
| A19参数名空格截断碰撞 | 确认原始身份问题，现选条件已覆盖 | 原expected确为[Ninja短名，binding原件明确两完整node均通过；B superseded判断成立 |
| A19“失败最后覆盖”，但又说Makefiles单独回归完全不可见 | 推翻后一无条件结论；旧parser未重新执行 | 两句逻辑不相容；现绑定raw_node_states逐项可见。B反驳成立，但不声称已对旧stage1跑mutant |
| A23/B公开核心充分 | 确认核心，保留范围歧义 | 题面明确test可用；旧/新helper同名，recipe import缺失，日志更像新helper。不能强制两个helper都修 |
| A24把全局is_multi_configuration排除Ninja当“等价正确”方案 | 推翻 | _build103–111依赖其保留--config；该错误方案可能过target断言但破坏配置。B已指出此缺口，确认 |
| A24/B不强制唯一内部实现 | 确认主要结论，收窄绝对pass | 条件写法自由；POSIX固定引号substring仍可能拒绝等价命令格式，初判静态风险保留 |
| A25仅生成器字符串/不跑CMake | 确认边界，推翻“与gold一样即弱”的暗示 | 根因正是生成器默认目标，按名字修并非投机；真正漏测是配置/显式target/skip/真实执行 |
| A26/27四P2P保行为、gold最小 | 确认有限范围 | 4P2P+两Ninja逐node已读；未验证所有回归。人工None状态不能单凭__new__当合法生产回归 |
| A6_7_11测试无需CMake/Ninja/公网 | 确认评分窄路径，非actor开发结论 | Mock.run仅记命令，临时preset；真实公开conan build仍需相应工具 |
| B环境verified、模型探针优先 | 确认已引用grader事实；探针资格不能继承 | 本批无actor初态/入口验证；唯一优先下一步仍是公开Ninja Multi-Config实际用户流程补配置与真实执行证据 |
| A建议测试列表/额外排除为空 | 空排除确认；测试只是建议 | 不把未读旧路径建议当新P2P或强制资格；不执行旧mutant/恢复/安全实验 |

初判核心判断未改变。另纠正初判阅读数量笔误：“5个公开元数据/提示文件”应为4个（public_bundle、base_identity、user_prompt、environment_brief），另读base子树相关文件；不是少了第五份已授权原件。

## 共同边界修正及未核范围

- 旧check3把“题面完整”记pass，不满足本批“实际输入”定义。计划题面可读，实际actor user/system/tool消息及hints仍unknown；规格问题归23。
- 旧check5关于本包无同族/某其它题不同文件的结论未核。本轮未读取其它题或跨池划分，记unknown，不能沿旧结论推导去重完成。
- 旧check29从题面无gold行/无PR指针推导“无泄漏”不足。实际actor工作树、未来Git历史、忽略资产和工具可见面未采集，29为unknown。授权私有审查见gold/测试/旧记录只记录usage，不记actor泄漏事件。
- 旧check31的conftest_user入口是仓库线索；本题原运行只说明普通noop/gold的可信setup/控制面attest成功，不证明恶意候选能否存活投影/保护并伪造评分。未执行攻击或读取完整当前恢复实现；判定unknown，额外排除列表保持空，不能照旧建议直接清整个测试目录。
- 旧环境pass/verified仅适用于其明确grader条件，不迁移到当前actor。旧成本minutes没有本轮工具观测，成本字段一律null。
- 未打开旧报告内的stage1工件、repo_level_findings、CODEX_REVIEW、repair_catalog、scope_reconciliation、analysis聚合或其它题；因此对这些原件未独立核实的旧主张明确保留未知。

本次仅新增读取本题history/refs.json以及其中两份sources旧记录全文。初判全文与SHA未改，历史未提供任何新运行；没有项目执行、测试、安装、联网或模型调用。reviewer尚未完成/未读取。

## 已释放旧记录身份
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-11594.json`；SHA256 `58e7ed564888683294caf9c5e0a11b78830cc41e31b533a30f528b284438d1f2`。
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-11594.json`；SHA256 `abb4c739ed6579b671d48127225a3f08ef8e30fcfa6b7bcf0933ec1fecd7eedd`。
