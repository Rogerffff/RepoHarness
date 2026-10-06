# conan-io__conan-15422：独立复核

2026-09-21。**同意主审的 needs_review / static_review、development_diagnostic 静态候选处置。** 主审的决定性证据与独立初判相符；没有发现需要改为拒题的确定性缺陷。保留默认值、多配置 jobs 更新、实际 CMake 消费及 actor 条件的未验范围。建议澄清一处边界措辞，并把后续 actor 开发验证与 grader 反例评分分开记证据。

## 阶段与阅读范围

第一阶段在收到他人结论前写入 `reviewer_initial.md`；第二阶段前只读校验为 SHA256 `1dd48d68b33b55ebc1861d5e4095e56e9b93d9d2cfc3d6e7ed01946733a6c250`。本轮没有修改该文件或主审产物。

收到协调者开放消息后，读本题 `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`。沿 delta 引用读取同题旧件 A（`env_overnight_20260916/L1_conan/records/conan-io__conan-15422.json`）和 B（`swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-15422.json`），未扩大读取其它题或仓库级旧总结。

以只读标准库比较 S2 原始三份 JSONL 第 38 行与本题包，public/grading/validation 均相等；test.patch 与 grading.test_patch、gold.patch 与 validation.golden_patch 均相等；F2P/P2P 数为 1/40。`analysis_before_history.md` 的实算 SHA256 `89895705a8a99d0a807f2f77f33bb22614a64a5b64687f7afa1739ff0a034878` 与 delta 登记一致。另定点复读 conf 的 None 处理、默认生成器、conftest 的工具选择、用户 preset 功能测试和 `.gitignore`。没有执行项目代码、测试、安装、Docker、SSH、模型或反例。

下文 `B` 为本题 PUBLIC/base，`P` 为本题 PRIVATE，`A` 为 analysis_before_history.md，`D` 为 old_findings_delta.md；绝对根及日志 N/G/L 沿 reviewer_initial.md 的定义。

## 决定性主张逐项复核

