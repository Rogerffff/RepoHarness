# Conan 包：三题静态复核完成

三题均完成公开读者、主审、独立reviewer和协调收口，21份逐题文件、9份封存初判齐全。[结构/阶段/请求配置/hash校验](pack02_output_verification.json)通过；均为needs_review/static_review，仅供development_diagnostic，actual actor和正式探针资格仍未验。5名角色均显式请求gpt-6-astra/high/fork_turns=none；详见assignments，不声称OS隔离或后端独立验真。

| 题目 | 核心结论 | 唯一优先下一步（未执行/未派发） |
| --- | --- | --- |
| [11594](results/conan-io__conan-11594/card.md) | reference-bindings-v1将短Ninja参考绑定两个完整node；历史6项真实执行不能与5个参考键混淆。gold保留多配置身份而修正默认target。测试仅查Mock命令target，未验--config或真实CMake执行；引号格式有潜在误拒风险。 | 实际actor中使用无编译语言、无外部依赖的小型Ninja Multi-Config公开recipe，观察默认test、--config Release和测试真正执行。 |
| [13230](results/conan-io__conan-13230/card.md) | 标题归因不等于另有compiler选择需求；根因是仅按build Macos进入Apple分支。F2P用Android内部属性，未验题面Linux最终flags。noop的xcrun127由错误逻辑触发，不默认要求安装SDK。 | 实际actor按公开Macos build/Linux host profiles执行generate；原例故意raise展示flags，须按异常位置和payload判断，不能机械要求rc0。 |
| [13721](results/conan-io__conan-13721/card.md) | 新验收五次install都用普通文件；核心软链接/with-context用途未测。一个旧P2P是两条恒真字符串assert，新substring也不限制名称结尾。后缀表示留白存在，但未裁定stem是完整正确解。 | 实际actor用无扩展名alpha/beta软链接共享生成器，通过公开with-context模板与CLI验证入口区分；带后缀规范另记未定，不阻断该流程。 |

历史对照按原条件有效：11594 reference_v1为1fail5pass→6pass，短Ninja合组要两个node全过；13230 baseline01/w01-1 ledger13/14为1fail34pass→35pass；13721同账本15/16为1fail6pass→7pass，noop在第一个assert停止，后四步不能记作已执行失败。主审与reviewer核过本题原ledger选中行、命令、逐项结果、投影/恢复及其边界。没有新增项目运行。

协调者采纳13721的两项复核纠正：主审delta把旧pilot归纳为完全消除后缀争议，措辞过强；原pilot明示仍需观察后缀且不把gold细节当强制规范。其实际分歧是处置优先级。协调者选择先验证无争议名字的公开开发流程，同时保留后缀留白；不会据此修改题面或把私有格式提示交solver。原delta保持提交时版本，纠正写入最终card、record的history_delta_adjudication及review.md，保留判断轨迹。

三题未发现已证gold新增回归；有限回归/替代实现未运行不构成普遍正确性证明。源镜像tag、预期digest、实际ID分别记录；缺失实际ID不填猜测。actual actor消息、准备后工作树、忽略资产、工具环境/权限和答案可见性unknown。普通gold投影恢复成功不能认证恶意候选控制面安全。check29仅记实际actor；授权私有阅读记usage。check40明确unknown，不从流程合规推导无漏检/误杀或抽样偏差。

六份主审card/record原版在收口前逐一匹配主审完成hash再归档，修改后hash及理由见[协调修订记录](coordinator_revisions/pack02_conan/revision_log.json)。初判、delta、review和所有历史原件未回改。候选清单为受限开发建议，CPU队列不为这些静态已定位的缺口机械增加私有实验；任务二仍由Claude B执行和调度。

根任务可重点抽验13721旧pilot原文及无后缀验证的边界、11594六node/五参考键与--config关系、13230原样raise的结果分类。首12题剩余Dask/Pydantic继续；储备20题保持待命。
