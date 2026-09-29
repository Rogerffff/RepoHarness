# Project-MONAI__MONAI-6975

静态审查 `needs_review/static_review`，仅供 `development_diagnostic`。base=`392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`。Dataset调用应保留Compose(lazy=True)设置；gold把公共apply_transform默认False改None。题意允许Dataset调用点传None的合理非gold修复。

| 需求/旧行为 | 断言/证据 | 限制 |
|---|---|---|
| Dataset保留四种组合类True | F2P日志_0–3历史全fail→pass | 只精确日志，丢弃返回值 |
| False、direct三态及旧数据流程 | 全59 P2P语义与状态已核 | 空测试、部分assertTrue不是相等比较 |
| 原题字典图像/返回数据 | 用户API调用链已查 | 新验收没有相应数据断言 |

八方面均已审查并在前稿列出精确范围：公开目标；版本/初态；全部断言/helper；非gold与漏测；公共helper及部分调用者；开发/资产/资源；可信测试恢复与源码投影；关系、私有暴露和用途。其他Dataset/底层resampling未全读，不能证明无回归。

09-19授权ledger5/6：`pytest -rA tests/test_compose.py tests/test_dataset.py`，63 collected；noop4目标日志失败/59pass，gold63pass，安装最后RC0、测试RC1→0，无skip/xfail。历史初态有依赖删除，actual image ID=null；实际actor消息、初态、图像资产/权限unknown。

关键漏测：候选可正确执行lazy并产生日志，却误返回原输入；当前四个目标断言无法发现。未证明gold有此缺陷。旧“git不跟踪图像所以离线缺文件”推断已撤回；“Dataset局部修复必须算错”扩大题意；旧Cache/Persistent行号实际为ZipDataset/NPZDictItemDataset。缺回归覆盖归25，不当26已证回归。主审出稿时未读reviewer；独立交叉复核随后完成。旧模型轨迹未读，不能宣称真实替代解已复验。

唯一优先后续：任务二在真实actor以内存字典Flipd流程比较direct/Dataset的返回图像并观察True/False/None执行模式，保存初态/导入证据。无需全仓、GPU或预置模型。additional_exclusions=[]、revision_refs=[]；gold/隐藏测试/history只留私有审查环境。


协调裁定：保留有条件静态开发候选，ready_for_probe=false；独立review已完成。check27统一为unknown，保留核心源码及历史正证据，完整性未证。日志缺返回值是实质漏测，下一步在同一实际actor公开流程联合检查Flipd返回图像和True/False/None模式；applied_operations长度不等于重采样次数。无需另设私有CPU前置，也不扩大为所有Dataset必须修改。
