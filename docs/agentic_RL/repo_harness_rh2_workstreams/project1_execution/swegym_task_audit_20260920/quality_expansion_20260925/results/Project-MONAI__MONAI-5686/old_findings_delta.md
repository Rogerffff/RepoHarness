# 历史主张对照：Project-MONAI__MONAI-5686

本包三份初稿封存并明确history release后，只读refs指定L1_monai_2记录，hash匹配；未沿stage1/跨题索引/5908/summary等链接扩读，也未读reviewer。封存稿不改。

| 旧主张/字段 | 判定 | 原件理由与处理 |
|---|---|---|
| base与gold/test文件对应、原始detachment缺陷 | 确认 | P/V、loss83–90、metric69–71、历史w06-1 ledger3/4均对应 |
| 题面复现清晰、模板未填写、Expected句前半现状 | 确认内容；check3仍unknown | 计划输入足够理解；真实actor消息未捕获，不能从题面质量记check3 pass；本批public_hints存在 |
| 只修改源码、可信测试恢复不覆盖gold | 确认有限路径 | projection仅loss.py，stage/log/setup原件吻合，追加排除为空；非全控制面安全证明 |
| 5686/5908同文件同测试、后者base含本题gold，应同侧 | 未核实线索 | 来自旧记录的跨题结论，本轮不能读5908或索引。仅本题材料不足证明具体版本包含关系，交协调者保留线索，不据此认证划分 |
| F2P直接来自题面，不锁helper名 | 确认 | test_grad只验输出requires_grad；不因gold用私有入口就强制它 |
| batch>1无覆盖，只修B1可满分 | 确认静态缺口 | 全F2P/P2P为B1C1；gold有B>1第二处改动。旧文无mutant原运行，本轮也未执行，记录静态推导。B2是有意义边界，B>=3已有拼接缺陷不能计成gold新回归 |
| 加0*y.sum()可保数值并制造假梯度 | 确认机制并细化 | 输出flag变真且y.grad可能存在但恒零，仍不是正确SSIM导数；说明只验backward不报错或grad非None也不充分。非相同图像的导数行为应有区分力，但不要求所有像素梯度非零 |
| check26 pass因为8项数值测试能挡常量 | 有限确认/降为unknown | 1/0两组期望能挡统一常量，但不证明无新回归或真梯度。8项仅单通道常量2D/3D，不能将覆盖集数量作回归完备性证明 |
| check27 issue因为绕过公共API“不修根因” | 推翻该理由 | metric公开入口detach是现存评估设计，loss调用无detach纯计算可以是正确修复；私有方法名本身不决定质量，未来重写也不能反推此时错误。本轮真正的27问题来自C>1递归再次调用带detach的入口 |
| gold只过渡性、七周后5908重写 | 未核实且非决定性依据 | 没读后题，不能采用未来修复推定；当前代码已足以定位多通道残留 |
| 参数表因CUDA扩展，参考身份“条目数与含义都变” | 部分确认、纠正过度推断 | CPU 10项；CUDA分支追加test2d_4/5、test3d_4/5、test_grad_2，既有_0…_3/_0…_1顺序与含义不变。总收集增多，不等于expected已有ID失配/判分必错；固定硬件条件仍重要 |
| 两CPU梯度参数语义重复/对象复用 | 确认有限语义 | x/y原在CPU，None/cpu转移无新语义，不能计成双倍覆盖；本轮未项目导入检查对象id。无需为了读取可知的参数顺序专门跑collect-only |
| stage1解析10项无skip、安装离线、7.3s、资源足够 | 旧运行未核实，当前限定事实另记 | 本次原logs确有10项、目标2fail→2pass、8P2P双方pass、missing/skip空、deny_all、2CPU指定内存；不沿用旧耗时/当前actor或GPU资格 |
| 无下载权重/数据、CPU足以复现 | 确认公开需求 | torch合成张量，无外部资产；当前actor依赖/写权/资源仍unknown |
| “缺口不影响CPU判分正确性”、ready_for_probe | 不采纳完整性含义 | CPU能按参考打分不等于衡量真实梯度修复；flag漏检与gold公开C5残留实质影响奖励语义。本批state=needs_review/scope=static_review，不宣布probe或训练合格 |
| 拟补B2、metric回归、其它集成测试 | 部分采纳但不机械扩验 | B2是有依据覆盖候选；metric旧语义应保留，但gold不改metric。当前唯一优先步骤为B1C1/B1C5公开例的gold私有CPU对照以证实残留，优先于未发现具体需求的集成扩扫 |
| 旧costs18分钟 | 不迁移 | 本轮无工具观测成本，null |

初判核心结论保持：梯度连通性漏测（25）、gold多通道不完整（27）、未证明新增回归（26）。后阶段新增/细化：保留未核实5908关系；CUDA追加项不改变既有ID含义；补充“0*y.sum()”能骗过仅检查grad存在的弱诊断。均不改封存稿。独立review待完成。

历史唯一来源：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_2/records/Project-MONAI__MONAI-5686.json`；SHA256 `6bc79ad28feaf47b8132b9c5817d0b4b995ede80869b8395da33d5fbd8524e0d`。封存初稿SHA256 `fe1224ecb0ad89c6695635d2520ad5ef5aebfd3d42fe34421dfe98570b6644b3`。

## 封存后的编号修正（协调者提醒）

协调者在阅读封存初稿后提醒：按授权流程，私有审查者见到gold/test并不等于actor本地发生答案泄漏。采纳此区分：初稿不改；后稿check29改为unknown（实际actor可见材料未取得），审查者见过的gold/隐藏测试/旧记录只记在usage与读取范围，不计成题目质量缺陷。此修正来自协调者封存后提醒，不冒称独立review结论。独立review仍待完成。
