# iterative__dvc-3665

目标：base `a2de48bdfbba` 的相对 cache.dir 在 Windows/Unix 保存一致。**needs_review / static_review**：题意与测试有实质争议，暂缓普通能力探针。

| 要求 | 决定性测试/证据 | 判断 |
| --- | --- | --- |
| 稳定POSIX相对缓存格式且目标位置不变 | cache relative测试保存配置后add文件；Linux noop已过 | 实际运行但不在P2P；Windows分支未测 |
| 相对/绝对路径与URL语义 | 4 F2P直接调用 `Config._to_relpath` | base无该私有方法，题面未要求；4次noop失败都是AttributeError |
| 配置与缓存旧行为 | 18 P2P已全部读，双角色通过 | 保护部分旧行为，不能证明跨平台目标 |

合理内联修复无需新增helper，可能被误拒；反过来，仅添加未接入保存链的helper可能得分。两者目前均为静态路线，未执行候选。gold使用已有PathInfo.as_posix，源码方向合理，Windows仍未验。

原件账本分开：实际33节点（gold33过，noop4失败/29过）；冻结22引用（4+18，reward1/0）；parser42键含9个捕获业务ERROR伪键，不撞引用。11个额外真实测试不自动计分。noop还保留setup.py的moto pin环境改动，不能称初态完全clean。

八方面已核公开需求、身份/补丁、全部变更断言/fixture、替代路线、相关调用者/gold、安装与恢复/投影、暴露用途；未核Windows、正式actor消息/权限/资产、跨题谱系、全仓与模型成本。原输入是dvc_install_v1c/recipes/本题.json，真实日志证实离线editable成功；COPY wheels本身不证明安装，grader成功也不代表actor资格。额外排除为空。

唯一下一步：对不新增helper的内联修复做窄Windows公开行为与冻结RH2评分对照，再决定测试修订。未自动扩大P2P或更改reward。独立 reviewer 已完成，协调者同意暂缓普通探针；已见gold/隐藏测试/旧记录，本上下文不能做solver。完整证据见 [封存](analysis_before_history.md)、[历史差异](old_findings_delta.md)、[JSON](screening_record.json)。

协调者复核：独立初判与最终复核的封存关系见 [review](review.md)。3665核心helper/保存接线出现在4785公开base中，6954为演化版本；这是具体代码包含关系，尚非完整Git谱系、重复题或实际solver泄漏证明。