| 主审主张 | 结论 | 核对原件与实际支持范围 |
| --- | --- | --- |
| 材料、base、补丁、S2 对应（A:9-13；checks 1/2） | 同意 | 本轮直接比较三份 S2 第 38 行及内嵌补丁；第一阶段已核 base、gold/log 哈希。base `_build_preset_fields` 无 jobs，与 N:932-940 的 KeyError 一致。Conan 2.0.14 是报告环境，2.1.0-dev 是指定 base 的运行版本，不构成目标已修的证据。 |
| 配置来源可从公开材料推出（A:11-12,35；checks 23） | 同意，保留适用范围 | B/conans/model/conf.py:55、build/cpu.py:8-28、cmake/cmake.py:11-23 共同支持配置优先和 CPU 默认。公开读者在未看 gold 时也独立指出此约定，不能把“题面没逐字写 tools.build:jobs”直接判成隐藏要求。跨 generator/特殊数值仍须分别判断。 |
| F2P 真正执行生成路径，不是只验 Mock 或文字（A:18-22；checks 18） | 同意 | test.patch 全部新增断言已读；TestClient 经同进程 CLI/API 执行，成功退出后读取临时目录真实 JSON。requests/getpass/IO Mock 不伪造 jobs。这里的“真实 CLI”是 CLI 实现路径，不代表已验证外部 conan 可执行文件或 actor 工具启动。 |
| 唯一 F2P 与全部参考 P2P 的运行结果可信（A:47-56；checks 19/20） | 同意，限定旧 grader | L:1-2 与 N/G 测试段对应 F2P 0/1→1/1、40 P2P 无失败。gold 为 41 passed、3 skipped、rc=0；3 项 skip 均非参考。第一阶段已核原日志哈希。parsed=42 不能作为测试执行数；主审没有这样使用。 |
| 没有绑定 gold 内部形状的误拒（A:35,39；checks 24） | 同意其有限表述 | 新断言只读题面指定 JSON 层级和已有配置值，不检查导入/变量/helper 身份。上游传值并同时覆盖新建与更新是合理替代路线。本轮未执行替代解，因此不把 checks 24 的 pass 扩成“所有正确实现必过”。 |
| 默认、其它显式值、多配置追加/替换值、实际构建缺覆盖（A:24-33,41；checks 25/26） | 同意 | F2P 仅首次安装/42/第一个条目。B 的 singleconfig/multiconfig 测试保护数量、名称、configuration 等，没有 jobs oracle。“只在显式配置时写 jobs”及“只改首次创建”是有依据的部分实现；是否实际获满分仍未跑。 |
| gold 最小且覆盖两条生成路径（A:43；checks 27） | 同意；澄清 None | gold 只改 presets.py，使用已交付 helper；presets.py:54-68,95 共用 `_build_preset_fields`，因此新建、单配置重建、多配置插入/替换均受改动。不改变 testPresets。普通输入上未见依赖未交付或其它需求混入。None 的精确说明见下一节。 |
| NMake/Visual 与真实 CMake 兼容性仍待核 | 保留未知，不能升级为坏 gold | base 的 CMake helper 确实排除 NMake 的 -j，并另用 Visual /MP；这些是调查线索，不足以证明 preset.jobs 无效、产生错误或必然资源超额。本题参考测试不执行这些后端。 |
| 合法修复不会被官方恢复覆盖（A:58；checks 4/file_rules） | 同意所观测范围 | N:689-695、G:715-721 只恢复官方 integration 文件；L:2 的 included_paths 为 conan/tools/cmake/presets.py、ignored_paths 为空。无需修改测试或系统文件即可交付。没有证据要求本题额外路径排除。 |
| 原镜像已有评分成功，不代表 actor 已验（A:56,60-71；checks 6/14） | 同意 | 身份是 rh2grader/54322、deny_all、Python3.10.14、2 CPU/4 GiB；解释器前缀可写是 grader 事实。candidate.apply_user=agent 不能证明完整 actor shell/开发体验。实际启动、消息、hints、镜像资产仍未验。 |
| conftest_user 是相关控制入口，但当前利用性未知（A:58；checks 31） | 同意 | B/conans/test/.gitignore 明列此文件；conftest.py:235-239 合并 default_profiles，TestClient:425-431 消费。旧件“能存活并执行”的结论依赖特定清理/投影，当前未经复验，不能仅从源码导入推出评分漏洞成立或不存在。 |
| 候选只用于开发诊断，不是训练/最终评测准入 | 同意 | card、screening_record 的 disposition.scope/state、usage 与证据范围一致。环境通过不替代质量判断，未用静态阅读推断模型能力或成功率。 |

## 需澄清与继续保留的内容

**澄清 A:43 的 `None/0/负数` 并列措辞。** `build_jobs` 把 `_cpu_count()` 作为 default 传给 `Conf.get`；B/conans/model/conf.py:314-315 明确将已 unset 的 `None` 回退到该 default。因此普通 `tools.build:jobs=None` 路径不意味着 gold 写出 `jobs: null`。A 的原文也没有明确声称写 null，这里建议精确化为“未设置/None 使用 CPU 默认；0、负整数及特定后端的语义尚未验证”。这不改变主要处置，也没有把未知变成 gold 故障。

**默认需求的依据来自公开约定，不能扩大为所有后端无条件相同行为。** 对题面普通 Unix Makefiles/Ninja 正整数路径，默认沿用 Conan CPU 机制有充分公开依据；允许有依据的后端兼容处理。没有必要把 gold 的每行实现抄进公开题面，也不需要因所有后端尚未实测而阻断范围明确的 Linux 字段诊断。

**评分薄弱的证据仍是静态候选。** 独立初判与主审都提出显式配置限定、硬编码和只修首次分支等反例方向，但没人执行。本题新增断言也未严格区分整数 42 与浮点 42.0。是否构成实际错误接收，应同时观察公开行为失败与官方评分成功；不能把预测填成实测结果。若补测试，应优先加入其它正整数、默认值和同名更新等原需求/旧行为断言，而不是扩大到新的跨平台政策。

