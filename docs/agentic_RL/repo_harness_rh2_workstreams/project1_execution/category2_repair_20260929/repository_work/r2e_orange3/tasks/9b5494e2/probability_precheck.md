# 9b54：默认多分类概率关系校准

2026-10-03。**真实目标环境下，base与gold保持默认multinomial行为，G1的默认OvR改动被概率关系识别。** 此前未验证的 `rtol=1e-5, atol=1e-7` 可在当前iris数据上保留。它是作者私有数值校准，新隐藏材料尚未发布、正式十方尚未执行。

| 版本 | 对显式multinomial的最大概率差 | 当前关系成立 |
| --- | --- | --- |
| base | 0 | 是 |
| gold | 0 | 是 |
| G1（默认OvR） | 0.38716698009532013 | 否 |

三组都在同一cpu-c镜像中，通过真实CC执行独立Python进程，在同一iris数据上拟合两个模型，再比较150×3概率矩阵。实测 `.venv` Python3.7.9、NumPy1.17.5、SciPy1.5.4、sklearn0.22.2.post1；Orange来自 `/testbed/Orange`。gold及G1补丁的解码内容SHA、`git apply --check`与实际应用返回值已核；base模块SHA匹配原生baseline，最后G1模块SHA匹配原生FrozenPatch内容。没有抄gold概率常数。

使用第五版冻结入口及原020材料，完整已批准配方 `r2e_derive_v1+env_v2`／`512277…`，实际镜像 `481eb85…`，21项镜像检查通过。七条Bash均返回0，八次网关／桩消息一致；CC正常结束，2 CPU／4 GiB／512进程限制与完整清理已核。45份actor和实际受信输入原件逐份核SHA。没有模型推理或正式评分，合成端点的tokens与cost不是模型消耗。

[校准收据](probability_precheck_v2.json)绑定完整摘要、实际轨迹和作者核对脚本。最后保存的是私有G1单模块修改，缓存排除路径变化为true；它不是模型产出的候选。旧[组合配方拒绝](probability_precheck_v1.json)发生在CC和拟合之前，原件保留；本次不叠加sysconfig，只限Python校准，不代替最终开发环境。前三次未获槽记录见[等待回执](probability_precheck_wait_receipt.json)，随后prepare v4及actor v1均正常结束。

下一步由公共维护者发布新隐藏材料并登记精确完整组合配方，再固定最终release和镜像执行十方，核完整逐测试日志、公开开发与实际交付，进行非作者结果复核。当前校准不证明所有合理替代解或所有数据集，13键中既有两个expected FAILED仍保留，不授予训练或留出资格。
