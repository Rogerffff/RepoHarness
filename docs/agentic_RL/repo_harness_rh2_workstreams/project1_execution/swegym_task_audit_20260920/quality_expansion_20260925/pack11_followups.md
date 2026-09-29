# pack11 后续建议（未执行、未派发）

任务二由Claude B负责。以下各为一项选择性私有CPU建议，不是模型/全池门槛。真实actor开发证据另行取得；含gold、隐藏测试和本审查结论的环境不得交给独立solver。

7894：固定x=da.ones((5,10),chunks=(5,5))，map_overlap函数lambda a:a.mean(0)[None,:]，depth=(0,1)，boundary='reflect'，drop_axis=0，new_axis=0，dtype=float。同条件base/gold对照，语义参考x.mean(0)[None,:]、shape=(1,10)，保存实际源码来源、lazy shape/chunks、同步compute值或准确异常和RC。该例没有外部资产、网络或GPU需求。若base正确而gold错误，才确认新增用户结果回归；若base也失败，撤回该新增回归方向，再决定是否转到主审的混合none边界漏接收对照，不自动追加第二项实验。

9212：A=Enum('Color',{'RED':1},module='audit_a')、B=Enum('Color',{'RED':1},module='audit_b')。同一个delayed(pure=True)函数返回type(e).__module__，对A.RED/B.RED建两任务，并一次dask.compute(left,right,scheduler='synchronous')，期望分别audit_a/audit_b。记录两参数token、两任务key、实际结果/异常、源码导入/解释器/初态及RC。module只是类型属性，此同步本地例无需导入虚构module或分布式序列化。base可区分/gold合并才将26升级；否则按实际调用图收窄假说。不另做泛化全仓、复杂value穷举或模型实验。
