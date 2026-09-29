# 13721：旧结论逐项对照

在明确history release后，仅读A=env_overnight_20260916/L1_conan/records本题JSON、B=swegym_task_audit_20260920/conan_pilot/records本题JSON。

| 旧主张 | 判定 | 决定性证据与影响 |
|---|---|---|
| A1/2/4_17、B基线无变量/材料对应/恢复正常 | 确认本次范围 | loader153–166无profile_name；gold单生产文件投影，测试恢复/patch apply0、present1 |
| A23题面“唯一语义线索”强制stem，含后缀无公开依据 | 推翻绝对措辞，保留歧义 | profile_name既有参数是文件路径，basename含后缀自然；但Jinja新变量并未公开定义，题面宏传stem也是实质线索 |
| B23据旧路径API/所有profile均渲染完全推翻后缀争议 | 部分不同意 | 旧文件查找参数与新模板变量可以采用不同表示；上述依据证明含后缀合理，不证明stem不合理。因此本批仍保留23/24未知约定与可能误拒；不是已证gold错误 |
| A include语义完全不可推知 | 推翻 | loader逐文件递归、当前conf覆盖；最终include_default合理。B解释确认；此assert不检验子文件自身名或全局父名传播 |
| A24只通过conf观察、不限制算法 | 确认算法自由，限定输出规范 | 不强制basename函数；仍强制foo.profile格式。未执行stem替代解，不能称已实测误拒 |
| A25未测按名生成片段、B未测symlink | 确认 | 五次install全为普通文件；realpath取目标名静态可能通过却不满足共享symlink用例；初判另指出substring后缀误接纳风险 |
| A26及ready_for_probe以六P2P“充分”作理由 | 推翻充分性 | test_profile_template两个assert均非空常量；其他五项仍查有效行为。B收窄理由确认 |
| A27gold最小、2行context补充 | 确认局部正确性 | 未解引用profile_path取basename；每次局部context避免跨调用串值；未实际跑symlink/with-context宏 |
| A6_7_11临时TestClient/不访问conancenter | 确认本次测试场景 | helper每次重置输出、临时cache和默认profile，recipe无依赖。actor真实HOME/权限/软链接支持仍unknown |
| A19/20、B原始对照有效 | 确认 | ledger15/16：7收集/7解析，noop首个foobar断言失败、其余四步未执行；gold全部完成、6P2P保留 |
| A“去后缀只挂foo.profile、属于部分失败” | 纠正度量 | 一个F2P函数内第二assert失败即唯一F2P失败，后续步骤不执行；reward可全失。具体stem运行未做，不能计为五项独立test中的一项 |
| A/B建议模型探针/量化后缀和symlink | 不继承资格，保留有目的建议 | 本批唯一优先是先明确公开变量约定，非每题凑CPU；确定后再用symlink公开工作流检验，无需现在跑两套答案 |
| A其它回归建议与额外排除空 | 空排除确认，建议非强制 | 未把旧建议节点变成新P2P或资格标准 |

核心初判不变；与B在“已足以排除后缀歧义”上保留有理由的分歧。不是沿旧标签改判，也不是仅因公开reader提案而造新规范。

## 共同边界修正及未核范围

- 旧check3把“题面完整”记pass，不满足本批“实际输入”定义。计划题面可读，实际actor user/system/tool消息及hints仍unknown；规格问题归23。
- 旧check5关于本包无同族/某其它题不同文件的结论未核。本轮未读取其它题或跨池划分，记unknown，不能沿旧结论推导去重完成。
- 旧check29从题面无gold行/无PR指针推导“无泄漏”不足。实际actor工作树、未来Git历史、忽略资产和工具可见面未采集，29为unknown。授权私有审查见gold/测试/旧记录只记录usage，不记actor泄漏事件。
- 旧check31的conftest_user入口是仓库线索；本题原运行只说明普通noop/gold的可信setup/控制面attest成功，不证明恶意候选能否存活投影/保护并伪造评分。未执行攻击或读取完整当前恢复实现；判定unknown，额外排除列表保持空，不能照旧建议直接清整个测试目录。
- 旧环境pass/verified仅适用于其明确grader条件，不迁移到当前actor。旧成本minutes没有本轮工具观测，成本字段一律null。
- 未打开旧报告内的stage1工件、repo_level_findings、CODEX_REVIEW、repair_catalog、scope_reconciliation、analysis聚合或其它题；因此对这些原件未独立核实的旧主张明确保留未知。

本次仅新增读取本题history/refs.json以及其中两份sources旧记录全文。初判全文与SHA未改，历史未提供任何新运行；没有项目执行、测试、安装、联网或模型调用。reviewer尚未完成/未读取。

## 已释放旧记录身份
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-13721.json`；SHA256 `8bf347e6b499f67f4ea4c0599efce94e71c3b068fbb9fde616f00ba0e73431fc`。
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-13721.json`；SHA256 `9f0e0b3342c41fd46bd2888644e3f968a3cddc373762dd35d2f75bf64f194413`。
