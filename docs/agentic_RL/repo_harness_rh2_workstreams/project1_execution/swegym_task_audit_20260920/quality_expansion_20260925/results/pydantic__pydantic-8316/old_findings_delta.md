# 8316 历史差异复核

本题只开放一份09-16 L1记录，root release后已读全文并核SHA。未读取旧记录所引hints_text原件、scripts/to_snake_diff.py、R2/R4或其他题；没有执行旧脚本。没有本题pilot记录可读，不能凭其他题结论补齐。

| 旧主张 | 处置 | 决定性证据与边界 |
|---|---|---|
| HTTPResponse核心缺陷、旧两个正则、新增CAMELToSnake参数与gold对应 | 确认 | 前稿完整核alias_generators.py、test.patch、参数helper；09-19noop目标字符串错误/gold PASS，和源码推演一致。 |
| to_camel第二诉求只有不可见维护者hints才能知道不应修改；实际输入错误 | 收窄/反驳其必然性 | 只读到旧记录转述hints，不证实际actor见或未见。独立公开config.py:131–159、alias_generator字段方向及原名/别名P2P已经说明HTTPResponseCode不等于原字段名或生成别名，能在公开源码内消解。check3仍unknown，范围解释归check23。 |
| 修附注必定/很可能违反P2P，建议运行按附注改to_camel的实验 | 未证具体误拒；不采用机械实验 | 没有给出具体合理候选和对应失败；现有to_camel参数确保护旧输出，但不能由模糊“按附注修”断言所有附加实现都会失败。无需为用户误解发明输入归一化新规格。 |
| 只有1个新参数，HTTPResponse原例和一般缩写未直接覆盖 | 确认并收窄 | 同类CAMELToSnake覆盖缩写边界，不能说原例因此不可验证；公开原例本身可用于开发命令。原例和一般化缺少评分保护仍是check25问题。 |
| gold把字母→数字规则收窄，小写前数字的旧17参数看不到 | 确认静态变化 | `[a-zA-Z]`变`[a-z]`是直接差异；前稿独立推演A1 a_1→a1、API2 api_2→api2，并读字段alias调用者，显示有真实输入/导出key影响路径。 |
| 旧脚本7例差异已实证且证明gold有范围外回归 | 部分确认、证据级别收窄 | 旧记录列CAMEL2/HTTP2/A1B2等输出；未获准读其脚本/输出原件，更未本轮执行。规则收窄静态可证；数字边界精确契约未明，不能把所有变化或HTTPResponse这类目标改善都判回归。check26保留具体兼容疑点；check27局部正确、完整性unknown。 |
| 任何正则/扫描只要符合输出都可以；无代码形状强制 | 确认局部 | 新参数只断言to_snake输出，不要求regex/helper名称；保旧数字规则并补缩写边界是合理非gold路线，但未实际运行，不能宣称普遍无误拒。 |
| 补两个断言后即可入 | 不继承准入 | 需先对数字边界和真实alias工作流确认，不隐式把gold的收窄变成新规格。actual actor工作树/消息/权限/依赖与模型表现未验。 |
| 旧install rc=2、只有安装需要网络 | 当前grader阻断已过时，原旧错误未复核 | 09-19 install-v1原件两次install RC0、离线wheels/deny_all、准确派生image已核；不证明actual actor开发可用。 |
| 本包唯一文件所以无重复；leak扫描0所以check29 pass；R4控制面残余 | 均收窄为未核 | 未审留出集/其他题/实际actor可见资产/网络，文件唯一性不足以证无重叠或无答案暴露；R4原件未读。审查者的私有授权暴露须单列usage。 |

前稿没有实质改判：保留缩写目标明确、附注可由公开契约消解、数字边界风险及评分覆盖窄。历史记录提供相近疑点，但其纯re实验不升级为本次或实际Pydantic实证。唯一下一步仍是任务二做窄公开API base/gold及alias模型工作流对照，并捕获actor入口事实；本次无新实验、无题目改写。


已读历史原件（仅以下路径，均核SHA）：
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8316.json` — `899c50c4a97d3407fa30fb1ab7ae844f256301540b584083e3a4f763cf7a79f9`

封存前稿SHA256：`be3f037f061cc57d96860b93edf952fc5f4a0a919acae0e55aadd335f61adf77`。前稿未改；无新项目执行。全部证据定位以本题analysis_before_history.md的PUBLIC/PRIVATE与原日志附录为准。