**实际消费不等于性能证明。** public_read 的可选功能测试路径准确：`test_presets_inherit.py:9-93` 使用 CMake 3.23、配置和构建继承的用户 presets，并运行示例；conftest.py:298-299,371-379 会区分配置路径缺失的失败与显式禁用的跳过。该测试通过能提高 schema/后端消费可信度，仍不测并发启动数或速度倍数。它不属于现有 40 P2P，也不是纯 JSON 字段测试的必要工具条件。

## 历史变更判断

已沿 D 的引用直接读同题 A/B 两份旧 JSON，确认 D 没有把旧主张改写成更易推翻的版本。

- 同意 D:11-14 的对应关系：旧 A 的规格问题本身已承认可从代码推出；旧 B 合理收窄此归因。漏默认、单值和第二配置 jobs oracle 确为旧件所记，本轮有更明确断言映射。40 P2P 的数量不证明新增 jobs 回归受全面保护。
- 同意 D:15：CPU 默认随资源变化符合既有契约，不足以推出稳定性缺陷或强制再跑无目标资源实验。这也不等于 actor 资源/默认值已验。
- 同意 D:16 的保留：当前日志/账本足以确认无参考缺席或跳过影响；旧 stage1 `[1]` 假键机制未重新核，不宜写成已经再现该 parser 问题。
- 同意 D:17-18：纯 Python 字段测试的依赖与真实 CMake 构建分开；旧 raw.hints_text 的社区回复与当前 public_hints 的操作指令不是同一字段内容；旧 ready_for_probe 不能沿用为本批 actor 已验。
- 同意 D:19-21：未核 14296 的具体需求/补丁血缘，不能凭同文件宣布答案泄漏或强制同侧；静态导出无 .git 不足以排除真实镜像泄漏；conftest_user 的源码入口和最新评分链利用性要分开记录。

本轮没有读取旧 stage1 运行目录、14296 材料或真实镜像，以上保留项没有被补成 pass。

## 最小后续实验与记录方式

同意主审优先做窄对照，建议分两种执行身份登记，避免一个“下一步”产生证据混用：

1. **实际 actor 公开开发验证。** 由统一入口记录镜像/配方、HEAD、UID/HOME/cwd、PATH、解释器和工作区包来源、临时目录权限，以及真正提供给 actor 的提示。用公开 TestClient/CLI recipe 做 Unix Makefiles：RelWithDebInfo + jobs=16、另一正整数、未配置；断言目标条目的 `jobs` 为整数且值对应当前配置或同环境的既有 CPU 逻辑。随后在同一生成目录做 Ninja Multi-Config 的 Release=2 → Debug=7 → Debug=3，检查数量不重复、Debug 的值刷新且 Release 条目保留。可运行原有 singleconfig/multiconfig 窄测试。无需公网、GPU 或 C++ 编译。
2. **独立 grader 负对照。** 在审查用途的临时候选中，仅在显式 conf 存在时添加 jobs；保留所有其它结构。沿统一评分链记录补丁哈希和官方 F2P/P2P 得分，并另做无 conf 的公开生成检查。只有出现“官方通过、默认仍缺失”才将本项从静态漏测候选升级为实测错误接收；不能把这个审查者构造的候选传给未见答案的模型 solver，或计为独立求解。

跨生成器实际构建、0/负数精确语义及镜像可见资产仍单独保留，前述实验不会自动验证它们。没有理由重跑所有环境维修、全仓测试或引入新路径排除。若仅使用现有 reward 做范围明确的字段传递诊断，可先保留静态候选；若要宣称完整问题已解决，需处理这些覆盖限度并检查模型补丁。

协调者收口时可将 card.md:15 和 screening_record 的 reviewer pending 标记更新为“复核同意有限处置，保留上述限制”，并引用本文件；reviewer 本轮未修改它们。15422 复核到此完成，等待协调者后续安排。
