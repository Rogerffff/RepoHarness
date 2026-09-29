# conan-io__conan-13788 — 旧结论差异

初判 SHA256：`508a697338f38cdde6e9b6cc111654d60d4f72a64be8e6e0312707a0aee81c95`，保持不变。协调者释放后只读 `runs/swegym_quality_expansion_20260925/history/conan-io__conan-13788/refs.json` 指定的 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-13788.json`（旧记录），原SHA256 `7876fdd3127594308e30a856ea2fd8c7d4d8a5e1ef807dddb6f3a826c9dd4748`核对一致。未跟随其中stage1/扫描、hints、repo_level_findings、其它题或reviewer链接。

证据根为 `/Users/roger/Desktop/claude-code-verl-stage0h`；P=`runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788`，V为同级private目录。源码引用相对P/base。初判原运行指本题09-19 RH2精确noop/gold，不能替代未读的旧stage1原件。

| 旧主张及位置 | 处置 | 决定性证据与本轮边界 |
| --- | --- | --- |
| public_view、checks23：用户期待禁止，所以gold与公开目标反向，禁止解应算合理 | 纠正/收窄 | 用户以疑问表述期望；graph_manager.py:21–43,359–367已有同上下文profile覆盖，公开graph_lock_build_requires_test.py:52–144允许host/build双节点、179–194允许不同消费者用不同版本。不能以疑问覆盖旧合理语义；全局禁止同名不是已证明合法替代解。缺具体复现/context仍是问题，但“只有记忆能解”未成立 |
| checks2：base存在按name覆盖问题、F2P失败 | 确认限定场景 | graph_lock.py:535–554与graph_builder.py:90–101根因链成立；原noop目标True只在第二次install后289行缺tool4.0，gold通过。没有用户具体锁文件，不能断言原报告一定是同一context场景 |
| checks3、input_incomplete：有6010字不可见hints，决定性澄清都在里面 | 未核并拆分 | 本轮未释放该hints原件，不读取/传播其内容；旧记录的字数和内容描述只能作为未核主张。计划P/user_prompt缺fixture已确认；actual actor消息仍unknown，归check3；可推导性另归23 |
| checks1、4_17：同PR、纯测试路径、gold可交付 | 确认局部/拆分 | 本题base/test/gold/candidate绑定直接核对；纯test与source路径分离，历史可信恢复有证据；同PR来源未另查，实际actor可写/可交付unknown，4/17分别记录 |
| checks5：无同族题 | 未核 | 两题当前不同功能不足以证明全局不重复或无留出重叠，check5 not_checked |
| checks24：联合键、分桶等均可通过，无唯一实现 | 收窄 | 无实现形状断言可确认，但替代解未运行。按context筛选/合理父context处理是静态合理路线；不声明所有正确实现都能过，check24 unknown |
| checks25：只True是F2P，False是P2P；原始profile/recipe组合未测 | 部分确认/收窄 | True/False与预期身份核对无误；但没有原始recipe/profile，不能指定某个未测组合为“题面原始场景”。本轮逐项读完整10项，明确新断言只查tool4.0存在，未查tool3.0/build边、节点context与cache变化；build工具普通子依赖也缺失 |
| checks26：9个P2P覆盖双context，故回归pass | 纠正为未证 | 旧两context测试的protobuf为空recipe，新tool同样无普通requires。gold fallback=CONTEXT_HOST，普通Requirement.context=None，而build节点的普通子依赖继承node.context=build（requires.py:14–32；graph_builder.py:193–208,437–479；GraphLock:296–324）。该具体调用链未被10项覆盖。check26 unknown且有高优先静态回归疑点，不写成已跑失败 |
| checks27：gold正确、最小、不依赖未交付改动 | 收窄 | 文件/候选身份及局部True修复和10项pass成立；整体正确/完整不能成立，受前述build普通依赖疑点约束。保持27 unknown，不用最小diff证明安全 |
| checks29：零文字命中故无泄漏 | 纠正 | 未复核leak扫描；即使成立也不审实际actor资产/消息/工具，check29 unknown，审查侧private暴露单列usage |
| checks6_7_11、19、20：纯本地Python、10/10对9/10、ID无碰撞 | 确认本题原运行范围 | 直接核09-19原logs/ledger：安装末命令RC0，10个完整ID、True失败→pass、无skip/xfail，测试命令一致。当前actor依赖/UID/HOME/资产/网络仍unknown；旧stage1扫描未核，不继承其完整环境结论 |
| checks31：conftest_user控制面和default_profiles影响 | 静态入口确认，复制的2.x说法纠正，实际利用未核 | 释放历史后补读本题.gitignore:1、conftest.py:8–19,178–201；有try-import tools_locations，未见default_profiles入口；tools.py定向检索也无default_profiles命中。旧记录先称1.x不消费default_profiles，随后又说本题受其影响更大，后句不获本题源码支持。存在可选Python导入入口不证明ignored-file被当前projection带入或可控制score |
| 建议删除conftest_user/全tests git clean -xfd | 不直接采纳 | 需要当前交付/权限/恢复的具体证据；不做攻击试验/配方修改，不增加路径排除，additional_exclusions=[] |
| proposed_regression_tests：py_requires共用locked_requires，应扩跑 | 未核/不采用为确定关系 | 本轮读到graph_lock.py:584后的独立python_requires访问和单独字段；没有证据证明该路径共用本次lock_node的refs索引。旧建议中的另一路径未打开，不从名称推导调用关系或全仓验证需求 |
| disposition：不补题面主要考记忆，盲解或禁止解作为反例 | 纠正证据层级 | 公开旧代码可支持推理，未做模型/替代解实验；全局禁止解违反公开旧行为，不是公平误拒的已证反例。改为needs_review/static_review，保留具体复现缺失与gold风险 |
| costs.minutes=22 | 不继承 | 旧自报与当前成本区分，当前token/费用/CPU观测null |

初判不改写，主要建议未变：唯一优先下一步是任务二按已给三节点公开fixture，验证root→build工具T→普通依赖D的两profile锁重放，做同条件base/gold对照并记录lock边context和错误位置。它能直接改变check26与27；旧记录“P2P覆盖好/gold正确”的断言不能替代这个证据。

历史后新增的是本题可选conftest_user/tools_locations入口的静态确认。未证明当前actor能交付此ignored文件、无资产污染或攻击成功；不新增CPU任务、路径排除，也不把此前未取得的hints/阶段1证据补成已知。公开目标仍按条件解释，实际模型表现和筛查漏检/误拒/偏差仍unknown。
