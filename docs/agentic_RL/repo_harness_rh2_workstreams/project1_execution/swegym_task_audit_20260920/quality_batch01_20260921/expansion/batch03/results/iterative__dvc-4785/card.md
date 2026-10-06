# iterative__dvc-4785

base `7da3de451f1580d0c48d7f0a82b1f96ea0e91157`。HTTP(S) exists 应让401/403报错，成功为True、404为False。独立复核后保留 **needs_review / static_review**，仅development_diagnostic，暂不优先普通能力探针。

| 公开目标或旧行为 | 冻结验收与证据 | 收束判断 |
| --- | --- | --- |
| 200/404/403分离 | F2P用同一Response分别断言True/False/DVC.HTTPError | 原gold通过、noop在403失败；不保护HEAD/GET不同响应 |
| 401也报错 | 题面明确，F2P未输入401 | 具体覆盖缺口；只修403路线尚未实测 |
| HEAD方法受限时回退GET | http.py:135–139解释兼容目的 | HEAD405→GET404时base False、gold抛405是静态行为变化；有回归疑点，CPU和规格判断仍待完成 |
| 异常类型与CLI出口 | 题面建议raise_for_status；公开download/upload及CLI使用DVC异常体系 | 保留契约争议，不能称任意原生Requests路线均合理或已经误拒 |
| 认证/TLS、下载错误 | 全读8项P2P和本地server fixture | 两侧通过；不代表exists差异状态或CLI均已覆盖 |

八方面已核公开要求、精确材料/初态、完整test.patch与1F2P/8P2P、合理路线、gold与相关调用者、安装开发需求、官方恢复/投影计分、暴露及具体代码关系。实际执行9、解析9、冻结9分别一致；gold9pass/reward1，noop1fail8pass/reward0，无missing/skip。两侧setup.py都有moto pin预改，不是完全clean base。真实日志证明离线editable安装成功；grader54322、apply54321不能证明正式actor，env_qualification=absent。额外排除=[]。

协调者采用 reviewer 的唯一优先项：base/gold真实HTTPTree使用分开的HEAD/GET Response，先核405→404，以405→200及同状态200/404/401/403为控制，保存调用顺序、最终选中响应、返回/异常类。无需先造额外候选；固定grader语义诊断可独立于正式actor资格推进。运行只能确认行为，不能替代公开契约判断。HEAD404→GET403属于响应冲突，当前不设武断oracle。主审首选的原生Requests异常/CLI差分保留为次序项，分歧没有从历史稿中抹去。

全部为未执行方案，无题面/源码/tests/gold/refs/reward修订。当前镜像、正式actor、全仓回归、重复并发、实际泄漏和模型成本仍未知。原件定位与阅读边界见[封存主审](analysis_before_history.md)、[历史差异](old_findings_delta.md)、[独立初判](reviewer_initial.md)、[最终复核](review.md)和[结构化记录](screening_record.json)。审查已见私有材料及旧记录，不能用作solver。

协调者复核：独立初判与最终复核的封存关系见 [review](review.md)。3665核心helper/保存接线出现在4785公开base中，6954为演化版本；这是具体代码包含关系，尚非完整Git谱系、重复题或实际solver泄漏证明。
